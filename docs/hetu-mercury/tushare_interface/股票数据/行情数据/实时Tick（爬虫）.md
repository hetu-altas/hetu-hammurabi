# 实时Tick（爬虫）

## 接口名
realtime_quote，A股实时行情
## 描述
本接口是tushare org版实时接口的顺延，数据来自网络，且不进入tushare服务器，属于爬虫接口，请将tushare升级到1.3.3版本以上。
## 权限
0积分完全开放，但需要有tushare账号，如果没有账号请先注册。
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts_code | str | N | 股票代码，需按tushare股票和指数标准代码输入，比如：000001.SZ表示平安银行，000001.SH表示上证指数 |
| src | str | N | 数据源 （sina-新浪 dc-东方财富，默认sina） |

### 输入参数

| src源 | 说明 | 描述 |
| --- | --- | --- |
| sina | 新浪财经 | 支持多个多个股票同时输入，举例：ts_code='600000.SH,000001.SZ'），一次最多不能超过50个股票 |
| dc | 东方财富 | 只支持单个股票提取 |

### 输出参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| name | str | 股票名称 |
| ts_code | str | 股票代码 |
| date | str | 交易日期 |
| time | str | 交易时间 |
| open | float | 开盘价 |
| pre_close | float | 昨收价 |
| price | float | 现价 |
| high | float | 今日最高价 |
| low | float | 今日最低价 |
| bid | float | 竞买价，即“买一”报价（元） |
| ask | float | 竞卖价，即“卖一”报价（元） |
| volume | int | 成交量（src=sina时是股，src=dc时是手） |
| amount | float | 成交金额（元 CNY） |
| b1_v | float | 委买一（量，单位：手，下同） |
| b1_p | float | 委买一（价，单位：元，下同） |
| b2_v | float | 委买二（量） |
| b2_p | float | 委买二（价） |
| b3_v | float | 委买三（量） |
| b3_p | float | 委买三（价） |
| b4_v | float | 委买四（量） |
| b4_p | float | 委买四（价） |
| b5_v | float | 委买五（量） |
| b5_p | float | 委买五（价） |
| a1_v | float | 委卖一（量，单位：手，下同） |
| a1_p | float | 委卖一（价，单位：元，下同） |
| a2_v | float | 委卖二（量） |
| a2_p | float | 委卖二（价） |
| a3_v | float | 委卖三（量） |
| a3_p | float | 委卖三（价） |
| a4_v | float | 委卖四（量） |
| a4_p | float | 委卖四（价） |
| a5_v | float | 委卖五（量） |
| a5_p | float | 委卖五（价） |

