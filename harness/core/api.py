# -*- coding: utf-8 -*-
"""看板查询 API（FastAPI）

数据来源：
- live：runlog/events/ 下实时采集事件（recorder）
- history：opencode_schedule/ 存量任务静态解析合成事件（history）

端点：
- GET /api/health             健康检查
- GET /api/stats/overview     总览（任务数/运行次数/成功率/门禁拦截率）
- GET /api/stats/nodes        按节点统计
- GET /api/stats/gates        门禁拦截统计
- GET /api/tasks              任务列表
- GET /api/tasks/{run_id}     任务详情
- GET /                      看板前端（harness/dashboard/）

启动：
    <venv>/bin/python -m uvicorn harness.core.api:app --port 8790
    （或 scripts/start_dashboard.sh）
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from harness.core import history as history_mod
from harness.core import recorder, stats

# 历史事件缓存时长（秒）：存量扫描有 IO 成本，做短缓存
_HISTORY_CACHE_TTL = 10  # 状态栏 5s 轮询需要及时看到新任务（历史扫描有 IO，10s 折中）


def load_events(runlog_root, schedule_root, workspace_dir=None) -> List[dict]:
    """合并 live + history 事件。

    Args:
        runlog_root: runlog 根目录（live 事件）。
        schedule_root: 宿主 opencode_schedule 根目录（单项目 history，兼容旧调用）。
        workspace_dir: 同父目录（提供时扫描全部 hetu-* 项目的 history）。

    Returns:
        合并后的事件列表。
    """
    events = list(recorder.iter_events(runlog_root))
    live_runs = {e.get("run_id") for e in events if e.get("run_id")}
    if workspace_dir:
        hist = history_mod.scan_all_schedule(workspace_dir)
    else:
        hist = history_mod.scan_schedule(schedule_root)
    # 宿主任务已有 live 事件（权威）时丢弃其 history 解析，避免双重统计
    events.extend(e for e in hist if e.get("run_id") not in live_runs)
    return events


def create_app(
    runlog_root,
    schedule_root,
    dashboard_dir=None,
    workspace_dir=None,
    cache_ttl: int = _HISTORY_CACHE_TTL,
) -> FastAPI:
    """构造看板 FastAPI 应用。

    Args:
        runlog_root: runlog 根目录。
        schedule_root: 宿主 opencode_schedule 根目录（workspace_dir 缺失时的单项目扫描）。
        dashboard_dir: 看板静态前端目录（默认 harness/dashboard）。
        workspace_dir: 同父目录；提供时历史统计覆盖全部 hetu-* 项目。
        cache_ttl: 历史扫描缓存时长（秒）。

    Returns:
        FastAPI 应用实例。
    """
    app = FastAPI(title="宪章体系运行看板", version="2.0.0")

    # 数据缓存：避免每次请求重扫历史
    cache: Dict[str, Any] = {"ts": 0.0, "events": []}

    def _events() -> List[dict]:
        now = time.time()
        if now - cache["ts"] > cache_ttl:
            cache["events"] = load_events(runlog_root, schedule_root, workspace_dir)
            cache["ts"] = now
        return cache["events"]

    @app.get("/api/health")
    def health() -> dict:
        """健康检查。"""
        return {"ok": True, "events": len(_events())}

    @app.get("/api/stats/overview")
    def api_overview(period: str = "all") -> dict:
        """总览统计。"""
        return stats.overview(_events(), period=period)

    @app.get("/api/stats/nodes")
    def api_nodes(period: str = "all") -> dict:
        """按节点统计。"""
        return {"nodes": stats.nodes_stats(_events(), period=period)}

    @app.get("/api/stats/gates")
    def api_gates(period: str = "all") -> dict:
        """门禁拦截统计。"""
        return stats.gates_stats(_events(), period=period)

    @app.get("/api/stats/benchmark")
    def api_benchmark() -> dict:
        """引擎性能对比（DSH vs opencode 宪章流程平均耗时）。"""
        return stats.engine_benchmark(_events(), workspace_dir)

    @app.get("/api/tasks")
    def api_tasks(period: str = "all") -> dict:
        """任务列表。"""
        return {"tasks": stats.tasks_stats(_events(), period=period)}

    @app.get("/api/tasks/{run_id}")
    def api_task_detail(run_id: str) -> dict:
        """任务详情。"""
        detail = stats.task_detail(_events(), run_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"任务不存在: {run_id}")
        return detail

    # 看板静态前端
    dash = Path(dashboard_dir) if dashboard_dir else Path(__file__).resolve().parent.parent / "dashboard"
    if dash.is_dir():
        app.mount("/", StaticFiles(directory=str(dash), html=True), name="dashboard")
    else:
        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(dash / "index.html")

    return app


# 默认实例：供 uvicorn harness.core.api:app 直接启动
# 历史统计覆盖同父目录全部 hetu-* 项目（含宿主），workspace_dir = hetu-altas
_HARNESS_ROOT = Path(__file__).resolve().parent.parent
_WORKSPACE_DIR = _HARNESS_ROOT.parent.parent
app = create_app(
    runlog_root=_HARNESS_ROOT.parent / "runlog",
    schedule_root=_HARNESS_ROOT.parent / "opencode_schedule",
    workspace_dir=_WORKSPACE_DIR,
)
