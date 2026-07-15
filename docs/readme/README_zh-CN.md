# RiskLens

语言: [English](../../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

RiskLens 是面向机构信贷风险评估的平台。它会为上市公司获取财务数据，计算 40+ 信用与经营比率，将 Altman Z-Score 映射为类 S&P 信用评级，检查贷后契约，并输出 Dashboard、JSON、Excel 和 PDF 报告。

## 功能范围

- 通过 FastAPI + React Dashboard 进行多 ticker 信用评估。
- 通过 `yfinance` 获取财务数据，并可选接入 AKShare 中国市场数据。
- 覆盖流动性、偿债能力、盈利能力、营运效率和现金流比率。
- Altman Z-Score 风险区间与类 S&P 评级映射。
- 契约阈值检查；当配置了阈值但数据缺失时，按尽调安全原则默认视为 breach。
- 前端术语支持英文、简体中文、繁体中文和日文。
- 支持 API JSON、前端工作簿导出和完整 PDF 导出。

## 运行路径

RiskLens 有两条后端路径：

| 路径 | 入口 | 用途 |
|------|------|------|
| Dashboard | `./run_app.sh` -> `src/api.py` | 主 FastAPI API 与 React SPA，运行在 `http://127.0.0.1:8000` |
| MVP 兼容 | `main.py` | 保留旧版 `/api/assess` 兼容与 smoke 检查 |

Dashboard 路径会从 `web/dist/` 托管 React 构建产物。运行 `./run_app.sh` 前需先构建前端。

## 环境要求

- Python 3.12+
- 用于前端的 Node.js 和 npm
- 实时 `yfinance`/AKShare 数据需要网络访问

## 快速开始

重建完整本地环境：

```bash
./scripts/rebuild_workspace.sh
```

该脚本会重建 `.venv`，安装 Python dev 依赖，执行 `npm ci`，并构建 `web/dist/`。

如需 AKShare 中国市场数据支持：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

启动 Dashboard：

```bash
./run_app.sh
```

访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 手动安装

后端：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
```

前端：

```bash
cd web
npm ci
npm run build
```

前端开发服务器：

```bash
cd web
npm run dev
```

## CLI

在仓库根目录使用启动器：

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
./run_cli.sh sources
./run_cli.sh version
```

CLI 在适用位置支持 `auto`、`yfinance`、`akshare` 和 `demo` 数据源。使用 `--output path/to/file.json` 可写入 JSON 文件，使用 `--compact` 可输出紧凑 JSON。

可选 shell 快捷方式：

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/risklens" ~/.local/bin/risklens
```

之后可运行：

```bash
risklens assess NVDA AMD --data-source yfinance
```

## API 示例

### 信用评估

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"tickers":["NVDA","0700.HK"],"data_source":"yfinance","include_suggestions":true}'
```

### 公司搜索

```bash
curl "http://127.0.0.1:8000/api/v1/symbols/search?q=apple&limit=20"
```

### 契约检查

```bash
curl -X POST http://127.0.0.1:8000/api/v1/covenants/check \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","data_source":"yfinance","covenants":{"min_current_ratio":1.2,"max_debt_to_equity":2.0}}'
```

### PDF 导出

`POST /api/v1/reports/pdf` 接收 `/api/v1/assess` 返回的单公司评估 payload。节选结构：

```json
{
  "report": { "ticker": "NVDA" },
  "lang": "zh-CN",
  "theme": "dark"
}
```

支持语言：`en`、`zh-CN`、`zh-TW`、`ja`。支持主题：`dark`、`light`。

批量下载使用 `POST /api/v1/reports/pdf/batch`，`reports` 支持 1–10 份报告。
响应为 `RiskLens_PDF_Reports.zip`，并带有 `X-ZIP-SHA256`/`X-ZIP-Bytes` 完整性校验头。
CJK 导出默认使用 `src/assets/fonts/` 中随包提供的 Noto 字体；部署时可通过
`RISKLENS_FONT_ZH_CN`、`RISKLENS_FONT_ZH_TW`、`RISKLENS_FONT_JA_BODY` 或
`RISKLENS_FONT_JA_HEADING` 覆盖字体路径。

## 测试

运行后端测试：

```bash
pytest
```

运行单个测试文件：

```bash
pytest tests/test_zscore.py
```

运行前端检查：

```bash
cd web
npm run lint
npm run build
npm run e2e:preflight
```

针对 MVP 兼容应用运行 legacy smoke 检查：

```bash
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 18000
./smoke_test.sh http://127.0.0.1:18000
```

## 项目结构

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
├── web/
│   ├── src/
│   └── dist/
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── readme/
│   └── report-workbook/
└── main.py
```

## 关键模块

| 模块 | 职责 |
|------|------|
| `src/api.py` | Dashboard FastAPI 应用、API 路由、SPA 静态托管、并发限制 |
| `src/services/rich_assessment_service.py` | Dashboard 多期间评估流水线 |
| `src/services/assessment_service.py` | Legacy MVP/CLI 单期间评估流水线 |
| `src/data_fetcher.py` | 财务数据获取与缓存 |
| `src/ratio_analyzer.py` | 40+ 财务比率计算 |
| `src/zscore.py` | Altman Z-Score 与评级映射 |
| `src/covenant_monitor.py` | 契约阈值检查 |
| `src/reportlab_pdf_exporter.py` | 完整 PDF 报告生成入口 |
| `web/src/App.tsx` | React Dashboard 主界面 |

## 配置

配置来自环境变量和可选 `.env` 文件。创建本地配置时可从 `.env.example` 开始。

常用配置：

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `APP_PORT` | `8000` | 本地 Dashboard 端口 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 前端开发来源 |
| `ASSESS_MAX_CONCURRENCY` | `8` | 并发 ticker 评估数 |
| `ASSESS_TICKER_TIMEOUT_SECONDS` | `20` | 单 ticker 评估超时 |
| `SYMBOL_SEARCH_TIMEOUT_SECONDS` | `8` | 公司搜索超时 |
| `CACHE_TTL_SECONDS` | `600` | 财务数据缓存 TTL |
| `SENTRY_DSN` | 空 | 仅设置后启用 Sentry |
| `API_REPORT_DIR` | `/tmp/credit_api_reports` | Dashboard 比率/报告产物目录 |

## 文档

- [Architecture](../architecture/ARCHITECTURE.md)
- [Methodology](../methodology/METHODOLOGY.md)
- [Report workbook spec](../report-workbook/REPORT_WORKBOOK_SPEC.md)
- [Release review checklist](../review/repository-release-checklist.md)
- README 翻译：[zh-CN](./README_zh-CN.md)、[zh-TW](./README_zh-TW.md)、[ja](./README_ja.md)

如果翻译内容与英文文档冲突，以英文文档为准。
