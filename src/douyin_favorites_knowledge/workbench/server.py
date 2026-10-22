"""Loopback-only HTTP boundary with same-origin, token and path checks."""
from __future__ import annotations

import json
from collections import deque
import mimetypes
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .app import SAFE_CARD, Workbench

MAX_BODY = 32_768


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(app: Workbench, static_dir: Path, port: int = 8765):
    rate_lock = threading.Lock()
    requests = {'GET': deque(), 'POST': deque()}

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def _rate_allowed(self, method):
            with rate_lock:
                stamp = time.monotonic()
                bucket = requests[method]
                while bucket and stamp - bucket[0] > 60:
                    bucket.popleft()
                if len(bucket) >= (300 if method == 'GET' else 30):
                    return False
                bucket.append(stamp)
                return True

        def log_message(self, *args):
            # Avoid logging paths, user content or query parameters.
            pass

        def _json(self, status, data=None, error=None):
            payload = {'success': error is None, **({'data': data} if error is None else {'error': {'message': error}})}
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers(); self.wfile.write(body)

        def _same_origin(self):
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed:
                return False
            origin = self.headers.get('Origin')
            if origin is not None and origin not in {'http://' + h for h in allowed}:
                return False
            fetch_site = self.headers.get('Sec-Fetch-Site')
            return fetch_site not in {'cross-site'}

        def do_GET(self):
            if not self._rate_allowed('GET'):
                return self._json(429, error='请求过于频繁，请稍后再试')
            if not self._same_origin():
                return self._json(403, error='仅允许本机工作台访问')
            parts = urlsplit(self.path)
            path = unquote(parts.path)
            try:
                if path == '/api/bootstrap':
                    return self._json(200, app.bootstrap())
                if path == '/api/items':
                    source = parse_qs(parts.query).get('source', ['all'])[0]
                    return self._json(200, app.items(source))
                if path == '/api/jobs':
                    return self._json(200, app.jobs())
                if path == '/api/cards':
                    return self._json(200, app.cards())
                if path.startswith('/api/items/'):
                    item = app.item(path.removeprefix('/api/items/'))
                    return self._json(200, item) if item else self._json(404, error='未找到视频')
                if path.startswith('/files/cards/'):
                    name = path.removeprefix('/files/cards/')
                    if not SAFE_CARD.fullmatch(name):
                        return self._json(404, error='未找到文件')
                    return self._file(app.cards_dir, name, card=True)
                if path.startswith('/api/') or path.startswith('/files/'):
                    return self._json(404, error='未找到内容')
                name = path.lstrip('/') or 'index.html'
                if '..' in Path(name).parts or '\\' in name:
                    return self._json(404, error='未找到文件')
                return self._file(static_dir, name)
            except ValueError:
                return self._json(400, error='请求参数不正确')
            except Exception:
                return self._json(500, error='暂时无法读取内容，请重试')

        def _file(self, root, name, card=False):
            root = root.resolve()
            target = root / name
            if target.is_symlink() or root not in target.resolve().parents or not target.is_file():
                return self._json(404, error='未找到文件')
            # Reject symlinked parents as well as symlink files.
            if any(p.is_symlink() for p in [target, *target.parents] if p != root and root in p.parents):
                return self._json(404, error='未找到文件')
            if target.stat().st_size > 32 * 1024 * 1024:
                return self._json(413, error='文件过大')
            data = target.read_bytes()
            self.send_response(200)
            kind = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            self.send_header('Content-Type', kind + ('; charset=utf-8' if kind.startswith('text/') else ''))
            self.send_header('Content-Length', str(len(data)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Cache-Control', 'no-store')
            csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
            if card:
                csp = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
            self.send_header('Content-Security-Policy', csp)
            self.end_headers(); self.wfile.write(data)

        def do_POST(self):
            if not self._rate_allowed('POST'):
                return self._json(429, error='操作过于频繁，请稍后再试')
            token = self.headers.get('X-CSRF-Token', '').encode('utf-8')
            if not self._same_origin() or not secrets.compare_digest(token, app.csrf_token.encode('utf-8')):
                return self._json(403, error='安全校验失败，请刷新工作台')
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                return self._json(415, error='需要 JSON 请求')
            path = urlsplit(self.path).path
            if path != '/api/jobs':
                return self._json(404, error='未找到操作')
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_BODY:
                    return self._json(413, error='请求体大小不正确')
                data = json.loads(self.rfile.read(size))
                return self._json(202, app.submit(data))
            except (ValueError, TypeError):
                return self._json(400, error='任务参数不正确')
            except RuntimeError:
                return self._json(409, error='已有任务正在处理，请稍后再试')
            except Exception:
                return self._json(500, error='无法创建任务，请重试')

    return LocalServer(('127.0.0.1', port), Handler)
