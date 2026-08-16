---
name: charter-taskbook
description: 任务书生成流程：根据一句话需求自动编写符合模板的任务书，用于研发流程的前置节点。Use when converting a free-text requirement into a task book during the charter dev workflow.
---
# 任务书生成流程

## 路径解析约定（harness 运行时拓扑）
- 本项目已安装 harness 时，**先读取当前项目 `.opencode/.harness-env`**（由 install_harness.sh 生成，字段：PROJECT_NAME / PROJECT_DIR / WORKSPACE_DIR / HARNESS_DIR / AETHER_DIR / VENV_BIN，均为绝对路径），用其中的变量替换下述 `<HARNESS_DIR>`、`<AETHER_DIR>`、`<VENV_BIN>` 占位符。
- **回退规则**（.harness-env 缺失或字段缺失时动态查找）：① 同父目录（WORKSPACE_DIR）下同时含 `constitution/constitution.md` + `harness/agents/`（旧布局为 `.opencode/agents/`，兼容识别）+ `docs/资源地图.md` 的 `hetu-*` 目录为 harness 宿主 → HARNESS_DIR；② 同父目录下 `hetu-aether` 为公共工具项目 → AETHER_DIR；③ 同父目录下 `venv-hetu/bin/python` 为共享环境 → VENV_BIN；④ 当前工作目录 basename 为 PROJECT_NAME。

## 第一步：解析需求
从一句话需求中抽取五要素：
- **目标功能**：要做什么（新增/修改/查询）
- **数据类别/领域**：股票行情、研报、Milvus 检索等
- **目标项目**：同父目录下任一 hetu-* 平级项目（默认当前项目）
- **产出物**：源码/脚本/文档
- **约束**：性能、权限、兼容性要求

## 第二步：资源匹配（必须）
读取 `<HARNESS_DIR>/docs/资源地图.md`（解析见上），为任务定位资源，**匹配顺序：先当前项目 `src/`、`docs/` → 再扫同父目录平级业务项目的 `src/`、`docs/`**：
- 接口文档：`<业务项目>/docs/<接口文档目录>/**`
- DDL：`<业务项目>/src/batch/sql/greatsql|tdengine/<专题>.sql`
- 参考代码：`<业务项目>/src/**`、`<AETHER_DIR>/utils/**`
- 宪章约束：`<HARNESS_DIR>/constitution/` 对应规范

## 第三步：按模板生成任务书
- 模板：`<HARNESS_DIR>/templates/task_book.md`
- 必须包含模板全部章节：任务要求 / 拆分策略(如涉及) / 文件与目录 / 接口与数据格式 / Shell脚本(如涉及) / 产出 / 单元测试 / 研发日志 / 资产沉淀 / 通知
- 命名与存放：任务目录 `opencode_schedule/<YYYYMMDD>/<YYYYMMDD>任务N<名称>/`，任务书 `<YYYYMMDD>任务N<名称>.md` 置于目录内
  - YYYYMMDD 取当天日期，N 为当日任务序号（已存在任务则递增）
- 引用资源须写明精确路径；明确的设计决策写入任务书，含含糊处标注"待确认"

## 第四步：核实
- 引用的接口/DDL/参考代码必须真实存在（路径可读），禁止虚构
- 验收标准尽量可量化（测试通过数、返回结构等）

## 约束
- 全程中文；只生成任务书，不实现业务代码。
