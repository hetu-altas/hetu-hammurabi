# -*- coding: utf-8 -*-
"""harness.core 命令行入口

供运行时插件（DSH charter-gate.ts / opencode charter-gate.ts）与手工运维
以子进程方式调用门禁判定与事件记录，保证判定逻辑唯一（核心在 Python，
插件只做薄适配）。

用法：
    python -m harness.core.cli decide \
        --task-dir <任务目录> --run-id <任务目录名> \
        --file <目标文件路径> --cmd <bash 命令> \
        [--secret-file <密钥文件>] [--json]

    python -m harness.core.cli record \
        --runlog <runlog 根> --run-id <任务目录名> --node 3 --node-name 单元测试 \
        --event node_end --status pass [--project hetu-thoth] [--round 1] \
        [--msg 说明] [--file 相关文件]

    python -m harness.core.cli seal-gate \
        --task-dir <任务目录> --run-id <任务目录名> \
        --results <result 文件...> --secret-file <密钥文件> [--json]
        # 编排器落闸专用：自动解析 result 核对数字后签名落盘（写/验分离）
        # （20260815任务1：删除 --total/--passed，数字以 result 解析值为准）

    python -m harness.core.cli re-seal \
        --task-dir <任务目录> --run-id <任务目录名> \
        --secret-file <密钥文件> [--runlog <runlog 根>] [--project <项目>] [--json]
        # 续签：仅刷新 updated_at 重签 token，其余字段不变（H4）

    python -m harness.core.cli rotate-secret \
        --secret-file <密钥文件> [--force]
        # 轮换密钥：旧闸 token 自然失效（H7）
"""

import argparse
import json
import sys
from pathlib import Path

from harness.core import assets_check, gate, recorder, redact, seal, secret


def _load_secret(secret_file) -> str:
    """加载宿主门禁密钥（委托 secret.load_secret 统一实现）。

    Args:
        secret_file: 密钥文件路径（内容为首行字符串）。

    Returns:
        密钥字符串。

    Raises:
        ValueError: 文件不存在或为空。
    """
    return secret.load_secret(secret_file)


def cmd_decide(args) -> int:
    """decide 子命令：门禁判定。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=放行，1=拦截）。
    """
    try:
        secret = _load_secret(args.secret_file)
    except ValueError as exc:
        print(json.dumps({"blocked": True, "code": "SECRET_MISSING", "reason": str(exc),
                          "event_type": "gate_block"}, ensure_ascii=False))
        return 1
    result = gate.decide(
        file_path=args.file or "",
        cmd=args.cmd or "",
        task_dir=args.task_dir,
        run_id=args.run_id,
        secret=secret,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("BLOCKED" if result["blocked"] else "ALLOWED", result["code"])
    return 1 if result["blocked"] else 0


def cmd_record(args) -> int:
    """record 子命令：记录运行事件。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=成功）。
    """
    detail = {}
    if args.msg:
        detail["msg"] = args.msg
    if args.file:
        detail["file"] = args.file
    try:
        recorder.record_event(
            runlog_root=args.runlog,
            run_id=args.run_id,
            node=args.node,
            node_name=args.node_name,
            event_type=args.event,
            status=args.status,
            project=args.project or "",
            round_=args.round,
            detail=detail,
        )
        return 0
    except ValueError as exc:
        print(f"[record] 失败: {exc}", file=sys.stderr)
        return 1


def cmd_seal_gate(args) -> int:
    """seal-gate 子命令：编排器落闸（解析 result 自动核对后签名写入 .gate.json v2）。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=成功，1=失败）。
    """
    try:
        secret_key = _load_secret(args.secret_file)
        g = seal.seal_gate(
            task_dir=args.task_dir,
            run_id=args.run_id,
            result_files=args.results,
            secret=secret_key,
        )
    except (ValueError, seal.SealError) as exc:
        print(json.dumps({"ok": False, "msg": str(exc)}, ensure_ascii=False))
        return 1
    gate_file = Path(args.task_dir) / gate.GATE_FILENAME
    if args.json:
        print(json.dumps({"ok": True, "gate_file": str(gate_file), "test_passed": g["test_passed"]},
                         ensure_ascii=False))
    else:
        print(f"[seal-gate] 已落闸 {gate_file}（test_passed={g['test_passed']}）")
    return 0


def cmd_re_seal(args) -> int:
    """re-seal 子命令：续签门禁（仅刷新 updated_at 并重签 token，其余字段不变）。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=成功，1=失败）。
    """
    try:
        secret_key = _load_secret(args.secret_file)
        g = seal.re_seal(
            task_dir=args.task_dir,
            run_id=args.run_id,
            secret=secret_key,
            runlog_root=args.runlog or None,
            project=args.project or "",
        )
    except (ValueError, seal.SealError) as exc:
        print(json.dumps({"ok": False, "msg": str(exc)}, ensure_ascii=False))
        return 1
    gate_file = Path(args.task_dir) / gate.GATE_FILENAME
    if args.json:
        print(json.dumps({"ok": True, "gate_file": str(gate_file), "updated_at": g["updated_at"]},
                         ensure_ascii=False))
    else:
        print(f"[re-seal] 已续签 {gate_file}（updated_at={g['updated_at']}）")
    return 0


def cmd_rotate_secret(args) -> int:
    """rotate-secret 子命令：轮换门禁密钥（旧闸 token 自然失效）。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=成功，1=失败）。
    """
    try:
        path = secret.rotate_secret(args.secret_file, force=args.force)
    except (ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "msg": str(exc)}, ensure_ascii=False))
        return 1
    ok, mode = secret.check_permission(path)
    if args.json:
        print(json.dumps({"ok": True, "secret_file": str(path), "mode": oct(mode)}, ensure_ascii=False))
    else:
        print(f"[rotate-secret] 已轮换密钥 {path}（权限 {oct(mode)}；旧闸 token 自然失效）")
    return 0


def cmd_redact(args) -> int:
    """redact 子命令：扫描文本中的疑似明文凭据并脱敏（插件 chat 钩子调用）。

    模式来源（REVISE 第1轮修复：secret_patterns 接线）：
    gate_rules.yaml 的 secret_patterns 段优先（经 gate.get_effective_rules 读取，
    键值对类自动补 IGNORECASE）；缺省时用内置默认三类。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=成功）。
    """
    pattern_strings = gate.get_effective_rules().get("secret_patterns")
    if pattern_strings:
        patterns = redact.compile_patterns(pattern_strings)
        text, hits = redact.redact_secrets(args.text, patterns)
    else:
        text, hits = redact.redact_secrets(args.text)
    if args.json:
        print(json.dumps({"text": text, "hits": hits}, ensure_ascii=False))
    else:
        print(text)
        if hits:
            print(f"[redact] 检测到 {hits} 处疑似明文凭据，已脱敏", file=sys.stderr)
    return 0


def cmd_assets_check(args) -> int:
    """assets-check 子命令：资产登记一致性检查（插件 after 钩子调用，软告警）。

    Args:
        args: 解析后的参数。

    Returns:
        退出码（0=已登记/不适用，1=未登记需告警）。
    """
    map_path = assets_check.resolve_resource_map_path(args.project_dir)
    ok, reason = assets_check.check_registered(args.file, map_path)
    if args.json:
        print(json.dumps({"ok": ok, "reason": reason, "map_path": str(map_path)},
                         ensure_ascii=False))
    else:
        print(f"[assets-check] {'OK' if ok else 'WARN'} {reason}")
    return 0 if ok else 1


def main(argv=None) -> int:
    """命令行入口。

    Args:
        argv: 命令行参数（默认 sys.argv[1:]）。

    Returns:
        退出码。
    """
    parser = argparse.ArgumentParser(prog="harness.core.cli", description="宪章体系核心 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_decide = sub.add_parser("decide", help="门禁判定")
    p_decide.add_argument("--task-dir", required=True, help="任务目录")
    p_decide.add_argument("--run-id", required=True, help="任务目录名（run_id 契约）")
    p_decide.add_argument("--file", default="", help="目标文件路径（写入类操作）")
    p_decide.add_argument("--cmd", default="", help="bash 命令文本")
    p_decide.add_argument("--secret-file", required=True, help="门禁密钥文件")
    p_decide.add_argument("--json", action="store_true", help="输出 JSON")
    p_decide.set_defaults(func=cmd_decide)

    p_record = sub.add_parser("record", help="记录运行事件")
    p_record.add_argument("--runlog", required=True, help="runlog 根目录")
    p_record.add_argument("--run-id", required=True, help="任务目录名")
    p_record.add_argument("--node", required=True, help="节点 id")
    p_record.add_argument("--node-name", required=True, help="节点名称")
    p_record.add_argument("--event", required=True, help="事件类型")
    p_record.add_argument("--status", required=True, help="状态")
    p_record.add_argument("--project", default="", help="业务项目名")
    p_record.add_argument("--round", type=int, default=1, help="轮次")
    p_record.add_argument("--msg", default="", help="说明")
    p_record.add_argument("--file", default="", help="相关文件")
    p_record.set_defaults(func=cmd_record)

    p_seal = sub.add_parser("seal-gate", help="编排器落闸（自动解析 result 核对数字）")
    p_seal.add_argument("--task-dir", required=True, help="任务目录")
    p_seal.add_argument("--run-id", required=True, help="任务目录名")
    p_seal.add_argument("--results", nargs="+", required=True, help="result 文件列表")
    p_seal.add_argument("--secret-file", required=True, help="门禁密钥文件")
    p_seal.add_argument("--json", action="store_true", help="输出 JSON")
    p_seal.set_defaults(func=cmd_seal_gate)

    p_reseal = sub.add_parser("re-seal", help="续签门禁（刷新 updated_at 重签 token）")
    p_reseal.add_argument("--task-dir", required=True, help="任务目录")
    p_reseal.add_argument("--run-id", required=True, help="任务目录名")
    p_reseal.add_argument("--secret-file", required=True, help="门禁密钥文件")
    p_reseal.add_argument("--runlog", default="", help="runlog 根目录（写 re_seal 审计事件）")
    p_reseal.add_argument("--project", default="", help="业务项目名")
    p_reseal.add_argument("--json", action="store_true", help="输出 JSON")
    p_reseal.set_defaults(func=cmd_re_seal)

    p_rotate = sub.add_parser("rotate-secret", help="轮换门禁密钥（旧闸自然失效）")
    p_rotate.add_argument("--secret-file", required=True, help="门禁密钥文件")
    p_rotate.add_argument("--force", action="store_true", help="跳过权限前置检查")
    p_rotate.add_argument("--json", action="store_true", help="输出 JSON")
    p_rotate.set_defaults(func=cmd_rotate_secret)

    p_redact = sub.add_parser("redact", help="脱敏文本中的明文凭据（插件 chat 钩子用）")
    p_redact.add_argument("--text", required=True, help="待扫描文本")
    p_redact.add_argument("--json", action="store_true", help="输出 JSON")
    p_redact.set_defaults(func=cmd_redact)

    p_assets = sub.add_parser("assets-check", help="资产登记一致性检查（插件 after 钩子用）")
    p_assets.add_argument("--project-dir", required=True, help="当前业务项目目录")
    p_assets.add_argument("--file", required=True, help="目标文件路径")
    p_assets.add_argument("--json", action="store_true", help="输出 JSON")
    p_assets.set_defaults(func=cmd_assets_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
