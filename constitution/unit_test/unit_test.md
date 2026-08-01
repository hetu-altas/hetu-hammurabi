# 单元测试规范

## 一、测试框架与运行

1. 统一使用 Python 标准库 `unittest` 框架
2. 测试文件可直接运行：`python test_xxx.py` 或 `python -m unittest test_xxx`
3. 不得引入第三方测试框架（pytest、nose 等）

```python
import unittest

if __name__ == "__main__":
    unittest.main()
```

## 二、文件与目录规范

### 2.1 文件命名
- 测试文件放在 `unit_test/` 目录下，以 `test_` 开头：`test_util_datetime.py`
- 测试结果输出到 `unit_test/test/` 目录下：`test_util_datetime_result.txt`

### 2.2 文件结构

```python
# -*- coding: utf-8 -*-
"""
模块名 单元测试
"""

import unittest

# 被测试模块的导入
from utils.xxx import TargetClass, helper_func


class TestTargetClass(unittest.TestCase):
    """测试 TargetClass 功能"""
    
    def test_normal_case(self):
        """正常案例描述"""
        ...

    def test_error_case(self):
        """异常案例描述"""
        ...

    def test_boundary_case(self):
        """边界条件描述"""
        ...


if __name__ == "__main__":
    unittest.main()
```

## 三、测试用例分类（必须覆盖）

每个被测试模块的测试用例必须覆盖以下三大类：

### 3.1 正常案例（Positive Tests）
验证函数在合法输入下返回预期结果。

```python
def test_str_to_date(self):
    """测试标准日期字符串转换"""
    result = DateUtil.str_to_date("20240101")
    self.assertEqual(result, date(2024, 1, 1))

def test_date_to_str(self):
    """测试日期转字符串"""
    d = date(2024, 1, 1)
    result = DateUtil.date_to_str(d)
    self.assertEqual(result, "20240101")

def test_days_diff(self):
    """测试日期天数差计算"""
    d1 = date(2024, 1, 1)
    d2 = date(2024, 1, 10)
    result = DateUtil.days_diff(d1, d2)
    self.assertEqual(result, 9)
```

对于数据获取类函数，至少验证：
- 返回类型正确（如 `assertIsInstance(df, pd.DataFrame)`）
- 返回数据非空（如 `assertGreater(len(df), 0)`）
- 关键字段存在（如 `assertIn("ts_code", df.columns)`）

```python
def test_fetch_daily(self):
    """测试获取单只股票日线数据"""
    df = fetch_daily(ts_code="000001.SZ", start_date="20240101", end_date="20240110", pro=self.pro)
    self.assertIsInstance(df, pd.DataFrame)
    self.assertGreater(len(df), 0)
```

### 3.2 反案例（Negative Tests）
验证函数在非法输入、异常条件下的行为。必须包含以下至少一种：

- **非法参数值**：传入错误类型、格式、范围外的值
- **缺失必要参数**：不传必填参数
- **异常抛出验证**：使用 `assertRaises` 验证预期的异常

```python
def test_str_to_date_invalid_format(self):
    """测试非法日期格式应抛出异常"""
    with self.assertRaises(ValueError):
        DateUtil.str_to_date("2024-01-01")

def test_str_to_date_empty_string(self):
    """测试空字符串应抛出异常"""
    with self.assertRaises(ValueError):
        DateUtil.str_to_date("")

def test_str_to_date_none_input(self):
    """测试None输入应抛出异常"""
    with self.assertRaises(TypeError):
        DateUtil.str_to_date(None)

def test_decorator_error(self):
    """验证被装饰函数抛出异常时自动记录ERROR日志并重新抛出"""
    with self.assertRaises(ValueError):
        error_raising_func()

def test_config_missing_token(self):
    """验证配置缺少token字段时抛出异常"""
    with self.assertRaises(ValueError):
        load_config_without_token()
```

### 3.3 边界条件（Boundary Tests）
验证函数在边界值、临界条件下的正确性。常见边界类型：

#### 时间边界
```python
def test_month_boundary_start(self):
    """测试月初第一天"""
    d = date(2024, 3, 1)
    result = DateUtil.get_month_start(d)
    self.assertEqual(result, date(2024, 3, 1))

def test_month_boundary_end(self):
    """测试月末最后一天"""
    d = date(2024, 3, 31)
    result = DateUtil.get_month_end(d)
    self.assertEqual(result, date(2024, 3, 31))

def test_year_boundary_start(self):
    """测试年初第一天"""
    d = date(2024, 1, 1)
    result = DateUtil.get_year_start(d)
    self.assertEqual(result, date(2024, 1, 1))

def test_year_boundary_end(self):
    """测试年末最后一天"""
    d = date(2024, 12, 31)
    result = DateUtil.get_year_end(d)
    self.assertEqual(result, date(2024, 12, 31))
```

#### 闰年边界
```python
def test_leap_year_feb(self):
    """测试闰年2月29日"""
    d = date(2024, 2, 29)
    result = DateUtil.get_month_end(d)
    self.assertEqual(result, date(2024, 2, 29))

def test_non_leap_year_feb(self):
    """测试非闰年2月只有28天"""
    d = date(2023, 2, 28)
    result = DateUtil.get_month_end(d)
    self.assertEqual(result, date(2023, 2, 28))
```

#### 季度边界
```python
def test_quarter_boundary_q1(self):
    """测试Q1季度第一天"""
    self.assertEqual(DateUtil.get_quarter(date(2024, 1, 1)), 1)

def test_quarter_boundary_q4(self):
    """测试Q4季度最后一天"""
    self.assertEqual(DateUtil.get_quarter(date(2024, 12, 31)), 4)

def test_quarter_transition(self):
    """测试季度交替边界"""
    self.assertEqual(DateUtil.get_quarter(date(2024, 3, 31)), 1)
    self.assertEqual(DateUtil.get_quarter(date(2024, 4, 1)), 2)
```

#### 周末/工作日边界
```python
def test_weekend_saturday(self):
    """测试周六为周末"""
    self.assertTrue(DateUtil.is_weekend(date(2024, 1, 6)))

def test_weekend_sunday(self):
    """测试周日为周末"""
    self.assertTrue(DateUtil.is_weekend(date(2024, 1, 7)))

def test_weekday_monday(self):
    """测试周一为工作日"""
    self.assertTrue(DateUtil.is_weekday(date(2024, 1, 1)))

def test_weekday_friday(self):
    """测试周五为工作日"""
    self.assertTrue(DateUtil.is_weekday(date(2024, 1, 5)))
```

#### 零值与空值边界
```python
def test_days_diff_same_day(self):
    """测试同一天天数差为0"""
    d = date(2024, 1, 1)
    result = DateUtil.days_diff(d, d)
    self.assertEqual(result, 0)

def test_format_duration_zero(self):
    """测试零秒格式化"""
    result = DateUtil.format_duration(0)
    self.assertEqual(result, "0秒")

def test_date_to_datetime_default_time(self):
    """测试日期转日期时间的默认时间边界（00:00:00）"""
    d = date(2024, 1, 1)
    result = DateUtil.date_to_datetime(d)
    self.assertEqual(result, datetime(2024, 1, 1, 0, 0, 0))

def test_date_to_datetime_end_of_day(self):
    """测试日期转日期时间的末尾时间（23:59:59）"""
    d = date(2024, 1, 1)
    result = DateUtil.date_to_datetime(d, "23:59:59")
    self.assertEqual(result, datetime(2024, 1, 1, 23, 59, 59))
```

#### 时间戳边界
```python
def test_timestamp_epoch(self):
    """测试Unix纪元时间戳"""
    result = DateUtil.timestamp_to_datetime(0)
    self.assertEqual(result, datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc))
```

#### 数量边界
```python
def test_cross_month_workdays(self):
    """测试跨月工作日天数（包含完整的周一至周日）"""
    start = date(2024, 1, 1)   # 周一
    end = date(2024, 1, 7)     # 周日
    result = DateUtil.workdays_between(start, end)
    self.assertEqual(result, 5)
```

#### 正负号边界
```python
def test_add_negative_days(self):
    """测试减去天数（跨过零点）"""
    d = date(2024, 1, 1)
    result = DateUtil.add_days(d, -1)
    self.assertEqual(result, date(2023, 12, 31))

def test_add_months_cross_year(self):
    """测试跨年加减月份"""
    d = date(2024, 11, 30)
    result = DateUtil.add_months(d, 2)
    self.assertEqual(result, date(2025, 1, 30))
```

## 四、setUp / tearDown 使用规范

### 4.1 setUp — 每个测试方法前执行
用于创建测试所需的对象、重置单例状态：

```python
class TestGreatSQL(unittest.TestCase):
    def setUp(self):
        """重置单例并创建新实例"""
        util_db.GreatSQL._instance = None
        self.db = util_db.GreatSQL()

class TestDingTalkAgent(unittest.TestCase):
    def setUp(self):
        """创建测试用的配置和Agent实例"""
        self.config = DingTalkConfig(
            access_token="test_token",
            secret="test_secret",
            at_all=False,
            at_mobiles=["13800000000"],
        )
        self.agent = DingTalkAgent(self.config)
```

### 4.2 tearDown — 每个测试方法后执行
用于清理 `setUp` 中创建的资源（临时文件、目录等）：

```python
class TestLogRecord(unittest.TestCase):
    def setUp(self):
        """创建临时日志目录和配置文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_conf = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        config = {
            "log_dir": self.temp_dir,
            "file_prefix": "test_app",
            "level": "DEBUG",
        }
        json.dump(config, self.temp_conf)
        self.temp_conf.close()

    def tearDown(self):
        """清理临时文件和目录"""
        if os.path.exists(self.temp_conf.name):
            os.remove(self.temp_conf.name)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
```

### 4.3 setUpClass — 整个测试类执行前执行一次
用于创建共享资源（API连接、数据库连接等），避免每个测试方法重复创建：

```python
class TestDaily(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """初始化API实例，所有测试方法共享"""
        cls.pro = init_tushare_api()
```

### 4.4 tearDownClass — 整个测试类执行后执行一次
用于清理 `setUpClass` 中的共享资源、恢复模块级单例：

```python
@classmethod
def tearDownClass(cls):
    """恢复全局日志实例"""
    import utils.util_log
    utils.util_log._log_instance = cls._original_instance
```

## 五、Mock / Patch 使用规范

### 5.1 @patch 装饰器
用于替换外部依赖（HTTP请求、数据库连接、文件操作）：

```python
from unittest.mock import patch, MagicMock

class TestSendMessage(unittest.TestCase):
    @patch("utils.util_dingtalk.requests.post")
    def test_send_text_success(self, mock_post):
        """测试发送文本消息成功"""
        mock_post.return_value.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        result = self.agent.send_text("hello world")
        
        self.assertEqual(result, {"errcode": 0, "errmsg": "ok"})
        mock_post.assert_called_once()

    @patch("utils.util_db.PooledDB")
    def test_get_connection(self, mock_pooled_db):
        """测试获取数据库连接"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.connection.return_value = mock_conn
        mock_pooled_db.return_value = mock_pool
        
        conn = self.db.connect()
        
        mock_pool.connection.assert_called_once()
        self.assertEqual(conn, mock_conn)
```

### 5.2 复杂 Mock 层级构建
当被测对象涉及多层调用时，逐层构建 MagicMock：

```python
@patch("utils.util_db.PooledDB")
def test_execute(self, mock_pooled_db):
    """测试SQL执行"""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # 构建上下文管理器行为
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    
    # 连接池返回连接
    mock_pool.connection.return_value = mock_conn
    mock_pooled_db.return_value = mock_pool
    
    self.db.execute("SELECT 1")
    
    mock_cursor.execute.assert_called_once_with("SELECT 1", None)
    mock_conn.commit.assert_called_once()
```

### 5.3 patch 上下文管理器
当 `@patch` 装饰不能修改被测对象作用域时，使用上下文管理器：

```python
def test_from_config_file(self):
    """测试从配置文件加载"""
    mock_config = {
        "accessToken": "file_token",
        "secret": "file_secret",
        "atAll": True,
        "atMobiles": ["13800000000"],
    }
    
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
        config = DingTalkConfig.from_config_file(Path("/fake/path"))
        self.assertEqual(config.access_token, "file_token")
```

### 5.4 Mock 验证规范
- 验证调用次数：`mock.assert_called_once()`、`mock.assert_not_called()`
- 验证调用参数：`mock.assert_called_once_with(arg1, arg2)`
- 检查调用细节：`mock.call_args`、`mock.call_args_list`

## 六、断言方法

常用的断言方法及其使用场景：

| 断言方法 | 使用场景 |
|---------|---------|
| `assertEqual(a, b)` | 验证返回值等于预期值 |
| `assertNotEqual(a, b)` | 验证返回值不等于某值 |
| `assertTrue(x)` | 验证布尔值为真 |
| `assertFalse(x)` | 验证布尔值为假 |
| `assertIs(a, b)` | 验证是同一个对象 |
| `assertIsNot(a, b)` | 验证不是同一个对象 |
| `assertIsNone(x)` | 验证值为 None |
| `assertIsNotNone(x)` | 验证值不为 None |
| `assertIsInstance(obj, cls)` | 验证对象类型 |
| `assertIn(member, container)` | 验证成员在容器中 |
| `assertNotIn(member, container)` | 验证成员不在容器中 |
| `assertGreater(a, b)` | 验证 a > b |
| `assertGreaterEqual(a, b)` | 验证 a >= b |
| `assertLess(a, b)` | 验证 a < b |
| `assertRaises(ExcType)` | 验证抛出指定异常 |

## 七、测试数据管理

1. 测试输入数据应直接硬编码在测试方法中，使用明确的字面量值
2. 需要临时文件/目录时使用 `tempfile` 模块创建
3. 涉及单例模式的类，`setUp` 中必须重置单例状态，避免测试间相互影响

```python
def setUp(self):
    """重置单例以保证测试隔离"""
    TargetClass._instance = None
    self.instance = TargetClass()
```

4. 被测试模块中如有模块级全局变量，`setUpClass` / `tearDownClass` 中需保存并恢复：

```python
@classmethod
def setUpClass(cls):
    import module_under_test
    cls._saved = module_under_test._global_state
    module_under_test._global_state = None

@classmethod
def tearDownClass(cls):
    import module_under_test
    module_under_test._global_state = cls._saved
```

## 八、测试结果输出

1. 测试结果保存到 `unit_test/test/` 目录下，文件名格式为 `test_<模块名>_result.txt`
2. 输出内容包括：测试总数、成功数、失败数、错误数、失败/错误用例详情

```python
import os
import unittest


def run_tests():
    """执行所有测试并输出结果"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestClass1))
    suite.addTests(loader.loadTestsFromTestCase(TestClass2))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_xxx_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("模块名 单元测试结果\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"测试总数: {result.testsRun}\n")
        f.write(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"失败: {len(result.failures)}\n")
        f.write(f"错误: {len(result.errors)}\n\n")

        if result.failures:
            f.write("-" * 40 + "\n失败用例:\n" + "-" * 40 + "\n")
            for test, traceback in result.failures:
                f.write(f"\n{test}:\n{traceback}\n")

        if result.errors:
            f.write("-" * 40 + "\n错误用例:\n" + "-" * 40 + "\n")
            for test, traceback in result.errors:
                f.write(f"\n{test}:\n{traceback}\n")

        f.write("\n" + "=" * 60 + "\n")
        if result.wasSuccessful():
            f.write("测试结果: 全部通过\n")
        else:
            f.write("测试结果: 存在失败/错误\n")
        f.write("=" * 60 + "\n")

    print(f"\n测试结果已保存至: {result_file}")
    return result


if __name__ == "__main__":
    # 简单运行时用 unittest.main()
    # 需要保存测试结果时用 run_tests()
    run_tests()
```

## 九、导入路径规范

1. 被测试模块在项目内的，直接 import：

```python
from utils.util_datetime import DateUtil, DATE_FORMAT, DATETIME_FORMAT
from utils.util_log import LogRecord, log_operation, get_logger
```

2. 被测试模块不在 Python 路径中的，使用 `sys.path.insert` 添加：

```python
import sys
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../src/fetch_tushare_data/stock_data/market_data"
))
from fetch_daily import fetch_daily
```

3. 多个测试模块共享相同依赖时，第一个模块导入初始化函数，后续模块仅导入功能函数：

```python
from fetch_daily import _load_tushare_config, init_tushare_api, fetch_daily
from fetch_weekly import fetch_weekly  # 复用第一个模块的init_tushare_api
```

## 十、测试命名规范

| 元素 | 规范 | 示例 |
|------|------|------|
| 测试文件 | `test_<被测试模块>.py` | `test_util_datetime.py` |
| 测试类 | `Test<被测试类/模块>` | `TestDateUtil`、`TestDaily` |
| 测试方法 | `test_<场景描述>` | `test_str_to_date`、`test_empty_input` |
| Docstring | 中文描述测试目标 | `"""测试标准日期字符串转换"""` |

## 十一、权限受限接口的处理

对于需要特殊权限才能调用的外部接口，使用 try/except 跳过测试而非失败：

```python
def test_fetch_restricted_api(self):
    """测试受限接口数据获取"""
    try:
        df = fetch_restricted_data(pro=self.pro)
        self.assertIsInstance(df, pd.DataFrame)
    except Exception as e:
        if "没有接口" in str(e) or "访问权限" in str(e):
            self.skipTest("接口需要特殊权限")
        raise  # 其他类型异常直接抛出，不应跳过
```

## 十二、测试要求总结

每个测试文件必须做到：

1. **正常案例覆盖**：每个公开函数/方法至少有一个正常输入测试
2. **反案例覆盖**：至少有一个非法输入/异常抛出的测试
3. **边界条件覆盖**：至少有一个边界值测试（零值、极大值、极小值、空值、类型边界、时间边界等）
4. **完整的 docstring**：每个测试类和测试方法都有中文 docstring
5. **测试结果持久化**：通过 `run_tests()` 将结果写入 `unit_test/test/` 目录
6. **测试隔离**：使用 `setUp`/`tearDown` 确保测试间互不影响
7. **Mock 外部依赖**：使用 `@patch` / `MagicMock` 隔离数据库、网络等外部依赖
