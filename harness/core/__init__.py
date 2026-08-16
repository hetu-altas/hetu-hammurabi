# -*- coding: utf-8 -*-
"""harness.core 包：宪章体系 DSH 重构的确定性核心

本包为纯 Python 实现，无任何 harness（opencode/DSH）运行时依赖，
可独立单元测试。DSH/opencode 插件仅做薄适配，调用本包完成判定。

子模块：
- gate:      门禁判定核心（run_id 隔离 / token 信任模型 / 绕过面覆盖）
- workflow:  流程定义解析与校验（workflow.yaml）
- recorder:  运行事件采集与落盘（run_event JSONL）
- stats:     聚合统计（看板数据口径）
- history:   历史任务静态解析（存量 opencode_schedule 数据）
- notify:    通知唯一出口（钉钉，受门禁管控）
- api:       看板查询 API（FastAPI）
"""
