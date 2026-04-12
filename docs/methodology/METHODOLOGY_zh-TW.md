# RiskLens 信用評級方法論

語言: [EN](./METHODOLOGY.md) | [简中](./METHODOLOGY_zh-CN.md) | [繁中](./METHODOLOGY_zh-TW.md) | [日本語](./METHODOLOGY_ja.md)

本文說明 RiskLens 用於產生內部信用評級與風險分數的量化框架。此方法將經典多變量違約預測模型（**Altman Z-Score**）與持續性的貸後契約監控結合。

---

## 1. 核心評分架構：Altman Z-Score

RiskLens 以 **Altman Z-Score** 作為上市公司評分引擎核心。Z-Score 是一個多變量公式，將企業財務健康的五個維度合成為單一預測分數。

**1.0 範圍說明：** 線上 API 流程目前僅使用 Altman Z-Score。`src/credit_risk_assessment.py` 的舊評分框架不會由 FastAPI 服務呼叫。

### Z-Score 公式
`Z = 1.2(X1) + 1.4(X2) + 3.3(X3) + 0.6(X4) + 1.0(X5)`

其中：
- **X1（營運資金 / 總資產）**：評估短期流動性與緩衝能力。
- **X2（保留盈餘 / 總資產）**：衡量累積獲利能力，對新設或長期虧損公司較不利。
- **X3（EBIT / 總資產）**：衡量營運效率與資產產出能力，不受稅與槓桿干擾。
- **X4（股權市值 / 總負債）**：引入市值，評估市場對償債能力的看法。
- **X5（營收 / 總資產）**：衡量資產周轉效率與資本密集度。

### Z-Score 風險分區
原始 Z-Score 會映射為三個風險區間：
1. **Safe Zone（Z ≥ 2.99）**：財務體質穩健，2 年內破產機率統計上較低。
2. **Grey Zone（1.81 ≤ Z < 2.99）**：中度風險，建議加強監控並收緊授信。
3. **Distress Zone（Z < 1.81）**：未來 24 個月違約或重組機率較高。

---

## 2. 隱含評級映射

為了將原始 Z-Score 轉換為機構授信可用語言，RiskLens 將風險區間映射為近似 S&P 語義的隱含評級。

| Z-Score 區間 | 分區 | 隱含評級 | 風險類別 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| ≥ 4.50 | Safe | **AAA / AA** | Prime | 償債能力極強。 |
| 2.99 - 4.49 | Safe | **A** | Upper Medium | 償債能力強，但對不利環境敏感。 |
| 2.50 - 2.98 | Grey | **BBB** | Lower Medium | 償債能力尚可，保護墊中等。 |
| 1.81 - 2.49 | Grey | **BB** | Speculative | 近端尚可，但不確定性高。 |
| 1.20 - 1.80 | Distress | **B** | Highly Speculative | 對經營/財務逆風較脆弱。 |
| < 1.20 | Distress | **CCC / D** | Substantial Risk | 當前脆弱，依賴外部有利條件。 |

---

## 3. 貸後契約監控

Z-Score 提供時點違約機率；契約指標則是持續性的「預警系統」。RiskLens 持續監控關鍵指標，於技術性違約前觸發告警。

### 標準監控契約
1. **槓桿測試**：`Debt / EBITDA < [Threshold]` —— 防止借款人透過營運或併購過度加槓桿。
2. **覆蓋測試**：`EBITDA / Interest Expense > [Threshold]` —— 確保營運現金可覆蓋債務服務成本。
3. **流動性測試**：`Current Assets / Current Liabilities > [Threshold]` —— 確保短期資產足以覆蓋到期負債。

*說明：RiskLens 在貸後監控中對 `null` 或缺失值採保守策略，預設視為 BREACH（需人工覆核），而非默認通過。*

---

## 4. 財務資料標準化

RiskLens 對跨市場財務科目進行標準化，確保評分引擎輸入一致：
- **美股/全球模型（yFinance）**：將標準 SEC XBRL 標籤統一映射到 RiskLens 核心變數。
- **中國 A 股（AKShare）**：將大陸會計科目（例如 *長期借款*、*營業總收入*）動態映射到同一數學結構，確保跨市場結果可比。
