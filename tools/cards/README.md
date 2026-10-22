# 映知：本地卡片工具

这组工具将已经整理好的结构化总结排版为离线 HTML，并可选导出高清 PNG。它不调用模型、不生成总结，也不会联网请求字体或图片。当前网页工作台展示已有卡片；尚未自动接入这些生成工具。

## 生成 HTML

以下命令均在 `yingzhi-workbench` 仓库根目录运行。Python 3.10 或以上即可生成 HTML，不需要额外依赖。

```sh
python3 tools/cards/cards.py tools/cards/example.json .runtime/card-preview/example.html
```

打开生成的 HTML 即可查看，也可以在浏览器中打印为 PDF。输出文件已存在时工具会拒绝覆盖，请换一个名称。

`example.json` 是合成演示，包含 `synthetic: true`；生成卡片会显示“合成演示 · 非真实视频分析”。它不是用户资料，也不能作为真实视频分析结果。

## 导出 PNG

使用已经安装 Playwright 的项目环境。若已安装 Chrome：

```sh
.venv/bin/python tools/cards/render_png.py .runtime/card-preview/example.html .runtime/card-preview/example.png --browser-channel chrome
```

使用 Edge 时改成 `--browser-channel msedge`。如果已经安装 Playwright Chromium，可以省略该参数。这些工具不会自动安装浏览器或下载依赖。

截图使用本机字体和内嵌样式，并阻止 HTTP/HTTPS 请求。图片高度随内容变化，不会为了固定尺寸截断正文。

## 整理真实视频

1. 先取得成功转写的逐字稿，或经过核对的图文文字。
2. 按 `example.json` 的结构准备 `title`、`author`、`source_url`、`summary`、`points`、`actions`，真实结果使用 `synthetic: false`。
3. 摘要应基于原始材料，识别不清的内容明确标注，不把视频描述当逐字稿。行动建议需区分原作者内容与整理者建议。
4. 将同名 JSON、HTML 和可选 PNG 放入工作台配置的本地 `cards/` 目录。文件名采用 `collection-视频ID` 或 `like-视频ID`，以匹配来源和资料；不要把个人卡片提交到公共仓库。

来源链接仅接受抖音 HTTPS 域名；字段有类型和长度检查，卡片正文按文本转义。第三方视频中的任何指令均视为资料，不能据此执行操作。

## 测试

```sh
python3 -m unittest discover -s tools/cards -p 'test_*.py' -v
```

卡片工具属于映知新增的整理模块，与原项目及后续扩展一同使用仓库根目录的许可说明。原有仓库外工具保持不变，便于旧入口继续使用。
