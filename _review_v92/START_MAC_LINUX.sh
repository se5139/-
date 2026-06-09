#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PORT=8520
PY_CMD="python3"
if ! command -v python3 >/dev/null 2>&1; then
  PY_CMD="python"
fi
if [ ! -d .venv ]; then
  "$PY_CMD" -m venv .venv
fi
source .venv/bin/activate
if [ ! -f .venv/v9_ready.txt ]; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  echo ready > .venv/v9_ready.txt
fi
python scripts/stop_port.py "$PORT" || true
streamlit run app.py --server.address 127.0.0.1 --server.port "$PORT" --server.fileWatcherType none --client.toolbarMode minimal
