# RiskLens MVP (FastAPI)

这是一个可本地运行的最小可用项目（MVP）：
- 后端：FastAPI
- 前端：`templates/ + static/` 原生 HTML/CSS/JS
- 目标：`GET /` 页面输入 ticker 后，调用 `POST /api/assess` 返回风险评估结果

## 1. 功能清单

- `GET /health`：健康检查
- `GET /docs`：Swagger 文档
- `GET /`：前端页面
- `POST /api/assess`：单 ticker 风险评估
- `POST /api/v1/assess`：兼容多 ticker 批量评估（简化版）

## 2. 项目结构

```text
RiskLens/
├── main.py                    # FastAPI 启动入口（uvicorn main:app）
├── src/
│   ├── data_fetcher.py        # 已有数据获取逻辑（复用）
│   ├── ratio_analyzer.py      # 已有比率分析逻辑（复用）
│   ├── zscore.py              # 已有 Z-Score 逻辑（复用）
│   └── services/
│       └── assessment_service.py   # 新增服务层（业务编排）
├── templates/
│   └── index.html             # 页面模板
├── static/
│   ├── css/app.css            # 页面样式
│   └── js/app.js              # 前端交互脚本
├── requirements.txt
├── .env.example
└── run_app.sh
```

## 3. 安装与启动

### 3.1 创建环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 启动服务

```bash
uvicorn main:app --reload
```

或一键启动：

```bash
./run_app.sh
```

## 4. 访问地址

- 首页：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/health`
- API 文档：`http://127.0.0.1:8000/docs`

## 5. API 快速示例

### 5.1 单 ticker 评估

```bash
curl -X POST http://127.0.0.1:8000/api/assess \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","data_source":"yfinance"}'
```

### 5.2 离线演示（推荐）

当本机网络不可用时使用 `demo`：

```bash
curl -X POST http://127.0.0.1:8000/api/assess \
  -H "Content-Type: application/json" \
  -d '{"ticker":"DEMO","data_source":"demo"}'
```

## 6. 配置说明

可选复制模板：

```bash
cp .env.example .env
```

当前 MVP 使用的环境变量：
- `APP_NAME`：应用名称（默认 `RiskLens MVP`）
- `APP_PORT`：本地端口（默认 `8000`）
- `ASSESS_TIMEOUT_SECONDS`：单次评估超时时间（秒，默认 `25`）
- `ENVIRONMENT` / `DEBUG` / `SENTRY_DSN`：预留给现有监控能力

## 7. Smoke 测试（推荐）

服务启动后执行：

```bash
./smoke_test.sh http://127.0.0.1:8000
```

会检查：
- `/health`
- `/docs`
- `/`
- `/api/assess`（demo 闭环 + 参数校验）

## 8. 常见问题（FAQ）

1. 页面提示“请求失败，请稍后重试”
- 先确认后端是否已启动：访问 `/health`。
- 再确认前端调用地址是否同源（默认就是同源）。

2. 使用 `AAPL` 等真实 ticker 返回网络错误
- 说明第三方数据源不可达或被限流。
- 可先用 `ticker=DEMO` + `data_source=demo` 完成闭环验证。

3. `ModuleNotFoundError`
- 确认在项目根目录启动。
- 确认已激活 `.venv` 并安装 `requirements.txt`。

4. `GET /` 打开但没有结果
- 打开浏览器开发者工具查看请求是否调用 `/api/assess`。
- 检查返回 JSON 中 `error` 字段。

## 9. 说明

仓库中 `src/api.py` 与 `web/` 仍保留，作为原有实现与后续扩展参考；
当前 MVP 验收以 `main.py` 入口为准。
