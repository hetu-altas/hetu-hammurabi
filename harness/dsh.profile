# 河图·汉谟拉比 宪章编程 DSH profile 清单
# bundles 按顺序叠加（dsh-base 为宿主基础包，随后加载宪章插件组合）
name: hetu-hammurabi
description: 宪章编程研发流水线（任务书→分析→编码→单测门禁→评审→日志→沉淀→通知）

bundles:
  - "@deepseek-ai/dsh-base"
  - "./plugins/charter-gate"
  - "./plugins/charter-recorder"
  - "./plugins/charter-orchestrator"
