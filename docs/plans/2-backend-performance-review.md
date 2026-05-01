# Backend Performance Review Plan

## 性能结论

当前后端最大的性能瓶颈在数据抓取链路，而不是财务公式计算。`/api/v1/assess` 虽然在 API 层使用 `asyncio.Semaphore` 和 `ThreadPoolExecutor` 做并发隔离，但所有 yfinance 网络调用最终都会经过 `src/data_fetcher.py` 的全局 `_PROXY_CLEAR_LOCK`，并且锁内包含 `time.sleep(0.3)`、`Ticker.info`、年度报表和季度报表读取。这会把批量 ticker 的主要上游 I/O 串行化。

第二类热点是失败路径和超时路径：失败后会继续发起 yfinance 搜索建议，超时不会取消已提交的线程任务，抓取、搜索、covenant 和 PDF 共用同一个执行池，容易在慢上游或批量失败时互相拖垮。

第三类热点是报告生成：PDF 数据整形会多次重建表格矩阵、复制行对象并做全量扫描，渲染阶段一次性构造完整 story 和完整 PDF bytes。正常 5 个 period 的报告可接受，但 API 验证允许 50 个 period，极端 payload 下 CPU 和内存峰值会明显上升。

未发现当前活跃后端 API 有 Excel/XLSX 导出实现；后端只看到 `RatioAnalyzer.export_ratios()` 支持 JSON/CSV。

## 热点列表

### P0 - 确定性能问题：yfinance 全局锁串行化高频抓取

- 位置：`src/data_fetcher.py:42`, `src/data_fetcher.py:45`, `src/data_fetcher.py:58`, `src/data_fetcher.py:1052`, `src/data_fetcher.py:1056`, `src/data_fetcher.py:1057`, `src/data_fetcher.py:1058`, `src/data_fetcher.py:1059`, `src/data_fetcher.py:1060`, `src/data_fetcher.py:1061`, `src/data_fetcher.py:1062`, `src/data_fetcher.py:1063`, `src/data_fetcher.py:1065`
- 问题：所有 yfinance 调用都通过 `_PROXY_CLEAR_LOCK`，锁内执行完整上游网络读取和固定 sleep。
- 为什么慢：API 层并发 ticker 会排队等待同一把锁；`assess_max_concurrency=8`、`upstream_max_workers=12` 实际无法让 yfinance miss 并行。
- 触发场景：批量评估多个未缓存美股/HK tickers；多个用户同时搜索或评估；上游单个 ticker 慢时，后续 ticker 被串行阻塞。
- 优化建议：
  - 把 `run_yfinance_call()` 改成默认不改全局 `os.environ`，只在检测到 proxy/curl 相关失败时进入带锁 clear-proxy 的一次重试。
  - 在 `FinancialDataFetcher.get_financial_data()` 的 yfinance 分支中，先调用 `run_yfinance_call(..., clear_proxy=False)`；仅 `DataFetchErrorType.NETWORK_ERROR` 且错误文本包含 proxy/curl 时重试 `clear_proxy=True`。
  - 增加配置项，例如 `yfinance_clear_proxy_mode: "retry_only" | "always" | "never"`，默认 `retry_only`，保留兼容开关。
  - 如果 yfinance 当前版本支持显式 session/proxy 配置，优先用 per-call/session 级配置替代全局环境变量 mutation。
- 预期收益：未缓存批量 yfinance 请求从近似串行变为接近 `assess_max_concurrency` 并行；批量 8 个 ticker 的 wall time 预期可下降 40%-70%，具体取决于 Yahoo 单 ticker 延迟。

### P0 - 确定性能问题：失败后逐 ticker 追加搜索建议，放大失败路径

- 位置：`src/api.py:432`, `src/api.py:455`, `src/api.py:465`, `src/api.py:475`, `src/api.py:488`, `src/api.py:509`, `src/api.py:657`, `src/api.py:667`, `src/api.py:671`, `src/api.py:677`, `src/api.py:691`
- 问题：每个失败 ticker 都同步排队执行 `_search_tickers()`；搜索同样使用 yfinance 和同一个 fetch executor，并且 `_build_company_name_localized()` 可能为数字 symbol 再调用 AKShare。
- 为什么慢：主评估失败后没有立即返回，反而追加低优先级上游 I/O；批量全失败时，失败成本接近翻倍，还会占用同一线程池容量。
- 触发场景：批量输入无效 ticker、上游超时、Yahoo rate limit、网络异常、用户粘贴很多错误 symbol。
- 优化建议：
  - 新增请求字段或查询参数 `include_suggestions: bool = false`，默认评估接口不做建议搜索；前端需要时再调用 `/api/v1/symbols/search`。
  - 对 timeout、upstream_busy、internal_error 不触发建议搜索；只对 `invalid_ticker` 或 `no_data_available` 触发。
  - 给 `_search_tickers()` 加独立 TTL cache，例如 `SimpleCache(default_ttl=3600, maxsize=1000)`，key 为 normalized query + limit。
  - 搜索建议使用独立低优先级 executor 或更小 semaphore，不与主评估/PDF 抢 `_FETCH_CAPACITY`。
- 预期收益：批量失败和上游异常时响应时间可减少一次额外上游 round-trip；线程池被失败建议拖满的概率显著下降。

### P0 - 潜在性能风险：超时不取消线程任务，抓取/PDF/搜索共用同一容量池

- 位置：`src/api.py:186`, `src/api.py:192`, `src/api.py:196`, `src/api.py:199`, `src/api.py:213`, `src/api.py:217`, `src/api.py:446`, `src/api.py:847`, `src/api.py:899`
- 问题：`asyncio.wait_for()` 超时后，底层 `ThreadPoolExecutor` 任务仍继续运行；容量信号量直到线程函数真正返回才释放。PDF、评估、covenant、symbol search 共用同一个 `_FETCH_EXECUTOR` 和 `_FETCH_CAPACITY`。
- 为什么慢：慢上游会产生“幽灵任务”，请求已 504 但线程继续占用容量；CPU 型 PDF 也会抢占抓取线程。
- 触发场景：Yahoo/AKShare 卡住、rate limit 后长时间等待、多个大 PDF 导出与批量评估同时发生。
- 优化建议：
  - 拆分执行池：`_FETCH_EXECUTOR` 只跑外部 I/O，新增 `_PDF_EXECUTOR` 跑 ReportLab CPU 工作，新增 `_SEARCH_EXECUTOR` 或小容量 semaphore 跑建议搜索。
  - 给 yfinance/AKShare 网络层设置真实低层 timeout；若库不支持，包装 requests/curl session 或在失败分类里快速熔断。
  - `_run_in_fetch_executor()` 增加指标：active、queued/refused、timed_out_but_running；暴露到 health/debug 或日志。
  - 对同一 upstream error type 加短期 cooldown，避免 50 个 ticker 在 rate limit 时继续排队。
- 预期收益：慢上游时系统吞吐更稳定；PDF 导出不会压低评估接口可用性；503/504 后容量恢复更可预测。

### P1 - 确定性能问题：covenant 检查只用最新期，却抓取完整历史和公司画像

- 位置：`src/api.py:797`, `src/api.py:799`, `src/api.py:828`, `src/api.py:836`, `src/data_fetcher.py:1057`, `src/data_fetcher.py:1058`, `src/data_fetcher.py:1059`, `src/data_fetcher.py:1060`, `src/data_fetcher.py:1061`, `src/data_fetcher.py:1062`, `src/data_fetcher.py:1063`
- 问题：`/api/v1/covenants/check` 只用 `history[0]`，但 `get_financial_data()` 总是读取 info、年度三表、季度三表并构造完整 history。
- 为什么慢：covenant 高频监控路径做了 dashboard 才需要的多期数据抓取和转换。
- 触发场景：贷后监控批量轮询；同一 ticker 高频 covenant check；只关心当前 covenant 状态的 API 调用。
- 优化建议：
  - 给 `get_financial_data()` 增加选项：`period_mode="latest" | "dashboard"`、`include_profile=False`、`include_quarterly=True/False`。
  - covenant 路由调用 latest-only 模式，只取最新可用 balance/income/cash 和必要 market cap。
  - 缓存 key 纳入 mode，例如 `AAPL:yfinance:latest` 和 `AAPL:yfinance:dashboard`，避免轻量缓存被重型 payload 污染。
- 预期收益：covenant 单次请求减少 3-6 个 yfinance property 读取和多期 DataFrame 构造；高频监控路径延迟和内存分配明显下降。

### P1 - 确定性能问题：A 股 auto/akshare 路径过度串行抓取并强制 yfinance 补充

- 位置：`src/data_fetcher.py:620`, `src/data_fetcher.py:656`, `src/data_fetcher.py:682`, `src/data_fetcher.py:710`, `src/data_fetcher.py:711`, `src/data_fetcher.py:712`, `src/data_fetcher.py:832`, `src/data_fetcher.py:838`, `src/data_fetcher.py:840`, `src/data_fetcher.py:841`, `src/data_fetcher.py:844`
- 问题：A 股路径先后请求 AKShare 公司信息、profile、主营构成、三张报表，然后再请求 yfinance info 和 income statement 补 market cap/EBITDA。
- 为什么慢：多个独立 I/O 串行执行；yfinance supplement 还会进入全局 yfinance 锁。
- 触发场景：`data_source=auto` 或 `akshare` 分析 6 位 A 股 ticker；批量 A 股评估。
- 优化建议：
  - 将 AKShare profile/product/statement 独立请求并行化，至少三张报表可并行。
  - `include_profile=False` 时跳过 `stock_individual_info_em`、`stock_profile_cninfo`、`stock_zygc_em`。
  - 将 yfinance supplement 拆为可选：仅当确实缺失 market cap 或 EBITDA 且调用方需要 Z-Score/PDF 时执行；失败时不要阻塞主报表返回。
  - 给 AKShare profile 和 yfinance supplement 单独缓存，TTL 可长于财务报表。
- 预期收益：A 股单 ticker 冷启动延迟可减少多个串行 round-trip；批量 A 股请求对 yfinance 锁的依赖下降。

### P1 - 确定性能问题：重试范围过大，失败结果不缓存，可能重复打满上游

- 位置：`src/data_fetcher.py:202`, `src/data_fetcher.py:227`, `src/data_fetcher.py:230`, `src/data_fetcher.py:240`, `src/data_fetcher.py:245`, `src/data_fetcher.py:922`, `src/data_fetcher.py:923`, `src/data_fetcher.py:926`, `src/data_fetcher.py:976`, `src/data_fetcher.py:980`, `src/data_fetcher.py:983`, `src/data_fetcher.py:990`
- 问题：外层 `get_financial_data()` 对大函数整体重试；失败不进入缓存。single-flight 等待者在失败后发现无缓存，会再次抢 in-flight slot 重新请求。
- 为什么慢：一次网络错误可能重跑完整 AKShare/yfinance pipeline；稳定失败的 invalid/no-data/rate-limit 在短时间内被重复请求。
- 触发场景：热门错误 ticker、Yahoo rate limit、AKShare 临时不可用、多个并发请求同一失败 ticker。
- 优化建议：
  - retry 缩小到具体上游调用，不包裹完整 `get_financial_data()`。
  - 增加 negative cache，缓存 `invalid_ticker`、`no_data_available` 5-15 分钟，缓存 `rate_limit` 30-60 秒，缓存 network error 5-10 秒。
  - single-flight 存储 result 或 exception，让等待者复用同一次失败结果，而不是失败后重新 fetch。
  - rate limit 不做指数重试；直接短 TTL cooldown 并返回 429。
- 预期收益：异常峰值下显著减少重复请求和线程占用；同一坏 ticker 的并发请求从 N 次上游请求降到 1 次。

### P2 - 确定性能问题：比率计算多次重复 DataFrame 查找和重复验证

- 位置：`src/services/rich_assessment_service.py:88`, `src/services/rich_assessment_service.py:104`, `src/services/rich_assessment_service.py:105`, `src/services/rich_assessment_service.py:106`, `src/services/rich_assessment_service.py:357`, `src/ratio_analyzer.py:715`, `src/ratio_analyzer.py:739`, `src/ratio_analyzer.py:776`, `src/ratio_analyzer.py:853`, `src/ratio_analyzer.py:908`, `src/ratio_analyzer.py:953`, `src/ratio_analyzer.py:1000`, `src/ratio_analyzer.py:1016`
- 问题：每个 period 将 DataFrame copy 后，在 `calculate_all_ratios()`、`_build_raw_metrics()`、`_build_assessment()` 中反复 `.loc` 查找相同 key，并且每个 ratio category 重复验证 DataFrame。
- 为什么慢：单次不大，但批量 ticker x 多 period 会产生大量 pandas 标量查找和对象分配。
- 触发场景：批量 50 ticker；每个 ticker 包含季度 + 3 年历史；未来增加更多 ratio 或导出时。
- 优化建议：
  - 新增轻量 `FinancialStatementSnapshot` 或 `dict[str, float]`，在每个 period 开始时把 balance/income/cash 的 `Value` 列转换一次。
  - `RatioAnalyzer.calculate_all_ratios()` 内部使用 snapshot，category 函数接收 dict 或一个 value getter，不再重复 validate。
  - `_build_raw_metrics()` 和 `_build_assessment()` 复用同一 snapshot 和 ratios，不再重新查 DataFrame。
  - 保留 DataFrame 输入兼容层，避免大范围 API 变更。
- 预期收益：CPU 型计算部分减少 pandas lookup 和 validation 开销；网络 miss 场景收益有限，但缓存命中、demo、测试和批量本地计算会更快。

### P2 - 确定性能问题：PDF 数据整形存在 O(labels * periods * rows) 扫描和重复矩阵构造

- 位置：`src/html_pdf_exporter.py:1695`, `src/html_pdf_exporter.py:1721`, `src/html_pdf_exporter.py:1729`, `src/html_pdf_exporter.py:1731`, `src/html_pdf_exporter.py:1732`, `src/html_pdf_exporter.py:1755`, `src/html_pdf_exporter.py:1756`, `src/html_pdf_exporter.py:1757`, `src/html_pdf_exporter.py:1924`, `src/html_pdf_exporter.py:1930`, `src/html_pdf_exporter.py:1934`, `src/pdf_report_core.py:259`, `src/pdf_report_core.py:377`, `src/pdf_report_core.py:403`, `src/pdf_report_core.py:422`, `src/pdf_report_core.py:423`
- 问题：`_build_statement_sections()` 对每个 label 在每个 period 的 rows 里 `next(...)` 线性扫描；之后 `build_pdf_document_model()` 和 `_sanitize_pdf_document_model()` 又重复构造 summary/detail table rows。
- 为什么慢：PDF payload period/行数增长时，CPU 和内存开销非线性增长；大量中间 list/dict/string 被创建。
- 触发场景：手工传入接近 50 periods 的 PDF payload；后续若导出更完整 statement rows；批量 PDF 导出。
- 优化建议：
  - 在 `_build_statement_sections()` 中为每个 period 构建 `dict[label, value]` 索引，替换 `next(...)` 线性扫描。
  - 只在一个阶段构造 `table_rows` 和 `detail_table_rows`；`pdf_report_core` 只校验和清洗，不再重建已清洗矩阵。
  - PDF export request 增加 `include_appendix_detail: bool = true` 或内部 hard cap；默认保留当前输出，但对超过阈值的 detail rows 做分页/截断或异步生成。
  - 将 report history 上限从 50 调低到 dashboard 实际需要的上限，或按 `max_pdf_periods` 配置裁剪。
- 预期收益：大 PDF payload 的 CPU 时间和峰值内存下降；正常 5 period 报告小幅下降，极端 50 period 报告收益明显。

### P2 - 潜在性能风险：PDF 一次性构建完整 story 和 bytes，内存峰值偏高

- 位置：`src/reportlab_pdf_renderer.py:603`, `src/reportlab_pdf_renderer.py:607`, `src/reportlab_pdf_renderer.py:1095`, `src/reportlab_pdf_renderer.py:1130`, `src/reportlab_pdf_renderer.py:1190`, `src/reportlab_pdf_renderer.py:1207`, `src/reportlab_pdf_renderer.py:1208`, `src/api.py:920`, `src/api.py:921`, `src/api.py:922`
- 问题：渲染时先把所有 Paragraph/Table 放进 `story`，ReportLab 写入 `BytesIO` 后 `getvalue()` 复制为 bytes，API 再用 `BytesIO(pdf_bytes)` 包装。
- 为什么慢/耗内存：大报告生成时至少保留 flowables、buffer、bytes 多份对象；计算 SHA256 也需要再扫一遍 bytes。
- 触发场景：大 payload PDF 导出；并发导出多个 PDF。
- 优化建议：
  - PDF 执行池独立后限制并发，例如默认 2-4。
  - 如必须保留 `X-PDF-SHA256`，用 buffer `getbuffer()` 计算并返回 `Response(content=pdf_bytes)`；否则移除 hash header，直接 streaming buffer。
  - 对大 PDF 走异步任务/文件落盘下载，避免 API worker 长时间持有内存。
- 预期收益：并发 PDF 导出时内存峰值更低；不会挤占抓取线程。

### P3 - 潜在性能风险：legacy `main.py` 批量接口串行处理

- 位置：`main.py:179`, `main.py:184`, `main.py:190`
- 问题：legacy `/api/v1/assess` 对 `payload.tickers` 串行循环，每个 ticker 单独等待。
- 为什么慢：如果有人误用 legacy entrypoint，批量请求没有 API 层并发。
- 触发场景：直接运行 `main.py` 而不是 `src/api.py`；旧 smoke/client 还打 legacy endpoint。
- 优化建议：
  - 明确 legacy 不承载生产批量；或者复用 `src.api.run_credit_assessment` 的并发实现。
  - 在 docs 和 route description 中标注 primary dashboard API 为 `src.api:app`。
- 预期收益：只影响 legacy 入口；主 dashboard 路径不受影响。

## 优化优先级

1. P0：解除 yfinance 全局锁默认串行化；重构失败建议搜索；拆分 executor/capacity。
2. P1：新增 latest-only 抓取模式给 covenant；重构 retry/negative cache/single-flight exception 复用；优化 A 股路径 optional/profile/supplement。
3. P2：优化 ratio snapshot 和 PDF 表格索引/矩阵构造；限制 PDF 大 payload 和 PDF 并发。
4. P3：legacy 入口说明或并发化。

## 具体代码改动建议

### 1. 数据抓取锁与重试

- 修改 `src/data_fetcher.py`：
  - 增加 `YFinanceProxyMode` 或简单配置读取，默认 `retry_only`。
  - 保留 `run_yfinance_call(fn, clear_proxy=True)` 兼容，但新增 `run_yfinance_call_with_proxy_retry(fn)`。
  - yfinance 主分支先不持 `_PROXY_CLEAR_LOCK` 执行 `_do_yfinance_calls()`；捕获 proxy/curl/network 特征后再带锁重试一次。
  - 将固定 `time.sleep(0.3)` 移出全局锁；最好改为 per-host rate limiter，且只在真实上游调用前执行。
- 验收：
  - 批量 8 个未缓存 demo/mock yfinance ticker 在测试中能并发进入 `_do_yfinance_calls()`，不是串行等待同一锁。
  - proxy 相关回归测试仍覆盖 clear-proxy retry。

### 2. 失败建议搜索降级

- 修改 `src/api.py`：
  - `AssessmentRequest` 增加 `include_suggestions: bool = False`。
  - `process_ticker()` 只在 `include_suggestions` 且错误类型为 invalid/no-data 时调用 `fetch_suggestions()`。
  - timeout、upstream_busy、internal_error 直接返回空 suggestions。
  - `_search_tickers()` 增加 cache；cache key 使用 `query.strip().upper(), limit, strict`。
- 验收：
  - 默认批量失败请求不调用 `_search_tickers()`。
  - 显式 `include_suggestions=true` 时仍返回建议。
  - timeout 错误不触发额外 yfinance search。

### 3. 执行池隔离

- 修改 `src/api.py`：
  - 将 `_FETCH_EXECUTOR` 保留给 `get_financial_data` 和 AKShare/yfinance。
  - 新增 `_PDF_EXECUTOR`、`_PDF_CAPACITY`，默认 worker 数 2 或从 settings 读取。
  - 新增 `_SEARCH_CAPACITY` 或 `_SEARCH_EXECUTOR`，搜索建议容量小于主 fetch。
  - `export_full_pdf()` 使用 `_run_in_pdf_executor()`，`search_symbols()` 和建议搜索使用 search executor。
- 修改 `src/config.py`：
  - 增加 `pdf_max_workers`, `search_max_workers`, `yfinance_clear_proxy_mode`, `negative_cache_ttl_seconds` 等配置。
- 验收：
  - 并发 PDF 导出不会让 `/api/v1/assess` 立即返回 upstream_busy。
  - executor capacity 指标或日志可区分 fetch/pdf/search。

### 4. latest-only 抓取模式

- 修改 `src/data_fetcher.py`：
  - `get_financial_data(ticker, data_source='auto', *, mode='dashboard', include_profile=True, include_supplement=True)`。
  - yfinance mode 为 `latest` 时只构造最新 period；可跳过季度/年度多列转换。
  - `include_profile=False` 时不构造完整 `company_profile`，尽量避免 `Ticker.info`，优先 `fast_info` 或已有 statement 数据。
  - cache key 包含 mode/profile/supplement。
- 修改 `src/api.py` covenant 路由：
  - 调用 latest-only + no-profile 模式。
- 验收：
  - covenant check mock 测试断言不会访问 quarterly statements。
  - dashboard assess 结果结构保持不变。

### 5. single-flight 和 negative cache

- 修改 `src/data_fetcher.py`：
  - `_in_flight` value 从 `threading.Event` 扩展为包含 event/result/exception 的对象。
  - leader 完成后设置 result 或 exception；waiter 复用结果或抛同一类异常。
  - `_data_cache` 可缓存成功结果；新增 `_error_cache` 缓存可复用失败。
  - invalid/no-data/rate-limit/network 使用不同 TTL。
- 验收：
  - 并发 10 个同一失败 ticker 只触发一次上游 mock。
  - rate-limit 后短时间重复请求直接返回 429，不重新请求 Yahoo。

### 6. A 股路径拆分和可选 supplement

- 修改 `src/data_fetcher.py`：
  - 将 `_fetch_a_share_akshare()` 拆为 `_fetch_akshare_profile()`, `_fetch_akshare_statements()`, `_supplement_a_share_from_yfinance()`。
  - statement 三表可用小线程池并发，或顺序保守实现但 profile/supplement 受 include flags 控制。
  - yfinance supplement 失败只记录 degraded metadata，不让主 AKShare history 失败。
- 验收：
  - `data_source=akshare` 且 `include_supplement=False` 不调用 yfinance。
  - A 股 dashboard 默认仍有 market cap/EBITDA 能力；缺失时返回明确 data_quality。

### 7. Ratio snapshot

- 修改 `src/ratio_analyzer.py` 和 `src/services/rich_assessment_service.py`：
  - 增加 `dataframe_to_value_map(df) -> dict[str, float]`。
  - `calculate_all_ratios()` 开始处只转换一次，后续 category 使用 map getter。
  - rich service 在 period 内复用 balance/income/cash maps 给 raw metrics 和 assessment。
- 验收：
  - 现有 ratio/zscore 测试全部通过。
  - 用 monkeypatch 统计 `get_dataframe_value()` 调用次数，rich 单 period 下降至少 50%。

### 8. PDF 表格构造和限制

- 修改 `src/html_pdf_exporter.py`：
  - `_build_statement_sections()` 中构造 `rows_by_period_maps = [{label: value}]`，替换 `next(...)`。
  - `summary_rows` 翻译 bug 一并检查：当前 `build_pdf_context()` 翻译 `summary_rows`，但 section 实际 key 是 `rows`。
- 修改 `src/pdf_report_core.py`：
  - 避免对已经规范化的 `table_rows/detail_table_rows` 重复 rebuild；只做清洗/验证。
- 修改 `src/reportlab_pdf_exporter.py` 或 request model：
  - 增加 PDF period/row cap 配置，或在超限时返回 422。
- 验收：
  - PDF 视觉回归测试或现有 PDF 测试通过。
  - 构造 50 period mock payload 的 PDF model build 时间下降，内存峰值不高于现状。

## 验收标准

- 功能正确性：
  - `pytest` 全部通过。
  - `pytest tests/test_data_fetcher.py tests/test_rich_assessment_service.py tests/test_api.py -q` 通过（如果具体文件名不同，使用现有对应测试）。
  - 前端依赖的 `/api/v1/assess` JSON schema 不破坏；默认 response 不新增昂贵 suggestions。
- 性能回归：
  - 新增 mock 性能/并发测试覆盖：
    - 8 个不同 yfinance ticker 冷 miss 不被 `_PROXY_CLEAR_LOCK` 串行化。
    - 10 个同一失败 ticker 只触发 1 次上游 fetch。
    - covenant latest-only 不访问 quarterly statements。
    - PDF 导出使用 PDF executor，不占用 fetch capacity。
  - 在无真实网络的 mock benchmark 中记录：
    - 批量 assess wall time 接近单 ticker mock latency 的 `ceil(N / assess_max_concurrency)`。
    - 默认失败请求不调用 `_search_tickers()`。
- 资源控制：
  - settings 中可配置 fetch/search/pdf worker 数和 PDF 上限。
  - 超时、busy、rate-limit 日志能区分来源。

## 执行顺序

1. 加测试保护当前行为和性能边界：并发 yfinance、失败 suggestions、single-flight failure、covenant latest-only、PDF executor。
2. 拆分 executor 和 suggestions 降级，先减少失败路径和资源互相抢占。
3. 调整 yfinance proxy retry 策略，解除默认全局锁串行化。
4. 实现 single-flight result/exception 复用和 negative cache。
5. 增加 latest-only 抓取模式，并改 covenant 路由使用。
6. 优化 A 股可选 profile/supplement。
7. 引入 ratio snapshot，减少 pandas lookup。
8. 优化 PDF statement 索引和重复矩阵构造，增加 PDF 大 payload 限制。
9. 运行完整测试和 smoke test，记录主要 benchmark 结果到 PR 描述。

## 后续 LLM 可执行修改 Prompt

请在 `/Users/rightleung/Documents/Python/RiskLens` 仓库中按 `docs/plans/2-backend-performance-review.md` 执行后端性能优化。只修改后端代码和必要测试，保持前端 API 兼容。

优先完成 P0/P1：

1. 在 `src/api.py` 拆分 fetch/search/pdf executor 和 capacity；PDF 导出不得占用主 fetch capacity。
2. 给 `AssessmentRequest` 增加 `include_suggestions: bool = False`；默认失败不搜索建议，只在显式开启且错误类型为 invalid/no-data 时搜索。timeout/upstream_busy/internal_error 不搜索。
3. 给 `_search_tickers()` 加 TTL cache。
4. 修改 `src/data_fetcher.py` 的 yfinance 调用策略：默认不持全局 proxy lock；只有 proxy/curl/network 相关失败才带锁 clear-proxy 重试一次。保留配置开关兼容旧行为。
5. 重构 single-flight：等待者复用 leader 的成功结果或异常；新增 negative cache，避免同一失败 ticker 重复打上游。
6. 给 `get_financial_data()` 增加 latest/dashboard 模式和 include_profile/include_supplement flags；`/api/v1/covenants/check` 使用 latest-only + no-profile。

然后完成 P2：

7. 在 ratio 计算中加入 DataFrame -> value map snapshot，减少重复 `.loc` 和重复 validation。
8. 优化 PDF statement 构造：用 per-period label map 替换 `next(...)` 线性扫描，避免 `pdf_report_core` 重复重建 table rows，并给 PDF payload period/row 增加可配置上限。

验收要求：

- 运行 `pytest -q`。
- 重点新增或更新测试，覆盖并发不串行、失败不默认 suggestions、single-flight 失败复用、covenant latest-only、PDF executor 隔离。
- 不改变 `/api/v1/assess` 成功响应结构；新增字段只能是向后兼容的 request option。
- 最终回复说明改动文件、关键性能收益和测试结果。
