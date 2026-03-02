# RiskLens

语言: [English](./README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

## 1. 运行路径

RiskLens 当前提供两条后端运行路径，分别用于不同场景：

1. Dashboard 路径（默认）
- 启动脚本：`./run_app.sh`
- 后端入口：`src/api.py`（`uvicorn api:app`）
- 前端：`web/`（React + Vite 构建产物由 FastAPI 静态路由托管）
- 主要接口：`/api/v1/assess`、`/api/v1/symbols/search`、`/api/v1/covenants/check`

2. MVP 兼容路径（保留）
- 后端入口：`main.py`
- 接口：`/api/assess`、`/api/v1/assess`
- 主要用于历史兼容与 `smoke_test.sh`（当前验证 `/api/assess`）

## 2. 功能范围（Dashboard 路径）

- `GET /`：Dashboard 页面
- `GET /health`：健康检查
- `GET /docs`：OpenAPI 文档
- `POST /api/v1/assess`：单/多 ticker 风险评估
- `GET /api/v1/symbols/search`：公司/代码搜索（以股票标的为主）
- `POST /api/v1/covenants/check`：契约预检查
- 前端公司搜索器：支持按公司名搜索、多选并回填到 ticker 输入框

## 3. 项目结构

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

## 4. 快速开始

### 4.1 Dashboard 路径（推荐）

```bash
./run_app.sh
```

访问：
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### 4.2 MVP 兼容路径（`/api/assess`）

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

## 5. API 示例（Dashboard 路径）

### 5.1 风险评估

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["AAPL","0700.HK"],"data_source":"yfinance"}'
```

### 5.2 公司搜索

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### 5.3 契约检查

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","data_source":"yfinance","covenants":{"min_current_ratio":1.2}}'
```

## 6. 文档分层

建议保留以下三份文档，因为它们对应不同的职责边界：

- [ARCHITECTURE.md](./ARCHITECTURE.md)：运行边界与组件职责
- [METHODOLOGY.md](./METHODOLOGY.md)：评分方法与风险分层口径
- [REPORT_WORKBOOK_SPEC.md](./REPORT_WORKBOOK_SPEC.md)：Excel 导出契约与字段规则

职责划分：
- README：上手与运行
- Architecture：系统设计与运行边界
- Methodology：模型与风险口径
- Workbook Spec：报表输出契约

## 7. 多语言文档维护策略

- 四语文档均提供完整内容。
- 出现描述冲突时，以英文版本为准。
