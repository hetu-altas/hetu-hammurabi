# hetu-mercury hk_hold修复报告

> **任务**：20260815任务2 ｜ **日期**：2026-08-15 ｜ 依据《hk_hold 缺失问题排查报告》

## 一、修复内容

| 环节 | 修复 |
|------|------|
| 超级表 | CREATE STABLE IF NOT EXISTS hk_hold（简化 DDL，REST 不支持中文 COMMENT）——SHOW STABLES/DESCRIBE 验证通过 |
| 同步 | `sync_hk_hold.py`：增量断点 + **(ts,ts_code) 粒度去重**（margin 教训）+ 0 条告警 + **SH/SZ/HK exchange 循环**；接入 daily_stock_sync.sh special 节（回看 5 天） |
| 联动 | sybil `_validate_fields` 反引号包裹——TDengine 保留字 `ratio` 致 hk_hold 查询语法错误的修复（通用） |

## 二、补数验证

- 近 5 交易日 **4794 条入库**（≈959 行/天，exchange=HK 南向）；幂等重跑 0 插入；
- sybil 查询 hk_hold 正常（ratio 可读）；sybil 305 回归全绿；本任务单测 8/8 + 落闸。

## 三、数据源限制（重要）

**tushare hk_hold 接口北向（exchange=SH/SZ）当前返回 0 行**（仅 HK 南向 959 行/天）——北向个股持股疑似因披露规则变化在接口侧停更。**sybil 个股视图 north（北向）维度仍无法填充，属数据源限制而非链路缺陷**；exchange 循环已就绪，北向恢复后自动入库。

## 四、遗留

1. prod 副本部署（sync_hk_hold.py / daily_stock_sync.sh / sybil tdengine_access 反引号）；
2. 北向数据恢复后验证 300750/002594 ratio；
3. 建表 DDL 元数据 COMMENT 缺失（REST 限制，无功能影响）。
