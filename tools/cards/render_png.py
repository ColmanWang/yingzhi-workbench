"""Optional PNG export using the project's already installed Playwright."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="把本地 HTML 卡片导出为 PNG（需要 Playwright Chromium）")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--browser-channel", choices=("chrome", "msedge"),
                        help="使用已安装的 Chrome 或 Edge，省去下载 Chromium")
    args = parser.parse_args()
    if not args.input.is_file() or args.input.suffix.lower() != ".html":
        parser.error("输入必须是已有的本地 HTML 文件")
    if args.output.exists():
        parser.error("输出文件已存在，请更换名称")
    try:
        from playwright.sync_api import Error, sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=args.browser_channel)
            page = browser.new_page(viewport={"width": 840, "height": 1100}, device_scale_factor=2)
            page.route("**/*", lambda route: route.abort() if route.request.url.startswith(("http:", "https:")) else route.continue_())
            page.goto(args.input.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            page.locator("#card").screenshot(path=str(args.output))
            browser.close()
    except ImportError:
        parser.exit(1, "请使用已安装 Playwright 的项目 Python 运行；此脚本不会自动下载依赖。\n")
    except (Error, OSError) as exc:
        parser.exit(1, "图片导出失败：%s\n" % exc)
    print("图片已生成：%s" % args.output.resolve())


if __name__ == "__main__":
    main()
