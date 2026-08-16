/**
 * charter-gate · 硬门禁（tools/pre-execute 钩子）· ConstitutionCoding-Plugin
 *
 * 在工具执行前拦截（官方扩展点，见 docs/dsh-docs/reference/tool-execution-pipeline.md）：
 * 1. 数据安全：危险命令（rm -rf/DROP/DELETE FROM/TRUNCATE/drop_collection）无 backup/备份 → deny
 * 2. 通知出口：直连钉钉（curl/requests/oapi.dingtalk.com）绕过唯一出口 → deny
 * 3. 日志门禁：研发日志写入（含 bash 重定向）在 .gate.json v2 未落闸前 → deny
 *
 * 判定委托 Python 核心（harness.core.cli decide），保证与 opencode 时代同源。
 * run_id 取当前工作目录下最新任务目录（/cc 单任务场景；落闸状态由该目录 .gate.json 判定）。
 */

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { findHarnessDir, latestTaskDir } from "./lib.js";

export const name = "charter-gate";
export const inject = [];

/** 参与门禁判定的工具。 */
const GATED_TOOLS = new Set(["bash", "write", "edit", "apply_patch"]);

/** 从 bash 命令提取重定向的研发日志目标（bash 重定向写入的日志门禁）。 */
function redirectedLogFile(cmd) {
  const m = cmd.match(/[>]{1,2}\s+([^\s;&|]*研发日志[^\s;&|]*\.md)/);
  return m ? m[1] : "";
}

/** 调用 Python 核心判定（与 opencode 时代 charter-gate 同源逻辑）。
 * 注意：decide CLI 在拦截时退出码为 1（stdout 仍含 JSON），必须用 spawnSync
 * 而非 execFileSync（后者在非零退出时抛异常导致误放行）。 */
function decide(harn, cmd, filePath) {
  const venv = path.join(path.dirname(harn), "venv-hetu", "bin", "python");
  const secretFile = path.join(harn, "conf", "gate_secret");
  const taskDir = latestTaskDir(process.cwd());
  const runId = taskDir ? path.basename(taskDir) : "";
  const args = [
    "-m", "harness.core.cli", "decide",
    "--task-dir", taskDir || process.cwd(),
    "--run-id", runId,
    "--file", filePath || "",
    "--cmd", cmd || "",
    "--secret-file", secretFile,
    "--json",
  ];
  const result = spawnSync(venv, args, {
    cwd: harn,
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  const out = (result.stdout || "").trim();
  if (out) {
    try {
      return JSON.parse(out);
    } catch {
      // fallthrough
    }
  }
  // 判定失败：fail-open（不误伤正常操作）
  return { blocked: false, code: "DECIDE_ERROR", reason: "判定失败" };
}

export function apply(ctx, config) {
  ctx.on("tools/pre-execute", async (exec, next) => {
    if (!GATED_TOOLS.has(exec.name)) return next();
    const args = exec.arguments && typeof exec.arguments === "object" ? exec.arguments : {};
    const cmd = typeof args.command === "string" ? args.command : "";
    let filePath = String(args.filePath || args.path || "");
    if (!cmd && !filePath) return next();

    // bash 重定向写研发日志：补构造 file_path 走日志门禁
    if (exec.name === "bash" && !filePath) {
      filePath = redirectedLogFile(cmd);
    }

    const harn = findHarnessDir(process.cwd(), config && config.harnessDir);
    if (!harn) return next();

    try {
      const decision = decide(harn, cmd, filePath);
      if (decision.blocked) {
        ctx.logger && ctx.logger.warn &&
          ctx.logger.warn(`[charter-gate] 拦截 ${exec.name}: ${decision.reason} (${decision.code})`);
        return { kind: "deny", reason: `[charter-gate] ${decision.reason}` };
      }
    } catch (err) {
      ctx.logger && ctx.logger.warn &&
        ctx.logger.warn(`[charter-gate] 判定失败（放行）: ${err.message}`);
    }
    return next();
  });

  ctx.logger && ctx.logger.info &&
    ctx.logger.info("[ConstitutionCoding] charter-gate 硬门禁已挂载（tools/pre-execute）");
}

export default { name, inject, apply };
