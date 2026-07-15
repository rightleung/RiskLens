# RiskLens

Language: [English](../../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

RiskLens は、機関投資家・金融機関向けの信用リスク評価プラットフォームです。上場企業の財務データを取得し、40 以上の信用・事業比率を計算し、Altman Z-Score を S&P 風の信用格付けへマッピングし、融資後のコベナンツを確認し、Dashboard、JSON、Excel、PDF レポートを出力します。

## 機能範囲

- FastAPI + React Dashboard による複数 ticker の信用評価。
- `yfinance` による財務データ取得。中国市場データ向けに AKShare を任意で利用可能。
- 流動性、ソルベンシー、収益性、効率性、キャッシュフロー比率を分析。
- Altman Z-Score のゾーン判定と S&P 風格付けマッピング。
- コベナンツ閾値チェック。閾値が設定されているのにデータが欠損している場合は、デューデリジェンス上の安全側として breach 扱い。
- フロントエンド用語は英語、簡体字中国語、繁体字中国語、日本語に対応。
- API JSON、フロントエンド workbook export、完全版 PDF export に対応。

## 実行パス

RiskLens には 2 つのバックエンドパスがあります。

| パス | エントリーポイント | 用途 |
|------|--------------------|------|
| Dashboard | `./run_app.sh` -> `src/api.py` | 主要 FastAPI API と React SPA。`http://127.0.0.1:8000` で実行 |
| MVP compatibility | `main.py` | 旧 `/api/assess` 互換と smoke checks |

Dashboard パスは `web/dist/` から React ビルド成果物を配信します。`./run_app.sh` を実行する前にフロントエンドをビルドしてください。

## 要件

- Python 3.12+
- フロントエンド用の Node.js と npm
- ライブ `yfinance`/AKShare データ取得にはネットワークアクセスが必要

## クイックスタート

ローカル環境をクリーンに再構築します。

```bash
./scripts/rebuild_workspace.sh
```

このスクリプトは `.venv` を作り直し、Python dev 依存関係をインストールし、`npm ci` を実行し、`web/dist/` をビルドします。

AKShare による中国市場データも使う場合：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

Dashboard を起動します。

```bash
./run_app.sh
```

アクセス先：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 手動セットアップ

バックエンド：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
```

フロントエンド：

```bash
cd web
npm ci
npm run build
```

フロントエンド開発サーバー：

```bash
cd web
npm run dev
```

## CLI

リポジトリルートからランチャーを使います。

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
./run_cli.sh sources
./run_cli.sh version
```

CLI は該当箇所で `auto`、`yfinance`、`akshare`、`demo` を data source としてサポートします。`--output path/to/file.json` で JSON をファイル出力し、`--compact` で compact JSON を出力できます。

任意の shell ショートカット：

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
```

その後：

```bash
risklens assess NVDA AMD --data-source yfinance
```

## API 例

### 信用評価

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["NVDA","0700.HK"],"data_source":"yfinance","include_suggestions":true}'
```

### 企業検索

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### コベナンツチェック

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","data_source":"yfinance","covenants":{"min_current_ratio":1.2,"max_debt_to_equity":2.0}}'
```

### PDF Export

`POST /api/v1/reports/pdf` は `/api/v1/assess` が返す単一企業の assessment payload を受け取ります。省略した構造：

```json
{
  "report": { "ticker": "NVDA" },
  "lang": "ja",
  "theme": "dark"
}
```

対応言語は `en`、`zh-CN`、`zh-TW`、`ja`。対応テーマは `dark` と `light` です。

## テスト

バックエンドテスト：

```bash
pytest
```

特定のテストファイル：

```bash
pytest tests/test_zscore.py
```

フロントエンドチェック：

```bash
cd web
npm run lint
npm run build
npm run e2e:preflight
```

MVP compatibility app に対して legacy smoke checks を実行：

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

## プロジェクト構成

```text
RiskLens/
├── run_app.sh
├── run_cli.sh
├── smoke_test.sh
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
│   ├── reportlab_pdf_exporter.py
│   ├── reportlab_pdf_renderer.py
│   ├── html_pdf_exporter.py
│   ├── pdf_report_core.py
│   ├── services/
│   └── legacy/
├── web/
│   ├── src/
│   └── dist/
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── pdf-template/
│   ├── readme/
│   └── report-workbook/
└── main.py
```

## 主要モジュール

| モジュール | 責務 |
|------------|------|
| `src/api.py` | Dashboard FastAPI app、API routes、SPA static serving、concurrency limits |
| `src/services/rich_assessment_service.py` | Dashboard の複数期間 assessment pipeline |
| `src/services/assessment_service.py` | Legacy MVP/CLI の単一期間 assessment pipeline |
| `src/data_fetcher.py` | 財務データ取得と caching |
| `src/ratio_analyzer.py` | 40+ financial ratio calculations |
| `src/zscore.py` | Altman Z-Score と rating mapping |
| `src/covenant_monitor.py` | コベナンツ閾値チェック |
| `src/reportlab_pdf_exporter.py` | 完全版 PDF report generation entrypoint |
| `web/src/App.tsx` | React Dashboard の主要画面 |

## 設定

設定は環境変数と任意の `.env` から読み込まれます。ローカル設定を作る場合は `.env.example` から始めてください。

よく使う設定：

| 変数 | デフォルト | 用途 |
|------|------------|------|
| `APP_PORT` | `8000` | ローカル Dashboard ポート |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | フロントエンド開発 origin |
| `ASSESS_MAX_CONCURRENCY` | `8` | 並列 ticker assessment 数 |
| `ASSESS_TICKER_TIMEOUT_SECONDS` | `20` | ticker ごとの assessment timeout |
| `SYMBOL_SEARCH_TIMEOUT_SECONDS` | `8` | 企業検索 timeout |
| `CACHE_TTL_SECONDS` | `600` | 財務データ cache TTL |
| `SENTRY_DSN` | 空 | 設定時のみ Sentry を有効化 |
| `API_REPORT_DIR` | `/tmp/credit_api_reports` | Dashboard ratio/report artifact directory |

## ドキュメント

- [Architecture](../architecture/ARCHITECTURE.md)
- [Methodology](../methodology/METHODOLOGY.md)
- [Report workbook spec](../report-workbook/REPORT_WORKBOOK_SPEC.md)
- [PDF template draft](../pdf-template/REPORT_PDF_TEMPLATE_DRAFT_zh-CN.md)
- README translations: [zh-CN](./README_zh-CN.md), [zh-TW](./README_zh-TW.md), [ja](./README_ja.md)

翻訳内容が英語ドキュメントと矛盾する場合は、英語版を正とします。
