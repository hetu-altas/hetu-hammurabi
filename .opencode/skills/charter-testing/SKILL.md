---
name: charter-testing
description: 遵循 hetu 系列单元测试宪章编写并运行测试，结果作为流程门禁，用于研发流程的测试节点
---
## 单元测试宪章

1. 阅读宪章源文件（相对于当前项目根目录）：
   - `../hetu-hammurabi/constitution/unit_test/unit_test.md`
2. 严格遵守以下要点：
   - 统一使用 `unittest`，禁止引入 pytest 等第三方框架
   - 测试文件放 `unit_test/` 下，命名 `test_<模块名>.py`
   - 必须覆盖三大类：正常案例 / 反案例（非法输入、异常抛出）/ 边界条件（零值、空值、时间边界、闰年、极值等）
   - 每个测试类与方法都有中文 docstring
   - 外部依赖（数据库、网络）用 `@patch` / `MagicMock` 隔离；单例类在 `setUp` 重置
   - 测试结果写入 `unit_test/test/test_<模块名>_result.txt`
   - 权限受限的外部接口用 try/except + skipTest 处理
3. 运行方式（项目目录下）：
   - 优先使用共享 venv：`/mnt/d/workspace/hetu-altas/venv-hetu/bin/python -m unittest unit_test.test_xxx -v`
   - 或直接运行 `python test_xxx.py`，确保结果文件已生成
