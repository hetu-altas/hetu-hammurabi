/**
 * charter-recorder · 运行事件采集插件（DSH 适配层）
 *
 * 缺陷修复对照（20260814任务1）：
 * - D6 无运行度量：节点 start/end、门禁 block/pass、retry、notify 事件
 *   委托 Python 核心 recorder 落盘 runlog/events/，供看板聚合。
 *
 * 接入说明：编排插件与 DSH agent 在节点推进时调用本插件的 record()；
 * 事件 schema 与落盘逻辑全部在 Python 核心（harness/core/recorder.py）。
 */

import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

const name = "charter-recorder";
const inject = ["logger"];

const VALID_EVENTS = new Set([
  "node_start", "node_end", "gate_block", "gate_pass", "retry", "notify", "error",
]);
const VALID_STATUSES = new Set(["running", "pass", "fail", "blocked"]);

function resolveEnv(projectDir) {
  const envPath = path.join(projectDir, ".opencode", ".harness-env");
  const env = { HARNESS_DIR: "", VENV_BIN: "", PROJECT_DIR: projectDir };
  if (existsSync(envPath)) {
    for (const line of readFileSync(envPath, "utf-8").split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const idx = t.indexOf("=");
      if (idx <= 0) continue;
      env[t.slice(0, idx).trim()] = t.slice(idx + 1).trim().replace(/^"|"$/g, "");
    }
  }
  return env;
}

function apply(ctx) {
  const logger = ctx.logger;

  /** 记录一条运行事件（薄适配 → harness.core.recorder）。 */
  function record({ projectDir, runId, node, nodeName, event, status, round = 1, msg = "", file = "" }) {
    if (!VALID_EVENTS.has(event)) throw new Error(`[charter-recorder] 非法事件类型: ${event}`);
    if (!VALID_STATUSES.has(status)) throw new Error(`[charter-recorder] 非法状态: ${status}`);
    const env = resolveEnv(projectDir);
    const runlogRoot = path.join(env.HARNESS_DIR, "runlog");
    const args = [
      "-m", "harness.core.cli", "record",
      "--runlog", runlogRoot,
      "--run-id", runId,
      "--node", String(node),
      "--node-name", nodeName,
      "--event", event,
      "--status", status,
      "--round", String(round),
      "--project", path.basename(projectDir),
    ];
    if (msg) args.push("--msg", msg);
    if (file) args.push("--file", file);
    const python = env.VENV_BIN || "python3";
    execFileSync(python, args, { cwd: env.HARNESS_DIR, encoding: "utf-8" });
    logger?.debug?.(`[charter-recorder] ${runId} 节点${node} ${event}/${status}`);
  }

  // 节点推进辅助：编排插件在进入/完成节点时调用
  return {
    nodeStart: (o) => record({ ...o, event: "node_start", status: "running" }),
    nodeEnd: (o) => record({ ...o, event: "node_end" }),
    gateBlock: (o) => record({ ...o, event: "gate_block", status: "blocked" }),
    gatePass: (o) => record({ ...o, event: "gate_pass", status: "pass" }),
    retry: (o) => record({ ...o, event: "retry", status: "running" }),
  };
}

export { name, inject, apply };
export default { name, inject, apply };
