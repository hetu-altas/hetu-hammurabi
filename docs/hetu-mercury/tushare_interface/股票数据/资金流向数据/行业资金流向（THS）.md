# 行业资金流向（THS）

## 接口名
moneyflow_ind_ths
## 描述
获取同花顺行业资金流向，每日盘后更新
## 限量
单次最大可调取5000条数据，可以根据日期和代码循环提取全部数据
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 代码 |
| trade_date | str | N | 交易日期(YYYYMMDD格式，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| ts_code | str | Y | 板块代码 |
| industry | str | Y | 板块名称 |
| lead_stock | str | Y | 领涨股票名称 |
| close | float | Y | 收盘指数 |
| pct_change | float | Y | 指数涨跌幅 |
| company_num | int | Y | 公司数量 |
| pct_change_stock | float | Y | 领涨股涨跌幅 |
| close_price | float | Y | 领涨股最新价 |
| net_buy_amount | float | Y | 流入资金(亿元) |
| net_sell_amount | float | Y | 流出资金(亿元) |
| net_amount | float | Y | 净额(亿元) |

## 接口示例
```python
#获取当日所有同花顺行业资金流向
df = pro.moneyflow_ind_ths(trade_date='20240927')
```

