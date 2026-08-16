# -*- coding: utf-8 -*-
"""运行事件聚合统计（看板数据口径）

缺陷修复对照（20260814任务1）：
- D6 无运行度量：从 runlog 事件库聚合节点运行次数/成功率/门禁拦截率/
  任务列表/任务详情，支撑看板与宪章修订反哺。

口径约定（与 docs/hetu-hammurabi/dashboard.md 一致）：
- 节点运行次数 = node_start 事件数
- 节点成功率 = node_end 且 status=pass / node_end 总数（含重试轮）
- 门禁拦截率 = gate_block 事件数 / (gate_block + gate_pass) 事件数
- 任务最终状态 = 该任务最新一个 node_end/error 事件的 status
- source 字段区分 live（实时采集）与 history（历史静态解析）
"""

from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from harness.core import history as history_mod
from harness.core import recorder

NODE_NAMES = {
    "-1": "任务书生成",
    "0": "校验",
    "1": "分析",
    "2": "编码",
    "3": "单元测试",
    "4": "代码评审",
    "5": "研发日志",
    "6": "资产沉淀",
    "7": "通知",
}


def _dedup_node_ends(ends: List[dict]) -> List[dict]:
    """node_end 去重：同一 (run_id, node) 只保留最新一条。

    场景：seal-gate 多次重落闸（任务4 节点3 有 5 条 end）、重试轮次——完成状态以最后一次为准。

    Args:
        ends: node_end 事件列表。

    Returns:
        去重后的事件列表（每 (run_id, node) 保留 ts 最新一条）。
    """
    latest: Dict[tuple, dict] = {}
    for e in ends:
        key = (e.get("run_id"), e.get("node"))
        prev = latest.get(key)
        if prev is None or e.get("ts", "") >= prev.get("ts", ""):
            latest[key] = e
    return list(latest.values())


def _node_label(node) -> str:
    """节点显示名。

    Args:
        node: 节点 id（str/int）。

    Returns:
        节点名称；未知节点返回原 id。
    """
    key = str(node)
    return NODE_NAMES.get(key, key)


def _date_of(ts: str) -> str:
    """取事件日期（YYYYMMDD）。

    Args:
        ts: ISO 时间戳。

    Returns:
        日期字符串；解析失败返回空串。
    """
    try:
        return datetime.fromisoformat(ts).strftime("%Y%m%d")
    except ValueError:
        return ""


def overview(events: List[dict], period: str = "all") -> Dict[str, Any]:
    """总览统计。

    Args:
        events: 全部事件列表（live + history 合并）。
        period: 周期过滤（all/day/week/month，按事件日期）。

    Returns:
        {
            "total_tasks": 任务数,
            "total_node_runs": 节点运行总次数,
            "success_rate": 总体成功率(0~1),
            "gate_block_rate": 门禁拦截率(0~1),
            "gate_block_count": 拦截次数,
            "gate_pass_count": 放行次数,
            "period": 实际统计周期,
            "period_start": 最早事件日期,
            "period_end": 最晚事件日期,
        }
    """
    filtered = _filter_by_period(events, period)
    tasks = {e.get("run_id") for e in filtered if e.get("run_id")}
    node_ends = _dedup_node_ends([e for e in filtered if e.get("event_type") == "node_end"])
    success = sum(1 for e in node_ends if e.get("status") == "pass")
    blocks = [e for e in filtered if e.get("event_type") == "gate_block"]
    passes = [e for e in filtered if e.get("event_type") == "gate_pass"]

    dates = sorted({_date_of(e.get("ts", "")) for e in filtered if _date_of(e.get("ts", ""))})
    return {
        "total_tasks": len(tasks),
        # 节点运行次数 = 完成次数（去重后 end 数，与节点表 runs 口径一致）
        "total_node_runs": len(node_ends),
        "success_rate": round(success / len(node_ends), 4) if node_ends else 0.0,
        "gate_block_rate": round(len(blocks) / (len(blocks) + len(passes)), 4)
        if (blocks or passes) else 0.0,
        "gate_block_count": len(blocks),
        "gate_pass_count": len(passes),
        "period": period,
        "period_start": dates[0] if dates else "",
        "period_end": dates[-1] if dates else "",
    }


def nodes_stats(events: List[dict], period: str = "all") -> List[Dict[str, Any]]:
    """按节点统计。

    Args:
        events: 全部事件列表。
        period: 周期过滤。

    Returns:
        每节点一条：
        {
            "node": id, "node_name": 名称,
            "runs": 运行次数, "success": 成功数, "fail": 失败数,
            "success_rate": 成功率, "avg_round": 平均轮次,
        }
    """
    filtered = _filter_by_period(events, period)
    starts: Dict[str, int] = defaultdict(int)
    ends: Dict[str, List[dict]] = defaultdict(list)
    rounds: Dict[str, List[int]] = defaultdict(list)

    for e in filtered:
        node = str(e.get("node", "?"))
        if e.get("event_type") == "node_start":
            starts[node] += 1
            rounds[node].append(int(e.get("round", 1)))
        elif e.get("event_type") == "node_end":
            ends[node].append(e)
    # 去重：同一 (run_id, node) 只计最后一次完成（多次 seal-gate 落闸/重试）
    for node in ends:
        ends[node] = _dedup_node_ends(ends[node])

    result: List[Dict[str, Any]] = []
    all_nodes = set(starts) | set(ends)
    for node in sorted(all_nodes, key=lambda n: (n != "-1", int(n) if n.lstrip("-").isdigit() else 0)):
        ends_list = ends[node]
        success = sum(1 for e in ends_list if e.get("status") == "pass")
        failed = sum(1 for e in ends_list if e.get("status") == "fail")
        total = len(ends_list)
        avg_round = round(sum(rounds[node]) / len(rounds[node]), 2) if rounds[node] else 0.0
        result.append({
            "node": node,
            "node_name": _node_label(node),
            # 运行次数 = 完成次数（去重后 end 数），保证 runs = success + fail
            "runs": total,
            "success": success,
            "fail": failed,
            "success_rate": round(success / total, 4) if total else 0.0,
            "avg_round": avg_round,
        })
    return result


# 验证性拦截关键词：冒烟验证/门禁自检等故意触发的拦截，不计为真实违规
_VERIFICATION_KEYWORDS = ("冒烟验证", "验证性", "门禁自检", "门禁测试")


def _is_verification_block(event: dict) -> bool:
    """判定拦截事件是否为验证性拦截（故意触发，非真实违规）。

    Args:
        event: 拦截事件 dict。

    Returns:
        验证性拦截返回 True（extra 显式标记优先，其次按关键词判定）。
    """
    if event.get("extra", {}).get("verification") is True:
        return True
    msg = str(event.get("detail", {}).get("msg", ""))
    return any(k in msg for k in _VERIFICATION_KEYWORDS)


def gates_stats(events: List[dict], period: str = "all") -> Dict[str, Any]:
    """门禁拦截统计。

    Args:
        events: 全部事件列表。
        period: 周期过滤。

    Returns:
        {"rate": 拦截率, "count": 拦截次数, "pass_count": 放行次数,
         "verification_count": 验证性拦截次数,
         "events": 拦截事件列表（时间倒序，最多 200 条，含 verification 标记）}
    """
    filtered = _filter_by_period(events, period)
    blocks = [e for e in filtered if e.get("event_type") == "gate_block"]
    passes = [e for e in filtered if e.get("event_type") == "gate_pass"]
    blocks_sorted = sorted(blocks, key=lambda e: e.get("ts", ""), reverse=True)
    annotated = []
    for e in blocks_sorted:
        item = dict(e)
        item["verification"] = _is_verification_block(e)
        annotated.append(item)
    return {
        "rate": round(len(blocks) / (len(blocks) + len(passes)), 4)
        if (blocks or passes) else 0.0,
        "count": len(blocks),
        "pass_count": len(passes),
        "verification_count": sum(1 for e in annotated if e.get("verification")),
        "events": annotated[:200],
    }


def tasks_stats(events: List[dict], period: str = "all") -> List[Dict[str, Any]]:
    """任务列表统计。

    Args:
        events: 全部事件列表。
        period: 周期过滤。

    Returns:
        每任务一条（按最近活动倒序）：
        {
            "run_id", "project", "date", "status",
            "node_count": 节点数, "last_ts": 最近事件时间,
            "source": live/history,
        }
    """
    filtered = _filter_by_period(events, period)
    by_run: Dict[str, List[dict]] = defaultdict(list)
    for e in filtered:
        if e.get("run_id"):
            by_run[e["run_id"]].append(e)

    result: List[Dict[str, Any]] = []
    for run_id, evs in by_run.items():
        evs_sorted = sorted(evs, key=lambda e: e.get("ts", ""))
        latest = evs_sorted[-1]
        status = latest.get("status", "")
        if latest.get("event_type") in ("node_end", "error", "notify"):
            status = latest.get("status", "")
        result.append({
            "run_id": run_id,
            "project": latest.get("project", ""),
            "date": _date_of(latest.get("ts", "")),
            "status": status,
            "node_count": len({e.get("node") for e in evs if e.get("node")}),
            "last_ts": latest.get("ts", ""),
            "source": latest.get("source", "live"),
        })
    result.sort(key=lambda t: t["last_ts"], reverse=True)
    return result


def task_detail(events: List[dict], run_id: str) -> Optional[Dict[str, Any]]:
    """任务详情（节点时间线 + 事件流）。

    Args:
        events: 全部事件列表。
        run_id: 任务目录名。

    Returns:
        {
            "run_id", "project", "source",
            "timeline": 节点时间线（按节点 id 分组：start/end/gate/retry/rounds）,
            "events": 事件流（时间升序）,
            "files": 产物文件提示（来自事件 detail）,
        }
        run_id 不存在返回 None。
    """
    evs = [e for e in events if e.get("run_id") == run_id]
    if not evs:
        return None
    evs = sorted(evs, key=lambda e: e.get("ts", ""))

    timeline: List[Dict[str, Any]] = []
    by_node: Dict[str, List[dict]] = defaultdict(list)
    for e in evs:
        by_node[str(e.get("node", "?"))].append(e)
    for node in sorted(by_node, key=lambda n: (n != "-1", int(n) if n.lstrip("-").isdigit() else 0)):
        node_evs = by_node[node]
        start = next((e for e in node_evs if e.get("event_type") == "node_start"), None)
        end = next((e for e in node_evs if e.get("event_type") == "node_end"), None)
        # 门禁取最后一次判定（block 后可能 pass，最终状态为准）
        gate = next(
            (e for e in reversed(node_evs) if e.get("event_type") in ("gate_block", "gate_pass")),
            None,
        )
        retry = [e for e in node_evs if e.get("event_type") == "retry"]
        timeline.append({
            "node": node,
            "node_name": _node_label(node),
            "status": end.get("status") if end else (start.get("status") if start else ""),
            "start_ts": start.get("ts") if start else "",
            "end_ts": end.get("ts") if end else "",
            "gate": gate.get("event_type") if gate else "",
            "retries": len(retry),
            "rounds": max([int(e.get("round", 1)) for e in node_evs], default=1),
            "detail": (end or start or {}).get("detail", {}),
        })

    files = sorted({
        str(e.get("detail", {}).get("file", "")).strip()
        for e in evs if str(e.get("detail", {}).get("file", "")).strip()
    })
    return {
        "run_id": run_id,
        "project": evs[-1].get("project", ""),
        "source": evs[-1].get("source", "live"),
        "timeline": timeline,
        "events": evs,
        "files": files,
    }


def _filter_by_period(events: List[dict], period: str) -> List[dict]:
    """按周期过滤事件（all/day/week/month）。

    Args:
        events: 全部事件列表。
        period: all/day/week/month。

    Returns:
        过滤后的事件列表。
    """
    if period == "all" or not period:
        return events
    dates = sorted({_date_of(e.get("ts", "")) for e in events if _date_of(e.get("ts", ""))})
    if not dates:
        return []
    if period == "day":
        keep = dates[-1:]
    elif period == "week":
        keep = dates[-7:]
    elif period == "month":
        keep = dates[-30:]
    else:
        keep = dates
    return [e for e in events if _date_of(e.get("ts", "")) in set(keep)]


# ---------------------------------------------------------------------------
# 引擎性能对比（DSH vs opencode）
# ---------------------------------------------------------------------------

# 引擎归属：run_id 以该日期开头视为 DSH 引擎执行（20260815 起全面使用 /cc）
DSH_ENGINE_PREFIX = "20260815"
# 人工执行任务（runlog 记录窗口不代表真实耗时，剔除）
MANUAL_EXEC_RUN_IDS = (
    "20260814任务1宪章体系DSH重构与运行看板",
    "20260814任务2宪章看板DSH原生面板",
)
# 跨天异常阈值（分钟）：超过视为状态文件跨多天，非单次执行
ABNORMAL_DURATION_MIN = 1000.0


def _parse_status_time(text: str):
    """解析状态文件时间列。

    Args:
        text: 时间列原文。

    Returns:
        datetime；无法解析（如仅日期）返回 None。
    """
    s = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _task_duration(run_id: str, task_dir, events: List[dict]):
    """计算单任务主流程耗时（分钟）。

    runlog 事件优先（节点 -1/0 start → 首次节点 7 end）；
    无事件时用状态文件首行→末行时间差。

    Args:
        run_id: 任务目录名。
        task_dir: 任务目录路径。
        events: 全部事件（含 live）。

    Returns:
        (耗时分钟, 节点行数, 来源)。不可算返回 (None, 0, "")。
    """
    evs = sorted(
        [e for e in events if e.get("run_id") == run_id and e.get("source") == "live"],
        key=lambda e: e.get("ts", ""),
    )
    if evs:
        start_ts = None
        for e in evs:
            if e.get("event_type") == "node_start" and str(e.get("node")) in ("-1", "0"):
                start_ts = e.get("ts")
                break
        end_ts = None
        for e in evs:
            if e.get("event_type") == "node_end" and str(e.get("node")) == "7":
                end_ts = e.get("ts")
                break
        if start_ts and end_ts:
            try:
                d0 = datetime.fromisoformat(start_ts)
                d1 = datetime.fromisoformat(end_ts)
                return (d1 - d0).total_seconds() / 60.0, 9, "runlog"
            except ValueError:
                pass
    if task_dir is None:
        return None, 0, ""
    status_file = task_dir / "研发流程状态.md"
    if status_file.is_file():
        rows = history_mod.parse_status_rows(status_file.read_text(encoding="utf-8"))
        times = [t for t in (_parse_status_time(r["time"]) for r in rows) if t]
        if len(times) >= 2:
            return (times[-1] - times[0]).total_seconds() / 60.0, len(rows), "status"
    return None, 0, ""


def engine_benchmark(events: List[dict], workspace_dir) -> Dict[str, Any]:
    """DSH vs opencode 引擎性能对比。

    数据源：runlog 事件（live，秒级）+ 各任务状态文件（分钟级）。
    引擎归属：run_id 以 20260815 开头 → dsh（/cc 全面启用日），否则 opencode。
    剔除：跨天异常（>1000 分钟）与人工执行任务（黑名单）。

    Args:
        events: 全部事件（load_events 结果）。
        workspace_dir: 同父目录（扫描各 hetu-* 项目任务目录）。

    Returns:
        {
            "dsh": {"count", "avg_min", "median_min", "per_node_avg_min"},
            "opencode": {...},
            "ratio_avg": 平均耗时比(dsh/opencode),
            "ratio_median": 中位耗时比,
            "excluded": [{"run_id", "reason"}],
        }
    """
    root = Path(workspace_dir)
    tasks = []  # (run_id, engine, dur, nodes)
    excluded = []
    if not root.is_dir():
        return {"dsh": None, "opencode": None, "ratio_avg": None, "ratio_median": None, "excluded": excluded}
    # 候选任务 = 任务目录 ∪ runlog live 事件任务（目录缺失时仍可算）
    candidates = {}  # run_id -> task_dir（可能为 None）
    for proj in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("hetu-")):
        sched = proj / "opencode_schedule"
        if not sched.is_dir():
            continue
        for day in sorted(p for p in sched.iterdir() if p.is_dir()):
            for task in sorted(p for p in day.iterdir() if p.is_dir()):
                if history_mod.is_charter_task_dir(task):
                    candidates.setdefault(task.name, task)
    for e in events:
        rid = e.get("run_id")
        if rid and e.get("source") == "live":
            candidates.setdefault(rid, None)
    for run_id, task in sorted(candidates.items()):
        engine = "dsh" if run_id.startswith(DSH_ENGINE_PREFIX) else "opencode"
        if run_id in MANUAL_EXEC_RUN_IDS:
            excluded.append({"run_id": run_id, "reason": "人工执行（runlog 记录窗口不代表真实耗时）"})
            continue
        dur, nodes, src = _task_duration(run_id, task, events)
        if dur is None:
            continue
        if dur > ABNORMAL_DURATION_MIN:
            excluded.append({"run_id": run_id, "reason": f"状态文件跨多天（{dur:.0f} 分），非单次执行"})
            continue
        tasks.append({"run_id": run_id, "engine": engine, "dur": dur, "nodes": nodes, "src": src})

    def _agg(engine: str) -> Optional[Dict[str, Any]]:
        group = [x for x in tasks if x["engine"] == engine]
        if not group:
            return None
        durs = sorted(x["dur"] for x in group)
        n = len(durs)
        median = durs[n // 2] if n % 2 else (durs[n // 2 - 1] + durs[n // 2]) / 2
        avg = sum(durs) / n
        node_avgs = [x["dur"] / x["nodes"] for x in group if x["nodes"] > 0]
        return {
            "count": n,
            "avg_min": round(avg, 1),
            "median_min": round(median, 1),
            "per_node_avg_min": round(sum(node_avgs) / len(node_avgs), 1) if node_avgs else None,
        }

    dsh = _agg("dsh")
    oc = _agg("opencode")
    return {
        "dsh": dsh,
        "opencode": oc,
        "ratio_avg": round(dsh["avg_min"] / oc["avg_min"], 2) if dsh and oc and oc["avg_min"] else None,
        "ratio_median": round(dsh["median_min"] / oc["median_min"], 2) if dsh and oc and oc["median_min"] else None,
        "excluded": excluded,
    }
