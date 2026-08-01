# ETF实时参考

## 接口名
rt_etf_sz_iopv
## 描述
ETF实时净值和申购赎回数据参考，目前只提供深市
## 限量
单次最大5000条，完全覆盖当前总量
## 权限
本接口为单独开权限的接口，跟积分多个无关。正式权限请参阅 权限说明
| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | ETF代码（默认为空，即一次全市场。支持单个和多个ETF过滤提取） |

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade_time | datetime | Y | 交易时间 |
| ts_code | str | Y | ETF代码 |
| vol | float | Y | 成交量（份） |
| num | int | Y | 成交笔数 |
| amount | float | Y | 成交金额（元） |
| price | float | Y | 最新价（元） |
| iopv | float | Y | 最近参考净值 |
| pre_iopv | float | Y | 前一日参考净值 |
| buy_num | int | Y | 申购笔数 |
| buy_vol | float | Y | 申购买量(份) |
| sell_num | int | Y | 赎回笔数 |
| sell_vol | float | Y | 赎回买量（份） |

