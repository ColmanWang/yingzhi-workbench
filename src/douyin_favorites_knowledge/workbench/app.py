"""Local workbench orchestration with one durable task at a time."""
from __future__ import annotations

import json
import fcntl
import os
import queue
import re
import secrets
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..browser_collector import collect_browser_favorites, default_profile_dir, login_browser
from ..local_whisper import check_environment, transcribe
from .store import ITEM_ID, Store, now, parse_note

SOURCES = {'like', 'collection'}
KINDS = {'login', 'collect', 'transcribe'}
SAFE_CARD = re.compile(r'^[A-Za-z0-9_-]+\.(html|png)$')


def _meaningful_title(value: str) -> bool:
    return bool(value.strip()) and value.strip() != '未命名视频' and not re.fullmatch(r'Douyin favorite \d+', value.strip(), re.I)


class Workbench:
    def __init__(self, data_dir: Path, knowledge_dir: Path, cards_dir: Path, *, start_worker: bool = True):
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock_file = (data_dir / 'workbench.lock').open('a+')
        os.chmod(data_dir / 'workbench.lock', 0o600)
        try:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._lock_file.close()
            raise RuntimeError('工作台已在运行，请使用已打开的窗口') from exc
        self.store = Store(data_dir)
        self.knowledge_dir = knowledge_dir
        self.cards_dir = cards_dir
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        self.csrf_token = secrets.token_urlsafe(32)
        self.collector = collect_browser_favorites
        self.transcriber = transcribe
        self.login = login_browser
        self._guard = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        self._closed = False
        self.import_notes()
        self._thread = None
        if start_worker:
            self._thread = threading.Thread(target=self._worker, daemon=True, name='workbench-tasks')
            self._thread.start()

    def close(self):
        self._closed = True
        self._queue.put(None)
        if self._thread is None or not self._thread.is_alive():
            self._release_lock()

    def _release_lock(self):
        if not self._lock_file.closed:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            self._lock_file.close()

    def import_notes(self):
        for path in self.knowledge_dir.rglob('*.md'):
            try:
                item = parse_note(path)
                if not item:
                    continue
                existing = self.store.item(item['id'])
                if existing is None:
                    self.store.upsert(item)
                elif _meaningful_title(item['title']) and (path.parent == self.knowledge_dir or not _meaningful_title(existing['title'])):
                    # Existing source notes retain their curated titles after a list refresh.
                    self.store.upsert({**existing, 'title': item['title']})
            except (OSError, ValueError):
                continue

    def items(self, source='all'):
        if source not in SOURCES | {'all'}:
            raise ValueError('来源必须为收藏或喜欢')
        return self.store.items(source)

    def item(self, ident):
        return self.store.item(ident) if ITEM_ID.fullmatch(ident) else None

    def jobs(self):
        return self.store.jobs()

    def settings(self):
        ready = check_environment()
        # Profile existence is not proof of authentication; UI must keep that distinction.
        configured = default_profile_dir().exists()
        return {'asr_ready': ready['ready'], 'login_configured': configured,
                'analysis_enabled': False, 'local_only': True, 'browser_channel': 'chrome',
                'transcription': {**ready, 'model': 'small'}, 'analysis': {'configured': False}}

    def bootstrap(self):
        return {'items': self.items(), 'jobs': self.jobs(), 'cards': self.cards(),
                'settings': self.settings(), 'csrf_token': self.csrf_token}

    def cards(self):
        result = []
        for path in sorted(self.cards_dir.glob('*.html')):
            if path.is_symlink() or not SAFE_CARD.fullmatch(path.name):
                continue
            metadata = path.with_suffix('.json')
            try:
                data = json.loads(metadata.read_text()) if metadata.is_file() and not metadata.is_symlink() and metadata.stat().st_size < 1_000_000 else {}
            except (OSError, ValueError):
                data = {}
            if not isinstance(data, dict):
                data = {}
            if data.get('synthetic'):
                continue
            stem = path.stem
            source = 'like' if stem.startswith('like-') else 'collection'
            ident = stem if ITEM_ID.fullmatch(stem) else f'{source}-{stem}'
            png = path.with_suffix('.png')
            result.append({'id': stem, 'item_id': ident, 'title': str(data.get('title') or '知识卡片'),
                           'author': str(data.get('author') or ''), 'source': source,
                           'html_url': '/files/cards/' + path.name,
                           'png_url': '/files/cards/' + png.name if png.is_file() and not png.is_symlink() else None})
        return result

    def submit(self, payload: Any):
        if not isinstance(payload, dict) or set(payload) - {'kind','source','ids','limit'}:
            raise ValueError('任务参数不正确')
        kind, source = payload.get('kind'), payload.get('source')
        if not isinstance(kind, str) or not isinstance(source, str) or kind not in KINDS or source not in SOURCES:
            raise ValueError('任务类型或来源不正确')
        limit = payload.get('limit', 3)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError('单次同步条数必须为 1 到 100')
        ids = payload.get('ids', [])
        if not isinstance(ids, list) or len(ids) > 100 or any(not isinstance(i, str) or not ITEM_ID.fullmatch(i) or not i.startswith(source + '-') for i in ids):
            raise ValueError('请选择同一来源的视频')
        ids = list(dict.fromkeys(ids))
        if kind == 'transcribe':
            if not ids or any(self.store.item(i) is None for i in ids):
                raise ValueError('请先同步列表，再选择要转写的视频')
        with self._guard:
            if any(j['status'] in {'queued','running'} for j in self.jobs()):
                raise RuntimeError('已有任务正在处理，请稍后再试')
            stamp = now()
            job = {'id': secrets.token_hex(12), 'kind': kind, 'source': source, 'status': 'queued',
                   'done': 0, 'total': len(ids) if kind == 'transcribe' else (limit if kind == 'collect' else 1),
                   'message': '等待处理', 'created_at': stamp, 'updated_at': stamp,
                   'payload': {'kind': kind, 'source': source, 'ids': list(dict.fromkeys(ids)), 'limit': limit}}
            self.store.save_job(job)
            self._queue.put(job['id'])
        return {k: v for k, v in job.items() if k != 'payload'}

    def _worker(self):
        try:
            while not self._closed:
                ident = self._queue.get()
                if ident is None:
                    break
                self.run_job(ident)
        finally:
            self._release_lock()

    def _update_job(self, job, **changes):
        updated = {**job, **changes, 'updated_at': now()}
        self.store.save_job(updated)
        return updated

    def run_job(self, ident):
        job = self.store.job(ident)
        if not job or job['status'] != 'queued':
            return
        job = self._update_job(job, status='running', message='正在处理')
        try:
            if job['kind'] == 'login':
                self.login(timeout_seconds=300, channel='chrome', source=job['source'])
                self._update_job(job, status='completed', done=1, message='登录完成，独立窗口已关闭')
            elif job['kind'] == 'collect':
                self._collect(job)
            else:
                self._transcribe(job)
        except Exception:
            # Detailed provider errors can include signed URLs, paths or credentials.
            self._update_job(job, status='failed', message='任务未完成，请检查登录状态或本地转写环境后重试')

    def _collect(self, job):
        records = self.collector(max_items=job['payload']['limit'], interactive_login=False,
                                 headed=False, channel='chrome', source=job['source'])
        for raw in records:
            aweme_id = str(raw.get('aweme_id', ''))
            ident = job['source'] + '-' + aweme_id
            if not ITEM_ID.fullmatch(ident):
                continue
            description = str(raw.get('description') or raw.get('title') or '').strip()
            existing = self.store.item(ident)
            title = existing['title'] if existing and _meaningful_title(existing['title']) else description[:200]
            if not _meaningful_title(title):
                title = '未命名视频'
            media = 'image' if raw.get('media_kind') == 'image' or raw.get('image_count', 0) else 'video'
            self.store.upsert({'id': ident, 'title': title,
                               'author': str(raw.get('author') or '未知作者'), 'source': job['source'],
                               'media_kind': media, 'status': 'skipped_image' if media == 'image' else 'pending',
                               'transcript': '', 'source_url': f'https://www.douyin.com/video/{aweme_id}',
                               'updated_at': now(), 'error': ''}, raw=raw)
        self._update_job(job, status='completed', done=len(records), total=len(records), message=f'已同步 {len(records)} 条，语音转写需另行选择')

    def _transcribe(self, job):
        failed = 0
        for index, ident in enumerate(job['payload']['ids']):
            item = self.store.item(ident, private=True)
            if item is None:
                failed += 1
                continue
            raw = item.pop('_raw')
            if item['status'] == 'success' and item['transcript']:
                job = self._update_job(job, done=index + 1, message=f'已保留已有逐字稿 {index + 1}/{job["total"]} 条')
                continue
            if item['media_kind'] == 'image':
                result = {'transcript_status': 'skipped_image', 'transcript': ''}
            elif not raw.get('play_url') and not raw.get('play_urls'):
                if item['status'] == 'success':
                    result = {'transcript_status': 'success', 'transcript': item['transcript']}
                else:
                    result = {'transcript_status': 'failed', 'transcript': ''}
            else:
                self.store.upsert({**item, 'status': 'transcribing', 'error': '', 'updated_at': now()}, raw, preserve=False)
                try:
                    result = self.transcriber(raw, {'model': 'small', 'options': {'max_media_bytes': 512 * 1024 * 1024}})
                except Exception:
                    result = {'transcript_status': 'failed', 'transcript': ''}
            status = result.get('transcript_status', 'failed')
            status = status if status in {'success','skipped_image','no_speech','unavailable'} else 'failed'
            if status in {'no_speech','unavailable','failed'}:
                failed += 1
            transcript = str(result.get('transcript') or '') if status == 'success' else ''
            updated = {**item, 'status': status, 'transcript': transcript, 'updated_at': now(),
                       'error': '未识别到可用语音' if status in {'no_speech','unavailable'} else ('转写失败，可重新同步列表后重试' if status == 'failed' else '')}
            self.store.upsert(updated, raw, preserve=False)
            self._write_note(updated)
            job = self._update_job(job, done=index + 1, message=f'已处理 {index + 1}/{job["total"]} 条')
        self._update_job(job, status='completed', message=f'转写结束，{failed} 条未获得可用语音' if failed else '本地转写完成，可阅读逐字稿')

    def _write_note(self, item):
        # Workbench owns only this subdirectory; existing hand-edited notes stay intact.
        directory = self.knowledge_dir / '工作台转写'
        directory.mkdir(exist_ok=True)
        text = '---\n' + '\n'.join(f'{k}: {json.dumps(item[k], ensure_ascii=False)}' for k in ('title','author','source','source_url'))
        text += '\ntranscript_status: ' + item['status'] + '\n---\n\n# ' + item['title'] + '\n\n### 转录\n\n' + item['transcript'] + '\n'
        target = directory / (item['id'] + '.md')
        temporary = target.with_suffix('.tmp')
        temporary.write_text(text, encoding='utf-8')
        temporary.replace(target)
