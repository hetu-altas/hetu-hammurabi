---
name: charter-analysis
description: 需求分析节点的资源匹配流程：按任务书自动定位接口文档、DDL、参考代码。Use when analyzing a task book during the charter dev workflow.
---
# 需求分析 · 资源匹配流程

## 第一步：读资源地图
先读取 `../hetu-hammurabi/docs/资源地图.md`，明确各类资源的存放位置，避免凭印象乱找。

## 第二步：解析任务书，抽取"检索键"
从任务书中提取用于匹配的关键信息：
- 数据类别/专题（如：股票行情、ETF、期货、研报、公告）→ 匹配接口文档板块与 DDL 文件
- 接口名 / 表名 / 字段名（如 `ts_code`、`daily`、`research_report`）→ 关键词检索
- 功能意图（如"同步""分块""向量入库"）→ 匹配参考代码模块

## 第三步：按三类资源自动匹配

### 3.1 接口文档
1. 由数据类别定位板块目录：`../hetu-hammurabi/docs/hetu-mercury/tushare_interface/<板块>/`
2. 在该目录用 grep 检索接口名/表名关键词，锁定对应 `.md`
3. 交叉验证：对照 `../hetu-mercury/src/batch/sql/greatsql/<专题>-接口列表.md` 确认接口权限与字段

### 3.2 DDL / 表结构
1. GreatSQL：`../hetu-mercury/src/batch/sql/greatsql/<专题>.sql`
2. TDengine：`../hetu-mercury/src/batch/sql/tdengine/<专题>.sql`
3. 在 `.sql` 内检索表名，提取建表语句与字段定义

### 3.3 参考代码
1. 数据获取类 → `../hetu-mercury/src/fetch_tushare_data/<品种>/**`
2. 同步/批量类 → `../hetu-mercury/src/data_sync/**`、`../hetu-mercury/src/batch/**`
3. 文档处理类 → `../hetu-thoth/src/{convert2md,download_files,text2jsonl,embedding,indexing,ingestion}/**`
4. 公共能力 → `../hetu-aether/utils/util_*.py`
5. 选定最相似实现后通读其主流程，作为新代码的基线

## 第四步：核实（必须）
- 每个匹配结果必须给出**精确文件路径 + 关键行号**，并说明匹配依据
- 核对字段/表名/接口参数与任务书是否一致；不一致说明偏差与取舍
- 无法匹配时明确标注"未找到"，不得虚构资源

## 第五步：写入实施计划
在 `实施计划.md` 末尾追加「资源匹配清单」表格：

| 需求点 | 匹配资源(路径+行号) | 类型(接口/DDL/代码) | 依据与偏差 |
|--------|--------------------|--------------------|-----------|

## 约束
- 全程中文；引用必须真实存在，禁止编造路径。
