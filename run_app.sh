#!/bin/bash
# RiskLens — Institutional Credit Risk API Launcher
# Starts the FastAPI backend which serves the modern SPA UI

echo "================================================"
echo "  RiskLens API & UI Launcher"
echo "================================================"
echo ""

# Navigate to project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "[System] Activating virtual environment (.venv)..."
    source .venv/bin/activate
fi

# Check if uvicorn/fastapi is installed
python3 -c "import uvicorn, fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[System] Installing dependencies..."
    pip install -q -r requirements.txt
    echo ""
fi

echo "[API] Starting FastAPI Data Gateway..."
cd "$SCRIPT_DIR/src"

echo "[Web] UI available at: http://localhost:8000/"
echo "[API] Swagger API Docs: http://localhost:8000/docs"
echo ""
echo ">>> Press Ctrl+C to stop <<<"
echo ""

# Run uvicorn in the foreground (Ctrl+C will kill it directly)
python3 -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
