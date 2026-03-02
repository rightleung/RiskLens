# RiskLens（日本語サマリー）

言語切替：[English Full](./README.md) | [简中摘要](./README_zh-CN.md) | [繁中摘要](./README_zh-TW.md) | [日本語サマリー](./README_ja.md)

## このページの位置づけ

本ページは**日本語の要約版**です。
完全かつ最新の手順は英語版を基準にしてください：
- [README.md](./README.md)

## 現在の構成（要約）

- デフォルト起動: `./run_app.sh` -> `src/api.py`（Dashboard）
- 互換起動: `main.py`（旧 API `/api/assess`）
- 企業検索: 会社名/コード検索 + ticker 入力欄への反映

## クイックスタート

```bash
./run_app.sh
```

アクセス先：
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 主要な英語ドキュメント

- アーキテクチャ: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 手法: [METHODOLOGY.md](./METHODOLOGY.md)
- Excel 仕様: [REPORT_WORKBOOK_SPEC.md](./REPORT_WORKBOOK_SPEC.md)

## 運用ポリシー

- 英語ドキュメントを唯一の完全仕様ソースとする。
- 本ページは要約と導線のみを保持する。
- 記述が矛盾する場合は英語版を優先する。
