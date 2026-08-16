# 宪章体系运行看板（dashboard）

> 20260814 任务1（宪章体系DSH重构与运行看板）登记。
> 可视化各节点运行次数、成功率、门禁拦截率与任务运行详情；
> 数据来自运行事件库（live）与存量任务静态解析（history）。

## 一、启动

```bash
bash scripts/start_dashboard.sh            # 默认端口 8790
bash scripts/start_dashboard.sh 8800       # 指定端口
```

访问：`http://127.0.0.1:<端口>/`（默认 8790）

> 端口冲突提示：DSH web 默认 3080；若与 Windows 应用（如 attu）冲突，
> 用 `npm exec @deepseek-ai/dsh web --port <新端口>` 启动 DSH 即可（看板数据通道自动跟随）。

## 二、界面说明

| 区域 | 内容 |
|------|------|
| 总览卡片 | 任务总数、节点运行次数、节点成功率、门禁拦截率（含拦截/放行计数） |
| 节点运行统计 | 每节点：运行次数、成功/失败、成功率（含进度条）、平均轮次 |
| 门禁拦截记录 | 拦截事件列表（时间/任务/节点/原因），附拦截率 |
| 任务列表 | run_id、项目、日期、最终状态、节点数、来源（实时/历史）；点击行查看详情 |
| 任务详情 | 节点时间线（状态点 + 门禁/重试标注）+ 最近 50 条事件流 |

顶部可切换统计周期（全部/今天/本周/本月），10 秒自动刷新。

## 三、指标口径

| 指标 | 口径 |
|------|------|
| 节点运行次数 | `node_start` 事件数（历史解析中「进行中」节点只计 start 不计 end；discover 为元事件不计入） |
| 节点成功率 | `node_end` 且 `status=pass` / `node_end` 总数（含重试轮） |
| 门禁拦截率 | `gate_block` 事件数 /（`gate_block` + `gate_pass`）事件数 |
| 任务最终状态 | 该任务最新 `node_end`/`error`/`notify` 事件的 status |
| 数据来源 | live=实时采集（`runlog/events/`）；history=存量任务静态解析——**覆盖同父目录全部 hetu-\* 项目**（hetu-hammurabi/aether/sybil/thoth 等，看板标注"历史"） |
| 统计范围 | 看板服务按宿主同父目录（workspace）扫描全部 hetu-\* 项目的 `opencode_schedule/`；空日期目录/备份目录自动过滤（`is_charter_task_dir` 判定：任务书/状态文件/门禁文件任一命中） |

## 四、API

| 接口 | 返回 |
|------|------|
| `GET /api/health` | 健康检查 + 事件总数 |
| `GET /api/stats/overview?period=all\|day\|week\|month` | 总览 |
| `GET /api/stats/nodes?period=...` | 按节点统计 |
| `GET /api/stats/gates?period=...` | 门禁拦截统计 |
| `GET /api/tasks?period=...` | 任务列表 |
| `GET /api/tasks/{run_id}` | 任务详情（时间线 + 事件流） |

## 五、DSH 原生面板（client-plugin，主入口）

20260814 任务2 交付：看板升级为 **DSH client-plugin 原生面板**，嵌入 DSH web GUI：

- **入口**：GUI 侧边栏底部「宪章看板」按钮（`sidebar.footer.action` 插槽），点击打开全屏看板浮层（`shell.overlay` 插槽）
- **内容**：总览 4 卡片 / 节点运行统计（含成功率条）/ 门禁拦截记录 / 任务列表（点击行展开节点时间线与事件流），与独立看板数据一致
- **数据**：同源 `GET /api/hetu-dashboard/api/*` → node 半区转发 → 看板服务 8790；8790 不可达时面板显示降级提示
- **实现**：`harness/dsh/hetu-dashboard/`（package.json 双面元数据 + client.js browser 半区 + lib/index.js node 半区）；开发指南见 [dsh-client-plugin.md](dsh-client-plugin.md)
- **注册**：包装入 dsh 安装目录 node_modules + web profile `cordis.patch.yml` insert 行（见 dsh-client-plugin.md 第三节）

独立看板服务（8790）与 `/dashboard` 代理路径**保留**，作为降级通道与数据源。

## 六、挂接到 DSH web GUI（代理方案，降级路径）

宪章看板可通过 webserver 前缀路由代理方式挂接进 DSH 的 web GUI（`dsh web`），
访问 `http://127.0.0.1:3080/dashboard` 直接查看（原生面板为主入口后，此为降级路径）：

```bash
# 挂接（写入 $DSH_HOME/profiles/web/，幂等可重跑）
bash scripts/attach_dashboard_to_dsh.sh

# 预览变更（不写入）
bash scripts/attach_dashboard_to_dsh.sh --check

# 卸载
bash scripts/attach_dashboard_to_dsh.sh --detach
```

挂接后需**重启 dsh web** 生效（配置启动时加载），并保持看板服务运行
（`bash scripts/start_dashboard.sh`）。插件源文件：`harness/dsh/plugins/dashboard-proxy.ts`，
注册两条前缀路由：`/dashboard`（页面代理）与 `/api/hetu-dashboard`（原生面板数据通道），
均转发到看板服务（可用环境变量 `HETU_DASHBOARD_PORT` 覆盖端口）；
页面路径在服务未启动时返回友好提示页，数据通道返回 `{"ok":false}` 降级 JSON。

## 七、数据链路

```
节点执行（编排插件）→ harness.core.recorder 落盘
                    → runlog/events/YYYYMMDD/<run_id>.jsonl
看板服务（uvicorn）→ 合并 live 事件 + history 静态解析 → /api/* → 前端渲染
```

- 事件写入：`python -m harness.core.cli record --runlog runlog --run-id ...`
- 落闸记录：`python -m harness.core.cli seal-gate --task-dir ...`（编排器专用，同时产生 `gate_pass` 事件的依据）
