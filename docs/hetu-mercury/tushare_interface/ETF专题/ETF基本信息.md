# ETF基本信息

## 接口名
etf_basic
## 描述
获取国内ETF基础信息，包括了QDII。数据来源与沪深交易所公开披露信息。
## 限量
单次请求最大放回5000条数据（当前ETF总数未超过2000）
## 权限
用户积8000积分可调取，具体请参阅积分获取办法
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | ETF代码（带.SZ/.SH后缀的6位数字，如：159526.SZ） |
| index_code | str | N | 跟踪指数代码 |
| list_date | str | N | 上市日期（格式：YYYYMMDD） |
| list_status | str | N | 上市状态（L上市 D退市 P待上市） |
| exchange | str | N | 交易所（SH上交所 SZ深交所） |
| mgr | str | N | 管理人（简称，e.g.华夏基金) |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | Y | 基金交易代码 |
| csname | str | Y | ETF中文简称 |
| extname | str | Y | ETF扩位简称(对应交易所简称) |
| cname | str | Y | 基金中文全称 |
| index_code | str | Y | ETF基准指数代码 |
| index_name | str | Y | ETF基准指数中文全称 |
| setup_date | str | Y | 设立日期（格式：YYYYMMDD） |
| list_date | str | Y | 上市日期（格式：YYYYMMDD） |
| list_status | str | Y | 存续状态（L上市 D退市 P待上市） |
| exchange | str | Y | 交易所（上交所SH 深交所SZ） |
| mgr_name | str | Y | 基金管理人简称 |
| custod_name | str | Y | 基金托管人名称 |
| mgt_fee | float | Y | 基金管理人收取的费用 |
| etf_type | str | Y | 基金投资通道类型（境内、QDII） |

