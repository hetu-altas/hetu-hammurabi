# YYYYMMDD任务N 任务名称

## 重要提示
通用宪章规范统一存放在 harness 宿主项目（运行期由当前项目 `.opencode/.harness-env` 的 HARNESS_DIR 定位，缺失时按回退规则查找：同父目录下同时含 `constitution/constitution.md` + `.opencode/agents/` + `docs/资源地图.md` 的 hetu-* 目录即宿主）的 constitution 目录中，以 `constitution/constitution.md` 为顶层约束，任务执行前请务必仔细阅读并严格遵守。
宪章编程的流程编排与各节点规范见 harness 宿主的 `.opencode` 与 `templates` 目录。

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

记录在任务目录 `opencode_schedule/<YYYYMMDD>/<日期>任务N<名称>/` 下。

## 九、资产沉淀

本次研发需沉淀/更新的 docs 文档（存于 harness 宿主 `<HARNESS_DIR>/docs/hetu-<项目>/`，HARNESS_DIR 由当前项目 `.opencode/.harness-env` 解析）：

- 新增：`docs/hetu-<项目>/xxx.md`
- 更新：`docs/hetu-<项目>/yyy.md`（说明变更内容）

## 十、通知

使用公共工具项目（`<AETHER_DIR>`，由当前项目 `.opencode/.harness-env` 解析）`utils.util_dingtalk.send_markdown` 发送完成通知。
