#!/bin/bash
# Credit Analyst Toolkit — Quick Start
# Run this script to launch the web application

echo "================================================"
echo "  Credit Analyst Toolkit"
echo "  Web Application Launcher"
echo "================================================"
echo ""

# Navigate to project directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
    echo ""
fi

echo "Starting Credit Analyst Web App..."
echo "Opening at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Launch streamlit from web/ directory
cd web
streamlit run app.py --server.port 8501 --server.address localhost
