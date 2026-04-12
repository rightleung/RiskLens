#!/usr/bin/env bash

# Shared bootstrap for RiskLens shell entrypoints.
# Expects RISKLENS_ROOT to point at the repository root.

if [ -z "${RISKLENS_ROOT:-}" ]; then
  echo "[Error] RISKLENS_ROOT is not set before sourcing venv_bootstrap.sh" >&2
  return 1
fi

if [ -x "$RISKLENS_ROOT/.venv/bin/python" ]; then
  if [ -z "${VIRTUAL_ENV:-}" ] || [ "$VIRTUAL_ENV" != "$RISKLENS_ROOT/.venv" ]; then
    # shellcheck disable=SC1091
    source "$RISKLENS_ROOT/.venv/bin/activate"
  fi
  PYTHON_BIN="$RISKLENS_ROOT/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

export PYTHON_BIN
