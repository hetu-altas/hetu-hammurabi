/**
 * dashboard-launcher · 看板服务自启钩子 · ConstitutionCoding-Plugin
 *
 * DSH web 启动时自动调起宪章看板数据服务（FastAPI，默认 127.0.0.1:8790）：
 * 1. 启动 1.5s 后探测 /api/health
 * 2. 未运行 → spawn 拉起（uvicorn harness.core.api:app，cwd=harness 宿主）
 * 3. 已在运行 → 跳过（幂等，不重复启动）
 *
 * 启动方式：detached + unref——看板独立于 DSH 生命周期常驻，
 * DSH 退出/重启不影响；日志落 <workspace>/logs/hetu-altas/dashboard.log。
 */

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, openSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { findHarnessDir } from "./lib.js";

export const name = "dashboard-launcher";
export const inject = [];

/** 探测看板服务健康状态（超时视为不可达）。 */
export function checkHealth(host, port, timeoutMs = 800) {
  return new Promise((resolve) => {
    const req = http.get(
      { host, port, path: "/api/health", timeout: timeoutMs },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      },
    );
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

/** 拉起看板服务（detached 常驻，日志落 <workspace>/logs/hetu-altas/dashboard.log）。 */
function launchDashboard(harn, port) {
  try {
    // 调试：记录实际启动参数（定位 DSH 环境 spawn 差异）
    const dbg = path.join(path.dirname(harn), "logs", "hetu-altas", "launcher-debug.log");
    const { appendFileSync, mkdirSync: _m } = require_node_fs();
    _m(path.dirname(dbg), { recursive: true });
    appendFileSync(dbg, JSON.stringify({
      ts: new Date().toISOString(),
      process_cwd: process.cwd(),
      harn,
      venv: path.join(path.dirname(harn), "venv-hetu", "bin", "python"),
      port,
      has_pythonpath: Object.prototype.hasOwnProperty.call(process.env, "PYTHONPATH"),
      pythonpath: process.env.PYTHONPATH || null,
    }) + "\n");
  } catch { /* debug 失败忽略 */ }
  const venv = path.join(path.dirname(harn), "venv-hetu", "bin", "python");
  const logDir = path.join(path.dirname(harn), "logs", "hetu-altas");
  mkdirSync(logDir, { recursive: true });
  const logFile = path.join(logDir, "dashboard.log");
  const out = openSync(logFile, "a");
  const child = spawn(
    venv,
    ["-m", "uvicorn", "harness.core.api:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
    {
      cwd: harn,
      // 显式 PYTHONPATH：DSH 进程内 spawn 的 cwd 传递不可靠，避免 uvicorn 找不到 harness.core
      env: { ...process.env, PYTHONPATH: harn },
      detached: true,
      stdio: ["ignore", out, out],
    },
  );
  child.unref();
  return child;
}

export function apply(ctx, config) {
  const port = Number(process.env.HETU_DASHBOARD_PORT || 8790);
  const harn = findHarnessDir(process.cwd(), config && config.harnessDir);
  if (!harn) {
    ctx.logger && ctx.logger.warn &&
      ctx.logger.warn("[dashboard-launcher] 无法定位 harness 宿主，看板自启跳过");
    return;
  }
  // 延迟探测：等 DSH 网络栈就绪
  setTimeout(async () => {
    try {
      const up = await checkHealth("127.0.0.1", port);
      if (up) {
        ctx.logger && ctx.logger.info &&
          ctx.logger.info(`[dashboard-launcher] 看板服务已在运行（127.0.0.1:${port}），跳过启动`);
        return;
      }
      launchDashboard(harn, port);
      ctx.logger && ctx.logger.info &&
        ctx.logger.info(`[dashboard-launcher] 看板服务已自动拉起（127.0.0.1:${port}，日志 logs/hetu-altas/dashboard.log）`);
    } catch (err) {
      ctx.logger && ctx.logger.warn &&
        ctx.logger.warn(`[dashboard-launcher] 看板自启失败: ${err.message}`);
    }
  }, 1500);
}

export default { name, inject, apply };
