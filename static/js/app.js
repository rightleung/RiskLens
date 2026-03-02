(function () {
  const form = document.getElementById("assess-form");
  const statusEl = document.getElementById("status");
  const errorEl = document.getElementById("error");
  const resultEl = document.getElementById("result");
  const summaryEl = document.getElementById("summary");
  const metricsEl = document.getElementById("metrics");
  const submitBtn = document.getElementById("submit-btn");

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtn.textContent = isLoading ? "评估中..." : "开始评估";
  }

  function setStatus(text) {
    statusEl.textContent = text || "";
  }

  function setError(text) {
    errorEl.textContent = text || "";
  }

  function showResult(payload) {
    const assessment = payload.assessment || {};
    const warnings = payload.warnings || [];

    summaryEl.innerHTML = [
      `<p><strong>公司</strong>：${payload.company_name || "-"} (${payload.ticker || "-"})</p>`,
      `<p><strong>期间</strong>：${payload.period || "-"}</p>`,
      `<p><strong>Z-Score</strong>：${assessment.z_score ?? "N/A"}</p>`,
      `<p><strong>风险区间</strong>：${assessment.risk_zone || "N/A"}</p>`,
      `<p><strong>隐含评级</strong>：${assessment.implied_rating || "N/A"}</p>`,
      warnings.length ? `<p><strong>提示</strong>：${warnings.join("；")}</p>` : "",
    ].join("");

    metricsEl.textContent = JSON.stringify(payload.key_metrics || {}, null, 2);
    resultEl.classList.remove("hidden");
  }

  function extractErrorMessage(payload) {
    if (!payload) return "请求失败，请稍后重试。";
    if (typeof payload.error === "string") return payload.error;
    if (payload.detail && typeof payload.detail === "string") return payload.detail;
    if (payload.detail && typeof payload.detail === "object") {
      if (Array.isArray(payload.detail.errors)) return payload.detail.errors.join("; ");
      if (typeof payload.detail.error === "string") return payload.detail.error;
    }
    return "请求失败，请检查输入或稍后重试。";
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    setError("");
    setStatus("正在请求后端...");
    resultEl.classList.add("hidden");
    setLoading(true);

    const ticker = (document.getElementById("ticker").value || "").trim();
    const dataSource = document.getElementById("data_source").value;

    if (!ticker) {
      setError("请输入 ticker。");
      setStatus("");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/assess", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ticker,
          data_source: dataSource,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(extractErrorMessage(payload));
      }

      showResult(payload);
      setStatus("评估完成。");
    } catch (error) {
      setError(error.message || "无法连接后端，请确认服务已启动。");
      setStatus("");
    } finally {
      setLoading(false);
    }
  });
})();
