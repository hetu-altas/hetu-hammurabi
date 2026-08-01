# 个股资金流向（THS）

## 接口名
moneyflow_ths
## 描述
获取同花顺个股资金流向数据，每日盘后更新
## 限量
单次最大6000，可根据日期或股票代码循环提取数据
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 股票代码 |
| trade_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| ts_code | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| pct_change | float | Y | 涨跌幅 |
| latest | float | Y | 最新价 |
| net_amount | float | Y | 资金净流入(万元) |
| net_d5_amount | float | Y | 5日主力净额(万元) |
| buy_lg_amount | float | Y | 今日大单净流入额(万元) |
| buy_lg_amount_rate | float | Y | 今日大单净流入占比(%) |
| buy_md_amount | float | Y | 今日中单净流入额(万元) |
| buy_md_amount_rate | float | Y | 今日中单净流入占比(%) |
| buy_sm_amount | float | Y | 今日小单净流入额(万元) |
| buy_sm_amount_rate | float | Y | 今日小单净流入占比(%) |

## 接口示例
```python
pro = ts.pro_api()

#获取单日全部股票数据
df = pro.moneyflow_ths(trade_date='20241011')

#获取单个股票数据
df = pro.moneyflow_ths(ts_code='002149.SZ', start_date='20241001', end_date='20241011')
```

