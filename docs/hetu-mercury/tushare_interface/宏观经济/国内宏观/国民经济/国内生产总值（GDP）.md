# 国内生产总值（GDP）

## 接口名
cn_gdp描述：获取国民经济之GDP数据限量：单次最大10000，一次可以提取全部数据权限：用户积累600积分可以使用，具体请参阅积分获取办法

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| q | str | N | 季度（2019Q1表示，2019年第一季度） |
| start_q | str | N | 开始季度 |
| end_q | str | N | 结束季度 |
| fields | str | N | 指定输出字段（e.g. fields='quarter,gdp,gdp_yoy'） |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| quarter | str | Y | 季度 |
| gdp | float | Y | GDP累计值（亿元） |
| gdp_yoy | float | Y | 当季同比增速（%） |
| pi | float | Y | 第一产业累计值（亿元） |
| pi_yoy | float | Y | 第一产业同比增速（%） |
| si | float | Y | 第二产业累计值（亿元） |
| si_yoy | float | Y | 第二产业同比增速（%） |
| ti | float | Y | 第三产业累计值（亿元） |
| ti_yoy | float | Y | 第三产业同比增速（%） |

