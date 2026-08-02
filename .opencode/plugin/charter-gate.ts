/**
 * charter-gate
 * 宪章编程 · 硬约束插件
 *
 * 1. 测试门禁（硬）：测试通过前（.gate.json 缺失或 test_passed != true），
 *    禁止写入研发日志/流程状态、禁止通过 bash 调用钉钉通知（util_dingtalk）。
 * 2. 数据安全（硬）：数据销毁类命令（rm -rf / DROP / DELETE / truncate / drop_collection）
 *    必须显式带 backup/备份，否则阻断。
 * 3. 密钥脱敏（硬）：对用户消息做明文凭据扫描并脱敏，告警记录。
 * 4. 资产登记一致性（提醒）：docs/hetu-xxx/ 下新增/修改文件未登记到 docs/资源地图.md 时告警。
 */

import type { Plugin } from "@opencode-ai/plugin"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import * as path from "node:path"

const GATE_FILE = ".gate.json"

function findAllGateFiles(directory: string): string[] {
  const base = path.join(directory, "opencode_schedule")
  if (!existsSync(base)) return []
  const found: string[] = []
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(p)
      else if (entry.name === GATE_FILE) found.push(p)
    }
  }
  walk(base)
  return found
}

function latestGateFile(directory: string): string | null {
  const files = findAllGateFiles(directory).sort()
  return files.length > 0 ? files[files.length - 1] : null
}

function gateOpen(directory: string): boolean {
  const p = latestGateFile(directory)
  if (!p) return false
  try {
    const state = JSON.parse(readFileSync(p, "utf-8"))
    return state.test_passed === true
  } catch {
    return false
  }
}

const SECRET_PATTERNS: RegExp[] = [
  /sk-[a-zA-Z0-9]{16,}/g,
  /Bearer\s+[a-zA-Z0-9._~+/=-]+/g,
  /(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access_token)\s*[=:]\s*['"]?[^\s'"]{8,}/gi,
]

function redactSecrets(text: string): { text: string; hits: number } {
  let hits = 0
  let out = text
  for (const re of SECRET_PATTERNS) {
    out = out.replace(re, () => {
      hits++
      return "[REDACTED]"
    })
  }
  return { text: out, hits }
}

export const CharterGate: Plugin = async ({ client, directory }) => {
  const log = (level: "info" | "warn" | "error", message: string, extra?: Record<string, unknown>) =>
    client.app?.log({ body: { service: "charter-gate", level, message, extra } }).catch(() => {})

  await log("info", "charter-gate plugin initialized", { directory })

  return {
    "tool.execute.before": async (input, output) => {
      const tool = input.tool
      const args = output.args ?? {}
      const cmd = typeof args.command === "string" ? args.command : ""
      const filePath = String(args.filePath ?? args.path ?? "")

      // ---- 门禁：测试通过前禁止 研发日志/流程状态 写入 与 钉钉通知 ----
      // 只拦截写入，不误伤读取（cat/grep 等读命令放行）
      const isLogWrite =
        (tool === "write" || tool === "edit" || tool === "apply_patch") &&
        /研发日志\.md|研发流程状态\.md/.test(filePath)
      const isLogWriteByBash =
        tool === "bash" && /(?:>\s*|>>\s*|tee\s+)[^;|&]*研发(?:日志|流程状态)\.md/.test(cmd)
      const isNotify = /util_dingtalk|send_markdown|send_text/.test(cmd)
      if ((isLogWrite || isLogWriteByBash || isNotify) && !gateOpen(directory)) {
        throw new Error(
          "[charter-gate] 测试门禁未通过（.gate.json 缺失或 test_passed=false）：禁止写入研发日志/流程状态、禁止发送钉钉通知。请先让 charter-tester 运行测试并生成 .gate.json。",
        )
      }

      // ---- 数据安全：数据销毁必须显式备份 ----
      const isDestructive = /^\s*(rm\s+-rf|DROP\s+(TABLE|STABLE)|DELETE\s+FROM|TRUNCATE|drop_collection|truncate)/i.test(cmd)
      if (isDestructive && !/backup|备份/i.test(cmd)) {
        throw new Error("[charter-gate] 数据销毁操作必须显式带 backup/备份 参数，禁止无备份删除。")
      }
    },

    "chat.message": async (input, output) => {
      let hits = 0
      for (const part of output.parts) {
        if (part.type === "text" && part.text) {
          const r = redactSecrets(part.text)
          if (r.hits > 0) {
            hits += r.hits
            part.text = r.text
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
      if ((input.tool === "write" || input.tool === "edit") && /docs\/hetu-[^/]+\//.test(filePath)) {
        const mapPath = path.join(directory, "docs", "资源地图.md")
        const registered = existsSync(mapPath) && readFileSync(mapPath, "utf-8").includes(path.basename(filePath))
        if (!registered) {
          await log("warn", `资产沉淀登记缺失：${filePath} 未出现在 docs/资源地图.md`, { sessionID: input.sessionID })
        }
      }
    },
  }
}

export default CharterGate
