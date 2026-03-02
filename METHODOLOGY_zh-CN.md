# RiskLens 信用评级方法论

语言: [EN](./METHODOLOGY.md) | [简中](./METHODOLOGY_zh-CN.md) | [繁中](./METHODOLOGY_zh-TW.md) | [日本語](./METHODOLOGY_ja.md)

本文描述 RiskLens 用于生成内部信用评级与风险分数的量化框架。该方法将经典多变量违约预测模型（**Altman Z-Score**）与持续性的贷后契约监控结合在一起。

---

## 1. 核心评分架构：Altman Z-Score

RiskLens 将 **Altman Z-Score** 作为上市公司评分引擎的核心。Z-Score 是一个多变量公式，将企业财务健康的五个维度合成为单一预测分数。

**1.0 范围说明：** 当前在线 API 流水线仅使用 Altman Z-Score。`src/credit_risk_assessment.py` 中的历史评分框架不会被 FastAPI 服务调用。

### Z-Score 公式
`Z = 1.2(X1) + 1.4(X2) + 3.3(X3) + 0.6(X4) + 1.0(X5)`

其中：
- **X1（营运资金 / 总资产）**：衡量短期流动性和缓冲能力。
- **X2（留存收益 / 总资产）**：衡量累计盈利能力，惩罚新成立或长期亏损企业。
- **X3（EBIT / 总资产）**：衡量经营效率和资产产出能力，不受税负和杠杆影响。
- **X4（股权市值 / 总负债）**：引入市值维度，衡量市场对偿债能力的看法。
- **X5（销售收入 / 总资产）**：衡量资产周转效率与资本密集度。

### Z-Score 风险分区
原始 Z-Score 会映射为三档风险区间：
1. **Safe Zone（Z ≥ 2.99）**：财务稳健，未来 2 年破产概率统计上较低。
2. **Grey Zone（1.81 ≤ Z < 2.99）**：中度风险，建议加强监控并收紧授信。
3. **Distress Zone（Z < 1.81）**：未来 24 个月发生违约或重组的概率较高。

---

## 2. 隐含评级映射

为了将原始 Z-Score 转为可用于授信政策的机构语言，RiskLens 将风险分区映射到近似 S&P 语义的隐含评级。

| Z-Score 区间 | 分区 | 隐含评级 | 风险类别 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| ≥ 4.50 | Safe | **AAA / AA** | Prime | 偿债能力极强。 |
| 2.99 - 4.49 | Safe | **A** | Upper Medium | 偿债能力强，但受不利环境影响时会下滑。 |
| 2.50 - 2.98 | Grey | **BBB** | Lower Medium | 偿债能力尚可，保护垫中等。 |
| 1.81 - 2.49 | Grey | **BB** | Speculative | 短期尚可，但不确定性较高。 |
| 1.20 - 1.80 | Distress | **B** | Highly Speculative | 对经营/财务逆风较敏感。 |
| < 1.20 | Distress | **CCC / D** | Substantial Risk | 当前脆弱，依赖外部有利条件。 |

---

## 3. 贷后契约监控

Z-Score 提供的是时点性违约概率，契约指标则提供持续性的“预警系统”。RiskLens 对关键指标进行持续监控，以便在技术性违约发生前触发预警。

### 默认监控的契约指标
1. **杠杆测试**：`Debt / EBITDA < [Threshold]` —— 防止借款人通过经营或并购过度加杠杆。
2. **覆盖测试**：`EBITDA / Interest Expense > [Threshold]` —— 确保经营现金足以覆盖债务服务成本。
3. **流动性测试**：`Current Assets / Current Liabilities > [Threshold]` —— 确保短期资产可覆盖到期负债。

*说明：RiskLens 对贷后监控中的 `null` 或缺失值采用保守策略，默认视为 BREACH（需要人工复核），而非静默放行。*

---

## 4. 财务数据标准化

RiskLens 会做跨市场的财务科目标准化，以保证评分引擎输入一致：
- **美股/全球模型（yFinance）**：将标准 SEC XBRL 标签统一映射到 RiskLens 核心变量。
- **中国 A 股（AKShare）**：将大陆会计科目（例如 *长期借款*、*营业总收入*）动态映射到同一数学结构，确保不同市场结果可比。
