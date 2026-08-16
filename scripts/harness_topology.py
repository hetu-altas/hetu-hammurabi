# -*- coding: utf-8 -*-
"""
harness_topology.py - 运行时项目拓扑解析纯函数库

功能说明：
    解析 hetu 系列多项目工作区（同一父目录下部署多个 hetu-* 项目 + 共享 venv）的
    运行时拓扑：harness 宿主判定、安装目标项目发现、公共工具/共享环境路径解析，
    以及 .harness-env 配置文本的生成与解析。

    本模块为**纯函数库**：不做任何文件写入（仅读），输入路径全部参数化，无副作用，
    可被 install_harness.sh 调用，也可被单元测试直接断言。

    .harness-env 字段契约（六字段，均为绝对路径）：
        PROJECT_NAME  当前项目名（目录 basename）
        PROJECT_DIR   当前项目绝对路径
        WORKSPACE_DIR 同父目录（所有 hetu-* 平级项目的根）绝对路径
        HARNESS_DIR   harness 宿主项目绝对路径
        AETHER_DIR    公共工具项目绝对路径（缺省回退：同父目录下 hetu-aether）
        VENV_BIN      共享虚拟环境 python 绝对路径（缺省回退：同父目录下 venv-hetu/bin/python）

    调试入口：
        python scripts/harness_topology.py --dump /path/to/project
        python scripts/harness_topology.py --json detect-host --workspace <dir>
        python scripts/harness_topology.py --json list-targets --workspace <dir> --host <dir> [--extra <name>]
        python scripts/harness_topology.py --build-env --project <dir> --workspace <dir> --host <dir>
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple

# harness 宿主要件（相对路径, 是否目录）：1a/1b 命中其一 + 2 + 3 才可判定为宿主
# 要件1 兼容新旧两套布局：新布局 harness/agents/（DSH 重构版）与旧布局 .opencode/agents/
_HOST_REQUIREMENTS = (
    ("harness/agents", True),              # 要件1a：含 harness/agents/ 目录（新布局）
    (".opencode/agents", True),            # 要件1b：含 .opencode/agents/ 目录（旧布局，兼容）
    ("constitution/constitution.md", False),  # 要件2：含 constitution/constitution.md 文件
    ("docs/资源地图.md", False),          # 要件3：含 docs/资源地图.md 文件
)

_HARNESS_ENV_HEADER = "# 由 install_harness.sh 自动生成，勿手改"


def _requirement_count(project_dir: str) -> int:
    """
    统计指定项目目录满足的宿主要件数量（0~4，1a/1b 各计 1）

    Args:
        project_dir: 候选项目绝对路径

    Returns:
        int: 要件命中数
    """
    count = 0
    for rel, is_dir in _HOST_REQUIREMENTS:
        if is_dir:
            if os.path.isdir(os.path.join(project_dir, rel)):
                count += 1
        elif os.path.isfile(os.path.join(project_dir, rel)):
            count += 1
    return count


def detect_host_dir(workspace_dir: str) -> str:
    """
    在工作区（同父目录）中判定 harness 宿主项目

    判定条件：目录名以 hetu- 为前缀（必须为目录），且同时含
    harness/agents/ 或 .opencode/agents/（目录）、constitution/constitution.md（文件）、
    docs/资源地图.md（文件）要件（1a/1b 命中其一即可，兼容新旧布局）。
    多个命中时取要件命中数最多者（新旧布局齐全者优先），
    要件数同级时按目录名升序取第一个（保证确定性输出）。

    Args:
        workspace_dir: 同父目录（所有 hetu-* 平级项目的根）

    Returns:
        str: 宿主项目绝对路径

    Raises:
        ValueError: 未找到满足要件的宿主时抛出，异常信息含候选目录列表
    """
    workspace_dir = os.path.abspath(workspace_dir)
    candidates: List[Tuple[int, str, str]] = []
    for entry in sorted(os.listdir(workspace_dir)):
        if not entry.startswith("hetu-"):
            continue
        cand = os.path.join(workspace_dir, entry)
        if not os.path.isdir(cand):
            continue
        count = _requirement_count(cand)
        if count > 0:
            candidates.append((count, entry, cand))
    if not candidates:
        raise ValueError(
            f"未找到 harness 宿主（需同时含 .opencode/agents/、"
            f"constitution/constitution.md、docs/资源地图.md）："
            f"workspace={workspace_dir}，候选目录: 无"
        )
    # 要件命中数降序、目录名升序，取第一个（确定性）
    candidates.sort(key=lambda item: (-item[0], item[1]))
    detail = "、".join(
        f"{name}(要件{count}/3)" for count, name, _ in candidates
    )
    top = candidates[0]
    if top[0] < 3:
        raise ValueError(
            f"未找到满足全部要件的 harness 宿主（需同时含 harness/agents/ 或 .opencode/agents/、"
            f"constitution/constitution.md、docs/资源地图.md）："
            f"workspace={workspace_dir}，候选目录: {detail}（要件均不完整）"
        )
    return top[2]


def list_target_projects(
    workspace_dir: str,
    host_dir: str,
    extra: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """
    发现安装目标项目列表

    Args:
        workspace_dir: 同父目录（所有 hetu-* 平级项目的根）
        host_dir: harness 宿主项目路径（将被排除）
        extra: 可选追加指定项目名（支持非 hetu-* 前缀项目）；
               指定的项目不存在时忽略并记入 skipped

    Returns:
        Tuple[List[str], List[str]]:
            targets - 目标项目绝对路径列表（hetu-* 前缀目录且非宿主，按名称排序）
            skipped - extra 指定但未生效的项目名列表（如指向不存在的目录）
    """
    workspace_dir = os.path.abspath(workspace_dir)
    host_dir = os.path.abspath(host_dir)
    targets: List[str] = []
    skipped: List[str] = []
    for entry in sorted(os.listdir(workspace_dir)):
        if not entry.startswith("hetu-"):
            continue
        cand = os.path.join(workspace_dir, entry)
        if not os.path.isdir(cand):
            continue  # hetu-* 命中但为文件（非目录）→ 跳过
        if cand == host_dir:
            continue  # 排除宿主自身
        targets.append(cand)
    if extra:
        extra_path = os.path.abspath(os.path.join(workspace_dir, extra))
        if os.path.isdir(extra_path):
            if extra_path not in targets:
                targets.append(extra_path)
        else:
            skipped.append(extra)
    targets.sort()
    return targets, skipped


def resolve_aether_dir(workspace_dir: str) -> Optional[str]:
    """
    解析公共工具项目路径

    Args:
        workspace_dir: 同父目录（所有 hetu-* 平级项目的根）

    Returns:
        Optional[str]: workspace_dir/hetu-aether 目录存在时返回其绝对路径，否则 None（调用方回退）
    """
    cand = os.path.join(workspace_dir, "hetu-aether")
    if os.path.isdir(cand):
        return os.path.abspath(cand)
    return None


def resolve_venv_bin(workspace_dir: str) -> Optional[str]:
    """
    解析共享虚拟环境 python 路径

    Args:
        workspace_dir: 同父目录（所有 hetu-* 平级项目的根）

    Returns:
        Optional[str]: workspace_dir/venv-hetu/bin/python 存在时返回其绝对路径，否则 None（调用方回退）
    """
    cand = os.path.join(workspace_dir, "venv-hetu", "bin", "python")
    if os.path.isfile(cand):
        return os.path.abspath(cand)
    return None


def _quote_value(value: str) -> str:
    """路径含空格时用双引号包裹，保证 KEY=VALUE 行可被安全解析"""
    return '"' + value + '"' if " " in value else value


def build_env_content(
    project_dir: str,
    workspace_dir: str,
    host_dir: str,
) -> str:
    """
    生成 .harness-env 文本（六字段齐全、绝对路径）

    Args:
        project_dir: 当前项目绝对路径（PROJECT_NAME 取其 basename）
        workspace_dir: 同父目录绝对路径
        host_dir: harness 宿主项目绝对路径

    Returns:
        str: .harness-env 文本，含「自动生成勿手改」头注释；
             AETHER_DIR/VENV_BIN 缺失时写空值并附注释说明（缺省回退约定）
    """
    project_dir = os.path.abspath(project_dir)
    workspace_dir = os.path.abspath(workspace_dir)
    host_dir = os.path.abspath(host_dir)
    aether_dir = resolve_aether_dir(workspace_dir)
    venv_bin = resolve_venv_bin(workspace_dir)

    lines = [_HARNESS_ENV_HEADER]
    lines.append("PROJECT_NAME=" + os.path.basename(project_dir))
    lines.append("PROJECT_DIR=" + _quote_value(project_dir))
    lines.append("WORKSPACE_DIR=" + _quote_value(workspace_dir))
    lines.append("HARNESS_DIR=" + _quote_value(host_dir))
    if aether_dir is not None:
        lines.append("AETHER_DIR=" + _quote_value(aether_dir))
    else:
        lines.append("# AETHER_DIR 缺失（同父目录无 hetu-aether），留空由调用方按回退规则查找")
        lines.append("AETHER_DIR=")
    if venv_bin is not None:
        lines.append("VENV_BIN=" + _quote_value(venv_bin))
    else:
        lines.append("# VENV_BIN 缺失（同父目录无 venv-hetu/bin/python），留空由调用方按回退规则查找")
        lines.append("VENV_BIN=")
    return "\n".join(lines) + "\n"


def parse_env_content(text: str) -> Dict[str, str]:
    """
    解析 .harness-env 文本为字典

    跳过空行与 # 注释行；KEY=VALUE 在首个等号处拆分；支持 KEY="带空格值"（引号剥离）；
    重复键后者覆盖。

    Args:
        text: .harness-env 文本内容

    Returns:
        Dict[str, str]: 字段名 → 字段值
    """
    result: Dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        result[key] = value
    return result


def _cmd_dump(project_dir: str) -> int:
    """--dump 调试入口：输出某项目的拓扑解析结果与 .harness-env 预览"""
    workspace_dir = os.path.dirname(os.path.abspath(project_dir))
    print("=" * 60)
    print(f"项目: {os.path.abspath(project_dir)}")
    print(f"工作区(同父目录): {workspace_dir}")
    print("=" * 60)
    try:
        host_dir = detect_host_dir(workspace_dir)
        print(f"harness 宿主: {host_dir}")
    except ValueError as exc:
        host_dir = ""
        print(f"harness 宿主: <未找到> {exc}")
    targets, skipped = list_target_projects(workspace_dir, host_dir or workspace_dir)
    print(f"安装目标项目: {targets}")
    print(f"跳过(extra 未生效): {skipped}")
    print(f"公共工具项目: {resolve_aether_dir(workspace_dir)}")
    print(f"共享环境 python: {resolve_venv_bin(workspace_dir)}")
    if host_dir:
        print("-" * 60)
        print("build_env_content 预览:")
        print(build_env_content(project_dir, workspace_dir, host_dir))
    return 0


def _parse_kv_args(args: List[str], keys: Tuple[str, ...]) -> Dict[str, str]:
    """解析 --key value 形式的命令行参数"""
    result: Dict[str, str] = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--") and arg[2:] in keys and i + 1 < len(args):
            result[arg[2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    return result


def _cmd_json(args: List[str]) -> int:
    """--json 子命令：输出 JSON 供 install_harness.sh 解析（只读）"""
    if len(args) < 1:
        print('{"error": "json 子命令缺少 action（detect-host / list-targets）"}')
        return 1
    action = args[0]
    kv = _parse_kv_args(args[1:], ("workspace", "host", "extra"))
    workspace_dir = kv.get("workspace", "")
    if not workspace_dir:
        print('{"error": "缺少 --workspace 参数"}')
        return 1
    if action == "detect-host":
        try:
            host_dir = detect_host_dir(workspace_dir)
            print(json.dumps({"host_dir": host_dir}, ensure_ascii=False))
            return 0
        except ValueError as exc:
            print(json.dumps({"host_dir": "", "error": str(exc)}, ensure_ascii=False))
            return 1
    if action == "list-targets":
        host_dir = kv.get("host", "")
        extra = kv.get("extra", "") or None
        targets, skipped = list_target_projects(workspace_dir, host_dir, extra)
        print(json.dumps({"targets": targets, "skipped": skipped}, ensure_ascii=False))
        return 0
    print(f'{{"error": "未知 json action: {action}"}}')
    return 1


def _cmd_build_env(args: List[str]) -> int:
    """--build-env 子命令：输出 .harness-env 文本到 stdout（供脚本重定向）"""
    kv = _parse_kv_args(args, ("project", "workspace", "host"))
    project_dir = kv.get("project", "")
    workspace_dir = kv.get("workspace", "")
    host_dir = kv.get("host", "")
    if not project_dir or not workspace_dir or not host_dir:
        print("错误: --build-env 需要 --project / --workspace / --host 三个参数", file=sys.stderr)
        return 1
    sys.stdout.write(build_env_content(project_dir, workspace_dir, host_dir))
    return 0


_USAGE = (
    "用法:\n"
    "  python scripts/harness_topology.py --dump <项目绝对路径>\n"
    "  python scripts/harness_topology.py --json detect-host --workspace <同父目录>\n"
    "  python scripts/harness_topology.py --json list-targets --workspace <同父目录> --host <宿主> [--extra <项目名>]\n"
    "  python scripts/harness_topology.py --build-env --project <项目> --workspace <同父目录> --host <宿主>\n"
)


def main(argv: Optional[List[str]] = None) -> int:
    """
    命令行入口（兼容 --xxx 与 xxx 两种写法）

    Args:
        argv: 命令行参数列表，默认取 sys.argv[1:]

    Returns:
        int: 进程退出码（0 成功 / 1 失败）
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(_USAGE, file=sys.stderr)
        return 1
    cmd = args[0]
    if cmd in ("--dump", "dump"):
        if len(args) < 2:
            print("错误: --dump 需要项目路径参数", file=sys.stderr)
            return 1
        return _cmd_dump(args[1])
    if cmd in ("--json", "json"):
        return _cmd_json(args[1:])
    if cmd in ("--build-env", "build-env"):
        return _cmd_build_env(args[1:])
    print(_USAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
