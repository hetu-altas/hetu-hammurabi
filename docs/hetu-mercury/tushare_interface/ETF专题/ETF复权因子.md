# ETF复权因子

## 接口名
fund_adj
## 描述
获取基金复权因子，用于计算基金复权行情
## 限量
单次最大提取2000行记录，可循环提取，数据总量不限制
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | TS基金代码（支持多只基金输入） |
| trade_date | str | N | 交易日期（格式：yyyymmdd，下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| offset | str | N | 开始行数 |
| limit | str | N | 最大行数 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | ts基金代码 |
| trade_date | str | Y | 交易日期 |
| adj_factor | float | Y | 复权因子 |

