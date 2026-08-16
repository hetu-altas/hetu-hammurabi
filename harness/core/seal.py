# -*- coding: utf-8 -*-
"""落闸核心（seal-gate / re-seal）：result 解析 + 数字核对 + 签名落盘

缺陷修复对照（20260815任务1 · harness硬约束体系优化）：
- H3 落闸可信：落闸数字不再由命令行透传，改为解析 result 文件自动提取
  并核对（八格式优先、原生格式回退、双格式交叉核对、任一拒绝即整体拒绝）。
- H4 续签机制：re_seal 仅刷新 updated_at 并重签 token，其余字段不变，
  写 runlog 审计事件（event_type=re_seal）。
- H9 并发安全：落盘统一走 flock 独占锁 + 锁内重读比对 updated_at，
  后写者收到「已被并发更新，请重试」；损坏文件拒绝。

对外契约：
- seal_gate / re_seal 内部调用 gate.build_gate_v2 与 gate.compute_gate_token
  （.gate.json v2 契约零改动）。
- 任一 result 文件无法解析/声明失败 → SealError（整体拒绝，fail-closed）。
"""

import fcntl
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from harness.core import gate, recorder

# ---------------------------------------------------------------------------
# 双格式解析模式（H3）
# ---------------------------------------------------------------------------

# ① unit_test 八格式（constitution/unit_test/unit_test.md 定义）
_UNIT_TEST_NUM_RE = {
    "total": re.compile(r"测试总数:\s*(\d+)"),
    "passed": re.compile(r"成功:\s*(\d+)"),
    "failed": re.compile(r"失败:\s*(\d+)"),
    "errors": re.compile(r"错误:\s*(\d+)"),
}
# ② unittest 原生汇总格式
_NATIVE_RAN_RE = re.compile(r"Ran\s+(\d+)\s+tests?")
_NATIVE_FAILED_RE = re.compile(r"FAILED", re.IGNORECASE)
_NATIVE_OK_RE = re.compile(r"^OK$", re.MULTILINE)

# 格式名
FMT_UNIT_TEST = "unit_test_8fmt"
FMT_UNITTEST_NATIVE = "unittest_native"


class SealError(Exception):
    """落闸/续签失败（携带中文原因，fail-closed 拒绝）。"""


# ---------------------------------------------------------------------------
# result 文件解析（H3：双格式 + 交叉核对）
# ---------------------------------------------------------------------------

def parse_unit_test_detail(text: str) -> Optional[Tuple[int, int, int, int]]:
    """解析八格式四数字（测试总数/成功/失败/错误）。

    Args:
        text: result 文件文本。

    Returns:
        四数字全齐 → (total, passed, failed, errors)；任一缺失返回 None。
    """
    nums: List[int] = []
    for key in ("total", "passed", "failed", "errors"):
        m = _UNIT_TEST_NUM_RE[key].search(text)
        if m is None:
            return None
        nums.append(int(m.group(1)))
    return (nums[0], nums[1], nums[2], nums[3])


def parse_unit_test_format(text: str) -> Optional[Tuple[int, int]]:
    """八格式解析（对外简版）。

    Args:
        text: result 文件文本。

    Returns:
        四数字齐全 → (total, passed)；否则 None。
    """
    detail = parse_unit_test_detail(text)
    if detail is None:
        return None
    return (detail[0], detail[1])


def parse_unittest_native_detail(text: str) -> Optional[Tuple[int, str]]:
    """解析 unittest 原生汇总格式。

    OK/FAILED 判定**仅限 "Ran N tests" 行之后的汇总段**（H3 回归修复）：
    unittest -v 输出中反案例测试的 docstring/测试名可能含 "FAILED" 字样
    （如 test_parse_native_format_failed），全文搜索会把真实通过结果误判为
    失败并拒绝落闸；截取汇总段后，正文中的 FAILED/OK 字样不再影响判定。

    Args:
        text: result 文件文本。

    Returns:
        含 "Ran N tests" → (total, status)，status 为 "OK" 或 "FAILED"；
        无 Ran 行返回 None。汇总段缺失/无法判定 → FAILED（fail-closed 拒绝）。
    """
    m = _NATIVE_RAN_RE.search(text)
    if m is None:
        return None
    total = int(m.group(1))
    # 汇总段 = "Ran N tests" 之后的文本（正文中的 FAILED/OK 字样不影响判定）
    tail = text[m.end():]
    if _NATIVE_FAILED_RE.search(tail):
        return (total, "FAILED")
    if _NATIVE_OK_RE.search(tail):
        return (total, "OK")
    return (total, "FAILED")


def parse_unittest_native_format(text: str) -> Optional[Tuple[int, int]]:
    """原生格式解析（对外简版）。

    Args:
        text: result 文件文本。

    Returns:
        命中且 OK → (total, total)；FAILED 或未命中 → None。
    """
    detail = parse_unittest_native_detail(text)
    if detail is None or detail[1] != "OK":
        return None
    return (detail[0], detail[0])


def parse_result_file(path) -> Tuple[int, int, str]:
    """解析单个 result 文件（八格式优先、原生回退、双格式交叉核对）。

    Args:
        path: result 文件路径（str 或 Path）。

    Returns:
        (total, passed, format_name)。

    Raises:
        SealError: 文件缺失、两种格式均无法解析（格式无法识别）、
            双格式交叉核对不一致、八格式声明含失败/错误（与内容不符）。
    """
    p = Path(path)
    if not p.is_file():
        raise SealError(f"result 文件缺失: {path}")
    text = p.read_text(encoding="utf-8", errors="replace")

    eight = parse_unit_test_detail(text)
    native = parse_unittest_native_detail(text)

    # 双格式交叉核对：同时命中且总数不一致 → 拒绝（防伪造，fail-closed）
    if eight is not None and native is not None:
        if eight[0] != native[0]:
            raise SealError(
                f"result 文件双格式交叉核对不一致（八格式 total={eight[0]} "
                f"vs 原生 Ran {native[0]}）: {path}"
            )
        if native[1] != "OK":
            raise SealError(f"result 声明与文件内容不符（{native[1]}）: {path}")
        return (eight[0], eight[1], FMT_UNIT_TEST)

    if eight is not None:
        # 八格式命中：失败+错误>0 → 声明与内容不符，拒绝
        if eight[2] + eight[3] > 0:
            raise SealError(
                f"result 声明与文件内容不符（失败 {eight[2]} / 错误 {eight[3]}）: {path}"
            )
        return (eight[0], eight[1], FMT_UNIT_TEST)

    if native is not None:
        if native[1] != "OK":
            raise SealError(f"result 声明与文件内容不符（{native[1]}）: {path}")
        return (native[0], native[0], FMT_UNITTEST_NATIVE)

    raise SealError(f"result 文件格式无法识别（需八格式或 unittest 原生格式）: {path}")


# ---------------------------------------------------------------------------
# 并发落盘（H9：flock 独占锁 + 锁内重读比对）
# ---------------------------------------------------------------------------

def _read_existing_gate(gate_file: Path) -> Optional[dict]:
    """读取现有 .gate.json（不存在返回 None）。

    Args:
        gate_file: .gate.json 路径。

    Returns:
        解析后的 dict；文件缺失返回 None；JSON 非法返回 None（锁内再判损坏）。
    """
    try:
        with open(gate_file, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def write_gate_locked(
    gate_file: Path, gate_dict: dict, expected_updated_at: Optional[str] = None
) -> None:
    """flock 独占锁落盘 + 锁内重读比对（后写者拒绝，H9）。

    Args:
        gate_file: .gate.json 路径。
        gate_dict: 待落盘的 gate dict。
        expected_updated_at: 落盘前读取的现有 updated_at；None 表示首次落闸
            （锁内已存在文件时视为并发冲突）。

    Raises:
        SealError: 文件损坏（非法 JSON）；已被并发更新（updated_at 与预期不符）。
    """
    gate_file.parent.mkdir(parents=True, exist_ok=True)
    with open(gate_file, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.seek(0)
            existing_text = fh.read()
            if existing_text.strip():
                try:
                    existing = json.loads(existing_text)
                except json.JSONDecodeError:
                    raise SealError(f"gate 文件损坏（非法 JSON）: {gate_file}")
                actual = existing.get("updated_at") if isinstance(existing, dict) else None
                if actual != expected_updated_at:
                    raise SealError("已被并发更新，请重试")
            fh.seek(0)
            fh.truncate()
            fh.write(json.dumps(gate_dict, ensure_ascii=False, indent=2) + "\n")
            fh.flush()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# 落闸 / 续签（H3 / H4）
# ---------------------------------------------------------------------------

def seal_gate(task_dir, run_id: str, result_files, secret: str) -> dict:
    """解析 result 文件并签名落闸（.gate.json v2，H3/H9）。

    Args:
        task_dir: 任务目录路径。
        run_id: 任务目录名（run_id 契约）。
        result_files: result 文件路径列表（任一拒绝即整体拒绝）。
        secret: 宿主密钥。

    Returns:
        落盘的 gate dict。

    Raises:
        SealError: 任一 result 无法解析/声明失败；并发冲突。
    """
    files = [Path(f) for f in result_files]
    if not files:
        raise SealError("未提供任何 result 文件")
    total, passed = 0, 0
    for f in files:
        t, p, _fmt = parse_result_file(f)  # 任一失败抛 SealError（整体拒绝）
        total += t
        passed += p
    gate_dict = gate.build_gate_v2(
        run_id=run_id,
        task_dir=str(task_dir),
        result_files=files,
        total=total,
        passed=passed,
        secret=secret,
    )
    gate_file = Path(task_dir) / gate.GATE_FILENAME
    expected = _read_existing_gate(gate_file)
    write_gate_locked(
        gate_file,
        gate_dict,
        expected_updated_at=expected.get("updated_at") if expected else None,
    )
    return gate_dict


def re_seal(
    task_dir,
    run_id: str,
    secret: str,
    runlog_root=None,
    project: str = "",
    now: Optional[datetime] = None,
) -> dict:
    """续签门禁：仅刷新 updated_at 并重签 token，其余字段不变（H4）。

    前置校验（防续签篡改）：
    1. 现有 .gate.json 存在且可解析（否则拒绝）
    2. schema_version==2 且 run_id 一致（拒绝跨任务续签）
    3. 重读 result_files 并重新核对（result 被改/缺失 → 拒绝）
    4. 解析数字与 .gate.json 的 total/passed 一致（否则拒绝）

    Args:
        task_dir: 任务目录路径。
        run_id: 任务目录名。
        secret: 宿主密钥。
        runlog_root: runlog 根目录；非空时写 re_seal 审计事件。
        project: 业务项目名（审计事件字段）。
        now: 当前时间（测试注入用）。

    Returns:
        续签后的 gate dict（已落盘）。

    Raises:
        SealError: 无闸可续 / schema/run_id 不符 / result 重读不符 / 并发冲突。
    """
    now = now or datetime.now()
    gate_file = Path(task_dir) / gate.GATE_FILENAME
    if not gate_file.is_file():
        raise SealError(f"无 .gate.json 可续签: {gate_file}")
    existing = gate.load_gate(gate_file)
    if existing is None:
        raise SealError(f".gate.json 不可解析（拒绝续签）: {gate_file}")
    if existing.get("schema_version") != gate.GATE_SCHEMA_VERSION:
        raise SealError(
            f"仅支持 schema_version={gate.GATE_SCHEMA_VERSION} 的 .gate.json 续签"
        )
    if existing.get("run_id") != run_id:
        raise SealError(
            f"run_id 不一致（现有 {existing.get('run_id')!r}，要求 {run_id!r}）：拒绝跨任务续签"
        )
    # 重读 result 重新核对（防 result 被改后沿用旧闸）
    result_files = existing.get("result_files") or []
    if not result_files:
        raise SealError("result_files 为空：拒绝续签")
    total, passed = 0, 0
    for f in result_files:
        p = Path(f)
        if not p.is_file():
            raise SealError(f"result 文件缺失: {f}")
        t, p_ok, _fmt = parse_result_file(p)
        total += t
        passed += p_ok
    if total != existing.get("total") or passed != existing.get("passed"):
        raise SealError(
            f"result 重读与 .gate.json 数字不符（result {total}/{passed} "
            f"vs gate {existing.get('total')}/{existing.get('passed')}）：拒绝续签"
        )
    # 仅刷新 updated_at + 重签 token，其余字段原样
    new_gate = dict(existing)
    new_gate["updated_at"] = now.isoformat(timespec="seconds")
    new_gate["gate_token"] = gate.compute_gate_token(new_gate, secret)
    write_gate_locked(
        gate_file, new_gate, expected_updated_at=existing.get("updated_at")
    )
    # 审计事件（re_seal，追加写）
    if runlog_root:
        recorder.record_event(
            runlog_root=runlog_root,
            run_id=run_id,
            node="3",
            node_name="单元测试",
            event_type="re_seal",
            status="pass",
            detail={
                "refreshed": new_gate["updated_at"],
                "total": total,
                "passed": passed,
            },
            project=project,
        )
    return new_gate
