/**
 * lib · 共享工具 · ConstitutionCoding-Plugin
 */

import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

/** 目录是否为 harness 宿主。
 * 三要件：constitution/constitution.md + harness/workflow.yaml + docs/资源地图.md。
 * 资源地图为宿主特有（业务项目软链 harness 组件后也有前两者，须用第三者区分）。 */
function isHostDir(dir) {
  return (
    existsSync(path.join(dir, "constitution", "constitution.md")) &&
    existsSync(path.join(dir, "harness", "workflow.yaml")) &&
    existsSync(path.join(dir, "docs", "资源地图.md"))
  );
}

/**
 * 定位 harness 宿主。
 *
 * 顺序：显式 config → 向上探测（cwd 的父链）→ 向下探测（cwd 的 hetu-* 子目录）。
 * 兼容两种启动场景：在宿主目录内启动 dsh（向上命中），
 * 或在工作区根（hetu-altas）启动 dsh（向下命中子项目宿主）。
 */
export function findHarnessDir(startDir, explicit) {
  if (explicit && isHostDir(explicit)) return explicit;
  // 向上探测
  let dir = startDir;
  for (let i = 0; i < 8; i += 1) {
    if (isHostDir(dir)) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  // 向下探测：cwd 的直接 hetu-* 子目录
  try {
    for (const entry of readdirSync(startDir, { withFileTypes: true })) {
      if (entry.isDirectory() && entry.name.startsWith("hetu-")) {
        const sub = path.join(startDir, entry.name);
        if (isHostDir(sub)) return sub;
      }
    }
  } catch {
    // 不可读则忽略
  }
  return null;
}

/**
 * 最新任务目录：扫描 cwd 与各 hetu-* 子项目的 opencode_schedule/<日期>/<任务>/，
 * 按任务目录 mtime 取最新（/cc 单任务场景，落闸状态由该目录 .gate.json 判定）。
 */
export function latestTaskDir(projectDir) {
  const roots = [projectDir];
  try {
    for (const entry of readdirSync(projectDir, { withFileTypes: true })) {
      if (entry.isDirectory() && entry.name.startsWith("hetu-")) {
        roots.push(path.join(projectDir, entry.name));
      }
    }
  } catch {
    // 不可读则忽略
  }
  let best = null;
  let bestMtime = 0;
  for (const root of roots) {
    const sched = path.join(root, "opencode_schedule");
    if (!existsSync(sched)) continue;
    const walk = (dir, depth) => {
      let entries;
      try {
        entries = readdirSync(dir, { withFileTypes: true });
      } catch {
        return;
      }
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const p = path.join(dir, entry.name);
        if (depth === 1) {
          walk(p, depth + 1);
        } else if (depth === 2) {
          const hasGate = existsSync(path.join(p, ".gate.json"));
          const hasStatus = existsSync(path.join(p, "研发流程状态.md"));
          if (hasGate || hasStatus) {
            const mtime = statSync(p).mtimeMs;
            if (mtime > bestMtime) {
              best = p;
              bestMtime = mtime;
            }
          }
        }
      }
    };
    walk(sched, 1);
  }
  return best;
}
