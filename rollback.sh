#!/usr/bin/env bash
# RiskLens release rollback helper (safe branch-based rollback)

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./rollback.sh <tag-or-commit> [--allow-dirty]

Examples:
  ./rollback.sh v1.0.0
  ./rollback.sh a1b2c3d --allow-dirty

Behavior:
  1) Validates target tag/commit exists.
  2) (Default) requires clean working tree.
  3) Creates a rollback branch from target and checks it out.
  4) Prints follow-up commands (run smoke checks, then push/deploy).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

TARGET="${1:-}"
ALLOW_DIRTY="${2:-}"

if [[ -z "$TARGET" ]]; then
  echo "[Rollback][ERROR] Missing rollback target."
  usage
  exit 1
fi

if [[ -n "$ALLOW_DIRTY" && "$ALLOW_DIRTY" != "--allow-dirty" ]]; then
  echo "[Rollback][ERROR] Unknown option: $ALLOW_DIRTY"
  usage
  exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "[Rollback][ERROR] Not inside a git repository."
  exit 1
fi

if [[ "$ALLOW_DIRTY" != "--allow-dirty" ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "[Rollback][ERROR] Working tree is not clean."
    echo "[Rollback][INFO] Commit/stash changes first, or rerun with --allow-dirty."
    exit 1
  fi
fi

if ! git rev-parse --verify "${TARGET}^{commit}" >/dev/null 2>&1; then
  echo "[Rollback][ERROR] Target not found: $TARGET"
  echo "[Rollback][INFO] Recent tags:"
  git tag --sort=-creatordate | head -n 10 || true
  exit 1
fi

SHORT_TARGET="$(git rev-parse --short "${TARGET}^{commit}")"
STAMP="$(date +%Y%m%d-%H%M%S)"
ROLLBACK_BRANCH="rollback/${SHORT_TARGET}-${STAMP}"

CURRENT_BRANCH="$(git branch --show-current || true)"
if [[ -z "$CURRENT_BRANCH" ]]; then
  CURRENT_BRANCH="(detached HEAD)"
fi

echo "[Rollback] Current branch: $CURRENT_BRANCH"
echo "[Rollback] Target: $TARGET ($SHORT_TARGET)"
echo "[Rollback] Creating branch: $ROLLBACK_BRANCH"

git checkout -b "$ROLLBACK_BRANCH" "$TARGET"

echo ""
echo "[Rollback][DONE] Checked out rollback branch at target revision."
echo "[Rollback][NEXT] Run smoke checks:"
echo "  ./smoke_test.sh http://127.0.0.1:8000"
echo "[Rollback][NEXT] Push rollback branch if checks pass:"
echo "  git push -u origin $ROLLBACK_BRANCH"
