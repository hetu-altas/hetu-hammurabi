/**
 * hetu-dashboard · browser 半区（client.js，手写 UMD，仿 DSH 官方构建产物形态）
 *
 * 结构：window.__ModuleLoader__.load({id, factory}) —— factory 内 require
 * react 等共享模块，导出 apply/inject（与 ui-workspace 等官方 client.js 一致）。
 *
 * 挂载点（均为 additive list seat，互不替换现有 UI）：
 * - sidebar.footer.action   ：侧边栏底部「宪章看板」按钮（折叠态显示图标）
 * - shell.overlay           ：全屏看板浮层（点击按钮开关）
 *
 * 数据：同源 fetch /api/hetu-dashboard/*（node 半区转发到看板服务 8790）；
 * 数据服务不可达时显示降级态。
 *
 * 说明：本文件为实际加载产物（无需构建链即可注册进 DSH web profile）；
 * 可构建源码见 src/client/index.tsx（等价的 React 源码，供构建链环境使用）。
 */

window.__ModuleLoader__.load({
  id: "@hetu-altas/ConstitutionCoding-Plugin", // 必须与包名一致（modules 按包名校验注册）
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
    let react = require("react");
    let { useState, useEffect, useSyncExternalStore, createElement: h, Fragment } = react;

    // ───────────────────────── CSS 注入（--dsw 主题变量） ─────────────────────────
    const css = `
      .hdb-overlay{position:fixed;inset:0;z-index:9999;background:color-mix(in srgb,var(--dsw-alias-overlay, rgba(0,0,0,.55)) 55%, transparent);display:flex;align-items:center;justify-content:center;padding:24px}
      .hdb-panel{width:min(1200px,96vw);height:min(820px,92vh);background:var(--dsw-panel-bg,var(--dsw-alias-surface, #161b22));border:1px solid var(--dsw-alias-border-l2,#2d333b);border-radius:12px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 12px 48px rgba(0,0,0,.5);color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-head{display:flex;align-items:center;justify-content:space-between;padding:12px 18px;border-bottom:1px solid var(--dsw-alias-border-l2,#2d333b);flex:none}
      .hdb-title{font-size:16px;font-weight:600;color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-title small{color:var(--dsw-alias-label-secondary,#8b949e);font-weight:400;margin-left:8px}
      .hdb-close{background:none;border:1px solid var(--dsw-alias-border-l2,#2d333b);color:var(--dsw-alias-label-secondary,#8b949e);border-radius:6px;width:28px;height:28px;cursor:pointer;font-size:14px}
      .hdb-close:hover{color:var(--dsw-alias-label-primary,#e6edf3);border-color:var(--dsw-alias-border-l3,#3a4250)}
      .hdb-body{flex:1;overflow:auto;padding:16px 18px;font-size:13px}
      .hdb-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
      .hdb-card{background:var(--dsw-alias-surface-l2,var(--dsw-panel-bg,#1c2330));border:1px solid var(--dsw-alias-border-l2,#2d333b);border-radius:10px;padding:12px 14px}
      .hdb-card b{display:block;font-size:24px;font-variant-numeric:tabular-nums;margin:4px 0 2px;color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-card span{color:var(--dsw-alias-label-secondary,#8b949e);font-size:12px}
      .hdb-section{margin:14px 0 6px;font-weight:600;color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-table{width:100%;border-collapse:collapse;background:var(--dsw-alias-surface-l2,var(--dsw-panel-bg,#1c2330));border:1px solid var(--dsw-alias-border-l2,#2d333b);border-radius:10px;overflow:hidden}
      .hdb-table th{text-align:left;padding:8px 12px;color:var(--dsw-alias-label-secondary,#8b949e);font-weight:500;font-size:12px;border-bottom:1px solid var(--dsw-alias-border-l2,#2d333b)}
      .hdb-table td{padding:8px 12px;border-bottom:1px solid var(--dsw-alias-border-l3,#21262d);font-variant-numeric:tabular-nums;vertical-align:top}
      .hdb-table tr:last-child td{border-bottom:none}
      .hdb-row-click{cursor:pointer}
      .hdb-row-click:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.04))}
      .hdb-ok{color:#3fb950}.hdb-fail{color:#f85149}.hdb-muted{color:var(--dsw-alias-label-secondary,#8b949e)}
      .hdb-rate{display:inline-block;width:52px;height:6px;background:var(--dsw-alias-surface,#0d1117);border-radius:3px;overflow:hidden;vertical-align:middle;margin-left:8px}
      .hdb-rate i{display:block;height:100%;background:#3fb950;border-radius:3px}
      .hdb-rate i.mid{background:#d29922}.hdb-rate i.low{background:#f85149}
      .hdb-empty{color:var(--dsw-alias-label-secondary,#8b949e);text-align:center;padding:28px 0}
      .hdb-error{color:#d29922;padding:20px;text-align:center;border:1px dashed var(--dsw-alias-border-l2,#2d333b);border-radius:10px}
      .hdb-tl{position:relative;padding-left:22px;margin:6px 0 12px}
      .hdb-tl:before{content:"";position:absolute;left:7px;top:4px;bottom:4px;width:2px;background:var(--dsw-alias-border-l2,#2d333b)}
      .hdb-tl-item{position:relative;margin-bottom:10px}
      .hdb-tl-item:before{content:"";position:absolute;left:-19px;top:4px;width:9px;height:9px;border-radius:50%;border:2px solid var(--dsw-alias-label-secondary,#8b949e);background:var(--dsw-panel-bg,#161b22)}
      .hdb-tl-item.pass:before{border-color:#3fb950;background:#3fb950}
      .hdb-tl-item.fail:before{border-color:#f85149;background:#f85149}
      .hdb-tl-item.running:before{border-color:#4f8cff;background:#4f8cff}
      .hdb-btn{display:flex;align-items:center;gap:8px;width:100%;background:none;border:none;color:var(--dsw-alias-label-secondary,#8b949e);cursor:pointer;padding:8px 12px;border-radius:8px;font-size:13px}
      .hdb-btn:hover{background:var(--dsw-alias-interactive-bg-hover,rgba(255,255,255,.04));color:var(--dsw-alias-label-primary,#e6edf3)}
      /* ── 引擎性能对比 ── */
      .hdb-bench{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;background:var(--dsw-alias-surface-l2,var(--dsw-panel-bg,#1c2330));border:1px solid var(--dsw-alias-border-l2,#2d333b);border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:12px}
      .hdb-bench-col{text-align:center}
      .hdb-bench-engine{color:var(--dsw-alias-label-secondary,#8b949e)}
      .hdb-bench-num{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-bench-num small{font-size:11px;color:var(--dsw-alias-label-secondary,#8b949e);font-weight:400}
      .hdb-bench-sub{color:var(--dsw-alias-label-secondary,#8b949e);font-size:11px}
      .hdb-bench-vs{text-align:center}
      .hdb-bench-ratio{color:#3fb950;font-size:16px;font-weight:700}
      .hdb-bench-note{grid-column:1/4;color:var(--dsw-alias-label-secondary,#8b949e);font-size:11px;text-align:center;border-top:1px solid var(--dsw-alias-border-l3,#21262d);padding-top:8px}

      /* ── 宪章流程状态栏（右侧 dock） ── */
      .hdb-dock{position:fixed;right:0;top:50%;transform:translateY(-50%);width:248px;background:var(--dsw-alias-surface,#161b22);border:1px solid var(--dsw-alias-border-l2,#2d333b);border-right:none;border-radius:10px 0 0 10px;z-index:9997;overflow:hidden;pointer-events:auto;box-shadow:-6px 0 24px rgba(0,0,0,.4);font-size:12px;color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-dock.minimized{width:34px;cursor:pointer}
      .hdb-dock-head{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:7px 10px;border-bottom:1px solid var(--dsw-alias-border-l2,#2d333b);background:var(--dsw-alias-surface-l2,#1c2330)}
      .hdb-dock-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .hdb-dock-title small{color:var(--dsw-alias-label-secondary,#8b949e);font-weight:400}
      .hdb-dock-min{background:none;border:none;color:var(--dsw-alias-label-secondary,#8b949e);cursor:pointer;font-size:12px;padding:0 2px}
      .hdb-dock-min:hover{color:var(--dsw-alias-label-primary,#e6edf3)}
      .hdb-dock-nodes{padding:6px 10px 10px;max-height:62vh;overflow:auto}
      .hdb-dock-idle{padding:14px 10px;color:var(--dsw-alias-label-secondary,#8b949e);text-align:center}
      .hdb-node{display:flex;align-items:center;gap:8px;padding:4px 0}
      .hdb-dot{width:8px;height:8px;border-radius:50%;background:var(--dsw-alias-label-secondary,#8b949e);flex:none}
      .hdb-dot.pass{background:#3fb950}.hdb-dot.fail{background:#f85149}
      .hdb-dot.running{background:#4f8cff;animation:hdb-pulse 1.2s ease-in-out infinite}
      @keyframes hdb-pulse{0%,100%{opacity:1}50%{opacity:.35}}
      .hdb-node-id{color:var(--dsw-alias-label-secondary,#8b949e);min-width:14px;font-variant-numeric:tabular-nums}
      .hdb-node-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .hdb-node-time{color:var(--dsw-alias-label-secondary,#8b949e);font-size:11px}
      @media (max-width:900px){.hdb-cards{grid-template-columns:repeat(2,1fr)}}
    `;
    const cssTagId = "@hetu-altas/ConstitutionCoding-Plugin/dashboard.css";
    if (typeof document !== "undefined" && document.querySelector("style[data-plugin-css=\"" + JSON.stringify(cssTagId).slice(1, -1) + "\"]") === null) {
      const tag = document.createElement("style");
      tag.dataset.plugin = "@hetu-altas/ConstitutionCoding-Plugin";
      tag.dataset.pluginCss = cssTagId;
      tag.textContent = css;
      document.head.appendChild(tag);
    }

    // ───────────────────────── 面板开关状态（模块级，跨 slot entry 共享） ─────────────────────────
    let open = false;
    const listeners = new Set();
    function setOpen(v) { open = v; listeners.forEach((l) => l()); }
    function getOpen() { return open; }
    function subscribe(l) { listeners.add(l); return () => listeners.delete(l); }
    function useOpen() { return useSyncExternalStore(subscribe, getOpen); }

    // ───────────────────────── 数据客户端（同源，node 半区转发） ─────────────────────────
    const API_BASE = "/api/hetu-dashboard/api"; // 转发后命中看板服务的 /api/*
    async function getJSON(path) {
      const resp = await fetch(API_BASE + path, { headers: { "accept": "application/json" } });
      if (!resp.ok) throw new Error(path + " -> " + resp.status);
      return resp.json();
    }
    function fmtTs(ts) { return ts ? ts.replace("T", " ").slice(0, 19) : "–"; }
    function pct(v) { return v == null ? "–" : (v * 100).toFixed(1) + "%"; }
    function stText(s) { return { pass: "通过", fail: "失败", running: "运行中", blocked: "拦截" }[s] || s || "–"; }
    function stClass(s) { return { pass: "hdb-ok", fail: "hdb-fail", blocked: "hdb-ok", running: "hdb-ok" }[s] || ""; }
    function rateCls(r) { return r >= 0.9 ? "" : r >= 0.7 ? "mid" : "low"; }
    function shortRun(id) { return id.length <= 34 ? id : id.slice(0, 34) + "…"; }

    // ───────────────────────── 看板浮层组件（shell.overlay） ─────────────────────────
    function DashboardOverlay() {
      const isOpen = useOpen();
      const [overview, setOverview] = useState(null);
      const [nodes, setNodes] = useState([]);
      const [gates, setGates] = useState(null);
      const [tasks, setTasks] = useState([]);
      const [detail, setDetail] = useState(null);
      const [error, setError] = useState("");
      const [period, setPeriod] = useState("all");
      const [bench, setBench] = useState(null);

      useEffect(() => {
        if (!isOpen) return;
        let alive = true;
        const load = async () => {
          try {
            const q = period === "all" ? "" : "?period=" + period;
            const [ov, nd, gt, tk, bm] = await Promise.all([
              getJSON("/stats/overview" + q),
              getJSON("/stats/nodes" + q),
              getJSON("/stats/gates" + q),
              getJSON("/tasks" + q),
              getJSON("/stats/benchmark"),
            ]);
            if (!alive) return;
            if (ov.ok === false) { setError(ov.reason || "看板数据服务不可用"); return; }
            setOverview(ov); setNodes(nd.nodes || []); setGates(gt); setTasks(tk.tasks || []); setBench(bm); setError("");
          } catch (e) {
            if (alive) setError("看板数据加载失败: " + e.message);
          }
        };
        load();
        const timer = setInterval(load, 10000);
        return () => { alive = false; clearInterval(timer); };
      }, [isOpen, period]);

      useEffect(() => { if (!isOpen) setDetail(null); }, [isOpen]);
      if (!isOpen) return null;

      const showDetail = async (runId) => {
        try {
          const d = await getJSON("/tasks/" + encodeURIComponent(runId));
          setDetail(d);
        } catch (e) { setError("任务详情加载失败: " + e.message); }
      };

      const cards = [
        ["任务总数", overview ? overview.total_tasks : "–"],
        ["节点运行次数", overview ? overview.total_node_runs : "–"],
        ["节点成功率", overview ? pct(overview.success_rate) : "–"],
        ["门禁拦截率", overview ? pct(overview.gate_block_rate) : "–"],
      ];

      return h("div", { className: "hdb-overlay", onClick: (e) => { if (e.target === e.currentTarget) setOpen(false); } },
        h("div", { className: "hdb-panel" },
          h("div", { className: "hdb-head" },
            h("div", { className: "hdb-title" }, "宪章体系运行看板",
              h("small", null, "hetu-hammurabi · " + (overview ? overview.period_start + " ~ " + overview.period_end : "加载中"))),
            h("button", { className: "hdb-close", onClick: () => setOpen(false), title: "关闭" }, "×")),
          h("div", { className: "hdb-body" },
            error ? h("div", { className: "hdb-error" }, error + "（请确认看板服务已启动: bash scripts/start_dashboard.sh）") : null,
            !error && h(Fragment, null,
              bench && bench.dsh && bench.opencode ? h("div", { className: "hdb-bench" },
                h("div", { className: "hdb-bench-col" },
                  h("div", { className: "hdb-bench-engine" }, "DSH /cc"),
                  h("div", { className: "hdb-bench-num" }, bench.dsh.avg_min, h("small", null, " 分")),
                  h("div", { className: "hdb-bench-sub" }, "中位 " + bench.dsh.median_min + " · " + bench.dsh.count + " 任务")),
                h("div", { className: "hdb-bench-vs" },
                  h("div", { className: "hdb-bench-ratio" }, "快 " + Math.round((1 - bench.ratio_avg) * 100) + "%"),
                  h("div", { className: "hdb-bench-sub" }, "平均")),
                h("div", { className: "hdb-bench-col" },
                  h("div", { className: "hdb-bench-engine" }, "opencode"),
                  h("div", { className: "hdb-bench-num" }, bench.opencode.avg_min, h("small", null, " 分")),
                  h("div", { className: "hdb-bench-sub" }, "中位 " + bench.opencode.median_min + " · " + bench.opencode.count + " 任务")),
                h("div", { className: "hdb-bench-note" }, "宪章流程平均耗时对比（剔除跨天异常与人工执行 " + (bench.excluded || []).length + " 项）")) : null,
              h("div", { className: "hdb-cards" }, cards.map(([k, v]) =>
                h("div", { className: "hdb-card", key: k }, h("span", null, k), h("b", null, v)))),
              h("div", { className: "hdb-section" }, "节点运行统计"),
              h("table", { className: "hdb-table" },
                h("thead", null, h("tr", null,
                  ["节点", "名称", "运行次数", "成功", "失败", "成功率", "平均轮次"].map((t) => h("th", { key: t }, t)))),
                h("tbody", null, nodes.map((n) =>
                  h("tr", { key: n.node },
                    h("td", null, n.node), h("td", null, n.node_name),
                    h("td", null, n.runs), h("td", { className: "hdb-ok" }, n.success),
                    h("td", { className: "hdb-fail" }, n.fail),
                    h("td", null, pct(n.success_rate),
                      h("span", { className: "hdb-rate" }, h("i", { className: rateCls(n.success_rate), style: { width: (n.success_rate * 100).toFixed(1) + "%" } }))),
                    h("td", null, n.avg_round))))),
              h("div", { className: "hdb-section" }, "门禁拦截记录" + (gates ? "（" + gates.count + " 次，验证性 " + (gates.verification_count || 0) + " / 拦截率 " + pct(gates.rate) + "）" : "")),
              h("table", { className: "hdb-table" },
                h("thead", null, h("tr", null, ["时间", "任务", "节点", "原因"].map((t) => h("th", { key: t }, t)))),
                h("tbody", null, gates && gates.events.length ? gates.events.map((e, i) =>
                  h("tr", { key: i },
                    h("td", { className: e.verification ? "hdb-muted" : "hdb-fail" }, fmtTs(e.ts)),
                    h("td", null, shortRun(e.run_id)),
                    h("td", null, e.node_name || e.node),
                    h("td", null, (e.verification ? "【验证性】" : "") + ((e.detail && (e.detail.msg || e.detail.code)) || "")))) :
                  h("tr", null, h("td", { colSpan: 4, className: "hdb-empty" }, "无门禁拦截记录")))),
              h("div", { className: "hdb-section" }, "任务列表（" + tasks.length + "）"),
              h("table", { className: "hdb-table" },
                h("thead", null, h("tr", null, ["任务（run_id）", "项目", "日期", "状态", "节点数", "来源"].map((t) => h("th", { key: t }, t)))),
                h("tbody", null, tasks.map((t) =>
                  h("tr", { key: t.run_id, className: "hdb-row-click", onClick: () => showDetail(t.run_id), title: "点击查看详情" },
                    h("td", null, shortRun(t.run_id)), h("td", null, t.project || "–"), h("td", null, t.date),
                    h("td", { className: stClass(t.status) }, stText(t.status)),
                    h("td", null, t.node_count),
                    h("td", { className: "hdb-muted" }, t.source === "history" ? "历史" : "实时"))))),
              detail ? h(Fragment, null,
                h("div", { className: "hdb-section" }, "任务详情 · " + detail.run_id),
                h("div", { className: "hdb-tl" }, detail.timeline.map((t) =>
                  h("div", { className: "hdb-tl-item " + (t.status || ""), key: t.node },
                    h("div", null, "节点 " + t.node + " · " + t.node_name,
                      t.gate ? h("small", { className: "hdb-muted" }, " 门禁:" + (t.gate === "gate_pass" ? "放行" : "拦截")) : null,
                      t.retries ? h("small", { className: "hdb-muted" }, " 重试 " + t.retries + " 次") : null),
                    h("div", { className: "hdb-muted" }, fmtTs(t.start_ts) + " → " + fmtTs(t.end_ts) + " · " + stText(t.status)),
                    t.detail && t.detail.msg ? h("div", { className: "hdb-muted" }, String(t.detail.msg)) : null)))) : null,
            ))))
    }

    // ───────────────────────── 侧边栏底部按钮（sidebar.footer.action） ─────────────────────────
    function DashboardButton() {
      const isOpen = useOpen();
      return h("button", {
        className: "hdb-btn",
        title: "宪章运行看板",
        onClick: () => setOpen(!isOpen),
      },
        h("span", { style: { fontSize: 14 } }, "📊"),
        h("span", null, isOpen ? "收起看板" : "宪章看板"));
    }

    // ───────────────────────── 宪章流程状态栏（右侧 dock） ─────────────────────────
    // 轮询看板 API：取最新 live 任务 → 节点时间线 → 渲染节点进展。
    // 数据来自 /cc 流程中模型按提示词要求记录的 runlog 事件。
    function CharterStatusDock() {
      const [task, setTask] = useState(null);
      const [detail, setDetail] = useState(null);
      const [error, setError] = useState("");
      const [minimized, setMinimized] = useState(false);

      useEffect(() => {
        let alive = true;
        const load = async () => {
          try {
            const tk = await getJSON("/tasks");
            const tasks = tk.tasks || [];
            // live 优先（实时事件权威）；无 live 时取日期最新的 history 任务
            // （模型按流程写状态文件即被 history 解析，状态栏据此兜底展示）
            let current = tasks
              .filter((x) => x.source === "live")
              .sort((a, b) => String(b.last_ts).localeCompare(String(a.last_ts)))[0];
            if (!current) {
              current = tasks
                .filter((x) => x.source === "history")
                .sort((a, b) =>
                  String(b.run_id).slice(0, 8).localeCompare(String(a.run_id).slice(0, 8)) ||
                  String(b.last_ts).localeCompare(String(a.last_ts)))[0];
            }
            if (!current) {
              if (alive) { setTask(null); setDetail(null); }
              return;
            }
            const d = await getJSON("/tasks/" + encodeURIComponent(current.run_id));
            if (!alive) return;
            setTask(current);
            setDetail(d);
            setError("");
          } catch (e) {
            if (alive) setError(e.message);
          }
        };
        load();
        const timer = setInterval(load, 5000);
        return () => { alive = false; clearInterval(timer); };
      }, []);

      if (minimized) {
        return h("div", { className: "hdb-dock minimized", title: "宪章流程状态（点击展开）", onClick: () => setMinimized(false) },
          h("div", { className: "hdb-dock-head" }, h("span", null, "📋")));
      }
      if (!task && !error) return null; // 空闲隐藏

      const nodes = detail ? detail.timeline : [];
      const done = nodes.some((n) => n.node === "7" && n.status === "pass");
      const stMap = { pass: "通过", fail: "失败", running: "进行中" };
      const rows = nodes.map((n) =>
        h("div", { className: "hdb-node", key: n.node },
          h("span", { className: "hdb-dot " + (n.status || "") }),
          h("span", { className: "hdb-node-id" }, n.node),
          h("span", { className: "hdb-node-name", title: (n.detail && n.detail.msg) || "" },
            n.node_name, " ", h("small", { className: "hdb-node-time" }, stMap[n.status] || n.status || "")),
          h("span", { className: "hdb-node-time" }, n.status === "pass" ? fmtTs(n.end_ts).slice(11) : ""))
      );

      return h("div", { className: "hdb-dock" },
        h("div", { className: "hdb-dock-head" },
          h("span", { className: "hdb-dock-title", title: task ? task.run_id : "" },
            "宪章流程", task ? h("small", null, " · " + shortRun(task.run_id)) : null),
          h("button", { className: "hdb-dock-min", title: "最小化", onClick: () => setMinimized(true) }, "—")),
        error ? h("div", { className: "hdb-dock-idle" }, "状态获取失败: " + error) :
        h("div", { className: "hdb-dock-nodes" },
          h("div", { className: "hdb-dock-idle", style: { padding: "2px 0 8px" } },
            done ? "✅ 流程已完成" : "⏳ 流程进行中 · " + fmtTs(task.last_ts)),
          rows)
      );
    }

    // ───────────────────────── 注册（与官方 client.js 一致的 apply/inject 形态） ─────────────────────────
    function apply(ctx) {
      ctx.slots.inject("sidebar.footer.action", () => ctx.slots.register({
        name: "sidebar.footer.action",
        id: "hetu-dashboard",
        label: "宪章看板",
      }, DashboardButton));
      ctx.slots.inject("shell.overlay", () => ctx.slots.register({
        name: "shell.overlay",
        id: "hetu-dashboard",
        label: "宪章运行看板",
      }, DashboardOverlay));
      ctx.slots.inject("shell.overlay", () => ctx.slots.register({
        name: "shell.overlay",
        id: "hetu-charter-status",
        label: "宪章流程状态栏",
        order: 100,
      }, CharterStatusDock));
    }
    var inject = ["slots"];

    exports.apply = apply;
    exports.inject = inject;
    return module.exports;
  }
});
