# 映知 · Yingzhi Workbench

> [!IMPORTANT]
> **免责与合规声明**：本项目仅供个人离线学习、研究及编程技术交流使用，严禁用于任何商业营利、批量搬运洗稿或违规爬虫。使用本项目前请务必阅读并遵守 [免责声明与开源准则 (DISCLAIMER.md)](DISCLAIMER.md)。因使用本工具导致的任何账号风险或法律纠纷，由使用者自行承担。

本地优先的视频知识工作台：在浏览器中整理抖音收藏与喜欢，将视频语音转成可回看的文字，并通过大模型自动提炼为排版精美的知识卡片。

映知基于 [tars1230/douyin-favorites-to-knowledge](https://github.com/tars1230/douyin-favorites-to-knowledge) 开发，现作为独立项目维护。保留上游提交历史、CLI 兼容入口与 MIT 许可证。

## 当前可以做什么

- **列表同步与单条录入**：分别同步自己账号的收藏、喜欢列表，亦支持粘贴单条抖音链接/分享口令直接解析导入。
- **高精准度语音转写**：采用本地 Whisper（默认推荐 `medium` 高精模型，针对中文普通话、标点符号与防 BGM 串扰专项优化）或一键切换云端 SenseVoice 极速高精引擎。
- **AI 智能提炼与卡片生成**：接入主流大模型（DeepSeek 官方 API、硅基流动 SiliconFlow、本地离线 Ollama、自定义 OpenAI 兼容接口），将逐字稿结构化提炼为核心观点、金句与行动建议。
- **多主题卡片与批量导出**：内置 4 套精美设计卡片排版主题，支持卡片预览、单张下载以及按批次一键导出 ZIP 压缩包。
- **可视化任务中心**：支持任务实时进度追踪（基于 SSE）、运行中任务主动取消与崩溃中断自动识别。
- **严格本地单机与安全防护**：服务严格绑定本机回环地址（`127.0.0.1`），拒绝任何跨站与非本机访问，敏感凭据全链路脱敏，个人数据完全留在本地。

## 安装与启动

当前工作台面向 macOS，需 Python 3.10+、Node.js 22.12+、uv 和 Chrome。建议 Python 3.12。

```sh
git clone https://github.com/ColmanWang/yingzhi-workbench.git
cd yingzhi-workbench
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python ./vendor/wheels/douyin_knowledge_core-0.2.1-py3-none-any.whl
uv pip install --python .venv/bin/python '.[local-asr]' imageio-ffmpeg
cd web
npm ci
npm run build
cd ..
./scripts/workbench.sh
```

以后双击仓库中的 `启动工作台.command` 即可打开 `http://127.0.0.1:8765`。请保持启动终端运行；关闭服务后页面将无法执行操作。

启动不会采集视频或下载语音模型。首次转写需要下载 Whisper small（约 500 MB），占用本机 CPU 与磁盘，无转写 API 费用。原有 Python 包与命令名暂时保留 `douyin-favorites-to-knowledge` / `douyin-favorites-knowledge`，避免破坏已有 CLI 和配置兼容性。

## 数据存放

程序代码与个人数据分开。默认个人数据在 `.runtime/workspace/`；设置 `DY_CARD_HOME` 可以复用已有工作目录中的 `.runtime/`、`knowledge/`、`cards/`。登录资料、模型、数据库、真实笔记和卡片不应上传公开仓库。

```text
src/douyin_favorites_knowledge/  采集、转写与本地服务
web/                           React 工作台界面
tools/cards/                   JSON → HTML / PNG 卡片工具及合成样例
tests/                         单元和集成测试
scripts/                       启动脚本
docs/                          使用、开发与来源说明
vendor/wheels/                 保留许可证的固定版本共享核心包
.runtime/                      本地运行数据，不入库
```

使用顺序：连接抖音 → 同步列表 → 勾选视频 → 本地转写 → 阅读逐字稿。图文需要额外 OCR，当前不会将背景音乐误当成正文。

## 文档

- [免责声明与开源准则 (DISCLAIMER.md)](DISCLAIMER.md)
- [工作台使用与开发](docs/WORKBENCH.md)
- [卡片工具](tools/cards/README.md)
- [来源与许可证](docs/ATTRIBUTION.md)
- [历史 CLI 参考](docs/CLI_REFERENCE.md)
- [第一版验收](docs/WORKBENCH_ACCEPTANCE.md)

## 验证

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s tools/cards -v
cd web
npm test
npm run build
```

仅对自己有权访问的内容进行整理，原视频和图文版权归原作者所有。服务只监听本机回环地址，写操作进行同源和 CSRF 校验。GitHub Actions 不包含向原作者镜像仓库写入的工作流。

## 许可证

沿用 [MIT](LICENSE)。原作者 Cheng Chen (tars1230) 的版权声明保留；映知新增工作台及工具的贡献归相应贡献者，详见来源说明。
