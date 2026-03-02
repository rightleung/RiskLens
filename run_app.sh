#!/usr/bin/env bash
# RiskLens Dashboard launcher

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="python3"
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
fi

"$PYTHON_BIN" -c "import fastapi, uvicorn" >/dev/null 2>&1 || {
  echo "[Setup] Installing dependencies..."
  "$PYTHON_BIN" -m pip install -r requirements.txt
}

if [ ! -f "$SCRIPT_DIR/web/dist/index.html" ]; then
  echo "[Setup] Frontend build not found at web/dist/index.html"
  echo "[Hint] Build frontend first:"
  echo "       cd web && npm install && npm run build"
  exit 1
fi

echo "[Run] UI: http://127.0.0.1:8000/"
echo "[Run] Health: http://127.0.0.1:8000/health"
echo "[Run] Docs: http://127.0.0.1:8000/docs"

cd "$SCRIPT_DIR/src"
"$PYTHON_BIN" -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
