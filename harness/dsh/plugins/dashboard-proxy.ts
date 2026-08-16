/**
 * hetu-dashboard-proxy · 宪章看板挂接 DSH web GUI 插件（零构建方案）
 *
 * 机制：DSH 的 dsh-host-webserver 提供 webServer.register({kind, path, handler})，
 * 本插件注册两条前缀路由，代理到本地看板服务（默认 127.0.0.1:8790）：
 * - /dashboard            ：看板完整页面（独立 HTML，降级路径）
 * - /api/hetu-dashboard   ：看板数据同源通道（原生面板 client-plugin 的数据面）
 *
 * 挂接步骤（由 scripts/attach_dashboard_to_dsh.sh 自动完成）：
 *   1. 本插件复制到 $DSH_HOME/profiles/web/plugins/hetu-dashboard-proxy.ts
 *   2. web profile 的 cordis.patch.yml 追加 insert 行（loader 支持绝对路径 .ts 插件）
 *   3. 重启 dsh web 生效
 *
 * 依赖：看板服务（8790）需在运行（插件在服务未启动时返回友好提示页/降级 JSON）。
 */

import http from "node:http";

const PREFIX = "/dashboard";
const API_PREFIX = "/api/hetu-dashboard";
const UPSTREAM_HOST = process.env.HETU_DASHBOARD_HOST || "127.0.0.1";
const UPSTREAM_PORT = Number(process.env.HETU_DASHBOARD_PORT || 8790);

const name = "hetu-dashboard-proxy";
const inject = ["webServer"];

/** 剥掉前缀，得到看板服务内的路径（/dashboard → /；/api/hetu-dashboard/x → /x）。 */
export function stripPrefix(pathname, prefix) {
  if (pathname.startsWith(prefix)) {
    const rest = pathname.slice(prefix.length);
    return rest === "" ? "/" : rest;
  }
  return pathname;
}

/** 友好错误页：看板服务未启动（页面降级）。 */
function sendUnavailablePage(res, err) {
  res.writeHead(502, { "content-type": "text/html; charset=utf-8" });
  res.end(
    `<h2>宪章运行看板服务未启动</h2>` +
      `<p>请在 hetu-hammurabi 目录运行：<code>bash scripts/start_dashboard.sh</code>` +
      `（或启动 127.0.0.1:${UPSTREAM_PORT} 上的看板服务）</p>` +
      `<p style="color:#888">代理错误: ${String(err && err.message || err)}</p>`,
  );
}

/** 降级 JSON：数据通道不可用（原生面板统一识别 {ok:false}）。 */
function sendUnavailableJson(res, err) {
  const body = JSON.stringify({
    ok: false,
    reason: "dashboard service unavailable",
    detail: String(err && err.message || err),
  });
  res.writeHead(200, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  res.end(body);
}

/** 构造上游代理请求（共用逻辑；onError 决定降级响应形态）。 */
function proxyToUpstream(req, res, targetPath, onError) {
  const upstreamReq = http.request(
    {
      host: UPSTREAM_HOST,
      port: UPSTREAM_PORT,
      path: targetPath,
      method: req.method,
      headers: { ...req.headers, host: `${UPSTREAM_HOST}:${UPSTREAM_PORT}` },
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    },
  );
  upstreamReq.on("error", (err) => {
    onError(res, err);
  });
  req.pipe(upstreamReq);
}

function apply(ctx) {
  // 页面代理（降级路径）：/dashboard → 看板首页
  ctx.webServer.register({
    kind: "prefix",
    path: PREFIX,
    handler: async (req, res) => {
      const raw = new URL(req.url ?? "/", "http://x");
      proxyToUpstream(req, res, stripPrefix(raw.pathname, PREFIX) + raw.search, sendUnavailablePage);
    },
  });

  // 数据通道（原生面板）：/api/hetu-dashboard/* → 看板 API
  ctx.webServer.register({
    kind: "prefix",
    path: API_PREFIX,
    handler: async (req, res) => {
      const raw = new URL(req.url ?? "/", "http://x");
      proxyToUpstream(req, res, stripPrefix(raw.pathname, API_PREFIX) + raw.search, sendUnavailableJson);
    },
  });

  ctx.logger?.info?.(
    `[hetu-dashboard] 已挂接: ${PREFIX} + ${API_PREFIX} -> http://${UPSTREAM_HOST}:${UPSTREAM_PORT}/`,
  );
}

export { name, inject, apply };
export default { name, inject, apply };
