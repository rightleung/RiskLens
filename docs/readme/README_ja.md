# RiskLens

言語：[English](../../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

RiskLens は、上場企業の公開財務データを分かりやすい信用リスクビューにまとめます。1つまたは複数の銘柄コードを入力するだけで、財務の健全性、企業比較、コベナンツ、共有可能なレポートを確認できます。

初期スクリーニングと分析のためのツールであり、正式な信用格付けや専門家による融資判断に代わるものではありません。

## できること

- Dashboard で1社または複数社を評価する。
- 流動性、レバレッジ、収益性、効率性、キャッシュフローの40以上の指標を確認する。
- Altman Z-Score、リスクゾーン、読みやすいインプライド格付けを見る。
- コベナンツ基準を設定し、合格、違反、データ不足を確認する。
- 期間別・企業別の比較を行い、手作業の表計算を減らす。
- JSON、Excel、または共有しやすい PDF に出力する。
- 英語、簡体字中国語、繁体字中国語、日本語で利用する。

## 銘柄コードからリスクビューまで

```text
銘柄コードを入力 → 財務データを取得・標準化 → リスク指標を計算 → 確認または出力
```

RiskLens は `yfinance` を通じて Yahoo Finance のグローバル上場企業データを取得します。中国市場の追加データには AKShare を有効化できます。

## クイックスタート

ローカル実行には Python 3.12+、Node.js、npm が必要です。ライブ市場データの取得にはネットワーク接続も必要です。

ローカル環境を構築します：

```bash
./scripts/rebuild_workspace.sh
```

RiskLens を起動します：

```bash
./run_app.sh
```

続いて [http://127.0.0.1:8000](http://127.0.0.1:8000) を開きます。

AKShare の中国市場データも利用する場合：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

## 使い方

### Dashboard

会社名で検索するか、銘柄コードを直接入力します。結果画面には、最新のリスク判断、過去の推移、財務諸表、コベナンツチェック、出力メニューが表示されます。

よく使うローカルページ：

- Dashboard：`http://127.0.0.1:8000/`
- サービス状態：`http://127.0.0.1:8000/health`
- 対話型 API ガイド：`http://127.0.0.1:8000/docs`

### コマンドライン

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
```

`--output path/to/file.json` で結果を保存できます。すべてのオプションは `./run_cli.sh --help` で確認できます。

### API

| エンドポイント | 用途 |
|---|---|
| `POST /api/v1/assess` | 1社または複数社を評価 |
| `GET /api/v1/symbols/search` | 上場企業の銘柄コードを検索 |
| `POST /api/v1/covenants/check` | 選択したコベナンツ基準を確認 |
| `POST /api/v1/reports/pdf` | 1社分の PDF を作成 |
| `POST /api/v1/reports/pdf/batch` | 最大10件の PDF を ZIP で取得 |

リクエストとレスポンスの例は `/docs` の対話型 API ガイドで確認できます。

## 結果の読み方

- **Z-Score**：5つの財務・収益シグナルを1つのスコアにまとめます。
- **リスクゾーン**：スコアを Safe、Grey、Distress に分類します。
- **インプライド格付け**：社内スクリーニング向けに、スコアを一般的な信用表現へ変換します。
- **指標とトレンド**：どの財務変化が結果を動かしたかを示します。
- **コベナンツチェック**：実績値と設定した基準を比較します。
- **データ品質の注記**：不足している入力や手動確認が必要な箇所を示します。

コベナンツ基準が設定されている一方で元データを取得できない場合、RiskLens は手動確認が終わるまで違反として扱います。データ不足を誤って合格と判断しないためです。

## 利用上の注意

- インプライド格付けは RiskLens 独自の解釈であり、S&P などの格付会社が発行する格付けではありません。
- 公開市場データには遅延、修正、欠損があり、会計基準によって項目の対応も異なる場合があります。
- 過去時点の時価総額がない場合、過去スコアに現在の時価総額を使うことがあります。
- Altman モデルは1つのリスクシグナルです。業界、株主、流動性、定性評価も併せて確認してください。
- RiskLens は投資、法律、融資に関する助言を提供しません。

## 開発に参加する方へ

変更を提出する前に、次のチェックを実行してください：

```bash
pytest
cd web && npm run lint && npm run build && npm run e2e:preflight
```

メインアプリは `src/api.py` と `web/` の React アプリです。ルートの `main.py` は互換性確認のためにのみ残されています。

## ガイド

- [RiskLens の仕組み](../architecture/ARCHITECTURE_ja.md)
- [RiskLens による信用リスクの読み方](../methodology/METHODOLOGY_ja.md)
- [Excel 出力の使い方](../report-workbook/REPORT_WORKBOOK_SPEC_ja.md)
- [他の言語のドキュメント](./README.md)
- [リリースチェックリスト](../review/repository-release-checklist.md)
