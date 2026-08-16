# -*- coding: utf-8 -*-
"""密钥脱敏核心（redact_secrets 纯函数）

迁移自旧版 .opencode/plugin/charter-gate.ts L80-96（SECRET_PATTERNS +
redactSecrets），缺陷修复对照（20260815任务1 · H5 脱敏回归）：
- 旧版实现丢失于新版 harness 体系，本模块以纯函数形式回归，
  供 DSH/opencode 插件 chat 消息钩子调用（模式可配）。

内置三类模式（与旧版一致）：
1. sk-<16+ 位字母数字>（OpenAI 系密钥）
2. Bearer <token>（鉴权头）
3. password/passwd/pwd/secret/token/api_key/access_key/access_token = 值
   （忽略大小写，值 ≥8 位非空白）

对外契约：
- redact_secrets(text, patterns=None) -> (redacted_text, hits)
  hits = 全部模式命中次数之和；patterns 为 None 时用内置默认。
- 若 gate_rules.yaml 含可选 secret_patterns 段（harness/core/gate.py 加载），
  调用方可优先传入编译后的自定义模式。
"""

import re
from typing import List, Optional, Tuple

# 内置默认模式（迁移自旧版 SECRET_PATTERNS，语义零改动）
DEFAULT_SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"sk-[a-zA-Z0-9]{16,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9._~+/=-]+"),
    re.compile(
        r"(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access_token)"
        r"\s*[=:]\s*['\"]?[^\s'\"]{8,}",
        re.IGNORECASE,
    ),
]

REDACTED = "[REDACTED]"

# 键值对类模式特征：含 password/passwd/pwd/secret/token/api_key/access_key 等
# 键名词汇（常见于 alternation 写法如 (?:client_secret|apikey)）→ 编译时自动补
# IGNORECASE，与内置默认第 3 类语义一致（REVISE 第1轮修复：yaml 自定义
# secret_patterns 接线；hint 仅检测键名词汇，不要求其后紧跟 '='）
_KV_PATTERN_HINT = re.compile(
    r"password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access_token",
    re.IGNORECASE,
)


def compile_patterns(pattern_strings: List[str]) -> List[re.Pattern]:
    """编译规则文件中的脱敏模式字符串。

    键值对类模式（password/token/api_key/access_key 等 = 值）自动补
    re.IGNORECASE，与内置默认第 3 类行为一致；其余模式按原样编译。

    Args:
        pattern_strings: 正则模式字符串列表（来自 gate_rules.yaml secret_patterns）。

    Returns:
        编译后的模式列表；空输入返回空列表。

    Raises:
        re.error: 任一模式非法。
    """
    patterns: List[re.Pattern] = []
    for p in pattern_strings:
        if _KV_PATTERN_HINT.search(p):
            patterns.append(re.compile(p, re.IGNORECASE))
        else:
            patterns.append(re.compile(p))
    return patterns


def redact_secrets(
    text: str, patterns: Optional[List[re.Pattern]] = None
) -> Tuple[str, int]:
    """扫描并脱敏文本中的疑似明文凭据。

    依次应用每个模式（后一个模式作用于前一个的替换结果），
    命中即替换为 [REDACTED] 并计数。

    Args:
        text: 待扫描文本。
        patterns: 模式列表；None 时用内置默认（与旧版一致）。

    Returns:
        (脱敏后的文本, 命中次数合计)。
    """
    pats = patterns if patterns is not None else DEFAULT_SECRET_PATTERNS
    hits = 0
    out = text
    for pat in pats:
        out, n = pat.subn(REDACTED, out)
        hits += n
    return out, hits
