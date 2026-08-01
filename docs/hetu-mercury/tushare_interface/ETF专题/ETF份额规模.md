# ETF份额规模

## 接口名
etf_share_size
## 描述
获取沪深ETF每日份额和规模数据，能体现规模份额的变化，掌握ETF资金动向，同时提供每日净值和收盘价；数据指标是分批入库，建议在每日19点后提取；另外，涉及海外的ETF数据更新会晚一些属于正常情况。
## 限量
单次最大5000条，可根据代码或日期循环提取
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 基金代码 （可从ETF基础信息接口提取） |
| trade_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| exchange | str | N | 交易所（SSE上交所 SZSE深交所） |

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_date | str | Y | 交易日期 |
| ts_code | str | Y | ETF代码 |
| etf_name | str | Y | 基金名称 |
| total_share | float | Y | 总份额（万份） |
| total_size | float | Y | 总规模（万元） |
| nav | float | N | 基金份额净值(元) |
| close | float | N | 收盘价（元） |
| exchange | str | Y | 交易所（SSE上交所 SZSE深交所 BSE北交所） |

