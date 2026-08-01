# 大盘资金流向（DC）

## 接口名
moneyflow_mkt_dc
## 描述
获取东方财富大盘资金流向数据，每日盘后更新
## 限量
单次最大3000条，可根据日期或日期区间循环获取
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | N | 交易日期(YYYYMMDD格式，下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| close_sh | float | Y | 上证收盘价（点） |
| pct_change_sh | float | Y | 上证涨跌幅(%) |
| close_sz | float | Y | 深证收盘价（点） |
| pct_change_sz | float | Y | 深证涨跌幅(%) |
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

## 接口示例
```python
#获取当日所有板块资金流向
df = pro.moneyflow_mkt_dc(start_date='20240901', end_date='20240930')
```

