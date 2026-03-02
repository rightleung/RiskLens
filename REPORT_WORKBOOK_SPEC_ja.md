# RiskLens Excel レポート ワークブック仕様（v1.0）

このドキュメントは、Excel エクスポートで生成される内容と、各セクションのロジックを定義します。

## 1) 単一企業エクスポート（`<TICKER>_Risk_Report.xlsx`）

### シート命名（統一）
1. `01_Risk_Report`
2. `02_KPI_Trends`
3. `03_Financial_Statements`

### `01_Risk_Report` の内容
- `Executive Summary`
  - Ticker
  - Company Name（ローカライズ）
  - Latest Period
  - Currency
  - Data Source
  - Generated At
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths（ローカライズ）
  - Watch Items（ローカライズ）
- `Key Metrics`
  - Interest Coverage
  - Debt / EBITDA
  - FCF / Debt
  - Current Ratio
  - 各指標について：
    - Actual
    - Benchmark
    - Signal（`Strong` / `Neutral` / `Watch`）
- `Covenant Pre-Check`
  - Covenant
  - Actual
  - Threshold
  - Status
  - Notes
- `Data Quality`
  - Breach Count
  - Notes（Breach Count の定義）
  - Missing Key Inputs
  - Missing Items
- `Methodology & Boundary`
  - モデル範囲の注記（v1.0 は Altman のみ）
  - 入力欠損は breach として扱う（保守的コントロール）
  - 投資助言ではない旨の免責

### `02_KPI_Trends` の内容
- 期間横断の主要 KPI トレンド表
- 年次期間には YoY 列を追加（可能な場合、増減額と増減率を表示）

### `03_Financial_Statements` の内容
- 財務諸表の生データ項目（損益 / 貸借対照 / キャッシュフロー）
- 複数期間比較
- 年次期間には YoY 列を追加（可能な場合、増減額と増減率を表示）

## 2) 複数企業エクスポート（`RiskLens_MultiCompany_Comparison.xlsx`）

### シート命名（統一）
1. `01_Portfolio_Risk_Summary`
2. `02_Portfolio_KPI_Comparison`
3. `03_Portfolio_Statement_Comparison`
4. `04_<TICKER>_Statements`（企業ごとに 1 シート）

### `01_Portfolio_Risk_Summary` の内容
- 生成タイムスタンプ
- 企業ごとのサマリー：
  - Ticker
  - Company Name
  - Latest Period
  - Z-Score
  - Implied Rating
  - Breach Count
  - Missing Key Inputs
  - Missing Items
- 境界注記と Breach Count 定義

### `02_Portfolio_KPI_Comparison` の内容
- 企業横断の期間別 KPI 比較
- 基準企業と他社の delta および delta %

### `03_Portfolio_Statement_Comparison` の内容
- 企業横断の期間別財務行項目比較
- 基準企業と他社の delta および delta %

### `04_<TICKER>_Statements` の内容
- 企業レベルの財務明細
- 期間ビューと YoY ビュー

## 3) ロジック定義

### Covenant 事前チェックルール（v1.0 デフォルト）
- Interest Coverage: `>= 3.0`
- Debt / EBITDA: `<= 4.0`
- Current Ratio: `>= 1.2`
- FCF / Debt: `>= 0.05`

### Breach Count の定義
`Breach Count = number of covenant checks flagged as BREACH, including DATA MISSING cases.`

### 欠損項目の扱い
- 主要入力の欠損はレポート出力に明示的に列挙します。
- 欠損した covenant 指標は breach として扱います（`BREACH (DATA MISSING)`）。

## 4) ローカライズ挙動
- Strengths / Watch Items はフロントエンドのテキスト翻訳器で翻訳します。
- Missing Items はローカライズ済み KPI ラベルを優先し、フォールバックとして metric-key prettifier を使用します。
- レポートラベルは `en`、`zh-CN`、`zh-TW`、`ja` をサポートします。
