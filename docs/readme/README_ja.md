# RiskLens

Language: [English](../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

## 1. 実行パス

RiskLens は現在、用途の異なる 2 つのバックエンド実行パスを提供しています。

1. Dashboard パス（デフォルト）
- 起動スクリプト：`./run_app.sh`
- バックエンド入口：`src/api.py`（`uvicorn src.api:app`）
- フロントエンド：`web/`（React + Vite のビルド成果物を FastAPI が静的配信）
- 主な API：`/api/v1/assess`、`/api/v1/symbols/search`、`/api/v1/covenants/check`

2. MVP 互換パス（維持）
- バックエンド入口：`main.py`
- API：`/api/assess`、`/api/v1/assess`
- 主に後方互換と `smoke_test.sh`（現在は `/api/assess` を検証）向け

## 2. 機能範囲（Dashboard パス）

- `GET /`：Dashboard UI
- `GET /health`：ヘルスチェック
- `GET /docs`：OpenAPI ドキュメント
- `POST /api/v1/assess`：単一/複数 ticker のリスク評価
- `GET /api/v1/symbols/search`：企業名/ティッカー検索（株式銘柄中心）
- `POST /api/v1/covenants/check`：コベナンツ事前チェック
- フロントエンド企業検索：企業名検索、複数選択、ticker 入力欄への反映

## 3. プロジェクト構成

```text
RiskLens/
├── run_app.sh
├── run_cli.sh
├── smoke_test.sh
├── rollback.sh
├── scripts/
│   ├── rebuild_workspace.sh
│   └── venv_bootstrap.sh
├── src/
│   ├── api.py
│   ├── risklens_cli.py
│   ├── data_fetcher.py
│   ├── ratio_analyzer.py
│   ├── zscore.py
│   ├── covenant_monitor.py
│   ├── akshare_data.py
│   ├── reportlab_pdf_exporter.py
│   ├── reportlab_pdf_renderer.py
│   ├── html_pdf_exporter.py
│   ├── pdf_report_core.py
│   ├── services/
│   └── legacy/
├── web/
│   ├── src/App.tsx
│   └── dist/
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── pdf-template/
│   ├── readme/
│   └── report-workbook/
├── main.py           (MVP 互換)
└── *.md
```

## 4. クイックスタート

### 4.1 Dashboard パス（推奨）

```bash
./run_app.sh
```

アクセス先：
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### 4.2 ワークスペースの再構築

ローカルワークスペースを一から再構築する場合：

```bash
./scripts/rebuild_workspace.sh
```

`.venv` の再作成、`web/node_modules` の復元、`web/dist/` の再ビルドを行います。

AKShare 中国市場データも必要な場合：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

### 4.3 MVP 互換パス（`/api/assess`）

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

### 4.4 CLI コマンド（`risklens`）の初回セットアップ

プロジェクトルート（`RiskLens/`）で一度だけ実行:

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
grep -q 'export PATH="$HOME/.local/bin:$PATH"' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

確認:

```bash
risklens version
```

基本コマンド:

- `risklens assess AAPL MSFT --data-source yfinance`
- `risklens search apple --limit 10`
- `risklens covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0`
- `risklens sources`
- `risklens version`

## 5. API 例（Dashboard パス）

### 5.1 リスク評価

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["AAPL","0700.HK"],"data_source":"yfinance"}'
```

### 5.2 企業検索

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### 5.3 コベナンツチェック

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","data_source":"yfinance","covenants":{"min_current_ratio":1.2}}'
```

## 6. ドキュメント階層

以下の文書は責務が異なるため、維持を推奨します。

- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)：実行境界とコンポーネント責務（多言語：[簡中](../architecture/ARCHITECTURE_zh-CN.md)、[繁中](../architecture/ARCHITECTURE_zh-TW.md)、[日本語](../architecture/ARCHITECTURE_ja.md)）
- [METHODOLOGY.md](../methodology/METHODOLOGY.md)：スコアリング手法とリスク区分（多言語：[簡中](../methodology/METHODOLOGY_zh-CN.md)、[繁中](../methodology/METHODOLOGY_zh-TW.md)、[日本語](../methodology/METHODOLOGY_ja.md)）
- [REPORT_WORKBOOK_SPEC.md](../report-workbook/REPORT_WORKBOOK_SPEC.md)：Excel 出力契約と項目ルール（多言語：[簡中](../report-workbook/REPORT_WORKBOOK_SPEC_zh-CN.md)、[繁中](../report-workbook/REPORT_WORKBOOK_SPEC_zh-TW.md)、[日本語](../report-workbook/REPORT_WORKBOOK_SPEC_ja.md)）
- [REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md](../pdf-template/REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md)：完全 PDF レポートテンプレートとワイヤーフレーム
- 他言語版は対応するディレクトリ（例: `docs/readme/` と `docs/architecture/`）にまとめ、ルートをすっきり保っています。

責務分担：
- README：導入と実行手順
- Architecture：システム設計とランタイム境界
- Methodology：モデルとリスク方針
- Workbook Spec：レポート出力契約
- PDF Template：全レポートページ構造とエクスポートレイアウト基準

## 7. 多言語ドキュメント運用方針

- 4 言語すべてで完全版ドキュメントを提供します。
- 記述に差異がある場合は英語版を優先します。
