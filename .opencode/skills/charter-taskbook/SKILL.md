---
name: charter-taskbook
description: 任务书生成流程：根据一句话需求自动编写符合模板的任务书，用于研发流程的前置节点。Use when converting a free-text requirement into a task book during the charter dev workflow.
---
# 任务书生成流程

## 第一步：解析需求
从一句话需求中抽取五要素：
- **目标功能**：要做什么（新增/修改/查询）
- **数据类别/领域**：股票行情、研报、Milvus 检索等
- **目标项目**：hetu-aether / hetu-mercury / hetu-thoth（默认当前项目）
- **产出物**：源码/脚本/文档
- **约束**：性能、权限、兼容性要求

## 第二步：资源匹配（必须）
读取 `../hetu-hammurabi/docs/资源地图.md`，为任务定位：
- 接口文档：`docs/hetu-mercury/tushare_interface/<板块>/**`
- DDL：`hetu-mercury/src/batch/sql/greatsql|tdengine/<专题>.sql`
- 参考代码：`hetu-mercury/src/**`、`hetu-thoth/src/**`、`hetu-aether/utils/**`
- 宪章约束：`constitution/` 对应规范

## 第三步：按模板生成任务书
- 模板：`../hetu-hammurabi/templates/task_book.md`
- 必须包含模板全部章节：任务要求 / 拆分策略(如涉及) / 文件与目录 / 接口与数据格式 / Shell脚本(如涉及) / 产出 / 单元测试 / 研发日志 / 资产沉淀 / 通知
- 命名与存放：任务目录 `opencode_schedule/<YYYYMMDD>/<YYYYMMDD>任务N<名称>/`，任务书 `<YYYYMMDD>任务N<名称>.md` 置于目录内
  - YYYYMMDD 取当天日期，N 为当日任务序号（已存在任务则递增）
- 引用资源须写明精确路径；明确的设计决策写入任务书，含含糊处标注"待确认"

## 第四步：核实
- 引用的接口/DDL/参考代码必须真实存在（路径可读），禁止虚构
- 验收标准尽量可量化（测试通过数、返回结构等）

## 约束
- 全程中文；只生成任务书，不实现业务代码。
