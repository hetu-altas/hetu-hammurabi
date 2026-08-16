/**
 * charter-orchestrator · 主编排插件（DSH 适配层）
 *
 * 缺陷修复对照（20260814任务1）：
 * - D5 流程定义外置：节点顺序/回退轮次/门禁挂载点读 harness/workflow.yaml，
 *   不再硬编码在系统提示词；本插件提供解析与推进校验。
 * - D2 落闸权上收：tester 只产 result 文件；本插件核对全部 result 通过后
 *   调用 Python 核心 seal-gate 签名落闸（.gate.json v2）。
 *
 * 接入说明：DSH agent 会话中由编排代理按本插件的 plan()/advance() 驱动节点；
 * 节点子代理（charter-*）执行顺序与重试按 workflow.yaml 的 requires/retry 规则。
 */

import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
const yaml = require("yaml");

const name = "charter-orchestrator";
const inject = ["logger"];

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

  /** 加载流程定义（外置 workflow.yaml，D5）。 */
  function loadWorkflow(projectDir) {
    const env = resolveEnv(projectDir);
    const wfPath = path.join(env.HARNESS_DIR, "harness", "workflow.yaml");
    if (!existsSync(wfPath)) {
      throw new Error(`[charter-orchestrator] workflow.yaml 不存在: ${wfPath}`);
    }
    return yaml.parse(readFileSync(wfPath, "utf-8"));
  }

  /** 计算下一批可执行节点（委托 Python 核心 next_allowed 语义）。 */
  function plan(wf, doneIds) {
    const done = new Set(doneIds);
    const result = [];
    for (const n of wf.nodes) {
      if (done.has(n.id)) continue;
      const req = n.requires || [];
      if (req.length > 0) {
        if (req.every((r) => done.has(r))) result.push(n);
      } else {
        const smaller = wf.nodes.filter((m) => m.id < n.id).map((m) => m.id);
        if (smaller.every((s) => done.has(s))) result.push(n);
      }
    }
    return result.sort((a, b) => a.id - b.id);
  }

  /** 校验一个节点是否可以推进（前置依赖 + 门禁）。 */
  function canEnter(wf, nodeId, doneIds) {
    const next = plan(wf, doneIds);
    return next.some((n) => n.id === nodeId);
  }

  /** 编排器落闸：解析 result 自动核对数字后签名写入 .gate.json v2（D2/H3）。 */
  function sealGate({ projectDir, taskDir, runId, results }) {
    const env = resolveEnv(projectDir);
    const secretFile = path.join(env.HARNESS_DIR, "conf", "gate_secret");
    const args = [
      "-m", "harness.core.cli", "seal-gate",
      "--task-dir", taskDir,
      "--run-id", runId,
      "--results", ...results,
      "--secret-file", secretFile,
      "--json",
    ];
    const python = env.VENV_BIN || "python3";
    const out = execFileSync(python, args, {
      cwd: env.HARNESS_DIR,
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
    const result = JSON.parse(out);
    if (!result.ok) throw new Error(`[charter-orchestrator] 落闸失败: ${result.msg}`);
    logger?.info?.(`[charter-orchestrator] 已落闸 ${result.gate_file}（test_passed=${result.test_passed}）`);
    return result;
  }

  /** 编排器续签：门禁过期（GATE_STALE）时刷新 updated_at 重签 token（H4）。 */
  function reSeal({ projectDir, taskDir, runId, runlog = "" }) {
    const env = resolveEnv(projectDir);
    const secretFile = path.join(env.HARNESS_DIR, "conf", "gate_secret");
    const args = [
      "-m", "harness.core.cli", "re-seal",
      "--task-dir", taskDir,
      "--run-id", runId,
      "--secret-file", secretFile,
      "--json",
    ];
    if (runlog) {
      args.splice(args.length - 1, 0, "--runlog", runlog);
    }
    const python = env.VENV_BIN || "python3";
    const out = execFileSync(python, args, {
      cwd: env.HARNESS_DIR,
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
    const result = JSON.parse(out);
    if (!result.ok) throw new Error(`[charter-orchestrator] 续签失败: ${result.msg}`);
    logger?.info?.(`[charter-orchestrator] 已续签 ${result.gate_file}（updated_at=${result.updated_at}）`);
    return result;
  }

  return { loadWorkflow, plan, canEnter, sealGate, reSeal };
}

export { name, inject, apply };
export default { name, inject, apply };
