/**
 * charter-gate · 宪章门禁插件（DSH 适配层）
 *
 * 缺陷修复对照（20260814任务1）：
 * - D1 串门：判定委托 Python 核心 gate.decide，只认当前任务目录的 .gate.json
 * - D2 伪造：.gate.json v2 token 校验（写/验分离，编排器落闸）
 * - D3 状态文件：研发流程状态.md 放行（审计记录）
 * - D4 绕过面：通知唯一出口 / 危险命令任意位置匹配
 *
 * 优化对照（20260815任务1 · harness硬约束体系优化）：
 * - H4 续签提示：判定命中 GATE_STALE 时，阻断消息追加「可执行 re-seal 续签」提示
 * - H5 脱敏回归：chat 消息明文凭据扫描脱敏（委托 Python 核心 harness.core.redact）
 * - H6 资产检查回归：write/edit 目标位于 docs/hetu-*/ 时检查资源地图登记
 *   （委托 Python 核心 harness.core.assets_check，软告警不阻断）
 *
 * 接入说明：本插件为 cordis 风格插件，在 DSH 工具执行管线中注册前置钩子
 * （tool.execute.before 等价物——DSH 运行时的具体中间件名以 dsh-agent 工具
 * 执行管线为准，接入点：apply() 内 ctx.agent.tool.before 或等价注入）。
 * chat 消息脱敏与 after 资产检查按运行时实际中间件名接入（chatMessage /
 * after 等价物），机制与 before 一致：子进程调用 Python 核心，判定逻辑唯一。
 * 判定逻辑全部在 Python 核心（harness/core），插件只做参数透传与阻断抛出。
 *
 * 注：修改本文件后需重启 DSH 生效。
 */

import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

const name = "charter-gate";
const inject = ["agent", "logger"];

/** 解析 .harness-env，取 HARNESS_DIR / VENV_BIN（拓扑契约）。 */
function resolveEnv(projectDir) {
  const envPath = path.join(projectDir, ".opencode", ".harness-env");
  const env = { HARNESS_DIR: "", VENV_BIN: "", PROJECT_DIR: projectDir };
  if (existsSync(envPath)) {
    for (const line of readFileSync(envPath, "utf-8").split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const idx = t.indexOf("=");
      if (idx <= 0) continue;
      const key = t.slice(0, idx).trim();
      const val = t.slice(idx + 1).trim().replace(/^"|"$/g, "");
      if (key in env) env[key] = val;
    }
  }
  return env;
}

/** 调用 Python 核心做门禁判定（仅拦截写入/通知/危险命令，读取放行）。 */
function decide(env, taskDir, runId, filePath, cmd) {
  const secretFile = path.join(env.HARNESS_DIR, "conf", "gate_secret");
  const args = [
    "-m", "harness.core.cli", "decide",
    "--task-dir", taskDir,
    "--run-id", runId,
    "--file", filePath || "",
    "--cmd", cmd || "",
    "--secret-file", secretFile,
    "--json",
  ];
  const python = env.VENV_BIN || "python3";
  const out = execFileSync(python, args, {
    cwd: env.HARNESS_DIR,
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
  return JSON.parse(out);
}

/** 调用 Python 核心脱敏文本（H5）。 */
function redactText(env, text) {
  const args = [
    "-m", "harness.core.cli", "redact",
    "--text", text,
    "--json",
  ];
  const python = env.VENV_BIN || "python3";
  const out = execFileSync(python, args, {
    cwd: env.HARNESS_DIR,
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
  return JSON.parse(out);
}

/** 调用 Python 核心做资产登记检查（H6，软告警）。 */
function checkAsset(env, projectDir, filePath) {
  const args = [
    "-m", "harness.core.cli", "assets-check",
    "--project-dir", projectDir,
    "--file", filePath,
    "--json",
  ];
  const python = env.VENV_BIN || "python3";
  const out = execFileSync(python, args, {
    cwd: env.HARNESS_DIR,
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
  return JSON.parse(out);
}

function apply(ctx) {
  const logger = ctx.logger;

  // 接入点（DSH 工具执行前置钩子，见文件头接入说明）：
  // ctx.agent.tool.before(async ({ tool, args, projectDir, taskDir, runId }) => {
  const before = async ({ tool, args = {}, projectDir, taskDir, runId }) => {
    const filePath = String(args.filePath ?? args.path ?? "");
    const cmd = typeof args.command === "string" ? args.command : "";

    // 只对写入/命令类工具做判定；读取类（read/cat/grep）直接放行
    if (!["write", "edit", "apply_patch", "bash"].includes(tool)) return;

    const env = resolveEnv(projectDir);
    const result = decide(env, taskDir, runId, filePath, cmd);

    if (result.blocked) {
      logger?.warn(`[charter-gate] 阻断 ${tool}: ${result.reason} (${result.code})`);
      // H4：门禁过期（GATE_STALE）时附续签提示（由编排器执行 re-seal）
      const message = String(result.reason).includes("GATE_STALE")
        ? `${result.reason}（提示：可执行 re-seal 续签，由编排器执行）`
        : result.reason;
      // DSH 中 throw 即硬阻断该工具调用
      throw new Error(`[charter-gate] ${message}`);
    }
    return;
  };

  // 接入点（DSH chat 消息钩子等价物，运行时中间件名以 dsh-agent 管线为准）：
  // ctx.agent.chatMessage 或等价注入
  const chatMessage = async ({ projectDir, parts }) => {
    let hits = 0;
    for (const part of parts ?? []) {
      if (part.type === "text" && part.text) {
        const env = resolveEnv(projectDir);
        const r = redactText(env, part.text);
        if (r.hits > 0) {
          hits += r.hits;
          part.text = r.text;
        }
      }
    }
    if (hits > 0) {
      logger?.warn(`[charter-gate] 检测到 ${hits} 处疑似明文凭据，已脱敏`);
    }
  };

  // 接入点（DSH 工具执行后置钩子等价物，运行时中间件名以 dsh-agent 管线为准）：
  // ctx.agent.tool.after 或等价注入
  const after = async ({ tool, args = {}, projectDir }) => {
    const filePath = String(args.filePath ?? args.path ?? "");
    if (!["write", "edit"].includes(tool)) return;
    if (!/docs[/\\]hetu-[^/\\]+[/\\]/.test(filePath)) return;
    const env = resolveEnv(projectDir);
    const r = checkAsset(env, projectDir, filePath);
    if (!r.ok) {
      logger?.warn(`[charter-gate] 资产沉淀登记缺失：${filePath} 未出现在 docs/资源地图.md`);
    }
  };

  logger?.info?.("[charter-gate] plugin loaded (DSH adapter)");
  return { before, chatMessage, after };
}

export { name, inject, apply };
export default { name, inject, apply };
