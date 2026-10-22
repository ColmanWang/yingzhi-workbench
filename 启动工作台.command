#!/bin/zsh
set -eu
REPO="${0:A:h}"
exec "$REPO/scripts/workbench.sh"
