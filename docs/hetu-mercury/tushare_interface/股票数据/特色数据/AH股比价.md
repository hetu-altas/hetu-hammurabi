# AH股比价

## 接口名
stk_ah_comparison，可以通过数据工具调试和查看数据。
## 描述
AH股比价数据，可根据交易日期获取历史
## 权限
5000积分起
### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| hk_code | str | N | 港股股票代码（xxxxx.HK) |
| ts_code | str | N | A股票代码(xxxxxx.SH/SZ/BJ) |
| trade_date | str | N | 交易日期（格式：YYYYMMDD下同） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| hk_code | str | Y | 港股股票代码 |
| ts_code | str | Y | A股股票代码 |
| trade_date | str | Y | 交易日期 |
| hk_name | str | Y | 港股股票名称 |
| hk_pct_chg | float | Y | 港股股票涨跌幅 |
| hk_close | float | Y | 港股股票收盘价 |
| name | str | Y | A股股票名称 |
| close | float | Y | A股股票收盘价 |
| pct_chg | float | Y | A股股票涨跌幅 |
| ah_comparison | float | Y | 比价(A/H) |
| ah_premium | float | Y | 溢价(A/H)% |

