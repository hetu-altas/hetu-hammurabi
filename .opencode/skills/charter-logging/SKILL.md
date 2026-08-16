---
name: charter-logging
description: 遵循 hetu 系列研发日志规范撰写研发日志，用于研发流程的日志节点
---
## 研发日志宪章

## 路径解析约定（harness 运行时拓扑）
- 本项目已安装 harness 时，**先读取当前项目 `.opencode/.harness-env`**（由 install_harness.sh 生成，字段：PROJECT_NAME / PROJECT_DIR / WORKSPACE_DIR / HARNESS_DIR / AETHER_DIR / VENV_BIN，均为绝对路径），用其中的变量替换下述 `<HARNESS_DIR>`、`<AETHER_DIR>`、`<VENV_BIN>` 占位符。
- **回退规则**（.harness-env 缺失或字段缺失时动态查找）：① 同父目录（WORKSPACE_DIR）下同时含 `constitution/constitution.md` + `.opencode/agents/` + `docs/资源地图.md` 的 `hetu-*` 目录为 harness 宿主 → HARNESS_DIR；② 同父目录下 `hetu-aether` 为公共工具项目 → AETHER_DIR；③ 同父目录下 `venv-hetu/bin/python` 为共享环境 → VENV_BIN；④ 当前工作目录 basename 为 PROJECT_NAME。

1. 参考来源：
   - 任务书模板：`<HARNESS_DIR>/templates/task_book.md`
   - 历史日志示例：本项目的 `opencode_schedule/<YYYYMMDD>/<任务目录>/任务N研发日志.md`
2. 日志要求：
   - 存放在任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/` 下，命名 `任务N研发日志.md`
   - 包含：任务概述、创建/修改文件清单（表格）、核心设计、测试结果（通过数/总数）、遗留问题
   - 全部使用中文
