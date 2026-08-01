# 东方财富App热榜

## 接口名
dc_hot
## 描述
获取东方财富App热榜数据，包括A股市场、ETF基金、港股市场、美股市场等等，每日盘中提取4次，收盘后4次，最晚22点提取一次。
## 限量
单次最大2000条，可根据日期等参数循环获取全部数据
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | N | 交易日期 |
| ts_code | str | N | TS代码 |
| market | str | N | 类型(A股市场、ETF基金、港股市场、美股市场) |
| hot_type | str | N | 热点类型(人气榜、飙升榜) |
| is_new | str | N | 是否最新（默认Y，如果为N则为盘中和盘后阶段采集，具体时间可参考rank_time字段，状态N每小时更新一次，状态Y更新时间为22：30） |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| data_type | str | Y | 数据类型 |
| ts_code | str | Y | 股票代码 |
| ts_name | str | Y | 股票名称 |
| rank | int | Y | 排行或者热度 |
| pct_change | float | Y | 涨跌幅% |
| current_price | float | Y | 当前价 |
| rank_time | str | Y | 排行榜获取时间 |

## 接口示例
```python
#获取查询月份券商金股
df = pro.dc_hot(trade_date='20240415', market='A股市场',hot_type='人气榜',  fields='ts_code,ts_name,rank')
```

