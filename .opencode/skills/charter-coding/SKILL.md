---
name: charter-coding
description: 遵循 hetu 系列编码宪章进行代码实现，用于研发流程的编码节点
---
## 编码宪章

1. 阅读宪章源文件（相对于当前项目根目录，详见 `../hetu-hammurabi/docs/资源地图.md`）：
   - `../hetu-hammurabi/constitution/constitution.md`（顶层约束与安全底线）
   - `../hetu-hammurabi/constitution/coding/coding.md`（Python 编码规范）
   - `../hetu-hammurabi/constitution/project/project.md`（项目结构规范）
2. 严格遵守以下要点：
   - 文件首行 `# -*- coding: utf-8 -*-`，包含模块级 docstring
   - 函数/方法必须标注参数与返回值类型，docstring 为 Google 或 Sphinx 风格
   - 命名规范、导入顺序（标准库→第三方→本地，组间空一行）、禁止 `from module import *`
   - 数据库连接使用 hetu-aether 的 `utils/util_db.py` 封装类与连接池，凭据从 `conf/` JSON 读取，禁止硬编码
   - 通用工具优先复用 hetu-aether `utils/`，禁止重复造轮子
   - 目录名小写加下划线、包目录含 `__init__.py`、目录层级不超过 5 层
3. 新增依赖需评估必要性并同步更新 `requirements.txt`。
