# -*- coding: utf-8 -*-
"""资产登记一致性检查核心（纯函数）

迁移自旧版 .opencode/plugin/charter-gate.ts L56-78（resolveResourceMapPath）
与 L148-158（tool.execute.after 资产检查），缺陷修复对照（20260815任务1 · H6）：
- 旧版实现丢失于新版 harness 体系，本模块以纯函数形式回归。

对外契约：
- resolve_resource_map_path(project_dir) -> Path：
  优先读 <project_dir>/.opencode/.harness-env 的 HARNESS_DIR 字段 →
  宿主 docs/资源地图.md；.harness-env 缺失 / HARNESS_DIR 字段缺失 /
  宿主资源地图不存在 → 回退 <project_dir>/docs/资源地图.md。
- check_registered(file_path, map_path) -> (bool, reason)：
  仅对 docs/hetu-*/ 前缀路径生效；目标文件 basename 是否出现在资源地图文本中
  （旧版 includes(basename) 语义）；非目标路径直接通过（不检查）。
"""

import re
from pathlib import Path
from typing import Tuple

# docs/hetu-<项目名>/ 前缀（旧版正则 docs\/hetu-[^/]+\/，兼容 / 与 \ 分隔符）
_HETU_DOCS_RE = re.compile(r"docs[/\\]hetu-[^/\\]+[/\\]")

# .harness-env 的 HARNESS_DIR 字段
_HARNESS_ENV_FILENAME = ".harness-env"
_HARNESS_ENV_PATH = Path(".opencode") / _HARNESS_ENV_FILENAME
_RESOURCE_MAP_FILENAME = "资源地图.md"


def resolve_resource_map_path(project_dir) -> Path:
    """解析资产登记检查用的资源地图路径（宿主优先，缺失回退当前项目）。

    Args:
        project_dir: 当前业务项目目录（str 或 Path）。

    Returns:
        资源地图绝对路径（<宿主>/docs/资源地图.md 或 <项目>/docs/资源地图.md）。
    """
    project = Path(project_dir)
    env_path = project / _HARNESS_ENV_PATH
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            idx = line.find("=")
            if idx <= 0:
                continue
            key = line[:idx].strip()
            if key != "HARNESS_DIR":
                continue
            value = line[idx + 1:].strip()
            # 兼容引号包裹的值（路径含空格场景）
            if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            if not value:
                continue
            host_map = Path(value) / "docs" / _RESOURCE_MAP_FILENAME
            if host_map.is_file():
                return host_map
            break  # HARNESS_DIR 已解析但宿主资源地图不存在 → 回退
    return project / "docs" / _RESOURCE_MAP_FILENAME


def check_registered(file_path, map_path) -> Tuple[bool, str]:
    """检查目标文件是否已登记资源地图（软告警依据，不阻断）。

    Args:
        file_path: 目标文件路径（write/edit 目标）。
        map_path: 资源地图路径（resolve_resource_map_path 的结果）。

    Returns:
        (是否通过检查, 原因说明)：
        - 非 docs/hetu-*/ 前缀路径 → (True, "非 docs/hetu-*/ 路径，跳过登记检查")
        - 资源地图不存在 → (False, "资源地图不存在: ...")
        - basename 已出现 → (True, "已登记")
        - 未出现 → (False, "未登记：<basename> 未出现在资源地图")
    """
    p = Path(file_path)
    if not _HETU_DOCS_RE.search(str(p)):
        return True, "非 docs/hetu-*/ 路径，跳过登记检查"
    map_file = Path(map_path)
    if not map_file.is_file():
        return False, f"资源地图不存在: {map_file}"
    content = map_file.read_text(encoding="utf-8", errors="replace")
    if p.name in content:
        return True, "已登记"
    return False, f"未登记：{p.name} 未出现在资源地图"
