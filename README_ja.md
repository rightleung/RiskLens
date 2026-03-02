# RiskLens

Language: [English](./README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

## 1. 実行パス

RiskLens は現在、用途の異なる 2 つのバックエンド実行パスを提供しています。

1. Dashboard パス（デフォルト）
- 起動スクリプト：`./run_app.sh`
- バックエンド入口：`src/api.py`（`uvicorn api:app`）
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
├── smoke_test.sh
├── src/
│   ├── api.py
│   ├── data_fetcher.py
│   ├── ratio_analyzer.py
│   ├── covenant_monitor.py
│   └── zscore.py
├── web/
│   ├── src/App.tsx
│   └── dist/
├── main.py
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

### 4.2 MVP 互換パス（`/api/assess`）

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

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

以下の 3 文書は責務が異なるため、維持を推奨します。

- [ARCHITECTURE.md](./ARCHITECTURE.md)：実行境界とコンポーネント責務
- [METHODOLOGY.md](./METHODOLOGY.md)：スコアリング手法とリスク区分
- [REPORT_WORKBOOK_SPEC.md](./REPORT_WORKBOOK_SPEC.md)：Excel 出力契約と項目ルール

責務分担：
- README：導入と実行手順
- Architecture：システム設計とランタイム境界
- Methodology：モデルとリスク方針
- Workbook Spec：レポート出力契約

## 7. 多言語ドキュメント運用方針

- 4 言語すべてで完全版ドキュメントを提供します。
- 記述に差異がある場合は英語版を優先します。
