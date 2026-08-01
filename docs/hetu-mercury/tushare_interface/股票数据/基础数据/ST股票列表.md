# ST股票列表

## 接口名
stock_st，可以通过数据工具调试和查看数据。
## 描述
获取ST股票列表，可根据交易日期获取历史上每天的ST列表
## 权限
3000积分起
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 股票代码 |
| trade_date | str | N | 交易日期（格式：YYYYMMDD下同） |
| start_date | str | N | 开始时间 |
| end_date | str | N | 结束时间 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| trade_date | str | Y | 交易日期 |
| type | str | Y | 类型 |
| type_name | str | Y | 类型名称 |

