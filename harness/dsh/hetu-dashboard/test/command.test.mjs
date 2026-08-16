/**
 * charter-command · 命令插件单测（node:test + strip-types）
 *
 * 运行：node --experimental-strip-types --test harness/dsh/hetu-dashboard/test/command.test.mjs
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { apply as applyCommand } from "../../plugins/charter-command.ts";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = path.resolve(HERE, "../../.."); // hetu-hammurabi

/** 组装一个 fake ctx 捕获注册的命令与 followup 注入。 */
function captureCommand(config) {
  let registered = null;
  const followed = [];
  const ctx = {
    commands: {
      register(def) { registered = def; },
    },
    logger: { info() {}, warn() {}, error() {} },
  };
  applyCommand(ctx, config);
  const agent = {
    followup(message) { followed.push(message); },
  };
  return {
    getCmd: () => registered,
    invoke: (rawInput) => registered.handler({ rawInput, agent }),
    followed,
  };
}

test("插件注册 /cc 命令", () => {
  const { getCmd } = captureCommand({ harnessDir: HARNESS });
  const cmd = getCmd();
  assert.ok(cmd, "命令未注册");
  assert.equal(cmd.name, "cc");
  assert.match(cmd.description, /宪章编程（constitution coding）/);
  assert.ok(typeof cmd.handler === "function");
});

test("任务书模式：注入 user message 且含流程定义与任务书路径", () => {
  const { invoke, followed } = captureCommand({ harnessDir: HARNESS });
  const taskBook = path.join(HARNESS, "templates", "task_book.md");
  const result = invoke(taskBook);
  assert.equal(result.kind, "success");
  assert.match(result.text, /宪章编程流程已启动/);
  // followup 注入断言：一条 user message，内容为编排提示词
  assert.equal(followed.length, 1);
  const msg = followed[0];
  assert.equal(msg.role, "user");
  assert.ok(Array.isArray(msg.content));
  const text = msg.content.map((c) => c.text).join("");
  assert.match(text, /schema_version: 1/);          // workflow.yaml 注入
  assert.match(text, /seal-gate/);                   // 门禁落闸约定
  assert.match(text, /HARNESS_NOTIFY/);              // 唯一通知出口
  assert.match(text, new RegExp(taskBook.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))); // 任务书路径
});

test("一句话需求模式：需求文本注入且提示生成任务书", () => {
  const { invoke, followed } = captureCommand({ harnessDir: HARNESS });
  const result = invoke("实现一个通用工具方法：对列表按日期字段排序并去重");
  assert.equal(result.kind, "success");
  assert.match(result.text, /一句话需求/);
  const text = followed[0].content.map((c) => c.text).join("");
  assert.match(text, /一句话需求：实现一个通用工具方法/);
  assert.match(text, /节点 -1 需按/);
});

test("空输入：返回错误提示，不注入", () => {
  const { invoke, followed } = captureCommand({ harnessDir: HARNESS });
  const result = invoke("");
  assert.equal(result.kind, "error");
  assert.match(result.text, /\/cc/);
  assert.equal(followed.length, 0);
});

test("相对路径任务书：相对工作目录解析", () => {
  const { invoke, followed } = captureCommand({ harnessDir: HARNESS });
  invoke("templates/task_book.md");
  const text = followed[0].content.map((c) => c.text).join("");
  assert.match(text, /任务书路径：.*task_book\.md/);
});

test("harness 定位：显式 config 缺失时向上探测", () => {
  const { invoke, followed } = captureCommand({});
  const result = invoke("一句话需求：测试");
  assert.equal(result.kind, "success");
  const text = followed[0].content.map((c) => c.text).join("");
  assert.match(text, /schema_version: 1/);
});
