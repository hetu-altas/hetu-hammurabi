# Libor利率

## 接口名
libor描述：Libor拆借利率限量：单次最大4000行数据，总量不限制，可通过设置开始和结束日期分段获取积分：用户积累120积分可以调取，具体请参阅积分获取办法

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| date | str | N | 日期 (日期输入格式：YYYYMMDD，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| curr_type | str | N | 货币代码  (USD美元  EUR欧元  JPY日元  GBP英镑  CHF瑞郎，默认是USD) |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| date | str | Y | 日期 |
| curr_type | str | Y | 货币 |
| on | float | Y | 隔夜 |
| 1w | float | Y | 1周 |
| 1m | float | Y | 1个月 |
| 2m | float | Y | 2个月 |
| 3m | float | Y | 3个月 |
| 6m | float | Y | 6个月 |
| 12m | float | Y | 12个月 |

