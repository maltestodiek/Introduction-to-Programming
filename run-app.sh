#!/bin/sh
set -eu
cd "$(dirname "$0")"
export UV_PROJECT_ENVIRONMENT="$HOME/Library/Caches/StudyDuel/venv"
export PYTHONPYCACHEPREFIX="$HOME/Library/Caches/StudyDuel/pycache"
exec "$HOME/.local/bin/uv" run --locked streamlit run app.py --server.address 127.0.0.1 --server.port 8501 "$@"
