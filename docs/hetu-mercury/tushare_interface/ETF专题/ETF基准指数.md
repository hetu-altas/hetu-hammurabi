# ETF基准指数

## 接口名
etf_index
## 描述
获取ETF基准指数列表信息
## 限量
单次请求最大返回5000行数据（当前未超过2000个）
## 权限
用户积累8000积分可调取，具体请参阅积分获取办法
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 指数代码 |
| pub_date | str | N | 发布日期（格式：YYYYMMDD） |
| base_date | str | N | 指数基期（格式：YYYYMMDD） |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | 指数代码 |
| indx_name | str | Y | 指数全称 |
| indx_csname | str | Y | 指数简称 |
| pub_party_name | str | Y | 指数发布机构 |
| pub_date | str | Y | 指数发布日期 |
| base_date | str | Y | 指数基日 |
| bp | float | Y | 指数基点(点) |
| adj_circle | str | Y | 指数成份证券调整周期 |

