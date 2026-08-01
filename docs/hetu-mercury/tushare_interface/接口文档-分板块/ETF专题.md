# ETF专题

## etf_share_size
ETF份额规模

描述: 获取沪深ETF每日份额和规模数据，能体现规模份额的变化，掌握ETF资金动向，同时提供每日净值和收盘价；数据指标是分批入库，建议在每日19点后提取；另外，涉及海外的ETF数据更新会晚一些属于正常情况。
限量: 单次最大5000条，可根据代码或日期循环提取

---

## stk_mins
ETF历史分钟

描述: 获取ETF分钟数据，支持1min/5min/15min/30min/60min行情，提供Python SDK和 http Restful API两种方式
限量: 单次最大8000行数据，可以通过股票代码和时间循环获取，本接口可以提供超过10年ETF历史分钟数据

### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | ETF代码，e.g. 159001.SZ |
| freq | str | 分钟频度（1min/5min/15min/30min/60min） |
| start_date | datetime | 开始日期 格式：2025-06-01 09:00:00 |
| end_date | datetime | 结束时间 格式：2025-06-20 19:00:00 |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | ETF代码 |
| trade_time | str | 交易时间 |
| open | float | 开盘价 |
| close | float | 收盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| vol | int | 成交量（股） |
| amount | float | 成交金额（元） |

---

## etf_index
ETF基准指数

描述: 获取ETF基准指数列表信息
限量: 单次请求最大返回5000行数据（当前未超过2000个）

### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 指数代码 |
| pub_date | str | 发布日期（格式：YYYYMMDD） |
| base_date | str | 指数基期（格式：YYYYMMDD） |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 指数代码 |
| indx_name | str | 指数全称 |
| indx_csname | str | 指数简称 |
| pub_party_name | str | 指数发布机构 |
| pub_date | str | 指数发布日期 |
| base_date | str | 指数基日 |
| bp | float | 指数基点(点) |
| adj_circle | str | 指数成份证券调整周期 |

---

## etf_basic
ETF基本信息

描述: 获取国内ETF基础信息，包括了QDII。数据来源与沪深交易所公开披露信息。
限量: 单次请求最大放回5000条数据（当前ETF总数未超过2000）

### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | ETF代码（带.SZ/.SH后缀的6位数字，如：159526.SZ） |
| index_code | str | 跟踪指数代码 |
| list_date | str | 上市日期（格式：YYYYMMDD） |
| list_status | str | 上市状态（L上市 D退市 P待上市） |
| exchange | str | 交易所（SH上交所 SZ深交所） |
| mgr | str | 管理人（简称，e.g.华夏基金) |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 基金交易代码 |
| csname | str | ETF中文简称 |
| extname | str | ETF扩位简称(对应交易所简称) |
| cname | str | 基金中文全称 |
| index_code | str | ETF基准指数代码 |
| index_name | str | ETF基准指数中文全称 |
| setup_date | str | 设立日期（格式：YYYYMMDD） |
| list_date | str | 上市日期（格式：YYYYMMDD） |
| list_status | str | 存续状态（L上市 D退市 P待上市） |
| exchange | str | 交易所（上交所SH 深交所SZ） |
| mgr_name | str | 基金管理人简称 |
| custod_name | str | 基金托管人名称 |
| mgt_fee | float | 基金管理人收取的费用 |
| etf_type | str | 基金投资通道类型（境内、QDII） |

---

## fund_adj
ETF复权因子

描述: 获取基金复权因子，用于计算基金复权行情
限量: 单次最大提取2000行记录，可循环提取，数据总量不限制

### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS基金代码（支持多只基金输入） |
| trade_date | str | 交易日期（格式：yyyymmdd，下同） |
| start_date | str | 开始日期 |
| end_date | str | 结束日期 |
| offset | str | 开始行数 |
| limit | str | 最大行数 |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | ts基金代码 |
| trade_date | str | 交易日期 |
| adj_factor | float | 复权因子 |

---

## rt_min
ETF实时分钟

描述: 获取ETF实时分钟数据，包括1~60min
限量: 单次最大1000行数据，可以通过ETF代码提取数据，支持逗号分隔的多个代码同时提取

### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| freq | str | 1MIN,5MIN,15MIN,30MIN,60MIN （大写） |
| ts_code | str | 支持单个和多个：589960.SH 或者 589960.SH,159100.SZ |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 股票代码 |
| time | None | 交易时间 |
| open | float | 开盘价 |
| close | float | 收盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| vol | float | 成交量(股） |
| amount | float | 成交额（元） |

---

## rt_etf_sz_iopv
ETF实时参考

描述: ETF实时净值和申购赎回数据参考，目前只提供深市
限量: 单次最大5000条，完全覆盖当前总量

---

## rt_etf_k
ETF实时日线

描述: 获取ETF实时日k线行情，支持按ETF代码或代码通配符一次性提取全部ETF实时日k线行情
### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 支持通配符方式，e.g. 5*.SH、15*.SZ、159101.SZ |
| topic | str | 分类参数，取上海ETF时，需要输入'HQ_FND_TICK'，参考下面例子 |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | ETF代码 |
| name | None | ETF名称 |
| pre_close | float | 昨收价 |
| high | float | 最高价 |
| open | float | 开盘价 |
| low | float | 最低价 |
| close | float | 收盘价（最新价） |
| vol | int | 成交量（股） |
| amount | int | 成交金额（元） |
| num | int | 开盘以来成交笔数 |
| ask_volume1 | int | 委托卖盘（股） |
| bid_volume1 | int | 委托买盘（股） |
| trade_time | str | 交易时间 |

---

## fund_daily
ETF日线行情

描述: 获取ETF行情每日收盘后成交数据，历史超过10年
限量: 单次最大5000行记录，可以根据ETF代码和日期循环获取历史，总量不限制

### 输入参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | 基金代码 |
| trade_date | str | 交易日期(YYYYMMDD格式，下同) |
| start_date | str | 开始日期 |
| end_date | str | 结束日期 |

### 输出参数

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| ts_code | str | TS代码 |
| trade_date | str | 交易日期 |
| open | float | 开盘价(元) |
| high | float | 最高价(元) |
| low | float | 最低价(元) |
| close | float | 收盘价(元) |
| pre_close | float | 昨收盘价(元) |
| change | float | 涨跌额(元) |
| pct_chg | float | 涨跌幅(%) |
| vol | float | 成交量(手) |
| amount | float | 成交额(千元) |

---

