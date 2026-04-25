#!/usr/bin/env bash

# Shared bootstrap for RiskLens shell entrypoints.
# Expects RISKLENS_ROOT to point at the repository root.

if [ -z "${RISKLENS_ROOT:-}" ]; then
  echo "[Error] RISKLENS_ROOT is not set before sourcing venv_bootstrap.sh" >&2
  return 1
fi

if [ ! -x "$RISKLENS_ROOT/.venv/bin/python" ]; then
  echo "[Error] Missing .venv. Run ./scripts/rebuild_workspace.sh first." >&2
  return 1
fi

if [ -z "${VIRTUAL_ENV:-}" ] || [ "$VIRTUAL_ENV" != "$RISKLENS_ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$RISKLENS_ROOT/.venv/bin/activate"
fi

PYTHON_BIN="$RISKLENS_ROOT/.venv/bin/python"

export PYTHON_BIN
