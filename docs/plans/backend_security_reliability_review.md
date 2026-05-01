# 后端安全与可靠性修复计划

## Summary
目标是把后端从“请求可返回”提升到“请求可控、失败可降级、结果可解释”。优先修复共同根因：阻塞外部调用没有真正超时控制、错误信息外泄、并发期间的全局状态污染、批量请求在单点异常下整体失败、缓存无上限。

## Key Changes
- `src/api.py`
  - 给 `AssessmentRequest`、`CovenantCheckRequest`、`PdfExportRequest` 增加更严格的输入边界，至少限制 ticker / query 长度、字符集和 PDF payload 规模。
  - 把 `process_ticker` 改成“单 ticker 失败不会拖垮整批”，补上 `except Exception` 兜底，并返回安全的 per-ticker 错误对象。
  - 去掉 `symbol search` 和 PDF 导出里对客户端暴露的 `str(exc)`，统一改成短错误码 + 安全提示，细节只进日志。
  - 停用 `_temporarily_clear_proxy_env` 的进程级 `os.environ` 修改，改成单线程锁或 per-call proxy 配置。
  - PDF 导出改为受限模型校验后再渲染，渲染本身放到线程池/专用 executor，避免阻塞事件循环。

- `src/data_fetcher.py`
  - 收紧 `retry_with_backoff` 的重试范围，只重试真正的网络/429 类错误，不重试无数据、字段缺失或明显业务失败。
  - 给缓存增加 `maxsize`，并为相同 ticker/source 增加 single-flight，避免并发击穿和内存无限增长。
  - 保留现有错误分类，但不要把底层异常原文再向上层透传到 API 响应。

- `src/services/rich_assessment_service.py`
  - 把“部分期间成功、部分期间失败”从隐式成功改成显式 `data_quality` 信息，至少包含 `status`、`failed_periods`、`latest_period_valid`。
  - 期间级异常只保留安全的 `reason_code`，不要把原始异常字符串直接放进返回值。
  - 维持当前“至少一个期间可算时返回结果”的行为，但让前端能明确看见这是 partial，而不是完整成功。

- `src/covenant_monitor.py`
  - 给 `FinancialCovenants` 加范围和有限数校验，拒绝负数、`NaN`、`inf` 这类无意义阈值。
  - 对缺失数据继续保持“默认 breach”，但消息要统一为安全文案，不带内部细节。

- `src/reportlab_pdf_exporter.py` / `src/pdf_report_core.py`
  - 给 PDF 输入增加总体大小和结构校验，限制 `history`、`rows`、`detail_rows`、字符串长度。
  - 对输出文件名做白名单清洗，避免报告 ticker 直接进入 `Content-Disposition`。
  - 保持现有“校验失败即拒绝生成”的保守策略，但把错误输出收敛成稳定的客户端错误码。

## Test Plan
- API 层测试：
  - 超长/非法 ticker、query、PDF report 字段应被 422 拒绝。
  - 单 ticker 普通异常不应让整批 `/api/v1/assess` 失败。
  - symbol search、PDF 导出不再回传 `str(exc)`、`original_error`、路径、代理 URL 等敏感内容。
  - timeout 场景仍返回 504，但不会继续泄漏内部细节。

- 并发与缓存测试：
  - 同一 ticker 并发 miss 时只触发一次上游调用。
  - 缓存达到上限后会淘汰旧项。
  - 代理清理逻辑不会污染并发请求。

- 业务可靠性测试：
  - 某些期间失败时，返回结果里必须带 `partial`/`failed_periods` 信息。
  - 所有期间失败仍应返回 422。
  - covenant 阈值的负数/极端值/非有限数应被拒绝。

- PDF 测试：
  - 正常 payload 仍能生成 PDF。
  - 超大 payload、恶意 ticker filename、异常嵌套结构应被拒绝。
  - PDF 生成不应阻塞事件循环的主路径。

## Assumptions
- 保持现有 API 路径和响应大体兼容，不引入认证/权限变更。
- `demo` 数据源继续保留，只是作为显式输入时使用。
- 优先修高风险路径，不先做依赖锁定或大规模重构。
- 允许部分结果继续返回，但必须显式标注为 partial，而不是默认成功。
