# RiskLens — 机构信贷风险与契约监测平台

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*一个专为机构信贷评估、强大的财务报表统一化处理以及持续的贷后契约监测而打造的企业级编排框架。*

---

## 🏛️ 项目目标

在商业及机构银行业务 (CIB) 中，企业借款人财务数据的自动化接入、统一化规范以及实时监测是一个关键的运营瓶颈。**RiskLens** 致力于消除杂乱无章、非结构化的财务报表与具备可操作性、可审计的信用洞察之间的鸿沟。

系统执行直通式处理 (STP) 管道以提取多样化的财务数据阵列，标准化计算超过 30 种基础信用比率，并客观地运用 **Altman Z-Score 模型**，将信贷敞口划分为安全 (Safe)、灰色 (Grey) 以及违约危机 (Distress) 档次。

## 🚀 企业级能力

### 1. 统一的全球数据标准化处理
- **多市场解析**：无缝获取并标准化美国、香港以及**中国大陆 (A股)** 市场的数据架构。
- **双语分类标准**：内置逻辑将复杂的中国在岸财务报告（通过 AKShare）直接映射为符合 IFRS/US GAAP 的等效标准。
- **动态周期解析**：处理并年化极其不规则的财年边界，包括累计的在岸季度报表（一季报、中报、三季报）以及离散的离岸报告。

### 2. 算法信贷评级体系 (`POST /api/v1/assess`)
- **Altman Z-Score 引擎**：自动化执行专为公众公司债务量身定制的多元破产预测公式。
- **压力差异化分析**：通过在 4 个财务周期内对利息保障倍数、FCF/债务 以及 债务/EBITDA 的轨迹进行交叉验证，程序化地分离企业的优势和劣势。
- **隐含标普评级转换**：将 Z-Score 输出直接投射到标准普尔 (S&P) 等效的机构评级（从 AAA 到 D），以便即时进行投资组合的分类与筛查。

### 3. 贷后契约监测 (`POST /api/v1/covenants/check`)
- **自动化合规性审查**：根据可定制的、基于特定贷款合同的财务契约（例如，最低流动性要求、最高杠杆率上限）评估最新传入的财务数据。
- **保守失败熔断机制**：为避免发生“假阴性”（因数据缺失而错误得判断为达标），数据不可用或出现异常的 NaN 值将安全地触发技术违约警报，强制交由承销商人工复核。
- **JSON-Schema 触发器**：具备通过结构化异常载荷（Payload）与下游核心银行系统或警报仪表板进行本机集成的能力。

---

## 📊 分析框架

RiskLens 仅依赖经过交叉验证的量化指标。核心评分代理使用 **Altman Z-Score 模型**，该模型将流动性、盈利能力、营运效率、杠杆率以及市场估值综合成一个预测违约概率的单一维度。

> *有关 Z-Score 权重的严谨数学分解、阈值映射表以及 30 多种底层信贷风险比率（例如 自由现金流/债务比率、利息保障倍数）的详细定义，请参阅 [METHODOLOGY.md](./METHODOLOGY_zh-CN.md)。*

**1.0 范围说明：** 当前 API 运行的评分模型仅使用 Altman Z-Score。`src/credit_risk_assessment.py` 为历史/实验性框架，未接入 FastAPI 服务。

---

## 🛠️ 技术栈与系统架构

基于严格的关注点分离原则构建，确保高吞吐量、并发能力和可靠性：

- **数据网关**：异步 `FastAPI` (Python) 执行环境，处理用以提取数据和进行多语言语义翻译的并发 HTTP 流。
- **分析引擎**：高度向量化的 `Pandas` 和 `Numpy` 核心，实现瞬时的时序财务聚合计算。
- **类型安全**：端到端的 `Pydantic` Schema 强制约束，确保在执行分析逻辑前提供绝不妥协的数据验证。
- **客户端界面**：基于 `Vite` 运行的极速响应 React 19 SPA。具备零延迟的控件切换状态、动态数据可视化以及强大的国际化支持。
- **本地化支持 (i18n)**：开箱即用的原生本地化能力，覆盖 `en`、`zh-CN`、`zh-TW` 和 `ja` 四种语言——配备完全翻译的财务报表分类目录以及 AI 辅助的跨国公司名称语义匹配。

---

## 🏁 部署协议

### 1. 通过配套网关执行
```bash
# 实例化完整的 API 以及前端环境
./run_app.sh
```

### 2. 手动启动
```bash
# 安装依赖
pip install -r requirements.txt

# 点燃 ASGI 服务器
cd src
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
*API Swagger / OpenAPI 接口文档访问地址：`http://localhost:8000/docs`*

### 3. 从 Linux 迁移到 macOS 后建议
```bash
# 1) 删除旧环境并重建（避免跨平台二进制残留）
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 2) 前端依赖重装
cd web
npm ci
```

---

## 👨‍💻 作者
**Right Leung**
