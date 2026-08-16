---
name: charter-testing
description: 遵循 hetu 系列单元测试宪章编写并运行测试，结果作为流程门禁，用于研发流程的测试节点
---
## 单元测试宪章

## 路径解析约定（harness 运行时拓扑）
- 本项目已安装 harness 时，**先读取当前项目 `.opencode/.harness-env`**（由 install_harness.sh 生成，字段：PROJECT_NAME / PROJECT_DIR / WORKSPACE_DIR / HARNESS_DIR / AETHER_DIR / VENV_BIN，均为绝对路径），用其中的变量替换下述 `<HARNESS_DIR>`、`<AETHER_DIR>`、`<VENV_BIN>` 占位符。
- **回退规则**（.harness-env 缺失或字段缺失时动态查找）：① 同父目录（WORKSPACE_DIR）下同时含 `constitution/constitution.md` + `.opencode/agents/` + `docs/资源地图.md` 的 `hetu-*` 目录为 harness 宿主 → HARNESS_DIR；② 同父目录下 `hetu-aether` 为公共工具项目 → AETHER_DIR；③ 同父目录下 `venv-hetu/bin/python` 为共享环境 → VENV_BIN；④ 当前工作目录 basename 为 PROJECT_NAME。

1. 阅读宪章源文件（相对于当前项目根目录）：
   - `<HARNESS_DIR>/constitution/unit_test/unit_test.md`
2. 严格遵守以下要点：
   - 统一使用 `unittest`，禁止引入 pytest 等第三方框架
   - 测试文件放 `unit_test/` 下，命名 `test_<模块名>.py`
   - 必须覆盖三大类：正常案例 / 反案例（非法输入、异常抛出）/ 边界条件（零值、空值、时间边界、闰年、极值等）
   - 每个测试类与方法都有中文 docstring
   - 外部依赖（数据库、网络）用 `@patch` / `MagicMock` 隔离；单例类在 `setUp` 重置
   - 测试结果写入 `unit_test/test/test_<模块名>_result.txt`
   - 权限受限的外部接口用 try/except + skipTest 处理
3. 运行方式（项目目录下）：
<<<<<<< Updated upstream
   - 优先使用共享 venv：`../venv-hetu/bin/python -m unittest unit_test.test_xxx -v`
=======
   - 优先使用共享环境解释器 `<VENV_BIN> -m unittest unit_test.test_xxx -v`
>>>>>>> Stashed changes
   - 或直接运行 `python test_xxx.py`，确保结果文件已生成
