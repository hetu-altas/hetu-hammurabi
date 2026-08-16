/**
 * hetu-dashboard · node 半区（host 侧 cordis 插件）
 *
 * 职责：注册 /api/hetu-dashboard 前缀路由，把面板数据请求同源转发到
 * 看板数据服务（默认 127.0.0.1:8790，即 scripts/start_dashboard.sh 启动的
 * FastAPI 服务）。browser 半区只 fetch 同源路径，无跨域、无直连依赖。
 *
 * 降级：数据服务不可达时返回 {"ok": false, "reason": "..."}（200），
 * 由 browser 半区统一渲染降级态（不返回 502 HTML，方便前端处理）。
 *
 * 路由注册复用 DSH webServer.register({kind: "prefix", path, handler}) API
 * （与任务1 的 dashboard-proxy.ts 同一机制，已在本环境验证可用）。
 */

import http from "node:http";

const PREFIX = "/api/hetu-dashboard";
const UPSTREAM_HOST = process.env.HETU_DASHBOARD_HOST || "127.0.0.1";
const UPSTREAM_PORT = Number(process.env.HETU_DASHBOARD_PORT || 8790);
const UPSTREAM_BASE = `http://${UPSTREAM_HOST}:${UPSTREAM_PORT}`;

const name = "hetu-dashboard";
const inject = ["webServer"];

/** 剥离前缀：/api/hetu-dashboard/stats/overview → /stats/overview。 */
function stripPrefix(pathname) {
  if (pathname.startsWith(PREFIX)) {
    const rest = pathname.slice(PREFIX.length);
    return rest === "" ? "/" : rest;
  }
  return pathname;
}

/** 数据服务不可达的降级响应（browser 半区统一识别）。 */
function sendUnavailable(res, err) {
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

function apply(ctx) {
  ctx.webServer.register({
    kind: "prefix",
    path: PREFIX,
    handler: async (req, res) => {
      const raw = new URL(req.url ?? "/", "http://x");
      const targetPath = stripPrefix(raw.pathname) + raw.search;

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
        sendUnavailable(res, err);
      });
      req.pipe(upstreamReq);
    },
  });

  ctx.logger?.info?.(
    `[hetu-dashboard] 同源数据路由已注册: ${PREFIX}/* -> ${UPSTREAM_BASE}/*`,
  );
}

export { name, inject, apply };
export default { name, inject, apply };
