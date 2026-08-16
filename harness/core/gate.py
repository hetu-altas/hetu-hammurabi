# -*- coding: utf-8 -*-
"""宪章门禁判定核心（DSH 重构版 · 规则外置升级）

本模块是 charter-gate 的确定性判定核心：纯函数、无 harness 依赖、可独立单元测试。
任何运行时插件（opencode charter-gate.ts / DSH charter-gate 插件）都只做薄适配，
把工具调用参数交给本模块判定，命中即阻断。

缺陷修复对照（20260814任务1）：
- D1 门禁串门：判定只扫描「当前任务目录自身」的 .gate.json，绝不递归扫描全局；
  gate_open 要求 run_id 与当前任务一致。
- D2 自写自验：.gate.json v2 携带 HMAC gate_token（run_id + 测试结果摘要 + 宿主密钥），
  写/验分离——charter-tester 只产 result 文件，编排器核对后落闸；
  任意代理直接伪造 .gate.json 无法通过 token 校验。
- D3 编排冲突：研发流程状态.md 是审计记录，判定为「允许写入」；
  门禁只拦截研发日志与通知类操作。
- D4 绕过面：通知出口按 URL/函数特征检测（覆盖 curl / requests 直发钉钉 webhook），
  仅放行唯一出口 harness.core.notify；危险命令任意位置匹配（非行首）；
  日志文件按「任务目录 + 文件名模式」识别，不依赖单一命名。

优化对照（20260815任务1 · harness硬约束体系优化）：
- H1 规则外置：全部判定规则外置到 <harness>/gate_rules.yaml（危险命令/通知特征/
  日志模式/放行名单/审计文件/新鲜度窗口），按 mtime 检测变更、改配置即生效；
  加载失败/schema 非法 → 回退内置默认并告警（fail-closed，默认值与默认文件一致）。
- H2 绕过面收窄：rm 递归删除变体 5 种（-rf/-fr/-r -f/--recursive --force//bin/rm/\\rm）、
  销毁类命令（shred/unlink/rmdir -r/mv 回收站）、URL 字符类点与变量拼接混淆识别、
  备份声明语义校验（剥离 echo/printf 文本与注释后搜索，销毁判定仍用原始 cmd）。
- H8 日志误伤：日志拦截增加放行名单（log_file.allowlist，精确文件名匹配）。
"""

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

# ---------------------------------------------------------------------------
# 常量（对外契约，零改动）
# ---------------------------------------------------------------------------

GATE_FILENAME = ".gate.json"
GATE_SCHEMA_VERSION = 2
GATE_DEFAULT_MAX_AGE_SECONDS = 600  # token 新鲜度默认值（rules 缺失时兜底）

# 规则文件默认路径：<harness>/gate_rules.yaml
RULES_FILENAME = "gate_rules.yaml"
_default_rules_path = Path(__file__).resolve().parent.parent / RULES_FILENAME

# 返回码（reason code）
RC_GATE_MISSING = "GATE_MISSING"
RC_GATE_SCHEMA = "GATE_SCHEMA"
RC_GATE_RUN_ID_MISMATCH = "GATE_RUN_ID_MISMATCH"
RC_GATE_TOKEN_INVALID = "GATE_TOKEN_INVALID"
RC_GATE_STALE = "GATE_STALE"
RC_GATE_NO_RESULTS = "GATE_NO_RESULTS"
RC_GATE_NOT_PASSED = "GATE_NOT_PASSED"
RC_GATE_PASS = "GATE_PASS"
RC_LOG_BLOCKED = "LOG_WRITE_BLOCKED"
RC_NOTIFY_BLOCKED = "NOTIFY_BLOCKED"
RC_DATA_SAFETY = "DATA_SAFETY_BLOCKED"
RC_OK = "OK"

# ---------------------------------------------------------------------------
# 规则加载器（H1：gate_rules.yaml 外置 + mtime 缓存重载 + fail-closed 回退）
# ---------------------------------------------------------------------------

_rules_cache: Optional[Tuple[int, dict, dict]] = None  # (mtime_ns, rules, compiled)
_rules_load_warning = ""  # 最近一次加载告警（回退原因），供诊断/测试


def _build_default_rules() -> dict:
    """构造内置默认规则（与默认 gate_rules.yaml 行为一致，fail-closed 回退用）。

    Returns:
        与 gate_rules.yaml 相同结构的规则 dict。
    """
    return {
        "schema_version": 1,
        "freshness_seconds": 600,
        "log_file": {
            "main_pattern": "研发日志",
            "ext_pattern": "日志",
            "allowlist": ["数据日志说明.md"],
            "task_dir_pattern": r"opencode_schedule[/\\]\d{8}[/\\][^/\\]+[/\\]",
        },
        "audit_files": ["研发流程状态.md"],
        "notify": {
            "url_patterns": [
                r"oapi\s*[.\[\]]\s*dingtalk\s*[.\[\]]\s*com",
                r"oapi\s*[.\[\]'\"+-]*\s*dingtalk\s*[.\[\]'\"+-]*\s*com",
                r"robot\s*/\s*send",
            ],
            "func_patterns": [
                r"util_dingtalk",
                r"send_markdown|send_text",
                r"HARNESS_NOTIFY",
                r"harness\.core\.notify",
            ],
            "allow_patterns": [
                r"HARNESS_NOTIFY",
                r"harness\.core\.notify",
            ],
        },
        "dangerous_commands": {
            "rm_recursive": (
                r"(?:\brm|/bin/rm|\\rm)\s+"
                r"(?:-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-r\s+-f|--recursive\s+--force|-fr|-rf)\b"
            ),
            "shred": r"\bshred\b",
            "unlink": r"\bunlink\b",
            "rmdir_recursive": r"\brmdir\s+-[a-zA-Z]*r",
            "mv_trash": r"\bmv\b.*(?:回收站|trash)",
            "drop_table": r"\bDROP\s+(TABLE|STABLE)\b",
            "delete_from": r"\bDELETE\s+FROM\b",
            "truncate": r"\bTRUNCATE\b",
            "drop_collection": r"\bdrop_collection\b",
        },
        "backup": {"pattern": "backup|备份", "semantic": "enforce"},
        "secret_patterns": [
            r"sk-[a-zA-Z0-9]{16,}",
            r"Bearer\s+[a-zA-Z0-9._~+/=-]+",
            r"(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access_token)"
            r"\s*[=:]\s*['\"]?[^\s'\"]{8,}",
        ],
    }


def validate_rules(rules) -> Tuple[bool, str]:
    """校验规则 dict 的 schema（必需字段存在且类型正确）。

    Args:
        rules: 待校验的规则 dict。

    Returns:
        (是否合法, 非法原因；合法时原因为空串)。
    """
    if not isinstance(rules, dict):
        return False, "根节点非 dict"
    if rules.get("schema_version") != 1:
        return False, f"schema_version 非法: {rules.get('schema_version')!r}"
    if not isinstance(rules.get("freshness_seconds"), int) or rules["freshness_seconds"] <= 0:
        return False, "freshness_seconds 非法（须为正整数）"
    log_file = rules.get("log_file")
    if not isinstance(log_file, dict):
        return False, "log_file 缺失或非 dict"
    for key in ("main_pattern", "ext_pattern", "task_dir_pattern"):
        if not isinstance(log_file.get(key), str) or not log_file[key]:
            return False, f"log_file.{key} 缺失或非非空字符串"
    if not isinstance(log_file.get("allowlist"), list):
        return False, "log_file.allowlist 缺失或非 list"
    if not isinstance(rules.get("audit_files"), list):
        return False, "audit_files 缺失或非 list"
    notify = rules.get("notify")
    if not isinstance(notify, dict):
        return False, "notify 缺失或非 dict"
    for key in ("url_patterns", "func_patterns", "allow_patterns"):
        if not isinstance(notify.get(key), list) or not all(
            isinstance(p, str) for p in notify[key]
        ):
            return False, f"notify.{key} 缺失或含非字符串项"
    dangerous = rules.get("dangerous_commands")
    if not isinstance(dangerous, dict) or not dangerous:
        return False, "dangerous_commands 缺失或为空"
    for key, pat in dangerous.items():
        if not isinstance(pat, str) or not pat:
            return False, f"dangerous_commands.{key} 非法（须为非空字符串）"
    # backup 段校验必须在 _compile_rules 之前（_compile_rules 会访问 backup.pattern，
    # 缺段/缺字段会导致 KeyError 逃逸，违反 fail-closed——REVISE 第1轮修复）
    backup = rules.get("backup")
    if not isinstance(backup, dict) or not isinstance(backup.get("pattern"), str) \
            or not backup["pattern"]:
        return False, "backup.pattern 缺失或非字符串"
    # 模式须可编译（非法正则视为 schema 非法，fail-closed）；
    # 统一捕获 (re.error, KeyError, TypeError)：缺字段/类型错也不得逃逸
    try:
        _compile_rules(rules)
    except (re.error, KeyError, TypeError) as exc:
        return False, f"规则编译失败: {exc}"
    secret_patterns = rules.get("secret_patterns")
    if secret_patterns is not None and (
        not isinstance(secret_patterns, list)
        or not all(isinstance(p, str) for p in secret_patterns)
    ):
        return False, "secret_patterns 非法（须为字符串 list）"
    return True, ""


def _compile_rules(rules: dict) -> dict:
    """预编译规则中的正则模式（内部结构，供判定函数使用）。

    Args:
        rules: 校验通过的规则 dict。

    Returns:
        编译后结构：含 log_main/log_ext/task_dir/notify/notify_allow/
        dangerous/backup/allowlist/audit_files/freshness_seconds。
    """
    log_file = rules["log_file"]
    notify = rules["notify"]
    dangerous = rules["dangerous_commands"]
    return {
        "log_main": re.compile(log_file["main_pattern"]),
        "log_ext": re.compile(log_file["ext_pattern"]),
        "task_dir": re.compile(log_file["task_dir_pattern"]),
        "allowlist": list(log_file.get("allowlist") or []),
        "audit_files": list(rules["audit_files"]),
        "notify": [
            re.compile(p, re.IGNORECASE)
            for p in list(notify["url_patterns"]) + list(notify["func_patterns"])
        ],
        "notify_allow": [
            re.compile(p, re.IGNORECASE) for p in notify["allow_patterns"]
        ],
        "dangerous": [
            re.compile(p, re.IGNORECASE) for p in dangerous.values()
        ],
        "backup": re.compile(rules["backup"]["pattern"], re.IGNORECASE),
        "freshness_seconds": int(rules["freshness_seconds"]),
    }


def load_rules(rules_path=None) -> dict:
    """加载规则文件；缺失/解析失败/schema 非法 → 回退内置默认并记录告警（fail-closed）。

    Args:
        rules_path: 规则文件路径（str 或 Path），默认 <harness>/gate_rules.yaml。

    Returns:
        规则 dict（加载失败时为内置默认）。
    """
    global _rules_load_warning
    path = Path(rules_path) if rules_path else _default_rules_path
    _rules_load_warning = ""
    if not path.is_file():
        _rules_load_warning = f"规则文件不存在: {path}，回退内置默认（fail-closed）"
        return _build_default_rules()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        _rules_load_warning = f"规则文件解析失败: {exc}，回退内置默认（fail-closed）"
        return _build_default_rules()
    if not isinstance(data, dict):
        _rules_load_warning = "规则文件根节点非法（非 mapping），回退内置默认（fail-closed）"
        return _build_default_rules()
    ok, msg = validate_rules(data)
    if not ok:
        _rules_load_warning = f"规则 schema 非法: {msg}，回退内置默认（fail-closed）"
        return _build_default_rules()
    return data


def get_effective_rules() -> dict:
    """获取生效规则（按文件 mtime 检测变更，变更即重载——改配置不重启即生效）。

    Returns:
        规则 dict。
    """
    global _rules_cache
    path = _default_rules_path
    mtime_ns = path.stat().st_mtime_ns if path.is_file() else -1
    if _rules_cache is None or _rules_cache[0] != mtime_ns:
        rules = load_rules(path)
        compiled = _compile_rules(rules)
        _rules_cache = (mtime_ns, rules, compiled)
    return _rules_cache[1]


def _get_compiled() -> dict:
    """获取编译后的判定结构（内部使用）。"""
    get_effective_rules()
    return _rules_cache[2]


def reset_rules_cache() -> None:
    """清空规则缓存（测试用：注入临时规则文件后强制重载）。"""
    global _rules_cache, _rules_load_warning
    _rules_cache = None
    _rules_load_warning = ""


# ---------------------------------------------------------------------------
# token 信任模型（D2）
# ---------------------------------------------------------------------------

def compute_results_digest(result_files) -> str:
    """计算测试结果文件的摘要（SHA-256）。

    Args:
        result_files: 结果文件路径列表（str 或 Path），文件不存在时跳过。

    Returns:
        全部结果文件内容的 SHA-256 十六进制摘要；无文件时返回空串。
    """
    hasher = hashlib.sha256()
    for f in result_files:
        p = Path(f)
        if not p.is_file():
            continue
        with open(p, "rb") as fh:
            hasher.update(fh.read())
    return hasher.hexdigest()


# token 覆盖的关键声明字段（篡改任一字段都会导致校验失败）
# 独立评审修复（20260814）：updated_at 纳入签名，杜绝"陈旧门禁改时间戳续命"攻击
_TOKEN_CLAIM_FIELDS = (
    "schema_version", "test_passed", "total", "passed", "run_id", "updated_at",
)


def _token_payload(gate: dict) -> str:
    """构造 token 签名的规范化 payload。

    覆盖关键声明字段（schema_version/test_passed/total/passed/run_id）
    与测试结果摘要，防止篡改任一字段后 token 仍有效（D2）。

    Args:
        gate: .gate.json 内容（dict）。

    Returns:
        规范化 payload 字符串。
    """
    run_id = gate.get("run_id", "")
    digest = compute_results_digest(gate.get("result_files") or [])
    claims = {k: gate.get(k) for k in _TOKEN_CLAIM_FIELDS}
    canonical = json.dumps(claims, sort_keys=True, ensure_ascii=False)
    return f"{run_id}::{digest}::{canonical}"


def compute_gate_token(gate: dict, secret: str) -> str:
    """计算 .gate.json v2 的 gate_token（HMAC-SHA256）。

    Args:
        gate: .gate.json 内容（dict）。
        secret: 宿主密钥。

    Returns:
        HMAC-SHA256 十六进制字符串。
    """
    payload = _token_payload(gate).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_gate_token(gate: dict, secret: str) -> bool:
    """校验 .gate.json v2 的 gate_token 是否有效。

    Args:
        gate: .gate.json 内容（dict）。
        secret: 宿主密钥。

    Returns:
        token 有效返回 True；缺失/格式错误/不匹配返回 False。
    """
    token = gate.get("gate_token")
    if not isinstance(token, str) or not token:
        return False
    expected = compute_gate_token(gate, secret)
    return hmac.compare_digest(token, expected)


def build_gate_v2(
    run_id: str,
    task_dir: str,
    result_files,
    total: int,
    passed: int,
    secret: str,
    updated_at: Optional[str] = None,
) -> dict:
    """构造完整的 .gate.json v2（编排器落闸专用，契约不变）。

    Args:
        run_id: 任务目录名（run_id 契约）。
        task_dir: 任务目录路径。
        result_files: 测试结果文件列表（token 签名依据，**不能为空**）。
        total: 测试总数。
        passed: 通过数。
        secret: 宿主密钥。
        updated_at: 落闸时间（ISO 字符串），默认当前时间。

    Returns:
        含 gate_token 的完整 gate dict（调用方负责 json 落盘）。

    Raises:
        ValueError: result_files 为空（零证据落闸被拒绝）。
    """
    if not result_files:
        raise ValueError("result_files 不能为空：零证据落闸被拒绝（GATE_NO_RESULTS）")
    gate: dict = {
        "schema_version": GATE_SCHEMA_VERSION,
        "run_id": run_id,
        "task_dir": task_dir,
        "test_passed": passed >= total > 0,
        "total": total,
        "passed": passed,
        "written_by": "charter-orchestrator",
        "result_files": [str(f) for f in result_files],
        "updated_at": updated_at or datetime.now().isoformat(timespec="seconds"),
    }
    gate["gate_token"] = compute_gate_token(gate, secret)
    return gate


def parse_gate_timestamp(ts) -> Optional[datetime]:
    """解析 .gate.json 的 updated_at 时间戳。

    支持 ISO-8601 与 "%Y-%m-%d %H:%M:%S" 两种格式。

    Args:
        ts: 时间戳字符串。

    Returns:
        解析成功的 datetime（naive，统一为本地时间），失败返回 None。
    """
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        pass
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 门禁文件定位（D1：只认当前任务目录）
# ---------------------------------------------------------------------------

def find_gate_file(task_dir) -> Optional[Path]:
    """在任务目录中定位 .gate.json（只查目录自身，不递归、不跨任务）。

    Args:
        task_dir: 任务目录路径（str 或 Path）。

    Returns:
        .gate.json 路径；不存在返回 None。
    """
    p = Path(task_dir)
    if not p.is_dir():
        return None
    gate_file = p / GATE_FILENAME
    return gate_file if gate_file.is_file() else None


def load_gate(gate_file) -> Optional[dict]:
    """读取并解析 .gate.json。

    Args:
        gate_file: .gate.json 路径（str 或 Path）。

    Returns:
        解析后的 dict；文件缺失或 JSON 非法返回 None。
    """
    try:
        with open(gate_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def gate_open(
    task_dir,
    run_id: str,
    secret: str,
    max_age_seconds: int = GATE_DEFAULT_MAX_AGE_SECONDS,
    now: Optional[datetime] = None,
) -> Tuple[bool, str]:
    """判定门禁是否开启（fail-closed，判定链契约不变）。

    开闸条件（全部满足）：
    1. 任务目录存在 .gate.json（D1：不认其他任务的文件）
    2. schema_version == 2
    3. run_id 与当前任务一致（D1）
    4. test_passed == True
    5. gate_token 校验通过（D2：防伪造）
    6. updated_at 在新鲜度窗口内（防陈旧文件复用）

    Args:
        task_dir: 当前任务目录路径。
        run_id: 当前任务的 run_id（任务目录名）。
        secret: 宿主密钥。
        max_age_seconds: token 新鲜度窗口（秒）。
        now: 当前时间（测试注入用），默认 datetime.now()。

    Returns:
        (是否开闸, 返回码)。任一条件不满足即返回 (False, 原因码)。
    """
    now = now or datetime.now()
    gate_file = find_gate_file(task_dir)
    if gate_file is None:
        return False, RC_GATE_MISSING
    gate_dict = load_gate(gate_file)
    if gate_dict is None:
        return False, RC_GATE_MISSING
    if gate_dict.get("schema_version") != GATE_SCHEMA_VERSION:
        return False, RC_GATE_SCHEMA
    if gate_dict.get("run_id") != run_id:
        return False, RC_GATE_RUN_ID_MISMATCH
    if gate_dict.get("test_passed") is not True:
        return False, RC_GATE_NOT_PASSED
    # 独立评审修复：空结果文件列表 = 零证据放行，拒绝
    if not (gate_dict.get("result_files") or []):
        return False, RC_GATE_NO_RESULTS
    if not verify_gate_token(gate_dict, secret):
        return False, RC_GATE_TOKEN_INVALID
    updated = parse_gate_timestamp(gate_dict.get("updated_at"))
    if updated is None:
        return False, RC_GATE_TOKEN_INVALID
    # 独立评审修复：未来时间戳拒绝（防"改时间续命"）
    if updated > now:
        return False, RC_GATE_STALE
    if now - updated > timedelta(seconds=max_age_seconds):
        return False, RC_GATE_STALE
    return True, RC_GATE_PASS


# ---------------------------------------------------------------------------
# 操作识别（D3 / D4 / H2 / H8）
# ---------------------------------------------------------------------------

def is_log_file_write(file_path: str) -> bool:
    """判定是否为研发日志写入（审计文件/放行名单放行，D3/H8）。

    规则：
    1. 审计记录文件（研发流程状态.md）→ 放行
    2. 放行名单（log_file.allowlist 精确文件名）→ 放行（H8）
    3. 文件名含「研发日志」（任意前缀/变体）→ 拦截
    4. 路径位于任务目录模式（opencode_schedule/YYYYMMDD/<任务目录>/）下、
       以 .md 结尾且文件名含「日志」→ 拦截（覆盖重命名变体）

    Args:
        file_path: 目标文件路径。

    Returns:
        需要拦截（是研发日志写入）返回 True。
    """
    p = Path(file_path)
    name = p.name
    c = _get_compiled()
    if name in c["audit_files"] or name in c["allowlist"]:
        return False
    if c["log_main"].search(name):
        return True
    if c["task_dir"].search(str(p)) and name.endswith(".md") and c["log_ext"].search(name):
        return True
    return False


def is_notify_call(cmd: str) -> bool:
    """判定命令是否包含通知外呼（URL 级 + 函数级特征，含混淆识别）。

    Args:
        cmd: bash 命令文本。

    Returns:
        命中通知特征返回 True。
    """
    c = _get_compiled()
    return any(p.search(cmd) for p in c["notify"])


def is_allowed_notify(cmd: str) -> bool:
    """判定命令是否为受管控的合法通知（唯一出口白名单）。

    Args:
        cmd: bash 命令文本。

    Returns:
        通过唯一出口（harness.core.notify / HARNESS_NOTIFY 标记）返回 True。
    """
    c = _get_compiled()
    return any(p.search(cmd) for p in c["notify_allow"])


def is_destructive(cmd: str) -> bool:
    """判定命令是否包含数据销毁操作（任意位置匹配，D4/H2）。

    Args:
        cmd: bash 命令文本。

    Returns:
        命中危险命令特征返回 True。
    """
    c = _get_compiled()
    return any(p.search(cmd) for p in c["dangerous"])


# 剥离用模式：echo/printf 的引号文本或单词参数、# 注释段
_ECHO_TEXT_PATTERN = re.compile(
    r"\b(?:echo|printf)\s+((?:'[^']*'|\"[^\"]*\"|[^\s;&|#]+)\s*)+"
)
_COMMENT_PATTERN = re.compile(r"#[^\n]*")


def _strip_declaration_noise(cmd: str) -> str:
    """剥离 echo/printf 文本与注释段（仅用于备份声明搜索）。

    注意：数据销毁判定仍用原始 cmd（防「把 rm 写进 echo 文本就绕过」，
    任意位置匹配语义不变）；只有备份声明搜索使用剥离后文本（H2d）。

    Args:
        cmd: bash 命令文本。

    Returns:
        剥离后的命令文本。
    """
    text = _ECHO_TEXT_PATTERN.sub("", cmd)
    text = _COMMENT_PATTERN.sub("", text)
    return text


def has_backup_declaration(cmd: str) -> bool:
    """判定命令是否显式声明备份（语义校验：剥离 echo/printf/注释后搜索）。

    Args:
        cmd: bash 命令文本。

    Returns:
        剥离后文本包含 backup/备份 返回 True。
    """
    c = _get_compiled()
    return c["backup"].search(_strip_declaration_noise(cmd)) is not None


# ---------------------------------------------------------------------------
# 统一判定入口
# ---------------------------------------------------------------------------

def decide(
    file_path: str,
    cmd: str,
    task_dir,
    run_id: str,
    secret: str,
    max_age_seconds: int = GATE_DEFAULT_MAX_AGE_SECONDS,
    now: Optional[datetime] = None,
) -> dict:
    """门禁统一判定入口（供插件与测试调用，签名契约不变）。

    判定顺序：
    1. 研发日志写入 / 通知外呼 → 要求门禁开启（gate_open），
       未开启即阻断；开启则放行（通知需命中唯一出口白名单，D4）
    2. 数据销毁操作 → 要求显式备份声明（剥离 echo/printf/注释后搜索），否则阻断

    Args:
        file_path: 工具调用的目标文件路径（写入类操作），无则传 ""。
        cmd: bash 命令文本，无则传 ""。
        task_dir: 当前任务目录路径。
        run_id: 当前任务 run_id（任务目录名）。
        secret: 宿主密钥。
        max_age_seconds: 门禁新鲜度窗口（秒）；未显式指定时取 rules.freshness_seconds。
        now: 当前时间（测试注入用）。

    Returns:
        判定结果 dict：
        {
            "blocked": bool,      # True=应阻断
            "code": str,          # 返回码
            "reason": str,        # 中文原因说明
            "event_type": str,    # 事件类型（gate_block / gate_pass / 其他）
        }
    """
    # 新鲜度窗口：rules 外置值优先（H1）；调用方显式指定时以调用方为准
    effective_age = get_effective_rules()["freshness_seconds"]
    if max_age_seconds != GATE_DEFAULT_MAX_AGE_SECONDS:
        effective_age = max_age_seconds

    # ---- 1. 研发日志写入（D3/D4/H8）----
    if is_log_file_write(file_path):
        opened, code = gate_open(task_dir, run_id, secret, effective_age, now)
        if not opened:
            return {
                "blocked": True,
                "code": RC_LOG_BLOCKED,
                "reason": f"测试门禁未通过（{code}）：禁止写入研发日志",
                "event_type": "gate_block",
            }
        return {"blocked": False, "code": RC_OK, "reason": "", "event_type": "gate_pass"}

    # ---- 2. 通知外呼（D4：唯一出口白名单）----
    if is_notify_call(cmd):
        if not is_allowed_notify(cmd):
            return {
                "blocked": True,
                "code": RC_NOTIFY_BLOCKED,
                "reason": "通知必须通过唯一出口 harness.core.notify（HARNESS_NOTIFY），禁止直连钉钉",
                "event_type": "gate_block",
            }
        opened, code = gate_open(task_dir, run_id, secret, effective_age, now)
        if not opened:
            return {
                "blocked": True,
                "code": RC_NOTIFY_BLOCKED,
                "reason": f"测试门禁未通过（{code}）：禁止发送通知",
                "event_type": "gate_block",
            }
        return {"blocked": False, "code": RC_OK, "reason": "", "event_type": "gate_pass"}

    # ---- 3. 数据销毁（D4：任意位置匹配 + 备份语义放行，H2d）----
    if is_destructive(cmd):
        if not has_backup_declaration(cmd):
            return {
                "blocked": True,
                "code": RC_DATA_SAFETY,
                "reason": "数据销毁操作必须显式带 backup/备份 参数（真实备份动作，非 echo 文本/注释），禁止无备份删除",
                "event_type": "gate_block",
            }
        return {"blocked": False, "code": RC_OK, "reason": "", "event_type": "gate_pass"}

    # ---- 4. 其他操作放行 ----
    return {"blocked": False, "code": RC_OK, "reason": "", "event_type": "gate_pass"}
