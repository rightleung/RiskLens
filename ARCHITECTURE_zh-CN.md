# RiskLens 架构（简中摘要）

语言切换：[EN Full](./ARCHITECTURE.md) | [简中摘要](./ARCHITECTURE_zh-CN.md) | [繁中摘要](./ARCHITECTURE_zh-TW.md) | [日本語サマリー](./ARCHITECTURE_ja.md)

本页为架构摘要。完整架构与组件边界请看英文版：
- [ARCHITECTURE.md](./ARCHITECTURE.md)

## 架构要点

- 默认链路：`run_app.sh` -> `src/api.py` -> `web/` 前端静态托管
- 主接口：`/api/v1/assess`、`/api/v1/symbols/search`、`/api/v1/covenants/check`
- 兼容链路：`main.py`（保留旧接口）
- 数据流：抓取(`data_fetcher`) -> 比率(`ratio_analyzer`) -> 评分(`zscore`) / 契约(`covenant_monitor`)

> 若本页与英文版有差异，以英文版为准。
