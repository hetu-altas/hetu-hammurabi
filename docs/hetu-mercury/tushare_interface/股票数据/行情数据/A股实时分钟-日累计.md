# A股实时分钟-日累计

## 接口名
rt_min_daily
## 描述
获取A股当日盘中历史分钟数据，可以提取单只股票当日开盘以来的所有分钟数据
## 权限
开通了实时分钟权限自动获得本接口权限
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| freq | str | Y | 频度：1MIN,5MIN,15MIN,30MIN,60MIN |
| ts_code | str | Y | 股票代码，如：600000.SH |

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | 股票代码 |
| freq | None | Y | 频次 |
| time | None | Y | 交易时间 |
| open | float | Y | 开盘价 |
| close | float | Y | 收盘价 |
| high | float | Y | 最高价 |
| low | float | Y | 最低价 |
| vol | float | Y | 成交量(股） |
| amount | float | Y | 成交额（元） |

