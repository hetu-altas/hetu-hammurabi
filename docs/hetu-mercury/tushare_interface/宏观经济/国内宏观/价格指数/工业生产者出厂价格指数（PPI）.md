# 工业生产者出厂价格指数（PPI）

## 接口名
cn_ppi描述：获取PPI工业生产者出厂价格指数数据限量：单次最大5000，一次可以提取全部数据权限：用户600积分可以使用，具体请参阅积分获取办法

### 输入参数

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| m | str | N | 月份（YYYYMM，下同），支持多个月份同时输入，逗号分隔 |
| start_m | str | N | 开始月份 |
| end_m | str | N | 结束月份 |

### 输出参数

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| month | str | Y | 月份YYYYMM |
| ppi_yoy | float | Y | PPI：全部工业品：当月同比 |
| ppi_mp_yoy | float | Y | PPI：生产资料：当月同比 |
| ppi_mp_qm_yoy | float | Y | PPI：生产资料：采掘业：当月同比 |
| ppi_mp_rm_yoy | float | Y | PPI：生产资料：原料业：当月同比 |
| ppi_mp_p_yoy | float | Y | PPI：生产资料：加工业：当月同比 |
| ppi_cg_yoy | float | Y | PPI：生活资料：当月同比 |
| ppi_cg_f_yoy | float | Y | PPI：生活资料：食品类：当月同比 |
| ppi_cg_c_yoy | float | Y | PPI：生活资料：衣着类：当月同比 |
| ppi_cg_adu_yoy | float | Y | PPI：生活资料：一般日用品类：当月同比 |
| ppi_cg_dcg_yoy | float | Y | PPI：生活资料：耐用消费品类：当月同比 |
| ppi_mom | float | Y | PPI：全部工业品：环比 |
| ppi_mp_mom | float | Y | PPI：生产资料：环比 |
| ppi_mp_qm_mom | float | Y | PPI：生产资料：采掘业：环比 |
| ppi_mp_rm_mom | float | Y | PPI：生产资料：原料业：环比 |
| ppi_mp_p_mom | float | Y | PPI：生产资料：加工业：环比 |
| ppi_cg_mom | float | Y | PPI：生活资料：环比 |
| ppi_cg_f_mom | float | Y | PPI：生活资料：食品类：环比 |
| ppi_cg_c_mom | float | Y | PPI：生活资料：衣着类：环比 |
| ppi_cg_adu_mom | float | Y | PPI：生活资料：一般日用品类：环比 |
| ppi_cg_dcg_mom | float | Y | PPI：生活资料：耐用消费品类：环比 |
| ppi_accu | float | Y | PPI：全部工业品：累计同比 |
| ppi_mp_accu | float | Y | PPI：生产资料：累计同比 |
| ppi_mp_qm_accu | float | Y | PPI：生产资料：采掘业：累计同比 |
| ppi_mp_rm_accu | float | Y | PPI：生产资料：原料业：累计同比 |
| ppi_mp_p_accu | float | Y | PPI：生产资料：加工业：累计同比 |
| ppi_cg_accu | float | Y | PPI：生活资料：累计同比 |
| ppi_cg_f_accu | float | Y | PPI：生活资料：食品类：累计同比 |
| ppi_cg_c_accu | float | Y | PPI：生活资料：衣着类：累计同比 |
| ppi_cg_adu_accu | float | Y | PPI：生活资料：一般日用品类：累计同比 |
| ppi_cg_dcg_accu | float | Y | PPI：生活资料：耐用消费品类：累计同比 |

