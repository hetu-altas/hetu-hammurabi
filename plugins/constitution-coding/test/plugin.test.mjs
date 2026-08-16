/**
 * ConstitutionCoding-Plugin · 包内单测（node:test）
 *
 * 覆盖：
 * - /cc 命令注册与 followup 注入（command.js）
 * - charter-gate 硬门禁（gate.js tools/pre-execute：危险命令/通知出口/日志门禁）
 *
 * 运行：node --experimental-strip-types --test plugins/constitution-coding/test/*.test.mjs
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { apply as applyCommand } from "../src/command.js";
import { apply as applyGate } from "../src/gate.js";
import { checkHealth } from "../src/dashboard-launcher.js";
import http from "node:http";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = path.resolve(HERE, "../.."); // hetu-hammurabi

// ───────────────────────── /cc 命令 ─────────────────────────

test("cc 命令：注册名小写、followup 注入编排提示词", () => {
  let registered = null;
  const followed = [];
  const ctx = {
    commands: { register(def) { registered = def; } },
    logger: { info() {}, warn() {} },
  };
  applyCommand(ctx, { harnessDir: HARNESS });
  assert.ok(registered, "命令未注册");
  assert.equal(registered.name, "cc");
  const taskBook = path.join(HARNESS, "templates", "task_book.md");
  const agent = { followup(msg) { followed.push(msg); } };
  const result = registered.handler({ rawInput: taskBook, agent });
  assert.equal(result.kind, "success");
  assert.equal(followed.length, 1);
  const text = followed[0].content.map((c) => c.text).join("");
  assert.match(text, /schema_version: 1/);
  assert.match(text, /seal-gate/);
  assert.match(text, /项目归属/);
});

test("cc 命令：空输入返回错误，不注入", () => {
  let registered = null;
  const ctx = {
    commands: { register(def) { registered = def; } },
    logger: { info() {}, warn() {} },
  };
  applyCommand(ctx, { harnessDir: HARNESS });
  const result = registered.handler({ rawInput: "", agent: { followup() {} } });
  assert.equal(result.kind, "error");
  assert.match(result.text, /\/cc/);
});


// ───────────────────────── 看板自启（checkHealth） ─────────────────────────

test("launcher：健康探测——服务在跑 → true", async () => {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  try {
    assert.equal(await checkHealth("127.0.0.1", port), true);
  } finally {
    server.close();
  }
});

test("launcher：健康探测——端口未监听 → false（触发自启）", async () => {
  assert.equal(await checkHealth("127.0.0.1", 59999), false);
});
// ───────────────────────── 硬门禁（tools/pre-execute） ─────────────────────────

function captureGate() {
  let handler = null;
  const ctx = {
    on(event, fn) {
      if (event === "tools/pre-execute") handler = fn;
    },
    logger: { info() {}, warn() {} },
  };
  applyGate(ctx, { harnessDir: HARNESS });
  assert.ok(handler, "tools/pre-execute 未挂载");
  const run = async (exec) => {
    let called = false;
    const next = async () => { called = true; return { kind: "allow" }; };
    const decision = await handler(exec, next);
    return { decision, nextCalled: called };
  };
  return run;
}

test("gate：危险命令无备份 → deny", async () => {
  const run = captureGate();
  const { decision, nextCalled } = await run({ name: "bash", arguments: { command: "rm -rf /tmp/a" } });
  assert.equal(decision.kind, "deny");
  assert.match(decision.reason, /备份/);
  assert.equal(nextCalled, false);
});

test("gate：危险命令带备份 → 放行", async () => {
  const run = captureGate();
  const { decision, nextCalled } = await run({ name: "bash", arguments: { command: "rm -rf /tmp/a --backup" } });
  assert.ok(decision.kind === "allow" || nextCalled, "应放行");
});

test("gate：curl 直连钉钉 → deny（通知唯一出口）", async () => {
  const run = captureGate();
  const { decision } = await run({
    name: "bash",
    arguments: { command: 'curl "https://oapi.dingtalk.com/robot/send?access_token=x"' },
  });
  assert.equal(decision.kind, "deny");
  assert.match(decision.reason, /唯一出口/);
});

test("gate：普通命令 → 放行", async () => {
  const run = captureGate();
  const { decision, nextCalled } = await run({ name: "bash", arguments: { command: "git status" } });
  assert.equal(nextCalled, true);
  assert.notEqual(decision.kind, "deny");
});

test("gate：写研发日志（门禁未开）→ deny", async () => {
  const run = captureGate();
  const { decision } = await run({
    name: "write",
    arguments: { filePath: "/tmp/opencode_schedule/20260815/20260815任务X/任务X研发日志.md" },
  });
  assert.equal(decision.kind, "deny");
});

test("gate：写研发流程状态.md（审计记录）→ 放行", async () => {
  const run = captureGate();
  const { decision, nextCalled } = await run({
    name: "write",
    arguments: { filePath: "/tmp/opencode_schedule/20260815/20260815任务X/研发流程状态.md" },
  });
  assert.equal(nextCalled, true);
});

test("gate：非门禁工具（read）→ 不拦截", async () => {
  const run = captureGate();
  const { decision, nextCalled } = await run({ name: "read", arguments: { filePath: "/a.txt" } });
  assert.equal(nextCalled, true);
  assert.notEqual(decision.kind, "deny");
});
