# 板块资金流向（DC）

## 接口名
moneyflow_ind_dc
## 描述
获取东方财富板块资金流向，每天盘后更新
## 限量
单次最大可调取5000条数据，可以根据日期和代码循环提取全部数据
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 代码 |
| trade_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| content_type | str | N | 资金类型(行业、概念、地域) |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| content_type | str | Y | 数据类型 |
| ts_code | str | Y | DC板块代码（行业、概念、地域） |
| name | str | Y | 板块名称 |
| pct_change | float | Y | 板块涨跌幅（%） |
| close | float | Y | 板块最新指数 |
| net_amount | float | Y | 今日主力净流入 净额（元） |
| net_amount_rate | float | Y | 今日主力净流入净占比% |
| buy_elg_amount | float | Y | 今日超大单净流入 净额（元） |
| buy_elg_amount_rate | float | Y | 今日超大单净流入 净占比% |
| buy_lg_amount | float | Y | 今日大单净流入 净额（元） |
| buy_lg_amount_rate | float | Y | 今日大单净流入 净占比% |
| buy_md_amount | float | Y | 今日中单净流入 净额（元） |
| buy_md_amount_rate | float | Y | 今日中单净流入 净占比% |
| buy_sm_amount | float | Y | 今日小单净流入 净额（元） |
| buy_sm_amount_rate | float | Y | 今日小单净流入 净占比% |
| buy_sm_amount_stock | str | Y | 今日主力净流入最大股 |
| rank | int | Y | 序号 |

## 接口示例
```python
#获取当日所有板块资金流向
df = pro.moneyflow_ind_dc(trade_date='20240927', fields='trade_date,name,pct_change, close, net_amount,net_amount_rate,rank')
```

