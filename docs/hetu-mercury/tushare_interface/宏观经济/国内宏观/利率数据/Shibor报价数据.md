# Shibor报价数据

## 接口名
shibor_quote描述：Shibor报价数据限量：单次最大4000行数据，总量不限制，可通过设置开始和结束日期分段获取积分：用户积累120积分可以调取，具体请参阅积分获取办法

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| date | str | N | 日期 (日期输入格式：YYYYMMDD，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| bank | str | N | 银行名称 （中文名称，例如 农业银行） |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| date | str | Y | 日期 |
| bank | str | Y | 报价银行 |
| on_b | float | Y | 隔夜_Bid |
| on_a | float | Y | 隔夜_Ask |
| 1w_b | float | Y | 1周_Bid |
| 1w_a | float | Y | 1周_Ask |
| 2w_b | float | Y | 2周_Bid |
| 2w_a | float | Y | 2周_Ask |
| 1m_b | float | Y | 1月_Bid |
| 1m_a | float | Y | 1月_Ask |
| 3m_b | float | Y | 3月_Bid |
| 3m_a | float | Y | 3月_Ask |
| 6m_b | float | Y | 6月_Bid |
| 6m_a | float | Y | 6月_Ask |
| 9m_b | float | Y | 9月_Bid |
| 9m_a | float | Y | 9月_Ask |
| 1y_b | float | Y | 1年_Bid |
| 1y_a | float | Y | 1年_Ask |

