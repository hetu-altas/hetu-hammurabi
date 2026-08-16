---
name: charter-coding
description: 遵循 hetu 系列编码宪章进行代码实现，用于研发流程的编码节点
---
## 编码宪章

## 路径解析约定（harness 运行时拓扑）
- 本项目已安装 harness 时，**先读取当前项目 `.opencode/.harness-env`**（由 install_harness.sh 生成，字段：PROJECT_NAME / PROJECT_DIR / WORKSPACE_DIR / HARNESS_DIR / AETHER_DIR / VENV_BIN，均为绝对路径），用其中的变量替换下述 `<HARNESS_DIR>`、`<AETHER_DIR>`、`<VENV_BIN>` 占位符。
- **回退规则**（.harness-env 缺失或字段缺失时动态查找）：① 同父目录（WORKSPACE_DIR）下同时含 `constitution/constitution.md` + `.opencode/agents/` + `docs/资源地图.md` 的 `hetu-*` 目录为 harness 宿主 → HARNESS_DIR；② 同父目录下 `hetu-aether` 为公共工具项目 → AETHER_DIR；③ 同父目录下 `venv-hetu/bin/python` 为共享环境 → VENV_BIN；④ 当前工作目录 basename 为 PROJECT_NAME。

1. 阅读宪章源文件（相对于当前项目根目录，详见 `<HARNESS_DIR>/docs/资源地图.md`）：
   - `<HARNESS_DIR>/constitution/constitution.md`（顶层约束与安全底线）
   - `<HARNESS_DIR>/constitution/coding/coding.md`（Python 编码规范）
   - `<HARNESS_DIR>/constitution/project/project.md`（项目结构规范）
2. 严格遵守以下要点：
   - 文件首行 `# -*- coding: utf-8 -*-`，包含模块级 docstring
   - 函数/方法必须标注参数与返回值类型，docstring 为 Google 或 Sphinx 风格
   - 命名规范、导入顺序（标准库→第三方→本地，组间空一行）、禁止 `from module import *`
   - 数据库连接使用 `<AETHER_DIR>/utils/util_db.py` 封装类与连接池，凭据从 `<AETHER_DIR>/conf/` JSON 读取，禁止硬编码
   - 通用工具优先复用 `<AETHER_DIR>/utils/`，禁止重复造轮子
   - 目录名小写加下划线、包目录含 `__init__.py`、目录层级不超过 5 层
3. 新增依赖需评估必要性并同步更新 `requirements.txt`。
