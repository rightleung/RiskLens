# RiskLens repository release review

This is the repeatable checklist for a repository-wide debug/review before a
PDF-export release PR. It intentionally separates source changes from local
PDF outputs and other generated artifacts.

## 1. Protect the worktree

```bash
git status --short --branch
git diff --binary > /tmp/risklens-worktree.patch
git switch -c codex/repo-review-pdf-release
```

Do not reset or discard existing PDF fixes. Restore only accidental deleted
tracked files, and keep `.agent/`, `output/`, `web/dist/`, `web/node_modules/`,
and generated PDFs out of the commit.

## 2. Deterministic baseline

```bash
./.venv/bin/python -m pip check
./.venv/bin/python -m pytest -q
git diff --check
uvx pip-audit -r requirements.txt

cd web
npm ci --registry=https://registry.npmjs.org
npm run lint
npm run build
npx playwright install --with-deps chromium
npm run e2e:preflight
npm audit --audit-level=high --registry=https://registry.npmjs.org
```

The expected baseline is: all Python tests pass, frontend lint/build/e2e pass,
Python audit has no known vulnerabilities, and npm has zero High/Critical
findings. The ExcelJS 4.x `uuid` Moderate advisory is documented as an
accepted exception because `npm audit fix --force` downgrades ExcelJS to 3.x.

## 3. Review the active export path

Check request validation and bounds (single report 2 MB, batch 1–10 reports,
theme allowlist), bounded PDF executor capacity/timeouts, atomic ZIP creation,
safe filenames, SHA-256/byte headers, CORS exposure, and generic error
responses that do not echo exception strings or query-string secrets.

Check assessment data quality, covenant missing-data semantics, period
selection (latest quarter versus annual comparison), localized labels, CJK
font discovery, renderer table width/row pagination, and both light/dark themes.
Legacy modules are documented separately and are not a release blocker unless
the active import path reaches them.

## 4. Live PDF matrix

Use yfinance-backed fixtures in a temporary directory; never commit the output:

| Market | Symbols |
|---|---|
| A-share | `600519.SS`, `002415.SZ`, `300866.SZ`, `603605.SS`, `300773.SZ` |
| H-share | `1211.HK`, `6690.HK`, `2338.HK`, `3759.HK`, `1877.HK` |
| US | `AAPL`, `F`, `CROX`, `FSLR`, `HAIN` |

For every symbol, require a successful analysis, a non-empty PDF on all pages,
`Data Source` and disclaimer text, and a valid `pdfinfo`/`pdftotext` result.
Generate representative `en`, `zh-CN`, `zh-TW`, and `ja` pages in both themes;
render at least one A-share CJK page, one H-share page, and one US page with
`pdftocairo` and inspect for clipping, overlap, blank pages, missing glyphs,
and incorrect colors. Build a four-report batch containing duplicate tickers;
verify `X-ZIP-SHA256`, `X-ZIP-Bytes`, `ZipFile.testzip()`, and collision-safe
filenames.

## 5. Stage, commit, and open the PR

Before staging, inspect `git diff --stat`, `git diff --cached --check`, and
`git status --short`. Stage only source, tests, docs, dependency manifests,
lockfiles, CI, Dependabot, and bundled font assets. Use focused commits such
as:

```text
fix(pdf): complete export repair and repository review fixes
chore(deps): remediate release-blocking vulnerabilities
ci: add regression and dependency quality gates
```

Push `codex/repo-review-pdf-release`, open a PR against `main`, attach the
test/audit results and the UUID exception, then wait for all required CI checks.
Do not merge automatically. After merge, enable Dependabot security updates
and protect `main` with required CI checks and review approval.
