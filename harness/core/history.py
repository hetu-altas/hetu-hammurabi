# -*- coding: utf-8 -*-
"""历史任务静态解析（存量 opencode_schedule 数据）

缺陷修复对照（20260814任务1）：
- D6 无运行度量：存量任务（事件库建立之前）从任务目录的
  研发流程状态.md 与 .gate.json v1 静态解析为合成事件（source=history），
  并入看板统计，保证历史数据可观测。

合成事件口径：
- 每条状态表记录 → 1 条 node_end 事件（status=通过/失败 → pass/fail）
- 存在 .gate.json v1 且 test_passed=true → 1 条 gate_pass 事件（node=3）
- 任务级 node_start 事件（node=0, 说明=任务目录发现）
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# 状态表行：| 时间 | 节点 | 状态 | 说明 |
STATUS_ROW_PATTERN = re.compile(
    r"^\|\s*(?P<time>[^|]+?)\s*\|\s*(?P<node>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|\s*(?P<detail>[^|]*)\s*\|"
)

GATE_V1 = ".gate.json"
TASK_DIR_RE = re.compile(r"^(\d{8})任务(\d+)(.*)$")


def parse_task_dir_name(name: str) -> Dict[str, str]:
    """解析任务目录名（YYYYMMDD任务N名称）。

    Args:
        name: 任务目录名（如 "20260804任务1河图Logo设计"）。

    Returns:
        {"date": "20260804", "no": "1", "title": "河图Logo设计"}；
        无法解析时返回空字段。
    """
    m = TASK_DIR_RE.match(name)
    if not m:
        return {"date": "", "no": "", "title": name}
    return {"date": m.group(1), "no": m.group(2), "title": m.group(3)}


def parse_status_rows(text: str) -> List[Dict[str, str]]:
    """解析研发流程状态.md 的状态表行。

    Args:
        text: 状态文件全文。

    Returns:
        [{"time":..., "node":..., "status":..., "detail":...}, ...]
    """
    rows = []
    for line in text.splitlines():
        m = STATUS_ROW_PATTERN.match(line)
        if not m:
            continue
        node = m.group("node").strip()
        if node in ("节点", ""):
            continue  # 跳过表头行
        if not re.search(r"节点|任务书生成|校验|分析|编码|单元测试|评审|日志|沉淀|通知", node):
            continue
        rows.append({
            "time": m.group("time").strip(),
            "node": node,
            "status": m.group("status").strip(),
            "detail": m.group("detail").strip(),
        })
    return rows


def _map_status_text(text: str) -> str:
    """状态列 → pass/running/skip/fail。

    兼容模型（/cc 流程）状态文件用词：✅ 完成 / 🔄 进行中 / ⏭️ 不适用 等。

    Args:
        text: 状态列原文。

    Returns:
        pass / running / skip / fail。
    """
    t = text.strip()
    if any(k in t for k in ("通过", "完成", "成功", "达成", "✅")):
        return "pass"
    if any(k in t for k in ("进行中", "处理中", "运行中", "🔄", "⏳")):
        return "running"
    if any(k in t for k in ("不适用", "跳过", "无需", "⏭️", "N/A")):
        return "skip"
    if any(k in t for k in ("失败", "未通过", "❌", "阻塞", "异常")):
        return "fail"
    return "fail"


def _map_node_label(label: str) -> str:
    """节点标签 → 节点 id（-1~7）。

    Args:
        label: 状态文件中的节点标签（如 "3 单元测试"）。

    Returns:
        节点 id 字符串；无法识别返回 "?"。
    """
    m = re.match(r"^\s*(-?\d+)\s*", label)
    if m:
        return m.group(1)
    for nid, name in (("-1", "任务书生成"), ("0", "校验"), ("1", "分析"),
                      ("2", "编码"), ("3", "单元测试"), ("4", "代码评审"),
                      ("5", "研发日志"), ("6", "资产沉淀"), ("7", "通知")):
        if name in label:
            return nid
    return "?"


def parse_task_dir(task_dir: Path, project: str = "") -> List[dict]:
    """解析单个历史任务目录为合成事件列表。

    Args:
        task_dir: 任务目录路径。
        project: 业务项目名（默认取父目录 basename 推断失败则为空）。

    Returns:
        合成事件列表（source=history）。
    """
    events: List[dict] = []
    name = task_dir.name
    meta = parse_task_dir_name(name)
    date = meta["date"]
    # ISO 日期（20260804 → 2026-08-04），保证 ts 可被 datetime.fromisoformat 解析
    iso_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else "2000-01-01"
    base_dt = datetime.strptime(f"{iso_date} 09:00:00", "%Y-%m-%d %H:%M:%S")
    if not project:
        project = task_dir.parent.parent.name if task_dir.parent.parent.name else ""

    def _ts(offset_minutes: int) -> str:
        """基准时间偏移 N 分钟 → ISO 字符串。"""
        return (base_dt + timedelta(minutes=offset_minutes)).isoformat(timespec="seconds")

    events.append({
        "event_id": f"hist-{name}-discover",
        "ts": _ts(0),
        "run_id": name,
        "project": project,
        "node": "0",
        "node_name": "校验",
        "event_type": "discover",  # 元事件：不参与节点统计
        "status": "running",
        "round": 1,
        "detail": {"msg": "历史任务目录发现", "source": "history"},
        "extra": {},
        "source": "history",
    })

    status_file = task_dir / "研发流程状态.md"
    if status_file.is_file():
        rows = parse_status_rows(status_file.read_text(encoding="utf-8"))
        for i, row in enumerate(rows):
            node_id = _map_node_label(row["node"])
            status = _map_status_text(row["status"])
            if status == "skip":
                # 不适用/跳过节点：不产出任何事件（不算失败也不算完成）
                continue
            # 成对事件：node_start + node_end，保证统计口径自洽
            events.append({
                "event_id": f"hist-{name}-start-{i}",
                "ts": _ts(i * 2 + 1),
                "run_id": name,
                "project": project,
                "node": node_id,
                "node_name": row["node"],
                "event_type": "node_start",
                "status": "running",
                "round": 1,
                "detail": {"msg": "历史节点开始", "source": "history"},
                "extra": {},
                "source": "history",
            })
            if status != "running":
                # 进行中节点未完成，不产出 node_end（避免污染完成统计）
                events.append({
                    "event_id": f"hist-{name}-node-{i}",
                    "ts": _ts(i * 2 + 2),
                    "run_id": name,
                    "project": project,
                    "node": node_id,
                    "node_name": row["node"],
                    "event_type": "node_end",
                    "status": status,
                    "round": 1,
                    "detail": {"msg": row["detail"], "source": "history"},
                    "extra": {},
                    "source": "history",
                })

    gate_file = task_dir / GATE_V1
    if gate_file.is_file():
        try:
            g = json.loads(gate_file.read_text(encoding="utf-8"))
            if g.get("test_passed") is True:
                events.append({
                    "event_id": f"hist-{name}-gate",
                    "ts": _ts(len(rows) * 2 + 3) if status_file.is_file() else _ts(1),
                    "run_id": name,
                    "project": project,
                    "node": "3",
                    "node_name": "单元测试",
                    "event_type": "gate_pass",
                    "status": "pass",
                    "round": 1,
                    "detail": {"msg": f"历史门禁通过 {g.get('passed')}/{g.get('total')}", "source": "history"},
                    "extra": {},
                    "source": "history",
                })
        except (OSError, json.JSONDecodeError):
            pass
    return events


def is_charter_task_dir(task_dir: Path) -> bool:
    """判定目录是否为宪章任务目录。

    条件（任一命中）：含与目录同名的任务书 .md、研发流程状态.md 或 .gate.json。
    用于过滤 opencode_schedule 下的空日期目录/备份目录（如 mercury 的 bak）。

    Args:
        task_dir: 候选任务目录路径。

    Returns:
        是宪章任务目录返回 True。
    """
    if (task_dir / "研发流程状态.md").is_file():
        return True
    if (task_dir / GATE_V1).is_file():
        return True
    if (task_dir / f"{task_dir.name}.md").is_file():
        return True
    return False


def scan_schedule(schedule_root, project: str = "") -> List[dict]:
    """扫描一个项目 opencode_schedule 下全部历史任务并合成事件。

    Args:
        schedule_root: opencode_schedule 根目录路径。
        project: 业务项目名（默认取 schedule_root 的父目录名）。

    Returns:
        全部合成事件列表（source=history，仅含真任务目录）。
    """
    root = Path(schedule_root)
    events: List[dict] = []
    if not root.is_dir():
        return events
    project = project or root.parent.name
    for day_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for task_dir in sorted(p for p in day_dir.iterdir() if p.is_dir()):
            if not is_charter_task_dir(task_dir):
                continue
            events.extend(parse_task_dir(task_dir, project=project))
    return events


def scan_all_schedule(workspace_dir) -> List[dict]:
    """扫描同父目录全部 hetu-* 项目（含 harness 宿主）的宪章任务。

    每个项目独立解析，project 字段取项目目录名（hetu-aether / hetu-thoth 等），
    看板任务列表据此区分项目。

    Args:
        workspace_dir: 同父目录（各 hetu-* 平级项目的根）。

    Returns:
        全部合成事件列表（source=history）。
    """
    root = Path(workspace_dir)
    events: List[dict] = []
    if not root.is_dir():
        return events
    for proj in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("hetu-")):
        schedule = proj / "opencode_schedule"
        if schedule.is_dir():
            events.extend(scan_schedule(schedule, project=proj.name))
    return events
