# Python 研发规范

## 一、文件编码与头部声明

1. 所有 Python 文件首行声明编码：`# -*- coding: utf-8 -*-`
2. 文件头部必须包含模块级 docstring，说明模块用途。数据获取类模块需详细列出输出字段：

```python
# -*- coding: utf-8 -*-
"""
fetch_daily.py - 获取A股日线行情数据

功能说明：
    通过Tushare API获取A股日线行情数据，包含前后复权数据。
    对应接口文档：https://tushare.pro/document/2?doc_id=27

输出字段说明：
    - ts_code: 股票代码
    - trade_date: 交易日期
    - open: 开盘价
    - high: 最高价
    - low: 最低价
    - close: 收盘价
"""
```

3. 非数据获取类模块可简化 docstring，仅说明模块用途：

```python
# -*- coding: utf-8 -*-
"""
日期时间工具类
提供日期和日期时间的格式化、计算、转换等功能
"""
```

## 二、命名规范

### 2.1 文件命名
- Python 文件使用小写字母加下划线：`util_datetime.py`、`fetch_daily.py`
- 数据获取类脚本统一采用 `fetch_<api_name>.py` 命名
- 包目录下必须包含 `__init__.py` 文件（可为空文件）
- 单元测试文件以 `test_` 开头：`test_util_datetime.py`、`test_stock_data.py`

### 2.2 代码命名
- 类名使用大驼峰：`DateUtil`、`GreatSQL`、`DingTalkAgent`
- 函数/方法名使用小写+下划线：`get_instance()`、`str_to_date()`、`fetch_daily()`
- 变量名使用小写+下划线：`config_path`、`log_extra`
- 常量使用全大写+下划线：`DATE_FORMAT`、`DINGTALK_API`
- 私有成员（属性/方法）使用单下划线前缀：`_config`、`_pool`、`_init_pool()`
- 模块级私有函数使用单下划线前缀：`_get_project_root()`、`_load_tushare_config()`

## 三、架构设计

### 3.1 类（Class）- 有状态/可复用场景
- 数据库连接、日志记录、配置管理、消息代理等有状态对象使用类封装
- 全局唯一实例使用单例模式，通过 `get_instance()` 获取
- 工具类优先使用 `@staticmethod`，避免强制实例化
- 资源管理类应实现上下文管理器协议或使用 `@contextmanager` 装饰器

```python
from contextlib import contextmanager
from typing import Optional

class GreatSQL:
    """GreatSQL 数据库操作类（使用连接池）"""
    _instance: Optional["GreatSQL"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, config_path: str = "conf/db_conf.json") -> "GreatSQL":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config_path)
        return cls._instance

    @contextmanager
    def get_connection(self):
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    def query_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[dict]:
        ...
```

### 3.2 函数（Function）- 无状态/数据获取场景
- 数据获取、格式转换、单一处理的场景使用纯函数模式
- 每个文件对外暴露一个主函数，命名与文件名对应
- 辅助函数使用下划线前缀标记为模块私有
- 每个文件末尾包含 `if __name__ == "__main__"` 示例调用块

```python
"""
fetch_daily.py - 获取A股日线行情数据
"""

import os
import json
from typing import Optional
from pathlib import Path

import pandas as pd
import tushare as ts

_TUSHARE_CONF_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "hetu-aether" / "conf" / "tushare_conf.json"
)

def _load_tushare_config() -> dict:
    """加载Tushare API配置文件"""
    config_path = os.path.abspath(_TUSHARE_CONF_PATH)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Tushare配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if "token" not in config:
        raise ValueError("Tushare配置中缺少token字段")
    return config

def init_tushare_api() -> ts.pro_api:
    """初始化Tushare Pro API实例"""
    config = _load_tushare_config()
    try:
        pro = ts.pro_api(token=config["token"])
        return pro
    except Exception as e:
        raise Exception(f"Tushare API初始化失败: {str(e)}")

def fetch_daily(
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fields: Optional[str] = None,
    pro: Optional[ts.pro_api] = None
) -> pd.DataFrame:
    """
    获取A股日线行情数据

    Args:
        ts_code (str, optional): 股票代码（支持多个股票同时提取，逗号分隔）
        trade_date (str, optional): 交易日期（YYYYMMDD）
        start_date (str, optional): 开始日期(YYYYMMDD)
        end_date (str, optional): 结束日期(YYYYMMDD)
        fields (str, optional): 指定返回字段，逗号分隔
        pro (ts.pro_api, optional): Tushare Pro API实例

    Returns:
        pd.DataFrame: 日线行情数据

    Raises:
        Exception: 调用Tushare API失败时抛出异常

    Examples:
        >>> df = fetch_daily(ts_code='000001.SZ', start_date='20180701', end_date='20180718')
        >>> df = fetch_daily(ts_code='000001.SZ,600000.SH', start_date='20180701', end_date='20180718')
    """
    if pro is None:
        pro = init_tushare_api()

    # 构建请求参数（过滤None值）
    kwargs = {}
    if ts_code is not None:
        kwargs["ts_code"] = ts_code
    if trade_date is not None:
        kwargs["trade_date"] = trade_date
    if start_date is not None:
        kwargs["start_date"] = start_date
    if end_date is not None:
        kwargs["end_date"] = end_date
    if fields is not None:
        kwargs["fields"] = fields

    try:
        df = pro.daily(**kwargs)
        return df
    except Exception as e:
        raise Exception(f"调用daily接口失败: {str(e)}")

if __name__ == "__main__":
    # 示例：获取指定日期范围的数据
    print("开始获取股票日线行情数据...")
    df = fetch_daily(ts_code='000001.SZ', start_date='20240101', end_date='20240131')
    print(f"共获取 {len(df)} 条数据")
    if len(df) > 0:
        print(df.head())
```

## 四、类型注解

1. 所有函数/方法的参数和返回值必须标注类型
2. 公共函数（对外暴露的主函数）要求完整标注所有参数和返回值类型
3. 私有辅助函数至少标注返回值类型，参数类型鼓励但不强制
4. 使用 `typing` 模块提供的类型：
   - `Optional[Type]` 用于可选参数/返回值
   - `Union[Type1, Type2]` 用于多类型
   - `List[Type]`、`Tuple[Type, ...]`、`Dict[Type, Type]` 用于容器类型
   - `Any` 仅在确实无法确定类型时使用

```python
from typing import Optional, Tuple, List, Union, Dict, Any

def query_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[dict]:
    ...

def add_days(d: Union[date, datetime], days: int) -> Union[date, datetime]:
    ...
```

## 五、注释与文档

### 5.1 Docstring 风格

项目兼容两种 docstring 风格，同一文件内必须统一使用一种：

**风格 A - Google 风格（推荐用于数据获取类模块）：**

```python
def fetch_daily(
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    获取A股日线行情数据

    Args:
        ts_code (str, optional): 股票代码
        start_date (str, optional): 开始日期(YYYYMMDD)

    Returns:
        pd.DataFrame: 日线行情数据

    Raises:
        Exception: 调用API失败时抛出异常

    Examples:
        >>> df = fetch_daily(ts_code='000001.SZ')
    """
```

**风格 B - Sphinx/reStructuredText 风格（推荐用于工具/服务类模块）：**

```python
def query_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[dict]:
    """
    查询单条记录
    :param sql: SQL 语句
    :param params: 参数元组
    :return: 查询结果字典
    """
```

### 5.2 Docstring 详细程度

- 数据获取类主函数的 docstring 必须包含：功能说明、`Args`、`Returns`、`Raises`，鼓励包含 `Examples`
- 工具类方法的 docstring 必须包含：功能说明、每个 `:param`、`:return`
- 私有辅助函数可使用单行 docstring：`"""加载Tushare API配置文件"""`
- 需要描述输出字段时，在模块级 docstring 中详列

### 5.3 行内注释
- 对关键逻辑步骤、分支判断使用行内注释说明意图
- 注释使用中文
- 避免无意义的注释（如 `i += 1  # i 加 1`）

```python
# 构建请求参数（过滤None值）
kwargs = {}
if ts_code is not None:
    kwargs["ts_code"] = ts_code

# 调用API获取数据
try:
    df = pro.daily(**kwargs)
    return df
except Exception as e:
    raise Exception(f"调用daily接口失败: {str(e)}")
```

## 六、代码风格

### 6.1 缩进与空格
- 使用 4 个空格缩进，禁止使用 Tab
- 运算符两侧加空格：`a = b + c`
- 逗号后加空格：`(a, b, c)`
- 函数参数中的 `=` 两侧不加空格：`def foo(x: int = 10)`

### 6.2 换行
- 函数/方法之间空一行
- 函数内逻辑块之间空一行
- 一行不超过 120 个字符
- 多行参数使用悬挂缩进：

```python
def send_action_card(
    self,
    title: str,
    text: str,
    btn_orientation: str = "0",
    single_title: str = "阅读全文",
    single_url: str = "",
) -> dict:
    ...
```

### 6.3 导入
- 导入顺序：标准库 → 第三方库 → 本地模块，各组之间空一行
- 避免使用 `from module import *`
- 每个导入独占一行
- 仅导入实际使用的模块，删除未使用的导入

```python
import json
import os
from typing import Optional, Tuple
from pathlib import Path

import pandas as pd
import tushare as ts

from utils.util_log import get_logger
```

### 6.4 `if __name__ == "__main__"` 块
- 每个可直接运行的脚本文件末尾应包含示例调用代码
- 用于展示模块的基本用法和快速验证

```python
if __name__ == "__main__":
    print("开始获取指数日线行情数据...")
    df = fetch_index_daily(ts_code="000001.SH", start_date="20260401", end_date="20260424")
    print(f"共获取 {len(df)} 条数据")
    if len(df) > 0:
        print(df.head())
```

## 七、错误处理

1. 不得使用裸 `except:`，必须指定异常类型
2. 在适当层级捕获异常，避免在底层函数中吞掉异常
3. 异常信息需通过日志模块记录（使用 `util_log`）
4. 外部 API 调用异常应包装后重新抛出，附带上下文信息和中文错误描述
5. 配置文件加载时需验证必要字段，缺失时报明确的错误

```python
# 配置文件验证
def _load_config() -> dict:
    config_path = os.path.abspath(_CONF_PATH)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if "token" not in config:
        raise ValueError("配置中缺少token字段")
    return config

# API调用异常包装
try:
    result = pro.daily(**kwargs)
    return result
except Exception as e:
    raise Exception(f"调用daily接口失败: {str(e)}")
```

## 八、日志规范

1. 统一使用 `utils/util_log.py` 中的日志模块
2. 通过 `get_logger()` 获取日志实例
3. 日志级别：
   - `debug()`：调试信息
   - `info()`：正常业务流程记录
   - `warning()`：可恢复的异常/警告
   - `error()`：不可恢复的错误
4. 关键操作使用 `@log_operation` 装饰器自动记录执行时间与异常

```python
from utils.util_log import get_logger, log_operation

logger = get_logger()

@log_operation("sync_data")
def sync_database_records():
    ...
```

## 九、数据库操作规范

1. 数据库连接必须使用 utils 目录下的封装类（`GreatSQL`、`TDengine` 等）
2. 连接配置统一从 `conf/` 目录下的 JSON 配置文件获取
3. 必须使用连接池
4. 使用 `with` 上下文管理器获取和释放连接，确保连接及时归还

```python
from utils.util_db import get_greatsql

db = get_greatsql()
result = db.query_one("SELECT * FROM users WHERE id = %s", (user_id,))

# 连接通过上下文管理器自动归还
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
```

5. SQL 语句中禁止直接拼接用户输入，必须使用参数化查询

## 十、配置管理

1. 所有连接配置（数据库、Redis、Milvus、Tushare 等）放在 `conf/` 目录下，以 JSON 格式存储
2. 配置文件中不得包含明文密码（如外部系统要求，需加密存储）
3. 跨项目引用配置时，使用 `Path(__file__).resolve().parent` 向上回溯到项目根目录拼接：

```python
# hetu-mercury 引用 hetu-aether 的配置
_TUSHARE_CONF_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "hetu-aether" / "conf" / "tushare_conf.json"
)
```

4. 不得在代码中硬编码任何密码、密钥、Token
5. 配置文件加载时须验证必要字段是否存在

## 十一、代码复用

1. 通用工具方法放在 `utils/` 目录下，按功能模块划分
2. 不要重复造轮子，如需使用数据库连接、日期处理、日志记录等功能，优先使用 utils 中已有方法
3. 数据获取类脚本中如出现重复的辅助函数（如 `_load_config()`、`init_api()`），应评估是否可以提升到 utils 统一管理
4. 新增通用方法应先评估是否适合放在现有 util 模块，或在 `utils/` 下新建模块

## 十二、面向对象设计

1. 工具类优先使用 `@staticmethod`，避免强制实例化
2. 数据库连接等有状态对象使用单例模式，通过 `get_instance()` 获取实例
3. 单例模式使用双重检查锁（double-checked locking）保证线程安全：

```python
_instance: Optional["MyClass"] = None
_lock = threading.Lock()

@classmethod
def get_instance(cls) -> "MyClass":
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
    return cls._instance
```

4. 资源管理类应实现上下文管理器协议或使用 `@contextmanager` 装饰器
5. 模块级工具函数提供便捷的工厂函数：

```python
def get_greatsql(config_path: str = "conf/db_conf.json") -> GreatSQL:
    """获取 GreatSQL 单例"""
    return GreatSQL.get_instance(config_path)
```

## 十三、并发与线程安全

1. 涉及共享状态的代码必须考虑线程安全
2. 使用 `threading.Lock` 保护临界区
3. 使用 `queue.Queue` 实现线程安全的连接池
4. 避免在锁内执行耗时操作

## 十四、数据获取类模块结构

数据获取类脚本（如通过 API 获取外部数据）采用统一结构：

```
1. 模块级 docstring（功能说明 + 输出字段说明）
2. 导入语句（标准库 → 第三方库 → 本地模块）
3. 模块级常量（配置路径等，使用 _SCREAMING_SNAKE_CASE）
4. 私有辅助函数（_load_config()、init_api() 等）
5. 主获取函数（fetch_<name>()）
6. if __name__ == "__main__" 示例调用块
```

### kwargs 构建模式

- 参数使用 `Optional[Type]` 声明，默认值为 `None`
- 构建 API 参数字典时逐个检查 `is not None`：

```python
kwargs = {}
if ts_code is not None:
    kwargs["ts_code"] = ts_code
if start_date is not None:
    kwargs["start_date"] = start_date
```

- 如有必填参数，可直接构建字面量字典：

```python
kwargs = {
    "start_date": start_date,
    "end_date": end_date,
}
if fields is not None:
    kwargs["fields"] = fields
```

## 十五、单元测试

1. 测试文件放在 `unit_test/` 目录下，以 `test_` 开头命名
2. 测试类继承 `unittest.TestCase`，测试方法以 `test_` 开头
3. 测试用例应覆盖：正常路径、边界条件、异常情况
4. 测试结果保存到 `unit_test/test/` 目录下，包含每个案例的执行结果和摘要
5. 对于数据获取类测试，需要将测试结果写入文件存档：

```python
import unittest
import os
import sys
import pandas as pd

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "../src/fetch_tushare_data/stock_data/market_data"))

from fetch_daily import fetch_daily

class TestDailyData(unittest.TestCase):
    """测试日线行情数据获取"""

    def test_fetch_daily(self):
        """测试获取日线行情数据"""
        df = fetch_daily(ts_code='000001.SZ', start_date='20240101', end_date='20240131')
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn('ts_code', df.columns)


def run_tests():
    """执行所有测试并输出结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestDailyData))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 保存测试结果
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)
    result_file = os.path.join(test_result_dir, "test_daily_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write(f"测试运行: {result.testsRun}\n")
        f.write(f"测试通过: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"测试失败: {len(result.failures)}\n")
        f.write(f"测试错误: {len(result.errors)}\n")
        for test, traceback in result.failures + result.errors:
            f.write(f"\n--- 失败/错误详情 ---\n")
            f.write(f"测试: {test}\n")
            f.write(f"详情: {traceback}\n")


if __name__ == "__main__":
    run_tests()
```

## 十六、Python 环境

1. 使用项目指定的 venv 虚拟环境，不得使用裸 Python 环境
2. 依赖包统一通过 `requirements.txt` 管理
3. 安装新包前需评估必要性与兼容性

## 十七、安全规范

1. 不得在代码中硬编码任何密码、密钥、Token
2. 不得在日志中输出密码、密钥等敏感信息
3. 对外部输入（用户输入、API 响应、文件内容）必须做校验与过滤
4. 文件操作使用安全的路径拼接方式（`os.path.join`、`pathlib.Path`）
5. 禁止执行动态拼接的 SQL、Shell 命令

## 十八、性能与资源

1. 数据库连接、文件句柄等资源使用后必须及时释放
2. 大数据量查询使用分页或游标
3. 避免在循环中进行数据库查询
4. 合理使用缓存减少重复计算
5. 连接池参数需根据实际场景调优（最大连接数、最小空闲数等）

## 十九、代码审查要点

1. 新增/修改的文件是否包含完整的 docstring 与类型注解
2. 数据库连接是否正确使用连接池并及时释放
3. 是否有硬编码的配置信息
4. 异常是否被正确处理和记录
5. 命名是否符合规范
6. 是否新增了不必要的依赖
7. 是否复用了已有的 utils 方法
8. 数据获取类模块是否包含 `if __name__ == "__main__"` 示例块
9. 重复的辅助函数是否应该提升到 utils 统一管理
10. 导入的模块是否都被实际使用
