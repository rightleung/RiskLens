# RiskLens

语言：[English](../../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

RiskLens 把上市公司的公开财务数据整理成清晰的信用风险视图。输入一个或多个股票代码，就可以查看财务健康度、比较公司、检查贷款契约，并导出便于分享的报告。

它适合做初步筛查和分析，不替代正式信用评级或专业授信判断。

## 你可以用它做什么

- 在 Dashboard 中评估一家公司或一组公司。
- 查看 40+ 流动性、杠杆、盈利、效率和现金流指标。
- 查看 Altman Z-Score、风险区间和易读的隐含评级。
- 设置契约阈值，识别通过、违约或数据缺失。
- 对比不同期间和不同公司，减少手工整理表格。
- 导出 JSON、Excel 或适合汇报的 PDF。
- 使用英文、简体中文、繁体中文或日文界面。

## 从股票代码到风险视图

```text
输入股票代码 → 获取并标准化财务数据 → 计算风险信号 → 查看或导出结果
```

RiskLens 默认通过 `yfinance` 获取 Yahoo Finance 的全球上市公司数据，也可以启用 AKShare 来补充中国市场数据。

## 快速开始

本地运行需要 Python 3.12+、Node.js、npm；实时市场数据还需要网络连接。

构建本地环境：

```bash
./scripts/rebuild_workspace.sh
```

启动 RiskLens：

```bash
./run_app.sh
```

然后打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

如果需要 AKShare 中国市场数据：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

## 使用方式

### Dashboard

可以按公司名称搜索，也可以直接输入股票代码。结果页会展示最新风险判断、历史趋势、财务报表、契约检查和导出入口。

本地常用页面：

- Dashboard：`http://127.0.0.1:8000/`
- 服务状态：`http://127.0.0.1:8000/health`
- 交互式 API 指南：`http://127.0.0.1:8000/docs`

### 命令行

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
```

使用 `--output path/to/file.json` 保存评估结果；运行 `./run_cli.sh --help` 查看全部选项。

### API

| 接口 | 用途 |
|---|---|
| `POST /api/v1/assess` | 评估一家或多家公司 |
| `GET /api/v1/symbols/search` | 查找上市公司股票代码 |
| `POST /api/v1/covenants/check` | 检查选定的契约阈值 |
| `POST /api/v1/reports/pdf` | 生成单公司 PDF |
| `POST /api/v1/reports/pdf/batch` | 将最多 10 份 PDF 打包下载 |

请求和响应示例可在 `/docs` 的交互式 API 指南中查看。

## 如何理解结果

- **Z-Score**：把五项资产负债和盈利信号合并为一个分数。
- **风险区间**：将结果归入 Safe、Grey 或 Distress。
- **隐含评级**：把分数转换成熟悉的信用语言，方便内部筛查。
- **指标与趋势**：解释结果由哪些财务变化推动。
- **契约检查**：把实际指标与你设置的阈值进行比较。
- **数据质量提示**：指出输入缺失和需要人工复核的部分。

如果已经设置契约阈值，但底层数据无法取得，RiskLens 会暂时标记为违约并要求人工复核，避免把缺失数据静默当作通过。

## 使用边界

- 隐含评级是 RiskLens 的内部解释，不是 S&P 或其他评级机构发布的评级。
- 公开市场数据可能延迟、重述、缺失，且不同会计准则下的科目映射可能不同。
- 缺少历史市值时，历史评分可能使用当前市值。
- Altman 模型只是一个风险信号，还应结合行业、股东背景、流动性和定性判断。
- RiskLens 不提供投资、法律或授信建议。

## 参与开发

提交改动前运行：

```bash
pytest
cd web && npm run lint && npm run build && npm run e2e:preflight
```

主应用由 `src/api.py` 和 `web/` 中的 React 应用组成。根目录 `main.py` 仅保留用于兼容性检查。

## 使用指南

- [RiskLens 如何工作](../architecture/ARCHITECTURE_zh-CN.md)
- [RiskLens 如何理解信用风险](../methodology/METHODOLOGY_zh-CN.md)
- [使用 Excel 导出](../report-workbook/REPORT_WORKBOOK_SPEC_zh-CN.md)
- [其他语言文档](./README.md)
- [发布检查清单](../review/repository-release-checklist.md)
