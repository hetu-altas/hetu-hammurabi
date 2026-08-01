# Shibor利率

## 接口名
shibor描述：shibor利率限量：单次最大2000，总量不限制，可通过设置开始和结束日期分段获取积分：用户积累120积分可以调取，具体请参阅积分获取办法

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| date | str | N | 日期 (日期输入格式：YYYYMMDD，下同) |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| date | str | Y | 日期 |
| on | float | Y | 隔夜 |
| 1w | float | Y | 1周 |
| 2w | float | Y | 2周 |
| 1m | float | Y | 1个月 |
| 3m | float | Y | 3个月 |
| 6m | float | Y | 6个月 |
| 9m | float | Y | 9个月 |
| 1y | float | Y | 1年 |

