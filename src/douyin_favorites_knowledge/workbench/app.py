"""Local workbench orchestration with one durable task at a time."""
from __future__ import annotations

import io
import json
import fcntl
import os
import queue
import re
import secrets
import threading
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..ai_summary import check_llm_connection, summarize_item
from ..browser_collector import collect_browser_favorites, default_profile_dir, login_browser
from ..local_whisper import check_environment, transcribe
from ..siliconflow_vision import read_screen
from .card_renderer import export_card_png, render_card
from .store import ITEM_ID, Store, now, parse_note
from .url_parser import resolve_aweme_id

SOURCES = {'like', 'collection'}
KINDS = {'login', 'collect', 'transcribe', 'summarize'}
SAFE_CARD = re.compile(r'^[A-Za-z0-9_-]+\.(html|png)$')


class EventChannel:
    def __init__(self):
        self._listeners: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._listeners.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._listeners:
                self._listeners.remove(q)

    def publish(self, event_type: str, data: Any = None):
        msg = {'type': event_type, 'data': data, 'timestamp': round(time.time(), 3)}
        with self._lock:
            for q in list(self._listeners):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass


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
        self.events = EventChannel()
        self._cancel_flags: dict[str, threading.Event] = {}
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

    def get_analysis_config(self) -> dict[str, Any]:
        stored = self.store.get_setting('analysis')
        if isinstance(stored, dict):
            has_creds = bool(stored.get("api_key") or stored.get("provider") == "ollama")
            if has_creds and not stored.get("enabled"):
                stored["enabled"] = True
            return stored
        env_key = os.environ.get("SILICONFLOW_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        return {
            "enabled": bool(env_key),
            "provider": "siliconflow" if os.environ.get("SILICONFLOW_API_KEY") else "custom",
            "endpoint": "https://api.siliconflow.cn/v1/chat/completions",
            "api_key": env_key,
            "model": "Qwen/Qwen2.5-7B-Instruct",
        }

    def get_transcription_config(self) -> dict[str, Any]:
        stored = self.store.get_setting('transcription')
        if isinstance(stored, dict):
            return stored
        return {
            "engine": "local_whisper",
            "model": "medium",
        }

    def settings(self):
        ready = check_environment()
        configured = default_profile_dir().exists()
        analysis_cfg = self.get_analysis_config()
        trans_cfg = self.get_transcription_config()
        key = analysis_cfg.get("api_key", "").strip()
        masked_key = ""
        if key:
            masked_key = key[:3] + "..." + key[-4:] if len(key) > 8 else "***"
        public_analysis = {
            "configured": bool(key or analysis_cfg.get("provider") == "ollama"),
            "enabled": analysis_cfg.get("enabled", False),
            "provider": analysis_cfg.get("provider", "custom"),
            "endpoint": analysis_cfg.get("endpoint", "https://api.siliconflow.cn/v1/chat/completions"),
            "model": analysis_cfg.get("model", "Qwen/Qwen2.5-7B-Instruct"),
            "has_key": bool(key),
            "masked_key": masked_key,
        }
        return {'asr_ready': ready['ready'], 'login_configured': configured,
                'analysis_enabled': public_analysis["enabled"], 'local_only': True, 'browser_channel': 'chrome',
                'transcription': {**ready, 'engine': trans_cfg.get('engine', 'local_whisper'), 'model': trans_cfg.get('model', 'medium')},
                'analysis': public_analysis}

    def save_transcription_settings(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("设置格式不正确")
        curr = self.get_transcription_config()
        engine = str(payload.get("engine") or curr.get("engine", "local_whisper")).strip()
        model = str(payload.get("model") or curr.get("model", "medium")).strip()
        if engine not in {"local_whisper", "siliconflow"}:
            engine = "local_whisper"
        if model not in {"small", "medium", "large-v3", "FunAudioLLM/SenseVoiceSmall"}:
            model = "medium"
        self.store.set_setting('transcription', {"engine": engine, "model": model})
        return self.settings()

    def save_analysis_settings(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("设置格式不正确")
        curr = self.get_analysis_config()
        new_key = payload.get("api_key")
        key_to_save = curr.get("api_key", "") if (new_key is None or new_key == "") and curr.get("api_key") else str(new_key or "").strip()
        has_credentials = bool(key_to_save or str(payload.get("provider")) == "ollama")
        enabled = True if has_credentials else bool(payload.get("enabled", False))
        updated = {
            "enabled": enabled,
            "provider": str(payload.get("provider", "custom")),
            "endpoint": str(payload.get("endpoint", "https://api.siliconflow.cn/v1/chat/completions")).strip(),
            "api_key": key_to_save,
            "model": str(payload.get("model", "Qwen/Qwen2.5-7B-Instruct")).strip(),
        }
        self.store.set_setting('analysis', updated)
        return self.settings()

    def save_settings(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("设置格式不正确")
        if 'transcription' in payload and isinstance(payload['transcription'], dict):
            self.save_transcription_settings(payload['transcription'])
        if 'analysis' in payload and isinstance(payload['analysis'], dict):
            self.save_analysis_settings(payload['analysis'])
        elif 'endpoint' in payload:
            self.save_analysis_settings(payload)
        return self.settings()

    def test_analysis_connection(self, payload: dict) -> dict:
        curr = self.get_analysis_config()
        endpoint = str(payload.get("endpoint") or curr.get("endpoint") or "").strip()
        api_key = str(payload.get("api_key") if payload.get("api_key") is not None else curr.get("api_key") or "").strip()
        model = str(payload.get("model") or curr.get("model") or "").strip()
        return check_llm_connection(endpoint, api_key, model)

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
                           'theme': str(data.get('theme') or 'classic'),
                           'html_url': '/files/cards/' + path.name,
                           'png_url': '/files/cards/' + png.name if png.is_file() and not png.is_symlink() else None})
        return result

    def import_single_url(self, url_or_text: str, source: str = 'collection') -> dict[str, Any]:
        if source not in SOURCES:
            source = 'collection'
        aweme_id, canonical_url = resolve_aweme_id(url_or_text)
        ident = f"{source}-{aweme_id}"
        existing = self.store.item(ident)
        if existing:
            return existing

        extracted_title = '未命名视频'
        extracted_author = '未知作者'
        bracket_match = re.search(r'【(.*?)】', url_or_text)
        if bracket_match:
            snippet = bracket_match.group(1).strip()
            if snippet.endswith('的作品'):
                extracted_author = snippet[:-3].strip() or '未知作者'
            elif snippet:
                extracted_title = snippet[:150]

        item = {
            'id': ident,
            'title': extracted_title,
            'author': extracted_author,
            'source': source,
            'media_kind': 'video',
            'status': 'pending',
            'transcript': '',
            'source_url': canonical_url,
            'updated_at': now(),
            'error': '',
        }
        self.store.upsert(item, raw={'aweme_id': aweme_id, 'play_url': canonical_url})
        self.events.publish('item_imported', item)
        return item

    def export_zip(self, ids: list[str]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for ident in ids:
                if not isinstance(ident, str) or not ITEM_ID.fullmatch(ident):
                    continue
                item = self.store.item(ident) or {}
                raw_title = item.get('title') or ident
                safe_title = re.sub(r'[\s/\\:*?"<>|\x00-\x1f]', '_', raw_title)[:50].strip('._') or ident
                html_file = self.cards_dir / f"{ident}.html"
                if html_file.is_file():
                    z.writestr(f"cards/{safe_title}-{ident}.html", html_file.read_bytes())
                png_file = self.cards_dir / f"{ident}.png"
                if png_file.is_file():
                    z.writestr(f"cards/{safe_title}-{ident}.png", png_file.read_bytes())
                json_file = self.cards_dir / f"{ident}.json"
                if json_file.is_file():
                    z.writestr(f"cards/{safe_title}-{ident}.json", json_file.read_bytes())
                note_file = self.knowledge_dir / '工作台转写' / f"{ident}.md"
                if note_file.is_file():
                    z.writestr(f"notes/{safe_title}-{ident}.md", note_file.read_bytes())
                elif item.get('transcript'):
                    note_content = f"# {raw_title}\n\n### 转录\n\n{item['transcript']}\n"
                    z.writestr(f"notes/{safe_title}-{ident}.md", note_content.encode('utf-8'))
        return buf.getvalue()

    def submit(self, payload: Any):
        if not isinstance(payload, dict) or set(payload) - {'kind','source','ids','limit','theme'}:
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
        if kind in {'transcribe', 'summarize'}:
            if not ids or any(self.store.item(i) is None for i in ids):
                raise ValueError('请先同步列表，再选择要处理的视频')
        with self._guard:
            if any(j['status'] in {'queued','running'} for j in self.jobs()):
                raise RuntimeError('已有任务正在处理，请稍后再试')
            stamp = now()
            theme = str(payload.get('theme') or 'classic')
            job = {'id': secrets.token_hex(12), 'kind': kind, 'source': source, 'status': 'queued',
                   'done': 0, 'total': len(ids) if kind in {'transcribe', 'summarize'} else (limit if kind == 'collect' else 1),
                   'message': '等待处理', 'created_at': stamp, 'updated_at': stamp,
                   'payload': {'kind': kind, 'source': source, 'ids': list(dict.fromkeys(ids)), 'limit': limit, 'theme': theme}}
            self._cancel_flags[job['id']] = threading.Event()
            self.store.save_job(job)
            self._queue.put(job['id'])
            self.events.publish('job_submitted', {k: v for k, v in job.items() if k != 'payload'})
        return {k: v for k, v in job.items() if k != 'payload'}

    def cancel_job(self, ident: str) -> bool:
        with self._guard:
            job = self.store.job(ident)
            if not job or job['status'] in {'completed', 'failed', 'cancelled', 'interrupted'}:
                return False
            flag = self._cancel_flags.get(ident)
            if flag:
                flag.set()
            if job['status'] == 'queued':
                self._update_job(job, status='cancelled', message='任务已由用户手动取消')
            return True

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
        self.events.publish('job_updated', {k: v for k, v in updated.items() if k != 'payload'})
        return updated

    def run_job(self, ident):
        job = self.store.job(ident)
        if not job or job['status'] != 'queued':
            return
        flag = self._cancel_flags.get(ident)
        if flag and flag.is_set():
            return
        job = self._update_job(job, status='running', message='正在处理')
        try:
            if job['kind'] == 'login':
                self.login(timeout_seconds=300, channel='chrome', source=job['source'])
                self._update_job(job, status='completed', done=1, message='登录完成，独立窗口已关闭')
            elif job['kind'] == 'collect':
                self._collect(job)
            elif job['kind'] == 'transcribe':
                self._transcribe(job)
            elif job['kind'] == 'summarize':
                self._summarize(job)
        except Exception as exc:
            # Detailed provider errors can include signed URLs, paths or credentials.
            cause = getattr(exc, '__cause__', None)
            base_msg = f"{exc} ({cause})" if cause and str(cause) != str(exc) else str(exc)
            msg = base_msg if base_msg and not any(k in base_msg.lower() for k in ('key', 'token', 'secret', 'password')) else '任务未完成，请检查配置或服务状态'
            self._update_job(job, status='failed', message=msg[:140])
        finally:
            self._cancel_flags.pop(ident, None)

    def _collect(self, job):
        headed = os.environ.get("DY_CARD_HEADED_SYNC", "0") == "1"
        records = self.collector(max_items=job['payload']['limit'], interactive_login=False,
                                 headed=headed, channel='chrome', source=job['source'])
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
        flag = self._cancel_flags.get(job['id'])
        for index, ident in enumerate(job['payload']['ids']):
            if flag and flag.is_set():
                self._update_job(job, status='cancelled', message=f'已处理 {index}/{job["total"]} 条，用户取消了任务')
                return
            item = self.store.item(ident, private=True)
            if item is None:
                failed += 1
                continue
            raw = item.pop('_raw')
            if item['status'] == 'success' and item['transcript']:
                job = self._update_job(job, done=index + 1, message=f'已保留已有逐字稿 {index + 1}/{job["total"]} 条')
                continue
            if item['media_kind'] == 'image':
                cfg = self.get_analysis_config()
                sf_key = os.environ.get("SILICONFLOW_API_KEY", "") or (cfg.get("api_key", "") if cfg.get("provider") == "siliconflow" else "")
                if sf_key:
                    os.environ["SILICONFLOW_API_KEY"] = sf_key
                    try:
                        enriched = read_screen(raw, {"max_daily_items": 30})
                        ocr_text = enriched.get("screen_text") or ""
                        if ocr_text:
                            result = {'transcript_status': 'success', 'transcript': f"【图文画面文字识别】\n{ocr_text}"}
                        else:
                            result = {'transcript_status': 'skipped_image', 'transcript': ''}
                    except Exception:
                        result = {'transcript_status': 'skipped_image', 'transcript': ''}
                else:
                    result = {'transcript_status': 'skipped_image', 'transcript': ''}
            elif not raw.get('play_url') and not raw.get('play_urls'):
                if item['status'] == 'success':
                    result = {'transcript_status': 'success', 'transcript': item['transcript']}
                else:
                    result = {'transcript_status': 'failed', 'transcript': ''}
            else:
                self.store.upsert({**item, 'status': 'transcribing', 'error': '', 'updated_at': now()}, raw, preserve=False)
                t_cfg = self.get_transcription_config()
                engine = t_cfg.get('engine', 'local_whisper')
                model_name = t_cfg.get('model', 'medium')
                sf_key = os.environ.get("SILICONFLOW_API_KEY", "") or (
                    self.get_analysis_config().get("api_key", "")
                    if self.get_analysis_config().get("provider") == "siliconflow"
                    else ""
                )
                if engine == 'siliconflow' and sf_key:
                    os.environ["SILICONFLOW_API_KEY"] = sf_key
                    try:
                        from ..siliconflow import transcribe as sf_transcribe
                        result = sf_transcribe(raw, {'model': 'FunAudioLLM/SenseVoiceSmall', 'options': {'max_media_bytes': 512 * 1024 * 1024}})
                    except Exception:
                        result = {'transcript_status': 'failed', 'transcript': ''}
                else:
                    try:
                        result = self.transcriber(raw, {'model': model_name, 'options': {'max_media_bytes': 512 * 1024 * 1024}})
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

    def _summarize(self, job):
        cfg = self.get_analysis_config()
        has_credentials = bool(cfg.get("api_key") or cfg.get("provider") == "ollama")
        if not (cfg.get("enabled") or has_credentials):
            raise RuntimeError("AI 总结服务尚未启用或配置，请在设置中配置大模型")
        endpoint = cfg.get("endpoint", "")
        api_key = cfg.get("api_key", "")
        model = cfg.get("model", "")
        ids = job['payload']['ids']
        theme = str(job['payload'].get('theme') or 'classic')
        failed = 0
        total = len(ids)
        flag = self._cancel_flags.get(job['id'])
        for index, ident in enumerate(ids):
            if flag and flag.is_set():
                self._update_job(job, status='cancelled', message=f'已提炼 {index}/{total} 张卡片，用户取消了任务')
                return
            item = self.store.item(ident, private=True)
            if item is None:
                failed += 1
                continue
            try:
                card_data = summarize_item(
                    item,
                    endpoint=endpoint,
                    api_key=api_key,
                    model=model,
                    timeout=90,
                )
                card_data['theme'] = theme
                json_path = self.cards_dir / f"{ident}.json"
                json_path.write_text(json.dumps(card_data, ensure_ascii=False, indent=2), encoding="utf-8")
                html_str = render_card(card_data, theme=theme)
                html_path = self.cards_dir / f"{ident}.html"
                html_path.write_text(html_str, encoding="utf-8")
                png_path = self.cards_dir / f"{ident}.png"
                export_card_png(html_path, png_path, browser_channel='chrome')

                if card_data.get("title") and (item["title"] == "未命名视频" or not _meaningful_title(item["title"])):
                    self.store.upsert({**item, "title": card_data["title"]})
            except Exception:
                failed += 1
            job = self._update_job(job, done=index + 1, message=f'已提炼 {index + 1}/{total} 张卡片')
        self._update_job(job, status='completed', message=f'总结完成，{failed} 条生成失败' if failed else f'已成功提炼并生成 {total} 张知识卡片')
