#!/bin/sh
set -eu
cd "$(dirname "$0")"
export UV_PROJECT_ENVIRONMENT="$HOME/Library/Caches/StudyDuel/venv"
export PYTHONPYCACHEPREFIX="$HOME/Library/Caches/StudyDuel/pycache"
exec "$HOME/.local/bin/uv" run --locked pytest -q "$@"
