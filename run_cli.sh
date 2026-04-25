#!/usr/bin/env bash
# RiskLens CLI launcher

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export RISKLENS_ROOT="$SCRIPT_DIR"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/scripts/venv_bootstrap.sh"

exec "$PYTHON_BIN" -m src.risklens_cli "$@"
