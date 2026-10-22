"""Private local catalog. Public views never include signed media addresses."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ITEM_ID = re.compile(r'^(collection|like)-([0-9]{6,30})$')


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Store:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        self.path = root / 'catalog.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY, title TEXT, author TEXT, source TEXT,
                    media_kind TEXT, status TEXT, transcript TEXT, source_url TEXT,
                    updated_at TEXT, error TEXT, raw TEXT);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, kind TEXT, source TEXT, status TEXT,
                    done INTEGER, total INTEGER, message TEXT, created_at TEXT,
                    updated_at TEXT, payload TEXT);
            ''')
            db.execute("UPDATE jobs SET status='interrupted', message='上次任务被中断，可重新发起', updated_at=? WHERE status IN ('queued','running')", (now(),))
            db.execute("UPDATE items SET status='interrupted', error='上次转写被中断' WHERE status='transcribing'")
        self.path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def items(self, source: str = 'all') -> list[dict]:
        with self.connect() as db:
            rows = db.execute('SELECT * FROM items' + ('' if source == 'all' else ' WHERE source=?') + ' ORDER BY updated_at DESC,id DESC', () if source == 'all' else (source,)).fetchall()
        return [{k: row[k] for k in row.keys() if k != 'raw'} for row in rows]

    def item(self, ident: str, private: bool = False) -> dict | None:
        with self.connect() as db:
            row = db.execute('SELECT * FROM items WHERE id=?', (ident,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        raw = result.pop('raw')
        if private:
            result['_raw'] = json.loads(raw or '{}')
        return result

    def upsert(self, item: dict, raw: dict | None = None, preserve: bool = True) -> None:
        previous = self.item(item['id'], private=True)
        if previous and preserve:
            item = {**item, **{k: previous[k] for k in ('status', 'transcript', 'error')}}
        payload = raw if raw is not None else (previous or {}).get('_raw', {})
        fields = ('id','title','author','source','media_kind','status','transcript','source_url','updated_at','error')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?)', tuple(item.get(k, '') for k in fields) + (json.dumps(payload, ensure_ascii=False),))

    def jobs(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute('SELECT * FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT 100').fetchall()
        return [{k: row[k] for k in row.keys() if k != 'payload'} for row in rows]

    def job(self, ident: str) -> dict | None:
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (ident,)).fetchone()
        if row is None:
            return None
        return {**dict(row), 'payload': json.loads(row['payload'])}

    def save_job(self, job: dict) -> None:
        fields = ('id','kind','source','status','done','total','message','created_at','updated_at')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)', tuple(job[k] for k in fields) + (json.dumps(job['payload']),))


def parse_note(path: Path) -> dict | None:
    match = ITEM_ID.fullmatch(path.stem)
    if not match or path.is_symlink() or path.stat().st_size > 10_000_000:
        return None
    text = path.read_text(encoding='utf-8')
    header = text.split('---', 2)[1] if text.startswith('---\n') else ''
    def field(name: str) -> str:
        found = re.search(r'^' + re.escape(name) + r':\s*(.*?)\s*$', header, re.M)
        value = found.group(1).strip() if found else ''
        if value.startswith('"'):
            try:
                return str(json.loads(value))
            except ValueError:
                pass
        return value.strip("'\"")
    title = re.search(r'^# (.+)$', text, re.M)
    transcript = ''
    for marker in ('### 转录', '## 原始本地转写（含识别错误）'):
        if marker in text:
            transcript = re.split(r'\n#{1,3} ', text.split(marker, 1)[1].strip(), 1)[0].strip()
            break
    status = field('transcript_status') or 'pending'
    if status != 'success':
        transcript = ''
    return {'id': path.stem, 'title': field('title') or (title.group(1) if title else '未命名视频'),
            'author': field('author') or _author_from_body(text), 'source': match[1],
            'media_kind': 'image' if status == 'skipped_image' else 'video', 'status': status,
            'transcript': transcript, 'source_url': f'https://www.douyin.com/video/{match[2]}',
            'updated_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec='seconds'), 'error': ''}


def _author_from_body(text: str) -> str:
    match = re.search(r'^作者：(.+)$', text, re.M)
    return match[1] if match else '未知作者'
