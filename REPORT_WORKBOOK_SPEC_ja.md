# RiskLens Excel ワークブック仕様（現行実装）

Language: [EN](./REPORT_WORKBOOK_SPEC.md) | [简中](./REPORT_WORKBOOK_SPEC_zh-CN.md) | [繁中](./REPORT_WORKBOOK_SPEC_zh-TW.md) | [日本語](./REPORT_WORKBOOK_SPEC_ja.md)

本書は `web/src/App.tsx` の `exportToExcel` に実装されている実際の Excel 出力挙動を説明します。

## 1. 単一企業エクスポート

- ファイル名：`<TICKER>_Financial_Data.xlsx`
- 実行トリガー：Dashboard の企業カード内エクスポートボタン

### シート構成（ローカライズ名）

1. リスクレポートシート（`riskText.sheetName`、紫タブ）
2. KPI 推移シート（`excelKpiSheet`、青タブ）
3. 財務諸表シート（`excelStatementsSheet`、緑タブ）

### リスクレポートシート

単一企業のシートには以下が含まれます。
- 結合タイトル行：`Company Name (Ticker)`
- サマリー行：
  - Ticker
  - Latest Period
  - Currency
  - Altman Z-Score
  - Z-Score Zone
  - Implied Rating
  - Strengths（ローカライズ）
  - Watch Items（ローカライズ）
- コベナンツ事前チェック表：
  - Metric / Actual / Threshold / Status / Signal / Notes
- データ品質ブロック：
  - Breach Count
  - Missing Key Inputs
  - Missing Items

ルール：
- コベナンツ実績値が欠損の場合は数値 `0` を出力
- 欠損コベナンツは `BREACH (DATA MISSING)` として扱う

### KPI 推移シート

- 列構成：期間列（`FYxx` / `yyQx`）+ 年次ペアの任意 YoY 列
- 指標：
  - EBIT
  - EBITDA
  - Total Debt
  - Debt / EBITDA
  - Interest Coverage
  - Free Cash Flow
  - FCF / Debt
  - Current Ratio

### 財務諸表シート

- 行は損益計算書/貸借対照表/キャッシュフロー計算書の科目を集約
- 行順は会計基準優先マッピング：
  - 米国 ticker -> USGAAP 順
  - 香港 ticker -> IFRS 順
  - 中国 A 株 ticker -> CAS 順
- 同義科目はフロントエンドのモーダルで主科目に折りたたみ、Excel は順序付きキー集合に基づき行を保持
- 年次ペアがある場合は任意で YoY 列を生成

## 2. 複数企業エクスポート

- ファイル名：`RiskLens_MultiCompany_Comparison.xlsx`
- 実行トリガー：複数企業表示時の上部 `Export All` ボタン

### シート構成

1. リスクレポートシート（`riskText.sheetName`、紫タブ）
2. ポートフォリオ KPI 比較（`excelPortfolioKpiSheet`、青タブ）
3. ポートフォリオ財務諸表比較（`excelPortfolioStatementsSheet`、青タブ）
4. 企業別財務シート：`<CompanyShortName> <excelCompanySheetSuffix>`（緑タブ）

### ポートフォリオリスクシート

- 企業ごとに 1 セクション
- 各セクションは結合・着色されたタイトル行で開始
- 各セクションにサマリー、コベナンツ事前チェック表、データ品質ブロックを含む

### ポートフォリオ KPI / 財務比較シート

- 最初に選択された企業を比較基準とする
- 各期間ブロックで以下を出力：
  - 基準企業値
  - 比較先企業値
  - 基準差分
  - 基準比 `%`

## 3. 書式ルール

- 期間ブロックごとにヘッダー色帯を適用
- タブ色：
  - risk：紫
  - portfolio comparison：青
  - statements：緑
- 列幅はセル文字長から自動調整
- 数値書式：
  - 値：`#,##0.00`
  - 比率：`0.00%`

## 4. ローカライズ

ワークブックのラベルは以下に対応：
- `en`
- `zh-CN`
- `zh-TW`
- `ja`

ローカライズ対象はシート名、リスクラベル、コベナンツ状態テキスト、strengths/watch items 翻訳です。
