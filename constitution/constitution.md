# 项目宪法（Constitution）

## 交互要求
- 所有回复请使用中文。
- 思考过程（如果可见）也请使用中文。

本文件为 hetu 系列项目的顶层约束。各子规范详见对应文档：

| 规范 | 文档 |
|------|------|
| 项目结构 | [constitution/project/project.md](project/project.md) |
| Python 编码 | [constitution/coding/coding.md](coding/coding.md) |
| 单元测试 | [constitution/unit_test/unit_test.md](unit_test/unit_test.md) |
| 日志 | [constitution/log/log.md](log/log.md) |
| TDengine | [constitution/tdengine/tdengine.md](tdengine/tdengine.md) |
| Milvus | [constitution/milvus/milvus.md](milvus/milvus.md) |
| 任务拆分 | [constitution/task_split/task_split.md](task_split/task_split.md) |
| 研发流程 | 见[十三、研发流程与宪章工作流](#十三研发流程与宪章工作流) |

---

## 一、安全底线

1. 禁止获取操作系统、数据库等任何系统的 root 权限，禁止进入容器
2. 禁止在终端、日志、代码中输出任何明文密码、密钥、Token
3. 任何数据的增删改操作，必须先备份，操作完成后验证恢复
4. 连接配置、用户名、密码等凭据必须从 `conf/` 目录的 JSON 配置文件获取，禁止硬编码

## 二、项目体系

1. `hetu-aether` 为公共项目，提供配置管理、数据库连接池、日志、工具方法等通用能力（代码资产）
2. `hetu-hammurabi` 为宪章编程 harness 模块，宪章规范统一存放在其 `constitution/` 目录，各项目不再各自维护 constitution
3. 其他项目统一命名为 `hetu-XXX`，通过相对路径引用 hetu-aether 的资源和工具、hetu-hammurabi 的宪章
4. 所有项目部署在同一父目录下，共享 `venv-hetu` 虚拟环境
5. 详见 [project.md](project/project.md)

## 三、Python 环境

1. 使用项目指定的 venv 环境（`../venv-hetu/bin`，相对路径约定：共享 venv 与各项目同父目录），禁止使用裸 Python 环境
2. 禁止随意新建 venv
3. 依赖包统一通过 `requirements.txt` 管理，新增依赖需评估必要性与兼容性
4. 本文档中所有路径均为**相对路径约定**（`../venv-hetu/`、`../logs/` 等），开源部署时按实际目录布局调整，替换占位约定即可

## 四、编码要求

1. 所有 Python 文件首行声明 `# -*- coding: utf-8 -*-`，包含模块级 docstring
2. 所有函数/方法必须标注参数和返回值类型
3. Docstring 格式：Google 风格（`Args`/`Returns`/`Raises`）或 Sphinx 风格（`:param`/`:return`），同一文件内统一
4. 类、方法、常量、变量命名遵循 [coding.md](coding/coding.md) 中的命名规范
5. 禁止使用 `from module import *`
6. 导入顺序：标准库 → 第三方库 → 本地模块，各组间空一行
7. 详见 [coding.md](coding/coding.md)

## 五、数据库与连接

1. 数据库连接必须使用 hetu-aether 的 `utils/util_db.py` 中封装的类
2. 所有数据库、Redis 等连接必须使用**连接池**
3. 连接使用完毕必须及时释放，推荐使用 `with` 上下文管理器
4. SQL 语句禁止直接拼接用户输入，必须使用参数化查询
5. 连接配置统一从 `conf/` 目录的 JSON 配置文件获取

## 六、单元测试

1. 测试文件放在 `unit_test/` 目录下，命名 `test_<文件名>.py`
2. 统一使用 `unittest` 框架
3. 每个测试文件必须覆盖：**正常案例**、**反案例**（异常/非法输入）、**边界条件**
4. 测试结果保存到 `unit_test/test/` 目录下
5. 外部依赖使用 `@patch` / `MagicMock` 隔离
6. 详见 [unit_test.md](unit_test/unit_test.md)

## 七、日志规范

1. 统一使用 hetu-aether 的 `utils/util_log.py` 日志模块
2. 日志输出目录：`../logs/hetu-altas/<项目名>/`
3. 每条日志必须包含：项目名、文件名、方法名、时间戳、操作名、执行状态、执行耗时
4. 错误日志还需包含错误码和异常堆栈
5. 日志按日期切割（每天零时），保留最近 30 天
6. 详见 [log.md](log/log.md)

## 八、代码复用

1. 通用工具方法放在 hetu-aether 的 `utils/` 目录下，业务项目禁止重复实现
2. 使用已有工具方法前先确认其存在，避免重复造轮子
3. 业务项目中出现重复的辅助函数，应评估是否提升到 hetu-aether 的 `utils/` 统一管理

## 九、文件与目录

1. 目录名使用小写字母加下划线，禁止中文/拼音
2. 每个 Python 包目录必须包含 `__init__.py`
3. 目录层级不超过 5 层
4. 项目根目录禁止新建非标准的一级目录
5. 详见 [project.md](project/project.md)

## 十、TDengine 规范

1. 使用 `get_tdengine()` 单例获取数据库连接，禁止重复创建 `TDengine` 实例
2. 连接必须通过 `with td.get_connection()` 上下文管理器获取和归还
3. 时序数据统一使用**超级表（STABLE）**模型，按 `ts_code` 标签分区，时间列命名为 `ts`
4. 子表命名采用 `前缀_股票代码` 格式，如 `d_000001_sz`
5. 批量插入按 `ts_code` 分组，每批不超过 500 行
6. 超级表 DDL 集中存放在 `src/batch/sql/tdengine/` 目录下，按数据类别分文件
7. 新增超级表需同步更新 `_TD_COLUMNS_MAP`、`_TD_FIELD_MAP`、`_TABLE_PREFIX` 三个映射
8. 全量同步使用 `DROP STABLE IF EXISTS` → `CREATE STABLE` 重建，增量同步不删除已有数据
9. 查询必须包含时间范围过滤，避免全表扫描
10. 详见 [tdengine.md](tdengine/tdengine.md)

## 十一、Milvus 规范

1. Milvus 连接与操作统一使用 hetu-aether 的 `utils/util_milvus.py` 公共工具，禁止直接使用原生 `MilvusClient` 或重复封装
2. 通过 `get_milvus(project_name="hetu-xxx")` 获取单例，连接用完必须释放
3. Collection 创建前先检查是否存在；删除前必须先备份
4. 批量入库每批不超过 1000 条，入库后核对插入数量并创建索引
5. 检索必须指定 top_k、加载 Collection 并用过滤表达式缩小范围
6. 连接配置统一从 `conf/milvus_conf.json` 读取，禁止硬编码
7. 详见 [milvus.md](milvus/milvus.md)

## 十二、任务拆分评估

1. 任务书编写前必须按 `task_split/task_split.md` 评估任务粒度：以当前模型上下文窗口为约束，单节点峰值 ≤ 窗口 60%、主会话累计 ≤ 窗口 30%
2. 任务按代码量分级：小（≤300 行）/ 中（≤1500 行）/ 大（≤4000 行）/ 超大（>4000 行，必须拆分）
3. 拆分以"可独立验证闭环"为单位（编码+单测+评审），按依赖顺序拆分，子任务间以接口为契约
4. 超限任务拆分为多个任务书（任务1/任务2/...），每个任务仍走完整流程
5. 详见 [task_split.md](task_split/task_split.md)

## 十三、研发流程与宪章工作流

1. 研发统一通过 hetu-hammurabi 的宪章工作流执行：在业务项目内使用 `/dev <任务书路径>` 命令触发 charter-orchestrator 编排。
2. 任务书按 hetu-hammurabi `templates/task_book.md` 模板编写，与实施计划、研发日志、流程状态一并存放于业务项目任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/` 下（以任务书名建目录）。
3. 流程节点严格按序执行，前序节点未完成不得进入下一节点：
   - 节点-1 任务书生成（仅一句话需求输入时）：按模板生成任务书并匹配资源
   - 节点0 校验：任务书/宪章/输出目录确认
   - 节点1 分析：解析任务书，产出 `实施计划.md`
   - 节点2 编码：按本宪法编码要求实现
   - 节点3 单元测试：按单测规范编写并运行，作为**门禁**，全部通过方可进入后续节点
   - 节点4 代码评审：按编码宪章与质量要求评审，产出 `评审报告.md`，**REVISE** 则回节点2修复后重测重审
   - 节点5 研发日志：撰写 `任务N研发日志.md`
   - 节点6 资产沉淀：将研发产出沉淀为 `docs/hetu-<项目>/` 下的文档，区分**新增**（创建并登记资源地图）与**更新**（仅追加/修订相关章节）
   - 节点7 通知：通过 hetu-aether `utils/util_dingtalk.py` 发送完成通知
4. 需求分析必须按 hetu-hammurabi `docs/资源地图.md` 匹配接口文档、DDL、参考代码；引用资源须给出精确文件路径与行号，禁止虚构。
5. 每个节点状态固化到任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/研发流程状态.md`，流程结束输出总结。
6. 研发日志必须包含：任务概述、创建/修改文件清单、核心设计、测试结果、遗留问题。
7. 门禁约束：测试未通过禁止进入日志、资产沉淀与通知节点；修复重试不超过 3 轮，仍失败则停止并通知用户。测试节点须将结果写入任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/.gate.json`，由 charter-gate 插件硬性拦截未过门禁的日志/通知操作。评审 `REVISE` 回退编码修复，重试不超过 2 轮。
8. 资产沉淀必须遵守 `docs/资源地图.md` 的登记机制：新增文档/参考实现须登记，更新文档不得破坏原有内容。
9. 流程编排与节点代理定义见 hetu-hammurabi 的 `.opencode/` 目录。
