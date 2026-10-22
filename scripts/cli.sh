#!/bin/zsh
set -eu
REPO="${0:A:h:h}"
DATA_ROOT="${DY_CARD_HOME:-$REPO/.runtime/workspace}"
export PYTHONPATH="$REPO/src"
export HF_HOME="$DATA_ROOT/.runtime/huggingface"
export DOUYIN_FAVORITES_PROFILE_DIR="$DATA_ROOT/.runtime/browser-profile"
export PATH="$DATA_ROOT/.runtime/bin:$REPO/.venv/bin:$PATH"
exec "$REPO/.venv/bin/python" -m douyin_favorites_knowledge --config "$DATA_ROOT/.runtime/config.json" "$@"
