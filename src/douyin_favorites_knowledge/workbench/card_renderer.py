"""Card rendering and optional PNG export with multi-theme support."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

THEMES: dict[str, dict[str, str]] = {
    "classic": {
        "name": "经典墨绿",
        "css": """
*{box-sizing:border-box}body{margin:0;background:#e9e6df;color:#232b29;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif}
main{width:760px;margin:32px auto;background:#faf8f2;border:1px solid #d8d8c9;box-shadow:0 16px 48px #26372e18;border-radius:2px}
.top{padding:40px 44px 30px;background:#223d35;color:#fff}.eyebrow{font-size:13px;letter-spacing:3px;color:#c9d9a7}
h1{font-size:34px;line-height:1.45;margin:18px 0;overflow-wrap:anywhere}.author{font-size:15px;color:#d6e0db}
.body{padding:30px 44px 38px}.summary{font-size:21px;line-height:1.8;margin:0 0 28px;white-space:pre-wrap;overflow-wrap:anywhere}
h2{font-size:14px;letter-spacing:2px;color:#5c7566;margin:28px 0 16px}ul{padding:0;list-style:none;margin:0}
li{position:relative;padding:0 0 14px 25px;font-size:18px;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere}
li:before{content:'•';position:absolute;left:3px;color:#7b9258}.actions{background:#ecefdf;padding:2px 22px 6px;border-radius:10px}
.footer{margin-top:30px;padding-top:18px;border-top:1px solid #d9dfd1;font-size:12px;line-height:1.7;color:#68756c;overflow-wrap:anywhere}
a{color:#496b59}.badge{margin-top:16px;color:#f7dcb1;font-size:13px}.note{margin-bottom:8px}
.credit{float:right;color:#8a9990}
@media(max-width:800px){main{width:calc(100% - 24px);margin:12px auto}.top,.body{padding-left:28px;padding-right:28px}}
@media print{body{background:white}main{margin:0;width:100%;box-shadow:none;border:0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
""",
    },
    "minimal": {
        "name": "极简纸白",
        "css": """
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#1e293b;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif}
main{width:760px;margin:32px auto;background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 10px 30px #0f172a0a;border-radius:8px}
.top{padding:38px 44px 28px;background:#f8fafc;border-bottom:1px solid #e2e8f0;color:#0f172a}
.eyebrow{font-size:12px;letter-spacing:2.5px;color:#64748b;font-weight:600;text-transform:uppercase}
h1{font-size:32px;line-height:1.4;margin:16px 0;color:#0f172a;overflow-wrap:anywhere}.author{font-size:14px;color:#64748b}
.body{padding:32px 44px 38px}.summary{font-size:20px;line-height:1.8;margin:0 0 28px;color:#334155;white-space:pre-wrap;overflow-wrap:anywhere}
h2{font-size:13px;letter-spacing:2px;color:#0f172a;margin:28px 0 16px;text-transform:uppercase;font-weight:700}
ul{padding:0;list-style:none;margin:0}
li{position:relative;padding:0 0 14px 24px;font-size:17px;line-height:1.75;color:#334155;white-space:pre-wrap;overflow-wrap:anywhere}
li:before{content:'—';position:absolute;left:0;color:#94a3b8}.actions{background:#f1f5f9;border:1px solid #e2e8f0;padding:4px 22px 8px;border-radius:6px}
.footer{margin-top:30px;padding-top:18px;border-top:1px solid #e2e8f0;font-size:12px;line-height:1.7;color:#64748b;overflow-wrap:anywhere}
a{color:#0284c7}.badge{margin-top:14px;color:#b45309;font-size:12px}.note{margin-bottom:8px}
.credit{float:right;color:#94a3b8}
@media(max-width:800px){main{width:calc(100% - 24px);margin:12px auto}.top,.body{padding-left:24px;padding-right:24px}}
@media print{body{background:white}main{margin:0;width:100%;box-shadow:none;border:0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
""",
    },
    "dark": {
        "name": "暗黑极客",
        "css": """
*{box-sizing:border-box}body{margin:0;background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif}
main{width:760px;margin:32px auto;background:#161b22;border:1px solid #30363d;box-shadow:0 16px 48px #00000080;border-radius:10px}
.top{padding:40px 44px 30px;background:#0d1117;border-bottom:1px solid #30363d;color:#f0f6fc}
.eyebrow{font-size:12px;letter-spacing:3px;color:#58a6ff;font-weight:600}
h1{font-size:32px;line-height:1.45;margin:18px 0;color:#f0f6fc;overflow-wrap:anywhere}.author{font-size:14px;color:#8b949e}
.body{padding:32px 44px 40px}.summary{font-size:20px;line-height:1.8;margin:0 0 28px;color:#c9d1d9;white-space:pre-wrap;overflow-wrap:anywhere}
h2{font-size:13px;letter-spacing:2px;color:#58a6ff;margin:28px 0 16px;text-transform:uppercase}
ul{padding:0;list-style:none;margin:0}
li{position:relative;padding:0 0 14px 25px;font-size:17px;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere}
li:before{content:'›';position:absolute;left:4px;font-size:22px;line-height:1;color:#58a6ff}.actions{background:#21262d;border:1px solid #30363d;padding:4px 22px 8px;border-radius:8px}
.footer{margin-top:32px;padding-top:18px;border-top:1px solid #30363d;font-size:12px;line-height:1.7;color:#8b949e;overflow-wrap:anywhere}
a{color:#58a6ff}.badge{margin-top:14px;color:#d29922;font-size:12px}.note{margin-bottom:8px}
.credit{float:right;color:#8b949e}
@media(max-width:800px){main{width:calc(100% - 24px);margin:12px auto}.top,.body{padding-left:24px;padding-right:24px}}
@media print{body{background:white;color:black}main{margin:0;width:100%;box-shadow:none;border:0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
""",
    },
    "xiaohongshu": {
        "name": "手账高赞",
        "css": """
*{box-sizing:border-box}body{margin:0;background:#fdf7f2;color:#2c2825;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif}
main{width:760px;margin:32px auto;background:#ffffff;border:1px solid #f2e2d5;box-shadow:0 18px 45px #ca7e5818;border-radius:18px;overflow:hidden}
.top{padding:42px 44px 32px;background:linear-gradient(135deg,#e85a4f,#ea6e5f);color:#fff}
.eyebrow{font-size:13px;letter-spacing:3px;color:#ffe3df;font-weight:600}
h1{font-size:32px;line-height:1.45;margin:16px 0;overflow-wrap:anywhere}.author{font-size:14px;color:#ffd9d4}
.body{padding:34px 44px 40px}.summary{font-size:20px;line-height:1.85;margin:0 0 28px;color:#3b3632;background:#fff8f3;padding:18px 22px;border-radius:12px;border-left:4px solid #e85a4f;white-space:pre-wrap;overflow-wrap:anywhere}
h2{font-size:14px;letter-spacing:1.5px;color:#e85a4f;margin:28px 0 16px;font-weight:700}
ul{padding:0;list-style:none;margin:0}
li{position:relative;padding:0 0 14px 26px;font-size:17px;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere}
li:before{content:'✦';position:absolute;left:2px;font-size:14px;color:#e85a4f}.actions{background:#fff4ee;border:1px dashed #f5cdc2;padding:6px 22px 10px;border-radius:14px}
.footer{margin-top:32px;padding-top:18px;border-top:1px solid #f4e3d7;font-size:12px;line-height:1.7;color:#8a7c73;overflow-wrap:anywhere}
a{color:#d64a3f}.badge{margin-top:16px;color:#ffe0bb;font-size:13px}.note{margin-bottom:8px}
.credit{float:right;color:#a89b91}
@media(max-width:800px){main{width:calc(100% - 24px);margin:12px auto}.top,.body{padding-left:24px;padding-right:24px}}
@media print{body{background:white}main{margin:0;width:100%;box-shadow:none;border:0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
""",
    },
}

STYLE = THEMES["classic"]["css"]


def validate_card(card: Any) -> dict[str, Any]:
    if not isinstance(card, dict):
        raise ValueError("卡片必须是 JSON 对象")
    for key, limit in (("title", 150), ("author", 150), ("summary", 1500)):
        value = card.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{key} 必须为非空文字，且不超过 {limit} 字")
    url = card.get("source_url")
    if not isinstance(url, str) or len(url) > 2000:
        raise ValueError("source_url 必须是抖音 HTTPS 链接")
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or not (host == "douyin.com" or host.endswith(".douyin.com"))
        or parsed.username
        or parsed.password
        or any(c.isspace() for c in url)
    ):
        raise ValueError("source_url 必须是抖音 HTTPS 链接")
    for key in ("points", "actions"):
        values = card.get(key)
        if not isinstance(values, list) or not 1 <= len(values) <= 12:
            raise ValueError(f"{key} 必须为包含 1–12 条文字的列表")
        if any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in values):
            raise ValueError(f"{key} 每条必须为非空文字，且不超过 500 字")
    if not isinstance(card.get("synthetic", False), bool):
        raise ValueError("synthetic 必须为 true 或 false")
    return card


def render_card(
    card: dict[str, Any],
    theme: str = "classic",
    author_credit: str | None = None,
) -> str:
    validate_card(card)
    theme_cfg = THEMES.get(theme) or THEMES["classic"]
    css = theme_cfg["css"]
    esc = lambda value: html.escape(str(value), quote=True)
    points = "".join(f"<li>{esc(v)}</li>" for v in card["points"])
    actions = "".join(f"<li>{esc(v)}</li>" for v in card["actions"])
    badge = '<div class="badge">合成演示 · 非真实视频分析</div>' if card.get("synthetic", False) else ""
    credit_html = f'<span class="credit">由 {esc(author_credit)} 整理</span>' if author_credit else ""

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<title>{esc(card["title"])}</title><style>{css}</style></head><body><main id="card">
<header class="top"><div class="eyebrow">视频知识卡片</div><h1>{esc(card["title"])}</h1><div class="author">来源作者 · {esc(card["author"])}</div>{badge}</header>
<section class="body"><p class="summary">{esc(card["summary"])}</p><h2>核心要点</h2><ul>{points}</ul>
<section class="actions"><h2>可以怎么做</h2><ul>{actions}</ul></section>
<footer class="footer"><div class="note">AI 辅助整理，请结合原视频核对。行动建议应区分原作者观点与整理者建议。{credit_html}</div>
原视频：<a href="{esc(card["source_url"])}" rel="noreferrer">{esc(card["source_url"])}</a></footer></section></main></body></html>"""


def export_card_png(html_path: Path, output_png_path: Path, browser_channel: str = "chrome") -> bool:
    """Attempt to render PNG using Playwright. Returns True if succeeded, False otherwise."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as playwright:
            channel_arg = {"channel": browser_channel} if browser_channel else {}
            try:
                browser = playwright.chromium.launch(**channel_arg)
            except Exception:
                browser = playwright.chromium.launch()

            page = browser.new_page(viewport={"width": 840, "height": 1100}, device_scale_factor=2)
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.url.startswith(("http:", "https:"))
                else route.continue_(),
            )
            page.goto(html_path.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            output_png_path.parent.mkdir(parents=True, exist_ok=True)
            page.locator("#card").screenshot(path=str(output_png_path))
            browser.close()
            return True
    except Exception:
        return False
