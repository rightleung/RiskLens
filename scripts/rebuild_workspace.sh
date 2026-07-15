#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/.venv"
WEB_DIR="$ROOT_DIR/web"

WITH_CN_DATA="${RISKLENS_WITH_CN_DATA:-0}"
EXTRA_SPEC=".[dev]"
if [ "$WITH_CN_DATA" = "1" ]; then
  EXTRA_SPEC=".[dev,cn-data]"
fi

echo "[Rebuild] Removing local environment artifacts"
rm -rf "$VENV_DIR" "$WEB_DIR/node_modules" "$WEB_DIR/dist"

echo "[Rebuild] Creating Python virtual environment"
python3 -m venv "$VENV_DIR"

echo "[Rebuild] Upgrading pip"
"$VENV_DIR/bin/python" -m pip install --upgrade pip

echo "[Rebuild] Installing Python dependencies ($EXTRA_SPEC)"
"$VENV_DIR/bin/python" -m pip install -e "$EXTRA_SPEC"

echo "[Rebuild] Installing frontend dependencies"
(
  cd "$WEB_DIR"
  npm ci --registry=https://registry.npmjs.org
  npm run build
)

if [ ! -f "$WEB_DIR/dist/index.html" ]; then
  echo "[Error] Frontend build did not produce web/dist/index.html" >&2
  exit 1
fi

echo "[Rebuild] Done"
