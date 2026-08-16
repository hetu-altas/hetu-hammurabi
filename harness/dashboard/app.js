/* 宪章体系运行看板 · 前端逻辑（原生 JS，无外部依赖） */

const API = "/api";
let currentPeriod = "all";
let currentRunId = null;
let autoRefreshTimer = null;

const $ = (id) => document.getElementById(id);

/* ---------- 工具 ---------- */

function fmtPct(v) {
  return v === null || v === undefined ? "–" : (v * 100).toFixed(1) + "%";
}

function fmtTs(ts) {
  if (!ts) return "–";
  return ts.replace("T", " ").slice(0, 19);
}

function statusClass(status) {
  const map = { pass: "st-pass", fail: "st-fail", running: "st-running", blocked: "st-blocked" };
  return map[status] || "";
}

function statusText(status) {
  const map = { pass: "通过", fail: "失败", running: "运行中", blocked: "拦截" };
  return map[status] || status || "–";
}

function rateClass(rate) {
  if (rate >= 0.9) return "";
  if (rate >= 0.7) return "mid";
  return "low";
}

async function getJSON(path) {
  const resp = await fetch(API + path);
  if (!resp.ok) throw new Error(path + " -> " + resp.status);
  return resp.json();
}

/* ---------- 渲染 ---------- */

async function renderOverview() {
  const ov = await getJSON(`/stats/overview?period=${currentPeriod}`);
  $("ovTasks").textContent = ov.total_tasks;
  $("ovTasksFoot").textContent = `统计区间 ${ov.period_start || "–"} ~ ${ov.period_end || "–"}`;
  $("ovRuns").textContent = ov.total_node_runs;
  $("ovRunsFoot").textContent = `成功率基数含重试轮`;
  $("ovSuccess").textContent = fmtPct(ov.success_rate);
  $("ovSuccessBar").style.width = (ov.success_rate * 100).toFixed(1) + "%";
  $("ovGate").textContent = fmtPct(ov.gate_block_rate);
  $("ovGateBar").style.width = (ov.gate_block_rate * 100).toFixed(1) + "%";
  $("ovRunsFoot").textContent = `门禁拦截 ${ov.gate_block_count} 次 / 放行 ${ov.gate_pass_count} 次`;
}

async function renderBenchmark() {
  const data = await getJSON("/stats/benchmark");
  const el = $("benchmarkBox");
  if (!data.dsh || !data.opencode) {
    el.innerHTML = `<div class="empty-hint">引擎性能对比数据不足（需 DSH 与 opencode 各至少一个可算任务）</div>`;
    return;
  }
  const d = data.dsh, o = data.opencode;
  const fastAvg = Math.round((1 - data.ratio_avg) * 100);
  const fastMed = Math.round((1 - data.ratio_median) * 100);
  el.innerHTML = `
    <div class="bench-grid">
      <div class="bench-col">
        <div class="bench-engine">DSH <span class="src-live">(/cc)</span></div>
        <div class="bench-num">${d.avg_min} <small>分</small></div>
        <div class="bench-sub">中位 ${d.median_min} 分 · ${d.count} 个任务</div>
      </div>
      <div class="bench-vs">
        <div class="bench-ratio">快 ${fastAvg}%</div>
        <div class="bench-sub">平均</div>
        <div class="bench-ratio" style="margin-top:6px">快 ${fastMed}%</div>
        <div class="bench-sub">中位</div>
      </div>
      <div class="bench-col">
        <div class="bench-engine">opencode <span class="src-history">(历史)</span></div>
        <div class="bench-num">${o.avg_min} <small>分</small></div>
        <div class="bench-sub">中位 ${o.median_min} 分 · ${o.count} 个任务</div>
      </div>
    </div>
    <div class="bench-note">宪章流程任务平均耗时对比（已剔除跨天异常与人工执行任务 ${data.excluded.length} 项）</div>`;
}

async function renderNodes() {
  const data = await getJSON(`/stats/nodes?period=${currentPeriod}`);
  const tbody = document.querySelector("#nodesTable tbody");
  tbody.innerHTML = "";
  for (const n of data.nodes) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${n.node}</strong></td>
      <td>${n.node_name}</td>
      <td>${n.runs}</td>
      <td class="st-pass">${n.success}</td>
      <td class="st-fail">${n.fail}</td>
      <td>
        <div class="rate-cell">
          <span>${fmtPct(n.success_rate)}</span>
          <div class="rate-bar"><div class="rate-fill ${rateClass(n.success_rate)}" style="width:${(n.success_rate * 100).toFixed(1)}%"></div></div>
        </div>
      </td>
      <td>${n.avg_round}</td>`;
    tbody.appendChild(tr);
  }
}

async function renderGates() {
  const data = await getJSON(`/stats/gates?period=${currentPeriod}`);
  const verif = data.verification_count || 0;
  $("gateCount").textContent =
    `${data.count} 次拦截（验证性 ${verif} 次）/ 拦截率 ${fmtPct(data.rate)}`;
  const tbody = document.querySelector("#gatesTable tbody");
  tbody.innerHTML = "";
  if (!data.events.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-hint">无门禁拦截记录</td></tr>`;
    return;
  }
  for (const e of data.events) {
    const tr = document.createElement("tr");
    const reason = (e.detail && (e.detail.msg || e.detail.code)) || e.extra?.code || "";
    const isVerif = e.verification === true;
    tr.innerHTML = `
      <td class="${isVerif ? "st-running" : "st-blocked"}">${fmtTs(e.ts)}</td>
      <td title="${escapeHtml(e.run_id)}">${escapeHtml(shortRun(e.run_id))}</td>
      <td>${e.node_name || e.node}</td>
      <td>${isVerif ? `<span class="badge">验证性</span> ` : ""}${escapeHtml(String(reason))}</td>`;
    tbody.appendChild(tr);
  }
}

async function renderTasks() {
  const data = await getJSON(`/tasks?period=${currentPeriod}`);
  $("taskCount").textContent = `${data.tasks.length} 个`;
  const tbody = document.querySelector("#tasksTable tbody");
  tbody.innerHTML = "";
  for (const t of data.tasks) {
    const tr = document.createElement("tr");
    tr.className = "clickable";
    tr.dataset.runId = t.run_id;
    tr.innerHTML = `
      <td title="${escapeHtml(t.run_id)}">${escapeHtml(shortRun(t.run_id))}</td>
      <td>${escapeHtml(t.project || "–")}</td>
      <td>${t.date}</td>
      <td class="${statusClass(t.status)}">${statusText(t.status)}</td>
      <td>${t.node_count}</td>
      <td class="src-${t.source}">${t.source === "history" ? "历史" : "实时"}</td>`;
    tr.addEventListener("click", () => showDetail(t.run_id));
    tbody.appendChild(tr);
  }
}

async function showDetail(runId) {
  currentRunId = runId;
  const d = await getJSON(`/tasks/${encodeURIComponent(runId)}`);
  $("detailRunId").textContent = `· ${d.run_id}`;
  const body = $("detailBody");

  // 节点时间线
  let html = `<div class="timeline">`;
  for (const t of d.timeline) {
    const cls = statusClass(t.status) ? t.status : "";
    const gateTag = t.gate ? `<span class="tag">门禁:${t.gate === "gate_pass" ? "放行" : "拦截"}</span>` : "";
    const roundTag = t.retries ? `<span class="tag">重试 ${t.retries} 次</span>` : "";
    const detailMsg = t.detail && t.detail.msg ? `<div class="tl-detail">${escapeHtml(String(t.detail.msg))}</div>` : "";
    html += `
      <div class="tl-item ${cls}">
        <div class="tl-node">节点 ${t.node} · ${t.node_name} ${gateTag}${roundTag}</div>
        <div class="tl-meta">${fmtTs(t.start_ts)} → ${fmtTs(t.end_ts)} · 状态 ${statusText(t.status)}</div>
        ${detailMsg}
      </div>`;
  }
  html += `</div>`;

  // 事件流（最近 50 条）
  const events = d.events.slice(-50);
  html += `<div class="panel-title" style="margin-top:10px">事件流（最近 ${events.length} 条）</div>`;
  html += `<table class="tbl event-table"><tbody>`;
  for (const e of events) {
    const msg = e.detail && e.detail.msg ? ` · ${escapeHtml(String(e.detail.msg))}` : "";
    html += `<tr>
      <td>${fmtTs(e.ts)}</td>
      <td class="${statusClass(e.status)}">${e.event_type}</td>
      <td>${e.node_name || e.node}</td>
      <td>${msg}</td>
    </tr>`;
  }
  html += `</tbody></table>`;
  body.innerHTML = html;
}

/* ---------- 工具函数 ---------- */

function shortRun(runId) {
  if (runId.length <= 30) return runId;
  return runId.slice(0, 30) + "…";
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ---------- 刷新 ---------- */

async function refreshAll() {
  try {
    await Promise.all([renderOverview(), renderBenchmark(), renderNodes(), renderGates(), renderTasks()]);
    if (currentRunId) {
      try { await showDetail(currentRunId); } catch (e) { currentRunId = null; }
    }
    $("updatedAt").textContent = "更新于 " + new Date().toLocaleTimeString();
  } catch (err) {
    $("updatedAt").textContent = "加载失败: " + err.message;
  }
}

/* ---------- 事件绑定 ---------- */

document.querySelectorAll(".period-switch button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".period-switch button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentPeriod = btn.dataset.period;
    refreshAll();
  });
});

$("refreshBtn").addEventListener("click", refreshAll);
$("closeDetail").addEventListener("click", () => {
  currentRunId = null;
  $("detailBody").innerHTML = `<div class="empty-hint">点击上方任务行查看详情</div>`;
  $("detailRunId").textContent = "";
});

// 自动刷新（10 秒）
autoRefreshTimer = setInterval(refreshAll, 10000);

refreshAll();
