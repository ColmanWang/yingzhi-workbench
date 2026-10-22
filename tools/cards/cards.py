"""Turn Codex-written summaries into local HTML cards; no model or network calls."""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlsplit


def validate_card(card):
    if not isinstance(card, dict):
        raise ValueError("卡片必须是 JSON 对象")
    for key, limit in (("title", 150), ("author", 150), ("summary", 1500)):
        value = card.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError("%s 必须为非空文字，且不超过 %s 字" % (key, limit))
    url = card.get("source_url")
    if not isinstance(url, str) or len(url) > 2000:
        raise ValueError("source_url 必须是抖音 HTTPS 链接")
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or not (host == "douyin.com" or host.endswith(".douyin.com"))
            or parsed.username or parsed.password or any(c.isspace() for c in url)):
        raise ValueError("source_url 必须是抖音 HTTPS 链接")
    for key in ("points", "actions"):
        values = card.get(key)
        if not isinstance(values, list) or not 1 <= len(values) <= 12:
            raise ValueError("%s 必须为包含 1–12 条文字的列表" % key)
        if any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in values):
            raise ValueError("%s 每条必须为非空文字，且不超过 500 字" % key)
    if not isinstance(card.get("synthetic", False), bool):
        raise ValueError("synthetic 必须为 true 或 false")
    return card


STYLE = """
*{box-sizing:border-box}body{margin:0;background:#e9e6df;color:#232b29;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif}
main{width:760px;margin:32px auto;background:#faf8f2;border:1px solid #d8d8c9;box-shadow:0 16px 48px #26372e18}
.top{padding:40px 44px 30px;background:#223d35;color:#fff}.eyebrow{font-size:13px;letter-spacing:3px;color:#c9d9a7}
h1{font-size:34px;line-height:1.45;margin:18px 0;overflow-wrap:anywhere}.author{font-size:15px;color:#d6e0db}
.body{padding:30px 44px 38px}.summary{font-size:21px;line-height:1.8;margin:0 0 28px;white-space:pre-wrap;overflow-wrap:anywhere}
h2{font-size:14px;letter-spacing:2px;color:#5c7566;margin:28px 0 16px}ul{padding:0;list-style:none;margin:0}
li{position:relative;padding:0 0 14px 25px;font-size:18px;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere}
li:before{content:'•';position:absolute;left:3px;color:#7b9258}.actions{background:#ecefdf;padding:2px 22px 6px;border-radius:10px}
.footer{margin-top:30px;padding-top:18px;border-top:1px solid #d9dfd1;font-size:12px;line-height:1.7;color:#68756c;overflow-wrap:anywhere}
a{color:#496b59}.badge{margin-top:16px;color:#f7dcb1;font-size:13px}.note{margin-bottom:8px}
@media(max-width:800px){main{width:calc(100% - 24px);margin:12px auto}.top,.body{padding-left:28px;padding-right:28px}}
@media print{body{background:white}main{margin:0;width:100%;box-shadow:none;border:0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def render_card(card):
    validate_card(card)
    esc = lambda value: html.escape(value, quote=True)
    points = "".join("<li>%s</li>" % esc(v) for v in card["points"])
    actions = "".join("<li>%s</li>" % esc(v) for v in card["actions"])
    badge = '<div class="badge">合成演示 · 非真实视频分析</div>' if card.get("synthetic", False) else ""
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<title>%s</title><style>%s</style></head><body><main id="card">
<header class="top"><div class="eyebrow">视频知识卡片</div><h1>%s</h1><div class="author">来源作者 · %s</div>%s</header>
<section class="body"><p class="summary">%s</p><h2>核心要点</h2><ul>%s</ul>
<section class="actions"><h2>可以怎么做</h2><ul>%s</ul></section>
<footer class="footer"><div class="note">AI 辅助整理，请结合原视频核对。行动建议应区分原作者观点与整理者建议。</div>
原视频：<a href="%s" rel="noreferrer">%s</a></footer></section></main></body></html>""" % (
        esc(card["title"]), STYLE, esc(card["title"]), esc(card["author"]), badge,
        esc(card["summary"]), points, actions, esc(card["source_url"]), esc(card["source_url"]))


def main():
    parser = argparse.ArgumentParser(description="将 Codex 整理的 JSON 导出为本地知识卡片")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 1_000_000:
            raise ValueError("输入文件不能超过 1 MB")
        output = render_card(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(output)
    except (OSError, ValueError) as exc:
        parser.exit(1, "导出失败：%s\n" % exc)
    print("卡片已生成：%s" % args.output.resolve())


if __name__ == "__main__":
    main()
