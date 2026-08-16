# -*- coding: utf-8 -*-
"""宪章流程定义解析与校验（workflow.yaml，DSH 重构版）

缺陷修复对照（20260814任务1）：
- D5 流程定义硬编码：节点顺序、回退轮次、门禁挂载点、前置依赖全部外置到
  workflow.yaml，由本模块解析校验；编排器读取执行，新增/调整节点只改 yaml。

workflow.yaml 结构（schema_version 1）：
    schema_version: 1
    nodes:
      - id: -1
        agent: charter-taskwriter
        when: input_is_requirement        # 可选：仅特定输入模式执行
      - id: 3
        agent: charter-tester
        gate: unit_test                   # 可选：硬门禁类型
        retry: {to: 2, max_rounds: 3}     # 可选：失败回退
        requires: []                      # 可选：前置节点（默认按序）
      - id: 5
        agent: charter-logger
        requires: [3, 4]
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# 合法门禁类型
VALID_GATES = ("unit_test", "review")
# 合法特殊 agent（内建节点）
BUILTIN_AGENTS = ("builtin_validate", "builtin_finish")


def load_workflow(path) -> Dict[str, Any]:
    """加载 workflow.yaml。

    Args:
        path: yaml 文件路径（str 或 Path）。

    Returns:
        解析后的 dict。

    Raises:
        ValueError: 文件不存在、YAML 非法或顶层结构错误。
    """
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"workflow 文件不存在: {p}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"workflow YAML 解析失败: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise ValueError("workflow 顶层必须包含 nodes 列表")
    return data


def validate_workflow(wf: Dict[str, Any]) -> List[str]:
    """校验 workflow 定义的合法性。

    Args:
        wf: load_workflow 的返回值。

    Returns:
        错误信息列表；为空表示合法。
    """
    errors: List[str] = []
    if wf.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")

    nodes = wf.get("nodes", [])
    ids = [n.get("id") for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append("节点 id 重复")

    known_ids = set(ids)
    for n in nodes:
        nid = n.get("id")
        agent = n.get("agent")
        if nid is None:
            errors.append("节点缺少 id")
            continue
        if not agent or not isinstance(agent, str):
            errors.append(f"节点 {nid} 缺少 agent")
        elif agent not in BUILTIN_AGENTS and not agent.startswith("charter-"):
            errors.append(f"节点 {nid} 的 agent 非法: {agent}")

        gate = n.get("gate")
        if gate is not None and gate not in VALID_GATES:
            errors.append(f"节点 {nid} 的 gate 非法: {gate}")

        retry = n.get("retry")
        if retry is not None:
            if not isinstance(retry, dict):
                errors.append(f"节点 {nid} 的 retry 必须是映射")
            else:
                if retry.get("to") not in known_ids:
                    errors.append(f"节点 {nid} 的 retry.to 指向不存在的节点: {retry.get('to')}")
                if not isinstance(retry.get("max_rounds"), int) or retry["max_rounds"] < 1:
                    errors.append(f"节点 {nid} 的 retry.max_rounds 必须为正整数")

        requires = n.get("requires") or []
        if not isinstance(requires, list):
            errors.append(f"节点 {nid} 的 requires 必须是列表")
        else:
            for r in requires:
                if r not in known_ids:
                    errors.append(f"节点 {nid} 的 requires 指向不存在的节点: {r}")
    return errors


def node_by_id(wf: Dict[str, Any], nid: int) -> Optional[Dict[str, Any]]:
    """按 id 取节点定义。

    Args:
        wf: workflow 数据。
        nid: 节点 id。

    Returns:
        节点定义 dict；不存在返回 None。
    """
    for n in wf.get("nodes", []):
        if n.get("id") == nid:
            return n
    return None


def sorted_node_ids(wf: Dict[str, Any]) -> List[int]:
    """按 id 升序返回全部节点 id。

    Args:
        wf: workflow 数据。

    Returns:
        节点 id 列表（升序）。
    """
    return sorted(n["id"] for n in wf.get("nodes", []))


def next_allowed(wf: Dict[str, Any], done_ids: List[int]) -> List[int]:
    """计算当前已完成节点下允许执行的下一批节点。

    规则：id 升序；节点可执行当且仅当
    1. 自身未完成
    2. 其 requires 依赖全部完成
    3. 若没有 requires，则要求所有 id 更小的节点已完成（按序执行）

    Args:
        wf: workflow 数据。
        done_ids: 已完成节点 id 列表。

    Returns:
        可执行的节点 id 列表（升序）。
    """
    done = set(done_ids)
    result: List[int] = []
    for n in wf.get("nodes", []):
        nid = n["id"]
        if nid in done:
            continue
        requires = n.get("requires") or []
        if requires:
            if all(r in done for r in requires):
                result.append(nid)
        else:
            smaller = [m["id"] for m in wf.get("nodes", []) if m["id"] < nid]
            if all(s in done for s in smaller):
                result.append(nid)
    return sorted(result)
