# -*- coding: utf-8 -*-
"""运行事件采集与落盘（run_event JSONL）

缺陷修复对照（20260814任务1）：
- D6 无运行度量：全部节点 start/end、门禁 block/pass、retry、notify、error
  事件按 run_id 采集落盘，供看板聚合与宪章修订反哺。

事件 schema（一行一事件，追加写不覆盖）：
    {
        "event_id": "uuid",
        "ts": "2026-08-14T10:00:00+08:00",
        "run_id": "20260814任务1xxx",
        "project": "hetu-thoth",
        "node": "3",
        "node_name": "单元测试",
        "event_type": "node_start|node_end|gate_block|gate_pass|retry|notify|error",
        "status": "running|pass|fail|blocked",
        "round": 1,
        "detail": {"msg": "...", "tool": "bash", "file": "..."},
        "extra": {},
        "source": "live"            # live=实时采集；history=历史静态解析
    }
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

EVENT_SCHEMA_FIELDS = (
    "event_id", "ts", "run_id", "project", "node", "node_name",
    "event_type", "status", "round", "detail", "extra", "source",
)

VALID_EVENT_TYPES = (
    "node_start", "node_end", "gate_block", "gate_pass",
    "retry", "notify", "error", "re_seal",
)
VALID_STATUSES = ("running", "pass", "fail", "blocked")

_lock = threading.Lock()


def event_file_for(runlog_root, run_id: str, ts: Optional[datetime] = None) -> Path:
    """计算事件文件路径（按日落盘，按 run_id 分文件）。

    Args:
        runlog_root: runlog 根目录（通常为宿主 runlog/）。
        run_id: 任务目录名（run_id 契约）。
        ts: 事件时间（默认当前时间）。

    Returns:
        runlog_root/events/YYYYMMDD/<run_id>.jsonl
    """
    ts = ts or datetime.now()
    root = Path(runlog_root)
    return root / "events" / ts.strftime("%Y%m%d") / f"{run_id}.jsonl"


def record_event(
    runlog_root,
    run_id: str,
    node,
    node_name: str,
    event_type: str,
    status: str,
    detail: Optional[Dict[str, Any]] = None,
    project: str = "",
    round_: int = 1,
    extra: Optional[Dict[str, Any]] = None,
    ts: Optional[datetime] = None,
    source: str = "live",
) -> dict:
    """记录一条运行事件并落盘（JSONL 追加，线程安全）。

    Args:
        runlog_root: runlog 根目录。
        run_id: 任务目录名。
        node: 节点 id（-1~7 的 int 或 str）。
        node_name: 节点名称（如 "单元测试"）。
        event_type: 事件类型（node_start/node_end/gate_block/...）。
        status: 状态（running/pass/fail/blocked）。
        detail: 事件明细（msg/tool/file 等）。
        project: 业务项目名（如 hetu-thoth）。
        round_: 重试轮次（默认 1）。
        extra: 附加字段。
        ts: 事件时间（默认当前时间）。
        source: 数据来源（live/history）。

    Returns:
        完整事件 dict（已落盘）。

    Raises:
        ValueError: event_type 或 status 非法。
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"非法 event_type: {event_type}")
    if status not in VALID_STATUSES:
        raise ValueError(f"非法 status: {status}")

    ts = ts or datetime.now()
    event: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "ts": ts.isoformat(timespec="seconds"),
        "run_id": run_id,
        "project": project,
        "node": str(node),
        "node_name": node_name,
        "event_type": event_type,
        "status": status,
        "round": round_,
        "detail": detail or {},
        "extra": extra or {},
        "source": source,
    }

    path = event_file_for(runlog_root, run_id, ts)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False)
    with _lock:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    return event


def iter_events(runlog_root) -> Iterator[dict]:
    """遍历 runlog 下全部事件（按日目录、文件名字典序）。

    Args:
        runlog_root: runlog 根目录。

    Yields:
        事件 dict（逐行解析，跳过损坏行）。
    """
    root = Path(runlog_root) / "events"
    if not root.is_dir():
        return
    for day_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for f in sorted(day_dir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def events_for_run(runlog_root, run_id: str) -> List[dict]:
    """取指定 run_id 的全部事件（按时间升序）。

    Args:
        runlog_root: runlog 根目录。
        run_id: 任务目录名。

    Returns:
        事件列表（按 ts 升序）。
    """
    events = [e for e in iter_events(runlog_root) if e.get("run_id") == run_id]
    events.sort(key=lambda e: e.get("ts", ""))
    return events
