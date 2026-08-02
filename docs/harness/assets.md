# 宪章与资产体系

> 本文阐述宪章（约束资产）与资源地图/文档沉淀（技术资产）两大资产体系的组织与流转。

## 一、宪章体系（约束资产）

### 1.1 结构

`constitution/` 是**唯一权威**的通用宪章规范（子项目不再各自维护）：

```
constitution/
├── constitution.md        # 顶层宪法（12 章）
│   ├── 一 安全底线         # root/密钥/备份/凭据
│   ├── 二 项目体系         # aether=代码资产, hammurabi=宪章
│   ├── 三 Python 环境      # venv-hetu / requirements.txt
│   ├── 四 编码要求
│   ├── 五 数据库与连接      # 连接池 / 参数化查询
│   ├── 六 单元测试
│   ├── 七 日志规范
│   ├── 八 代码复用          # 复用 aether utils
│   ├── 九 文件与目录
│   ├── 十 TDengine 规范
│   ├── 十一 Milvus 规范
│   └── 十二 研发流程与宪章工作流
├── coding/coding.md       # Python 编码细则
├── unit_test/unit_test.md # 单测细则
├── log/log.md             # 运行时日志细则
├── project/project.md     # 项目结构细则
├── tdengine/tdengine.md   # TDengine 细则
├── milvus/milvus.md       # Milvus 细则（统一 aether util_milvus）
└── task_split/task_split.md # 任务拆分评估（上下文预算与粒度分级）
```

### 1.2 宪章如何约束模型

```
宪章源文件 (constitution/) ──引用──▶ Skill (charter-*) ──加载──▶ 节点代理 (charter-*)
    修改宪章只需动源文件，Skill/代理提示词零改动
```

### 1.3 宪章维护规则

- 只改 `constitution/`，不同步回子项目（子项目副本已停更）
- 新增领域规范：在 `constitution/` 加子目录 + 顶层宪法加章节与索引行
- 涉及流程/门禁变更：同步更新顶层宪法第十二章

## 二、资源地图（可寻址资产索引）

`docs/资源地图.md` 是**分析节点的第一检索入口**，解决"模型不知道去哪找"的问题：

| 章节 | 内容 | 路径示例 |
|------|------|---------|
| 一、宪章 | 各规范文件位置 | `../hetu-hammurabi/constitution/coding/coding.md` |
| 二、接口文档 | 各板块接口文档/清单 | `docs/hetu-mercury/tushare_interface/<专题>/**` |
| 三、DDL | GreatSQL/TDengine 建表 | `hetu-mercury/src/batch/sql/greatsql/<专题>.sql` |
| 四、公共工具 | aether utils 职责 | `util_db`/`util_dingtalk`/`util_milvus` 等 |
| 五、参考实现 | 相似代码入口 | mercury fetch/batch、thoth 文档全链路 |
| 六、其他 | 模板/venv/归档目录 | `templates/`、`venv-hetu` |

分析节点必须：读地图 → 提取检索键 → 三类资源自动匹配 → **给出精确路径+行号并核实** → 写入实施计划的「资源匹配清单」。

## 三、资产沉淀（技术资产反哺）

### 3.1 节点职责

每次研发完成后（节点6），charter-assetter 把可复用产出沉淀为文档：

| 可沉淀资产 | 示例 |
|-----------|------|
| 接口/数据结构 | 新接口调用方式、字段说明 |
| 工具方法 | 新封装的通用能力 |
| 流程指引 | 同步流程、分块策略、Shell 用法 |
| 参考实现 | 供后续相似任务对照的代码路径 |

### 3.2 新增 vs 更新（强制判定）

| 判定 | 动作 |
|------|------|
| 目标文档**不存在** → 新增 | 遵循目标目录既有命名与结构创建 + **登记资源地图** |
| 目标文档**已存在** → 更新 | 保持结构与命名，仅追加/修订相关章节，标注日期与来源任务 |

一致性保障：charter-gate 插件对 `docs/hetu-*/` 改动做资源地图登记检查（未登记则告警）。

## 四、资产流转闭环

```
需求 → 分析(读资源地图) → 编码(复用参考实现) → 测试 → 评审
                                                │
                      ┌─────────────────────────┘
                      ▼
              资产沉淀(写 docs/资源地图登记) ──▶ 下一次需求的"可寻址资产" ↑
```

## 五、文档资产（归集层）

`docs/hetu-aether|mercury|thoth/` 归集各项目的文档快照：

- 接口文档：`docs/hetu-mercury/tushare_interface/`（约 200 篇，按板块分目录）
- 同步指引：`docs/hetu-mercury/sync_data/`
- thoth 指南：`docs/hetu-thoth/`（convert2md / download_files / indexing / text2jsonl 等）

> 演进建议：文档量 < 500 篇时资源地图 + 关键词检索足够；超过或出现跨域模糊检索需求时，可复用 thoth 的 Milvus 链路做语义检索，届时需解决"索引与源同步"的新鲜度问题。
