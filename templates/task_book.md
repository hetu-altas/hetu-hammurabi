# YYYYMMDD任务N 任务名称

## 重要提示
通用宪章规范统一存放在与本项目目录同级的 hetu-hammurabi 项目的 constitution 目录中，以 `constitution/constitution.md` 为顶层约束，任务执行前请务必仔细阅读并严格遵守。
宪章编程的流程编排与各节点规范见 hetu-hammurabi 的 `.opencode` 与 `templates` 目录。

---

## 一、任务要求

- 需求背景：
- 目标：
- 验收标准：

## 二、拆分策略（如涉及分块/切分/抽样）

| 规则 | 值 |
|------|-----|

## 三、文件与目录

| 文件 | 说明 | 类型(新建/修改) |
|------|------|------|
| `src/xxx.py` | 主实现 | 新建 |
| `scripts/xxx.sh` | 启动脚本 | 新建 |
| `unit_test/test_xxx.py` | 单元测试 | 新建 |
| `requirements.txt` | 依赖 | 修改 |

## 四、接口 / 数据格式定义

- 输入：
- 输出：
- 关键字段：

## 五、Shell 脚本

```bash
用法说明
```

## 六、产出

- 输出路径：
- 数据库/日志落点：

## 七、单元测试

测试文件：`unit_test/test_xxx.py`
必须覆盖：正常案例 / 反案例 / 边界条件，结果保存到 `unit_test/test/` 下。

## 八、研发日志

记录在 `opencode_schedule/YYYYMMDD/` 下。

## 九、资产沉淀

本次研发需沉淀/更新的 docs 文档（存于 hetu-hammurabi `docs/hetu-<项目>/`）：

- 新增：`docs/hetu-<项目>/xxx.md`
- 更新：`docs/hetu-<项目>/yyy.md`（说明变更内容）

## 十、通知

使用 hetu-aether `utils.util_dingtalk.send_markdown` 发送完成通知。
