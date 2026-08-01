# ETF日线行情

## 接口名
fund_daily
## 描述
获取ETF行情每日收盘后成交数据，历史超过10年
## 限量
单次最大5000行记录，可以根据ETF代码和日期循环获取历史，总量不限制
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 基金代码 |
| trade_date | str | N | 交易日期(YYYYMMDD格式，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | TS代码 |
| trade_date | str | Y | 交易日期 |
| open | float | Y | 开盘价(元) |
| high | float | Y | 最高价(元) |
| low | float | Y | 最低价(元) |
| close | float | Y | 收盘价(元) |
| pre_close | float | Y | 昨收盘价(元) |
| change | float | Y | 涨跌额(元) |
| pct_chg | float | Y | 涨跌幅(%) |
| vol | float | Y | 成交量(手) |
| amount | float | Y | 成交额(千元) |

## 接口示例
```python
pro = ts.pro_api()

#获取”沪深300ETF华夏”ETF2025年以来的行情，并通过fields参数指定输出了部分字段
df = pro.fund_daily(ts_code='510330.SH', start_date='20250101', end_date='20250618', fields='trade_date,open,high,low,close,vol,amount')
```

