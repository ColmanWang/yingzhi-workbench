# 映知：本地可视化工作台

第一版本将已有抖音收藏／喜欢采集和本地 Whisper 转写整合成网页。所有业务从浏览器操作；原有 CLI 继续保留。AI 总结服务尚未接入；现有卡片可浏览、下载，新转写不会自动变成总结卡片。

## 安装

在仓库目录中运行，需要 Python 3.10+、Node.js 22.12+。以下命令仅安装依赖；不登录、不采集、不下载 Whisper 模型。

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python ./vendor/wheels/douyin_knowledge_core-0.2.1-py3-none-any.whl
uv pip install --python .venv/bin/python '.[local-asr]' imageio-ffmpeg
cd web
npm ci
npm run build
cd ..
./scripts/workbench.sh
```

打开 http://127.0.0.1:8765 。默认数据保存在仓库 `.runtime/workspace`，不会上传 Git。通过 `DY_CARD_HOME` 指定已有工作目录，复用其中 `.runtime/browser-profile`、`.runtime/huggingface`、`knowledge/`、`cards/`。端口可用 `DY_CARD_PORT` 设置。

本地转写首次需要下载 Whisper small 模型（约 500 MB），需要网络和足够磁盘空间。已有缓存可离线复用。执行转写前请确认愿意下载；它不会因打开工作台而自动下载。当前 CPU int8 路线无转写 API 费用。需已安装 Chrome；登录在独立浏览器中完成，窗口登录成功后自动关闭。

## 日常使用

1. 选择收藏或喜欢；点击「连接抖音」完成官方页面登录。
2. 点击「同步列表」，先少量读取视频资料，不自动转写。
3. 勾选视频，点击「本地转写」。任务中心显示实际任务与逐条进度，队列串行执行。
4. 点开视频查看描述、逐字稿或失败原因。点击“展开阅读”可在大窗口中切换逐字稿和卡片，滚动阅读全文；按 Escape 或点击关闭返回。图文和未识别到语音的内容不会显示成成功转写。
5. 知识卡片中浏览已有卡片，下载 HTML 或 PNG。

任务失败可以重新提交；应用退出时尚未完成的任务在下次启动标记为中断，不自动重跑。AI 总结配置留待下一阶段，暂无付费调用、自动日报或定时采集。工作台启动不访问抖音。

## 数据与安全

服务仅监听本机回环地址，不提供局域网共享。写操作需同源请求和 CSRF token，视频描述及逐字稿按不可信文本显示。浏览器 Cookie、签名播放地址和文件路径不返回网页。不得提交或分享 `.runtime/`。卡片预览限定文件目录并隔离 HTML。

工作台用独立 SQLite 管理视频来源、转写状态、任务和进度，不改写旧 CLI 的同步账本。已有 Markdown 笔记和卡片作为兼容内容导入；收藏和喜欢以复合标识分开存储。

## 开发

后端源码位于 `src/douyin_favorites_knowledge/workbench/`，前端位于 `web/`。生产模式使用 Python 同时提供本地 API 和已构建的前端文件。保留上游 MIT 许可证及原作者归属；独立仓库为 ColmanWang/yingzhi-workbench。卡片生成工具已合并到 tools/cards/；AI总结仍未接入。原命令行高级选项见 CLI_REFERENCE.md，项目来源见 ATTRIBUTION.md。
