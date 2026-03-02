#!/usr/bin/env bash
# RiskLens release smoke checks (non-destructive)

set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[Smoke] Base URL: $BASE_URL"

health_file="$TMP_DIR/health.json"
curl --noproxy '*' -fsS "$BASE_URL/health" >"$health_file"

if ! grep -q '"status":"healthy"' "$health_file"; then
  echo "[Smoke][FAIL] /health did not report healthy status."
  cat "$health_file"
  exit 1
fi
echo "[Smoke][PASS] /health"

docs_code="$(curl --noproxy '*' -sS -o /dev/null -w "%{http_code}" "$BASE_URL/docs")"
if [[ "$docs_code" != "200" ]]; then
  echo "[Smoke][FAIL] /docs expected 200, got $docs_code"
  exit 1
fi
echo "[Smoke][PASS] /docs"

root_code="$(curl --noproxy '*' -sS -o /dev/null -w "%{http_code}" "$BASE_URL/")"
if [[ "$root_code" != "200" ]]; then
  echo "[Smoke][FAIL] / expected 200, got $root_code"
  exit 1
fi
echo "[Smoke][PASS] /"

demo_file="$TMP_DIR/assess_demo.json"
demo_code="$(
  curl --noproxy '*' -sS -o "$demo_file" -w "%{http_code}" \
    -X POST "$BASE_URL/api/assess" \
    -H 'Content-Type: application/json' \
    -d '{"ticker":"DEMO","data_source":"demo"}'
)"
if [[ "$demo_code" != "200" ]]; then
  echo "[Smoke][FAIL] /api/assess demo expected 200, got $demo_code"
  cat "$demo_file"
  exit 1
fi
if ! grep -q '"risk_zone"' "$demo_file"; then
  echo "[Smoke][FAIL] /api/assess demo response missing risk_zone."
  cat "$demo_file"
  exit 1
fi
echo "[Smoke][PASS] /api/assess demo"

validation_file="$TMP_DIR/assess_validation.json"
validation_code="$(
  curl --noproxy '*' -sS -o "$validation_file" -w "%{http_code}" \
    -X POST "$BASE_URL/api/assess" \
    -H 'Content-Type: application/json' \
    -d '{"ticker":"   ","data_source":"demo"}'
)"
if [[ "$validation_code" != "422" ]]; then
  echo "[Smoke][FAIL] /api/assess expected 422 for empty ticker, got $validation_code"
  cat "$validation_file"
  exit 1
fi
echo "[Smoke][PASS] /api/assess validation"

echo "[Smoke] All checks passed."
