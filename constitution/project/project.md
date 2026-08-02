# 项目结构规范

## 一、多项目布局

### 1.1 项目组织
同一产品线下的多个项目部署在统一父目录下，共享虚拟环境和公共项目：

```
<workspace>/
├── hetu-aether/       # 公共项目（配置、工具类、通用服务、规范文档）
├── hetu-XXX/          # 业务项目（业务逻辑、数据获取、对外接口）
├── hetu-YYY/          # 业务项目
└── venv-hetu/         # 共享 Python 虚拟环境
```

### 1.2 项目命名
- 公共项目固定命名为 `hetu-aether`
- 其他项目统一采用 `hetu-XXX` 格式，`XXX` 为小写英文，反映项目职能
- 虚拟环境命名为 `venv-hetu`

### 1.3 项目角色

| 项目 | 角色 | 职责 | 典型目录 |
|------|------|------|---------|
| hetu-aether | 公共项目 | 提供配置管理、数据库连接、日志、消息通知、编码规范等通用能力 | `conf/`、`utils/`、`constitution/` |
| hetu-XXX | 业务项目 | 实现具体业务逻辑，依赖 hetu-aether | `src/`、`docs/` |

### 1.4 跨项目引用
- 业务项目通过相对路径或 PYTHONPATH 引用 hetu-aether 的资源和工具
- hetu-aether 的 `utils/` 是全局共享资源，业务项目中禁止重复实现相同功能
- 禁止循环依赖

---

## 二、通用目录结构

```
<project>/
├── README.md               # 项目说明（必须）
├── .gitignore               # Git 忽略规则（必须）
├── conf/                    # 配置文件（hetu-aether 必须，业务项目可选）
│   └── *_conf.json
├── src/                     # 源代码（业务项目必须）
│   ├── <业务模块>/
│   │   └── ...
│   ├── utils/               #   项目级工具（可选）
│   └── <其他模块>/
├── utils/                   # 工具模块（hetu-aether 必须）
│   ├── __init__.py
│   └── util_*.py
├── unit_test/               # 单元测试（必须）
│   ├── __init__.py
│   ├── test_*.py
│   └── test/                #   测试结果输出目录（必须）
├── constitution/            # 项目规范（hetu-aether 必须，业务项目可选）
│   ├── constitution.md      #   顶层约束
│   ├── coding/              #   编码规范
│   ├── unit_test/           #   测试规范
│   └── project/             #   项目结构规范
├── docs/                    # 文档（可选）
│   └── ...
└── opencode_schedule/       # 开发日志归档（可选）
    └── YYYYMMDD/
        └── *.md
```

**说明：**
- 标注"必须"的目录/文件，所有项目都必须具备
- 标注"hetu-aether 必须"的，仅 hetu-aether 公共项目强制要求
- 标注"业务项目必须"的，仅当该项目定位为业务项目时强制要求
- 标注"可选"的，根据项目实际需要决定是否创建

---

## 三、必需目录与文件

### 3.1 所有项目通用

| 文件/目录 | 用途 |
|----------|------|
| `README.md` | 项目说明，包含项目描述、目录结构、环境依赖、使用方法 |
| `.gitignore` | Git 忽略规则，至少包含 `__pycache__/`、`*.pyc`、`venv/`、IDE 目录 |
| `unit_test/` | 单元测试代码 |
| `unit_test/test/` | 测试结果输出目录 |

### 3.2 hetu-aether 公共项目额外必须

| 文件/目录 | 用途 |
|----------|------|
| `conf/` | 所有连接配置的 JSON 文件 |
| `utils/` | 通用工具方法模块，含 `__init__.py` |
| `constitution/` | 项目规范文档 |

### 3.3 业务项目额外必须

| 文件/目录 | 用途 |
|----------|------|
| `src/` | 源代码，按业务模块划分 |

---

## 四、目录命名规范

### 4.1 通用规范
- 目录名使用小写字母加下划线：`unit_test`、`data_sync`、`full_sync`
- 每个 Python 包目录必须包含 `__init__.py` 文件（可为空文件）
- 目录层级不超过 5 层（从项目根目录起算）
- 禁止使用中文、拼音或拼音缩写命名目录

### 4.2 业务模块命名
- 使用英文小写加下划线，反映业务领域
- 示例：`stock_data/`、`data_sync/`、`market_data/`
- 业务模块内可按子领域再分一层子目录

### 4.3 constitution 规范目录
`constitution/` 存放项目规范与约束文档，按规范类型划分子目录：

```
constitution/
├── constitution.md           # 顶层约束
├── coding/                   # 编码规范
│   └── coding.md
├── unit_test/                # 单元测试规范
│   └── unit_test.md
├── project/                  # 项目结构规范
│   └── project.md
└── <新增规范>/               # 按需扩展
    └── <规范名>.md
```

新增规范类型时，在 `constitution/` 下新建小写+下划线命名的子目录。

### 4.4 开发日志目录
`opencode_schedule/` — 按日期 `YYYYMMDD/` 归档，同日多任务以**任务目录**隔离：
```
opencode_schedule/<YYYYMMDD>/
└── <YYYYMMDD>任务<N>_<名称>/   # 任务目录（以任务书名去掉 .md 命名）
    ├── <YYYYMMDD>任务<N>_<名称>.md   # 任务定义
    └── 实施计划/评审报告/研发日志/流程状态等中间产物
```
- 任务定义：`<日期>任务<N>.md`（位于任务目录内）
- 会话记录：`<日期>_session.md`

---

## 五、文件命名规范

### 5.1 源代码文件

| 类型 | 命名格式 | 示例 |
|------|---------|------|
| 工具模块 | `util_<功能>.py` | `util_db.py`、`util_log.py` |
| 业务模块 | `<动词>_<名词>.py` 或 `<功能描述>.py` | `fetch_daily.py`、`data_cleaner.py` |
| 单元测试 | `test_<被测试模块>.py` | `test_util_datetime.py`、`test_fetch_data.py` |
| 包标识 | `__init__.py` | 必含，可为空文件 |

### 5.2 配置文件
- 统一使用 JSON 格式：`<组件名>_conf.json`
- 示例：`db_conf.json`、`redis_conf.json`、`log_conf.json`

### 5.3 文档文件
- 规范文档：`<规范名>.md`，存放于 `constitution/<类别>/` 下
- 项目文档：`<描述>.md`，存放于 `docs/` 下
- 开发日志：`<日期>_<描述>.md`，存放于任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/` 下

---

## 六、配置目录

### 6.1 配置存放
- hetu-aether 的配置统一存放在 `conf/` 目录下
- 业务项目不持有独立配置，通过相对路径引用 hetu-aether 的配置
- 用户级敏感配置（如 Token）存放在 `~/.config/` 下，不进入项目仓库

### 6.2 配置文件格式
统一使用 JSON 格式，字段包含 host、port、user、password、连接池参数等。

### 6.3 安全要求
- 配置文件不得提交敏感凭证到版本控制（使用 `.gitignore` 排除或环境变量替代）
- 配置读取使用 utils 中的封装方法

---

## 七、源代码组织

### 7.1 hetu-aether 公共项目
- `utils/` 下每个模块遵循单一职责原则
- 通过 `__init__.py` 对外暴露接口
- 模块间避免循环引用

### 7.2 业务项目（hetu-XXX）
- `src/` 下按业务领域划分子目录
- 每个子目录内文件按功能命名，保持统一前缀
- 项目级工具类可放在 `src/utils/`，优先复用 hetu-aether 的 `utils/`

### 7.3 模块间依赖
```
hetu-XXX/src/  ──→  hetu-aether/conf/   （配置）
               ──→  hetu-aether/utils/  （工具）
```
- 业务项目依赖 hetu-aether，反之不可
- 业务项目之间不可相互依赖
- 如需共享工具方法，应提取到 hetu-aether 的 `utils/` 中

---

## 八、文档组织

### 8.1 文档类型与位置

| 文档类型 | 存放位置 | 说明 |
|---------|---------|------|
| 项目说明 | `README.md` | 根目录，项目概述、结构、使用方法 |
| 编码规范 | `constitution/coding/coding.md` | Python 编码标准 |
| 测试规范 | `constitution/unit_test/unit_test.md` | 单元测试规则 |
| 项目结构规范 | `constitution/project/project.md` | 目录结构与命名规则 |
| 顶层约束 | `constitution/constitution.md` | 项目级安全与编码底线 |
| 业务文档 | `docs/` | 按业务类别组织的说明文档 |
| 开发日志 | `opencode_schedule/<YYYYMMDD>/<任务目录>/` | 按日期+任务目录归档的开发过程记录 |

### 8.2 文档语言
- 项目说明、技术文档、规范文档使用中文
- 代码中的注释和 docstring 使用中文
- API 字段名和技术术语保留英文

---

## 九、新增目录规则

### 9.1 允许新建的目录
- 业务模块目录（`src/<模块>/`）
- 业务子模块目录（`src/<模块>/<子模块>/`）
- 文档子目录（`docs/<分类>/`）
- 规范子目录（`constitution/<类别>/`）
- SQL/脚本目录（`src/batch/`、`src/script/` 等）

### 9.2 禁止的操作
- 禁止在项目根目录新建非标准的一级目录
- 禁止在 `conf/` 外新建存放配置文件的目录
- 禁止在 hetu-aether 的 `utils/` 外新建通用工具目录
- 禁止创建无实际代码的深层嵌套空包

### 9.3 新建目录检查清单
- [ ] 目录用途是否属于已有标准目录之一？如果是，放在标准目录内
- [ ] 命名是否符合规范（小写+下划线、英文）？
- [ ] 如需作为 Python 包，是否包含 `__init__.py`？
- [ ] 目录层级是否在 5 层以内？

---

## 十、Python 包结构

### 10.1 包标识
- 每个 Python 包目录必须包含 `__init__.py` 文件（可为空）
- 如需对外暴露接口，在 `__init__.py` 中显式导入

### 10.2 包层级
- hetu-aether 的 `utils/` 为一级包，不嵌套子包
- 业务层 `src/<模块>/` 为包，最多嵌套一层子包
- 推荐最大包深度：2 层（不含项目根目录）

```
✓ 推荐: src/<模块>/<子模块>/
✗ 避免: src/a/b/c/d/e/    (过深，维护困难)
```

### 10.3 导入路径
- 项目内模块使用相对导入：`from .util_db import get_connection`
- 跨项目时通过 PYTHONPATH 配置引用路径

---

## 十一、`.gitignore` 模板

```gitignore
# Byte-compiled files
__pycache__/
*.py[cod]

# Virtual Environment
venv/
venv-*/
.venv/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Environment
.env
*.env.local

# Logs
*.log
logs/

# Temporary
tmp/
temp/
*.tmp

# Distribution
dist/
build/
*.egg-info/
```

---

## 十二、REAMDE.md 模板

```markdown
# <项目名称>

## 项目简介
<简要描述>

## 目录结构
<项目>/
├── README.md
├── conf/               # 配置文件
├── src/                # 源代码
├── utils/              # 工具模块
├── unit_test/          # 单元测试
└── docs/               # 文档

## 环境要求
- Python <版本>
- 虚拟环境：`<路径>`

## 快速开始
<使用说明>

## 开发指南
- 编码规范：`constitution/coding/coding.md`
- 测试规范：`constitution/unit_test/unit_test.md`
- 项目结构：`constitution/project/project.md`
```
