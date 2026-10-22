#!/bin/zsh
set -eu
REPO="${0:A:h:h}"
DATA_ROOT="${DY_CARD_HOME:-$REPO/.runtime/workspace}"
PYTHON="$REPO/.venv/bin/python"
if [[ ! -x "$PYTHON" || ! -f "$REPO/web/dist/index.html" ]]; then
  echo '请先按 docs/WORKBENCH.md 完成依赖安装和网页构建。'
  exit 1
fi
mkdir -p "$DATA_ROOT/.runtime/bin"
chmod 700 "$DATA_ROOT/.runtime"
export PYTHONPATH="$REPO/src"
export HF_HOME="$DATA_ROOT/.runtime/huggingface"
export DOUYIN_FAVORITES_PROFILE_DIR="$DATA_ROOT/.runtime/browser-profile"
export PATH="$DATA_ROOT/.runtime/bin:$REPO/.venv/bin:$PATH"
if ! command -v ffmpeg >/dev/null 2>&1; then
  "$PYTHON" - "$DATA_ROOT/.runtime/bin/ffmpeg" <<'PY'
import pathlib, sys
try:
    import imageio_ffmpeg
except ImportError:
    raise SystemExit('缺少 FFmpeg，请安装 imageio-ffmpeg 或系统 FFmpeg。')
path = pathlib.Path(sys.argv[1])
if not path.exists():
    path.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
PY
fi
OPEN_ARGS=()
if [[ "${DY_CARD_OPEN_BROWSER:-1}" == "1" ]]; then
  OPEN_ARGS=(--open-browser)
fi
exec "$PYTHON" -m douyin_favorites_knowledge.workbench \
  --data-dir "$DATA_ROOT/.runtime/workbench" \
  --knowledge-dir "$DATA_ROOT/knowledge" \
  --cards-dir "$DATA_ROOT/cards" \
  --static-dir "$REPO/web/dist" --port "${DY_CARD_PORT:-8765}" "${OPEN_ARGS[@]}"
