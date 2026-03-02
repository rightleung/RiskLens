# RiskLens 架構（繁中摘要）

語言切換：[EN Full](./ARCHITECTURE.md) | [简中摘要](./ARCHITECTURE_zh-CN.md) | [繁中摘要](./ARCHITECTURE_zh-TW.md) | [日本語サマリー](./ARCHITECTURE_ja.md)

本頁為架構摘要。完整架構與元件邊界請看英文版：
- [ARCHITECTURE.md](./ARCHITECTURE.md)

## 架構重點

- 預設鏈路：`run_app.sh` -> `src/api.py` -> `web/` 前端靜態託管
- 主要介面：`/api/v1/assess`、`/api/v1/symbols/search`、`/api/v1/covenants/check`
- 相容鏈路：`main.py`（保留舊介面）
- 資料流：抓取(`data_fetcher`) -> 比率(`ratio_analyzer`) -> 評分(`zscore`) / 契約(`covenant_monitor`)

> 若本頁與英文版有差異，以英文版為準。
