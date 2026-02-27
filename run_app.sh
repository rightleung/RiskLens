#!/usr/bin/env bash
# RiskLens — Institutional Credit Risk API Launcher
# Starts the FastAPI backend which serves the modern SPA UI

set -euo pipefail

echo "================================================"
echo "  RiskLens API & UI Launcher"
echo "================================================"
echo ""

# Navigate to project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Select Python interpreter (prefer project venv for portability)
PYTHON_BIN="python3"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "[System] Activating virtual environment (.venv)..."
    # shellcheck disable=SC1091
    source .venv/bin/activate
    PYTHON_BIN=".venv/bin/python"
fi

# Check if uvicorn/fastapi is installed
"$PYTHON_BIN" -c "import uvicorn, fastapi" >/dev/null 2>&1 || {
    echo "[System] Installing dependencies..."
    "$PYTHON_BIN" -m pip install -q -r requirements.txt
    echo ""
}

echo "[API] Starting FastAPI Data Gateway..."
cd "$SCRIPT_DIR/src"

echo "[Web] UI available at: http://localhost:8000/"
echo "[API] Swagger API Docs: http://localhost:8000/docs"
echo ""
echo ">>> Press Ctrl+C to stop <<<"
echo ""

# Run uvicorn in the foreground (Ctrl+C will kill it directly)
"$PYTHON_BIN" -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
