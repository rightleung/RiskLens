# RiskLens

語言：[English](../../README.md) | [简体中文](./README_zh-CN.md) | [繁體中文](./README_zh-TW.md) | [日本語](./README_ja.md)

RiskLens 將上市公司的公開財務資料整理成清楚的信用風險視圖。輸入一個或多個股票代碼，即可檢視財務健康度、比較公司、檢查貸款契約，並匯出方便分享的報告。

它適合用於初步篩選與分析，不取代正式信用評級或專業授信判斷。

## 你可以用它做什麼

- 在 Dashboard 中評估一家公司或一組公司。
- 檢視 40+ 流動性、槓桿、獲利、效率與現金流指標。
- 查看 Altman Z-Score、風險區間與易讀的隱含評級。
- 設定契約門檻，識別通過、違約或資料缺失。
- 比較不同期間與不同公司，減少手動整理試算表。
- 匯出 JSON、Excel 或適合簡報的 PDF。
- 使用英文、簡體中文、繁體中文或日文介面。

## 從股票代碼到風險視圖

```text
輸入股票代碼 → 取得並標準化財務資料 → 計算風險訊號 → 檢視或匯出結果
```

RiskLens 預設透過 `yfinance` 取得 Yahoo Finance 的全球上市公司資料，也可以啟用 AKShare 補充中國市場資料。

## 快速開始

本機執行需要 Python 3.12+、Node.js、npm；即時市場資料還需要網路連線。

建立本機環境：

```bash
./scripts/rebuild_workspace.sh
```

啟動 RiskLens：

```bash
./run_app.sh
```

然後開啟 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

如需 AKShare 中國市場資料：

```bash
RISKLENS_WITH_CN_DATA=1 ./scripts/rebuild_workspace.sh
```

## 使用方式

### Dashboard

可以依公司名稱搜尋，也可以直接輸入股票代碼。結果頁會顯示最新風險判斷、歷史趨勢、財務報表、契約檢查與匯出入口。

本機常用頁面：

- Dashboard：`http://127.0.0.1:8000/`
- 服務狀態：`http://127.0.0.1:8000/health`
- 互動式 API 指南：`http://127.0.0.1:8000/docs`

### 命令列

```bash
./run_cli.sh assess AAPL MSFT --data-source yfinance
./run_cli.sh search apple --limit 10
./run_cli.sh covenants AAPL --min-current-ratio 1.2 --max-debt-to-equity 2.0
```

使用 `--output path/to/file.json` 儲存評估結果；執行 `./run_cli.sh --help` 查看所有選項。

### API

| 端點 | 用途 |
|---|---|
| `POST /api/v1/assess` | 評估一家或多家公司 |
| `GET /api/v1/symbols/search` | 尋找上市公司股票代碼 |
| `POST /api/v1/covenants/check` | 檢查選定的契約門檻 |
| `POST /api/v1/reports/pdf` | 產生單一公司 PDF |
| `POST /api/v1/reports/pdf/batch` | 將最多 10 份 PDF 打包下載 |

請求與回應範例可在 `/docs` 的互動式 API 指南中查看。

## 如何理解結果

- **Z-Score**：將五項資產負債與獲利訊號合併為一個分數。
- **風險區間**：將結果歸入 Safe、Grey 或 Distress。
- **隱含評級**：把分數轉成熟悉的信用語言，方便內部篩選。
- **指標與趨勢**：說明結果由哪些財務變化推動。
- **契約檢查**：將實際指標與你設定的門檻比較。
- **資料品質提示**：指出輸入缺失與需要人工覆核的部分。

若已設定契約門檻，但底層資料無法取得，RiskLens 會暫時標記為違約並要求人工覆核，避免把缺失資料默認為通過。

## 使用邊界

- 隱含評級是 RiskLens 的內部解讀，不是 S&P 或其他評級機構發布的評級。
- 公開市場資料可能延遲、重編、缺失，且不同會計準則下的科目映射可能不同。
- 缺少歷史市值時，歷史評分可能使用目前市值。
- Altman 模型只是一項風險訊號，仍應結合產業、股東背景、流動性與定性判斷。
- RiskLens 不提供投資、法律或授信建議。

## 參與開發

提交變更前執行：

```bash
pytest
cd web && npm run lint && npm run build && npm run e2e:preflight
```

主要應用程式由 `src/api.py` 與 `web/` 中的 React 應用組成。根目錄 `main.py` 僅保留作為相容性檢查。

## 使用指南

- [RiskLens 如何運作](../architecture/ARCHITECTURE_zh-TW.md)
- [RiskLens 如何理解信用風險](../methodology/METHODOLOGY_zh-TW.md)
- [使用 Excel 匯出](../report-workbook/REPORT_WORKBOOK_SPEC_zh-TW.md)
- [其他語言文件](./README.md)
- [發布檢查清單](../review/repository-release-checklist.md)
