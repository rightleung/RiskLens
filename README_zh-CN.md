# RiskLens（简中摘要）

语言切换：[English Full](./README.md) | [简中摘要](./README_zh-CN.md) | [繁中摘要](./README_zh-TW.md) | [日本語サマリー](./README_ja.md)

## 文档定位

本页为**简体中文摘要**。
完整、最新、可执行细节以英文主文档为准：
- [README.md](./README.md)

## 项目现状（摘要）

- 默认运行链路：`./run_app.sh` -> `src/api.py`（Dashboard）
- 兼容链路：`main.py`（用于旧接口 `/api/assess`）
- 公司查找器：支持按公司名/代码搜索并回填 ticker

## 快速开始

```bash
./run_app.sh
```

访问：
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 关键英文文档

- 架构： [ARCHITECTURE.md](./ARCHITECTURE.md)
- 方法论： [METHODOLOGY.md](./METHODOLOGY.md)
- Excel 规范： [REPORT_WORKBOOK_SPEC.md](./REPORT_WORKBOOK_SPEC.md)

## 维护策略

- 英文文档为唯一完整规范源。
- 本页仅保留高层摘要与跳转。
- 若中英文冲突，以英文文档为准。
