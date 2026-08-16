/**
 * /cc 命令（宪章编程 GUI 钩子）· ConstitutionCoding-Plugin
 *
 * 用户输入 /cc <任务书路径 或 一句话需求>：
 *   1. 解析输入，构造编排提示词（workflow.yaml + 宪章 + 门禁约定）
 *   2. createUserMessage + agent.followup() 注入当前会话并唤醒模型
 *   3. 模型按 workflow.yaml 执行节点 -1~7，GUI 全程可见
 *
 * 命令名必须全小写（DSH 规范：大写会导致启动失败）。
 */

import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { findHarnessDir } from "./lib.js";
import { createUserMessage } from "@deepseek-ai/dsh-llm";

export const name = "cc";
export const inject = ["commands"];

/** 解析输入：已有 .md 文件 → 任务书；非空 → 一句话需求；空 → 提示用法。 */
function parseInput(projectDir, raw) {
  const trimmed = raw.trim();
  if (!trimmed) return { mode: "list" };
  const candidates = [trimmed, path.resolve(projectDir, trimmed)];
  for (const c of candidates) {
    if (existsSync(c) && c.endsWith(".md")) {
      return { mode: "taskbook", path: path.resolve(c) };
    }
  }
  return { mode: "requirement", text: trimmed };
}

/** 构造编排提示词（与 scripts/run_charter.sh 同源）。 */
function buildCharterPrompt(harn, projectDir, projectName, parsed) {
  const workflow = readFileSync(path.join(harn, "harness", "workflow.yaml"), "utf-8");
  const venv = path.join(path.dirname(harn), "venv-hetu", "bin", "python");
  const gateSecret = path.join(harn, "conf", "gate_secret");
  const constitution = path.join(harn, "constitution", "constitution.md");

  let inputDesc;
  if (parsed.mode === "taskbook") {
    inputDesc = `任务书路径：${parsed.path}\n请先用 read 工具读取任务书全文，再按流程执行。`;
  } else if (parsed.mode === "requirement") {
    inputDesc = `一句话需求：${parsed.text}\n节点 -1 需按 ${harn}/templates/task_book.md 模板生成任务书。`;
  } else {
    inputDesc = "（未提供输入）请先列出可用任务书或要求用户提供任务书路径/一句话需求。";
  }

  return [
    `你是河图体系「宪章编程」研发流程的主编排代理（charter-orchestrator）。用户通过 /cc 命令启动了宪章研发流程。`,
    ``,
    `## 输入`,
    `- ${inputDesc}`,
    `- 当前工作目录：${projectDir}（basename=${projectName}）`,
    ``,
    `## 项目归属（重要）`,
    `- 任务目录与事件记录的项目名以**任务实际归属**为准：任务书/需求内容属于哪个 hetu-* 业务项目（hetu-sybil/hetu-thoth/hetu-mercury/hetu-aether/hetu-hammurabi），任务目录就建到该项目下（opencode_schedule/<YYYYMMDD>/<任务目录>/），record 事件的 --project 用该项目名`,
    `- 若当前工作目录已是业务项目（含 opencode_schedule/ 或 .opencode/.harness-env），按当前项目归属`,
    `- 若当前工作目录是工作区根（如 hetu-altas，basename 以 hetu- 开头但非业务模块项目），按任务内容判定归属项目`,
    ``,
    `## 宪章（必须遵守，先阅读再执行）`,
    `- 顶层宪法：${constitution}`,
    `- 子规范：${harn}/constitution/ 下的 coding / unit_test / log / project / task_split 等`,
    `- 安全底线：禁止获取 root 权限、禁止输出明文密钥、数据增删改必须先备份`,
    ``,
    `## 流程定义（严格按序执行，前序未完成不得进入下一节点；来自 harness/workflow.yaml）`,
    workflow,
    ``,
    `## 节点执行要求`,
    `- 节点 -1（仅一句话需求时）：按 ${harn}/templates/task_book.md 模板生成任务书`,
    `- 节点 0：校验任务书/宪章/输出目录，解析任务目录名（YYYYMMDD任务N名称）`,
    `- 节点 1（charter-analyst）：读 ${harn}/docs/资源地图.md 匹配资源，产出 实施计划.md`,
    `- 节点 2（charter-coder）：按宪章实现全部文件（Python 首行编码声明、类型标注、Google docstring）`,
    `- 节点 3（charter-tester）：编写 unit_test/test_*.py（正常/反例/边界），用 ${venv} 运行，`,
    `  结果写入 unit_test/test/test_*_result.txt；**只写结果，不自行落闸**`,
    `- 节点 4（charter-reviewer）：只读评审，产出 评审报告.md；APPROVE 才放行，REVISE 回节点 2（最多 2 轮）`,
    `- 节点 5（charter-logger）：撰写 任务N研发日志.md`,
    `- 节点 6（charter-assetter）：沉淀为 ${harn}/docs/hetu-${projectName}/ 下文档，新增登记资源地图，更新仅追加章节`,
    `- 节点 7（charter-notifier）：通过唯一出口发送钉钉：`,
    `  HARNESS_NOTIFY=1 ${venv} -m harness.core.notify --run-id <任务目录名> --project ${projectName} --title "..." --text "..."`,
    ``,
    `## 门禁约定（.gate.json v2 信任模型，写/验分离）`,
    `- 节点 3 全部测试通过后，由你（编排器）核对 result 文件并落闸：`,
    `  ${venv} -m harness.core.cli seal-gate --task-dir <任务目录> --run-id <任务目录名> --results <全部 result 文件> --total <总数> --passed <通过数> --secret-file ${gateSecret}`,
    `- 落闸前禁止写研发日志、禁止发通知；研发流程状态.md 为审计记录可随时写`,
    `- 数据销毁命令必须显式带 backup/备份（charter-gate 硬门禁会机器拦截）`,
    ``,
    `## 输出目录（任务目录，所有中间产物放这里）`,
    `${projectDir}/opencode_schedule/<YYYYMMDD>/<YYYYMMDD任务N名称>/`,
    `  ├── <YYYYMMDD任务N名称>.md    任务书（输入或节点-1 生成）`,
    `  ├── 实施计划.md                节点1`,
    `  ├── .gate.json                 节点3 落闸（seal-gate 生成）`,
    `  ├── 评审报告.md                节点4`,
    `  ├── 任务N研发日志.md           节点5`,
    `  └── 研发流程状态.md            每完成一个节点追加：时间 | 节点 | 状态 | 说明`,
    ``,
    `## 状态固化`,
    `每完成一个节点，向任务目录 研发流程状态.md 追加记录；流程结束输出总结`,
    `（改动文件数、测试通过数、评审结论、遗留事项）。全程使用中文。`,
    ``,
    `## 节点事件记录（状态栏数据源，每进入/完成一个节点必须执行一次；先 cd 到宿主目录保证模块可导入）`,
    `节点开始：cd ${harn} && ${venv} -m harness.core.cli record --runlog ${harn}/runlog --run-id <任务目录名> --node <节点id> --node-name <节点名> --event node_start --status running --project ${projectName} --msg <简要说明>`,
    `节点完成：cd ${harn} && ${venv} -m harness.core.cli record --runlog ${harn}/runlog --run-id <任务目录名> --node <节点id> --node-name <节点名> --event node_end --status pass --project ${projectName} --msg <结果说明>`,
    `门禁拦截：cd ${harn} && ${venv} -m harness.core.cli record --runlog ${harn}/runlog --run-id <任务目录名> --node <节点id> --node-name <节点名> --event gate_block --status blocked --project ${projectName} --msg <原因>`,
    `（事件进入 runlog，GUI 右侧流程状态栏据此实时展示节点进展；即使事件缺失，状态栏也会按任务目录状态文件兜底显示）`,
  ].join("\n");
}

export function apply(ctx, config) {
  ctx.commands.register({
    name: "cc",
    description: "宪章编程（constitution coding）：输入任务书路径或一句话需求，按 workflow.yaml 执行完整研发流程（命令名必须小写 /cc）",
    input: { hint: "[<任务书路径 或 一句话需求>]" },
    handler: (invocation) => {
      const harn = findHarnessDir(process.cwd(), config && config.harnessDir);
      if (harn === null) {
        return {
          kind: "error",
          text: "无法定位 harness 宿主（需含 constitution/constitution.md + harness/workflow.yaml 的 hetu-* 目录）。请通过插件 config.harnessDir 显式指定。",
        };
      }
      const projectDir = process.cwd();
      const projectName = path.basename(projectDir);
      const parsed = parseInput(projectDir, invocation.rawInput || "");
      if (parsed.mode === "list") {
        return {
          kind: "error",
          text: "请提供任务书路径或一句话需求：/cc <任务书路径 或 一句话需求>（任务书可放 opencode_schedule/<YYYYMMDD>/<任务目录>/ 下）",
        };
      }
      const prompt = buildCharterPrompt(harn, projectDir, projectName, parsed);
      const message = createUserMessage({
        content: [{ type: "text", text: prompt }],
        source: { kind: "charter" },
      });
      invocation.agent.followup(message);
      return {
        kind: "success",
        text: `宪章编程流程已启动（${parsed.mode === "taskbook" ? "任务书" : "一句话需求"}）：${parsed.mode === "taskbook" ? parsed.path : parsed.text}\n编排提示词已注入当前会话，模型将按 workflow.yaml 执行节点 -1~7。`,
      };
    },
  });
  ctx.logger && ctx.logger.info && ctx.logger.info("[ConstitutionCoding] /cc 命令已注册");
}

export default { name, inject, apply };
