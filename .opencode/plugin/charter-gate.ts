/**
 * charter-gate · 宪章门禁插件（opencode 入口薄适配层）
 *
 * 双体系并行（20260815 任务2）：opencode 入口（/cc，本文件）与 DSH 入口
 * （harness/plugins/charter-gate.ts）并行长期维护，两入口均为薄适配层，
 * 判定逻辑唯一在 Python 核心（harness/core/cli.py → gate.py / redact.py /
 * assets_check.py），共享同一外置规则 harness/gate_rules.yaml。
 *
 * 旧判定逻辑 → 新委托 对照（缺陷修复追溯）：
 * - D1 串门：原 L19-48 全局扫描 latestGateFile → 委托 decide（只认当前任务
 *   目录 .gate.json，run_id 与任务目录一致）
 * - D2 伪造：原无 token 校验 → 委托 decide（gate_token HMAC 校验，写/验分离）
 * - D4 绕过：原 L105-130 函数名/行首匹配 → 委托 decide（gate_rules.yaml 外置
 *   规则：通知 URL 双特征 + 唯一出口，危险命令任意位置匹配）
 * - H5 脱敏：原 L80-96 SECRET_PATTERNS 硬编码 → 委托 redact（gate_rules.yaml
 *   secret_patterns 段外置）
 * - H6 资产检查：原 L56-78 resolveResourceMapPath 两级回退 → 委托 assets-check
 *   （宿主→当前项目→缺失 三级回退，纯函数核心）
 *
 * 钩子行为（与 DSH 侧同构；差异点：opencode 钩子签名 (input, output)、日志
 * 接口 client.app.log、任务上下文从工具参数推导、导出形态 export default）：
 * - tool.execute.before（write/edit/apply_patch/bash）→ decide：blocked=true
 *   抛错拦截；GATE_STALE 附续签提示；判定调用异常 fail-closed 拦截 + error 告警
 * - chat.message → redact：hits>0 替换 text parts + warn 告警（含 sessionID）；
 *   调用失败返回原文 + error 告警
 * - tool.execute.after（write/edit 且目标在 docs/hetu-[项目名]/）→ assets-check：
 *   ok=false warn 软告警（不阻断）
 *
 * 注：修改本文件后需重启 opencode 生效（配置启动时加载、不热更新）。
 */

import type { Plugin } from "@opencode-ai/plugin"
import { execFileSync } from "node:child_process"
import { existsSync, readFileSync, readdirSync } from "node:fs"
import * as path from "node:path"

/** 运行环境三元组（resolveEnv 产出，供三个委托函数使用）。 */
interface Env {
  HARNESS_DIR: string
  VENV_BIN: string
  PROJECT_DIR: string
}

/** decide 判定结果（与 cli.py 出参契约一致）。 */
interface DecideResult {
  blocked: boolean
  code: string
  reason: string
  event_type: string
}

/** 脱敏结果（与 cli.py 出参契约一致）。 */
interface RedactResult {
  text: string
  hits: number
}

/** 资产登记检查结果（与 cli.py 出参契约一致）。 */
interface AssetResult {
  ok: boolean
  reason: string
  map_path: string
}

/**
 * 宿主查找：同父目录下同时含 constitution/constitution.md + .opencode/agents/
 * + docs/资源地图.md 三要件的 hetu-* 目录即 harness 宿主（拓扑回退规则①，
 * 宿主自身三要件齐全时同样命中自身）；无命中返回当前项目自身。
 *
 * Args:
 *     projectDir: 当前项目绝对路径。
 *
 * Returns:
 *     宿主绝对路径（或当前项目自身）。
 */
function findHostDir(projectDir: string): string {
  const parent = path.dirname(projectDir)
  let candidates: string[] = []
  try {
    for (const entry of readdirSync(parent, { withFileTypes: true })) {
      if (!entry.isDirectory() || !entry.name.startsWith("hetu-")) continue
      candidates.push(path.join(parent, entry.name))
    }
  } catch {
    return projectDir
  }
  candidates.sort()
  for (const dir of candidates) {
    if (
      existsSync(path.join(dir, "constitution", "constitution.md")) &&
      existsSync(path.join(dir, ".opencode", "agents")) &&
      existsSync(path.join(dir, "docs", "资源地图.md"))
    ) {
      return dir
    }
  }
  return projectDir
}

/**
 * 解析 .opencode/.harness-env，取 HARNESS_DIR / VENV_BIN（拓扑契约）。
 * K=V 逐行解析：跳过空行与 # 注释、剥离引号包裹的值（路径含空格场景）。
 * 缺失或字段缺失时回退：VENV_BIN → python3；HARNESS_DIR → findHostDir
 * 宿主查找（宿主自身无 .harness-env，回退命中自身，如 hetu-hammurabi）。
 *
 * Args:
 *     projectDir: 当前项目绝对路径。
 *
 * Returns:
 *     运行环境三元组 { HARNESS_DIR, VENV_BIN, PROJECT_DIR }。
 */
function resolveEnv(projectDir: string): Env {
  const env: Env = { HARNESS_DIR: "", VENV_BIN: "", PROJECT_DIR: projectDir }
  const envPath = path.join(projectDir, ".opencode", ".harness-env")
  if (existsSync(envPath)) {
    try {
      for (const line of readFileSync(envPath, "utf-8").split(/\r?\n/)) {
        const t = line.trim()
        if (!t || t.startsWith("#")) continue
        const idx = t.indexOf("=")
        if (idx <= 0) continue
        const key = t.slice(0, idx).trim()
        const val = t.slice(idx + 1).trim().replace(/^"|"$/g, "")
        if (key === "HARNESS_DIR") env.HARNESS_DIR = val
        else if (key === "VENV_BIN") env.VENV_BIN = val
      }
    } catch {
      // 解析失败保持空值，走下方回退
    }
  }
  if (!env.VENV_BIN) env.VENV_BIN = "python3"
  if (!env.HARNESS_DIR) env.HARNESS_DIR = findHostDir(projectDir)
  return env
}

/**
 * 子进程调用 Python 核心 CLI（cwd 必须为 HARNESS_DIR，保证模块可导入）。
 *
 * Args:
 *     env: 运行环境三元组。
 *     args: CLI 参数数组（execFileSync 数组传参，无 shell 注入面）。
 *
 * Returns:
 *     stdout 去除首尾空白后的文本。
 *
 * Raises:
 *     Error: 子进程启动失败或非零退出（由调用方按 fail-closed 处理）。
 */
function runCli(env: Env, args: string[]): string {
  const python = env.VENV_BIN || "python3"
  return execFileSync(python, args, {
    cwd: env.HARNESS_DIR,
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim()
}

/**
 * 从工具参数（filePath/cmd）推导任务目录与 run_id。
 * opencode 运行时无任务注入（DSH 由 dsh-agent 注入 taskDir/runId），
 * 按 opencode_schedule/<YYYYMMDD>/<任务目录> 路径模式推导；推导不到时
 * 以项目目录为 task_dir、run_id 为空串——命中日志/通知判定时因 run_id
 * 不匹配被拦截（fail-closed），非日志路径由核心直接放行。
 *
 * Args:
 *     directory: 当前项目绝对路径。
 *     filePath: 工具调用的目标文件路径。
 *     cmd: bash 命令文本。
 *
 * Returns:
 *     { taskDir, runId } 任务上下文。
 */
function resolveTaskContext(
  directory: string,
  filePath: string,
  cmd: string,
): { taskDir: string; runId: string } {
  const m = `${filePath}\n${cmd}`.match(/opencode_schedule[/\\]\d{8}[/\\][^/\\\s]+/)
  if (m) {
    const rel = m[0].replace(/\\/g, "/")
    const runId = rel.slice(rel.lastIndexOf("/") + 1)
    return { taskDir: path.join(directory, rel), runId }
  }
  return { taskDir: directory, runId: "" }
}

/**
 * 委托 Python 核心做门禁判定（D1/D2/D4；与 DSH 侧 decide 同构）。
 * blocked=true 时 CLI 以退出码 1 结束，execFileSync 抛错但 stdout 仍为判定
 * JSON——从 err.stdout 解析并返回，保证 reason/code 完整透传（GATE_STALE
 * 续签提示依赖于此）；其余异常视为判定子进程失败，抛错交由调用方 fail-closed。
 *
 * Args:
 *     env: 运行环境三元组。
 *     taskDir: 任务目录绝对路径。
 *     runId: 任务目录名。
 *     filePath: 目标文件路径（写入类操作），无则 ""。
 *     cmd: bash 命令文本，无则 ""。
 *
 * Returns:
 *     decide 判定结果 dict（blocked/code/reason/event_type）。
 *
 * Raises:
 *     Error: 判定子进程真异常（stdout 无合法 JSON 或启动失败）。
 */
function decide(env: Env, taskDir: string, runId: string, filePath: string, cmd: string): DecideResult {
  const secretFile = path.join(env.HARNESS_DIR, "conf", "gate_secret")
  const args = [
    "-m", "harness.core.cli", "decide",
    "--task-dir", taskDir,
    "--run-id", runId,
    "--file", filePath || "",
    "--cmd", cmd || "",
    "--secret-file", secretFile,
    "--json",
  ]
  try {
    return JSON.parse(runCli(env, args)) as DecideResult
  } catch (err) {
    const stdout = String((err as { stdout?: string }).stdout ?? "").trim()
    if (stdout) {
      try {
        return JSON.parse(stdout) as DecideResult
      } catch {
        // stdout 非 JSON：判定子进程异常，走 fail-closed
      }
    }
    throw new Error(`门禁判定子进程失败（fail-closed 拦截）: ${String(err)}`)
  }
}

/**
 * 委托 Python 核心脱敏文本（H5；与 DSH 侧 redactText 同构）。
 *
 * Args:
 *     env: 运行环境三元组。
 *     text: 待扫描文本。
 *
 * Returns:
 *     { text: 已脱敏文本, hits: 命中数 }。
 *
 * Raises:
 *     Error: 子进程失败（调用方返回原文 + error 告警）。
 */
function redactText(env: Env, text: string): RedactResult {
  const args = [
    "-m", "harness.core.cli", "redact",
    "--text", text,
    "--json",
  ]
  return JSON.parse(runCli(env, args)) as RedactResult
}

/**
 * 委托 Python 核心做资产登记检查（H6，软告警；与 DSH 侧 checkAsset 同构）。
 *
 * Args:
 *     env: 运行环境三元组。
 *     projectDir: 当前业务项目目录。
 *     filePath: 目标文件路径（write/edit 目标）。
 *
 * Returns:
 *     { ok, reason, map_path }。
 *
 * Raises:
 *     Error: 子进程失败（调用方按未登记软告警处理）。
 */
function checkAsset(env: Env, projectDir: string, filePath: string): AssetResult {
  const args = [
    "-m", "harness.core.cli", "assets-check",
    "--project-dir", projectDir,
    "--file", filePath,
    "--json",
  ]
  return JSON.parse(runCli(env, args)) as AssetResult
}

export const CharterGate: Plugin = async ({ client, directory }) => {
  const log = (level: "info" | "warn" | "error", message: string, extra?: Record<string, unknown>) =>
    client.app?.log({ body: { service: "charter-gate", level, message, extra } }).catch(() => {})

  await log("info", "charter-gate plugin initialized", { directory })

  return {
    "tool.execute.before": async (input, output) => {
      const tool = input.tool
      // 只对写入/命令类工具做判定；读取类（read/cat/grep）直接放行
      if (!["write", "edit", "apply_patch", "bash"].includes(tool)) return
      const args = output.args ?? {}
      const filePath = String(args.filePath ?? args.path ?? "")
      const cmd = typeof args.command === "string" ? args.command : ""
      const env = resolveEnv(directory)
      const { taskDir, runId } = resolveTaskContext(directory, filePath, cmd)

      let result: DecideResult
      try {
        result = decide(env, taskDir, runId, filePath, cmd)
      } catch (err) {
        // fail-closed：判定子进程失败 → 拦截 + error 告警（宁拦勿放）
        await log("error", `门禁判定调用失败（fail-closed 拦截）: ${String(err)}`, { tool, filePath })
        throw new Error(`[charter-gate] 门禁判定调用失败（fail-closed 拦截）: ${String(err)}`)
      }

      if (result.blocked) {
        await log("warn", `阻断 ${tool}: ${result.reason} (${result.code})`, { tool, filePath })
        // H4：门禁过期（GATE_STALE）时附续签提示（由编排器执行 re-seal）
        const message = String(result.reason).includes("GATE_STALE")
          ? `${result.reason}（提示：可执行 re-seal 续签，由编排器执行）`
          : result.reason
        // throw 即硬阻断该工具调用
        throw new Error(`[charter-gate] ${message}`)
      }
      return
    },

    "chat.message": async (input, output) => {
      let hits = 0
      const env = resolveEnv(directory)
      for (const part of output.parts) {
        if (part.type === "text" && part.text) {
          try {
            const r = redactText(env, part.text)
            if (r.hits > 0) {
              hits += r.hits
              part.text = r.text
            }
          } catch (err) {
            // 脱敏失败不拦会话，但必须告警标注风险（返回原文）
            await log("error", `消息脱敏调用失败，未脱敏原文输出（风险提示）: ${String(err)}`, {
              sessionID: input.sessionID,
            })
            return
          }
        }
      }
      if (hits > 0) {
        await log("warn", `检测到 ${hits} 处疑似明文凭据，已脱敏`, { sessionID: input.sessionID })
      }
    },

    "tool.execute.after": async (input, output) => {
      const args = input.args ?? {}
      const filePath = String(args.filePath ?? args.path ?? "")
      if (!["write", "edit"].includes(input.tool)) return
      if (!/docs[/\\]hetu-[^/\\]+[/\\]/.test(filePath)) return
      const env = resolveEnv(directory)
      try {
        const r = checkAsset(env, directory, filePath)
        if (!r.ok) {
          await log("warn", `资产沉淀登记缺失：${filePath} 未出现在 docs/资源地图.md`, {
            sessionID: input.sessionID,
          })
        }
      } catch (err) {
        // 软告警本就只提醒：检查失败按未登记告警
        await log("warn", `资产登记检查调用失败（按未登记软告警）: ${String(err)}`, {
          sessionID: input.sessionID,
        })
      }
    },
  }
}

export default CharterGate
