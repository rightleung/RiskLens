# RiskLens Architecture（日本語サマリー）

言語切替：[EN Full](./ARCHITECTURE.md) | [简中摘要](./ARCHITECTURE_zh-CN.md) | [繁中摘要](./ARCHITECTURE_zh-TW.md) | [日本語サマリー](./ARCHITECTURE_ja.md)

本ページはアーキテクチャ要約です。完全仕様は英語版を参照してください：
- [ARCHITECTURE.md](./ARCHITECTURE.md)

## 要点

- デフォルト経路: `run_app.sh` -> `src/api.py` -> `web/` 静的配信
- 主 API: `/api/v1/assess`、`/api/v1/symbols/search`、`/api/v1/covenants/check`
- 互換経路: `main.py`（旧 API 互換）
- データ処理: 取得(`data_fetcher`) -> 比率(`ratio_analyzer`) -> スコア(`zscore`) / コベナンツ(`covenant_monitor`)

> 内容差分がある場合は英語版を優先してください。
