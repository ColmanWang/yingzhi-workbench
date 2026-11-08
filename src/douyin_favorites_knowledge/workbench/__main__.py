from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from .app import Workbench
from .server import make_server


def main():
    if sys.version_info < (3, 10):
        sys.exit(
            f"错误：映知工作台需要 Python 3.10 或更高版本（当前版本为 {sys.version.split()[0]}）。\n"
            "建议使用 Python 3.12 并在虚拟环境中运行：\n"
            "  uv venv --python 3.12 .venv\n"
        )
    parser = argparse.ArgumentParser(description='启动本地抖音知识工作台')
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--knowledge-dir', type=Path, required=True)
    parser.add_argument('--cards-dir', type=Path, required=True)
    parser.add_argument('--static-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('端口必须为 1 到 65535')
    try:
        app = Workbench(args.data_dir, args.knowledge_dir, args.cards_dir)
    except RuntimeError:
        print('工作台已在运行，请使用已打开的网页。', flush=True)
        if args.open_browser:
            webbrowser.open(f'http://127.0.0.1:{args.port}')
        return
    try:
        server = make_server(app, args.static_dir, args.port)
    except OSError:
        app.close()
        parser.exit(1, '端口已被占用，请关闭另一个服务或设置 DY_CARD_PORT。\n')
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'工作台已启动：{url}', flush=True)
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close(); app.close()


if __name__ == '__main__':
    main()
