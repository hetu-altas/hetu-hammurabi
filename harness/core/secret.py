# -*- coding: utf-8 -*-
"""门禁密钥管理：权限校验（600 强制）/ 加载 / 轮换（rotate-secret）

缺陷修复对照（20260815任务1 · harness硬约束体系优化）：
- H7 密钥管理薄弱：conf/gate_secret 权限 777、无轮换机制。
  本模块提供：
  1. check_permission：600 强制校验（decide/seal 路径告警用）
  2. load_secret：读取密钥；enforce_600=True 时权限非 600 自动修正后重读
  3. rotate_secret：openssl rand -hex 32（回退 /dev/urandom 同 install_dsh.sh
     L56-60 逻辑）→ 原子写入（临时文件 + rename，防半写损坏）→ chmod 600；
     轮换后旧闸 token（旧密钥 HMAC）自然失效。
"""

import os
import secrets
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def check_permission(secret_file) -> Tuple[bool, int]:
    """检查密钥文件权限是否为 600（强制）。

    Args:
        secret_file: 密钥文件路径（str 或 Path）。

    Returns:
        (是否 600, 当前权限八进制；文件不存在时 (False, 0))。
    """
    p = Path(secret_file)
    if not p.is_file():
        return False, 0
    mode = p.stat().st_mode & 0o777
    return mode == 0o600, mode


def load_secret(secret_file, enforce_600: bool = False) -> str:
    """加载宿主门禁密钥。

    Args:
        secret_file: 密钥文件路径（内容为首行字符串）。
        enforce_600: True 时权限非 600 自动 chmod 600 后重读（rotate 路径）。

    Returns:
        密钥字符串。

    Raises:
        ValueError: 文件不存在或为空。
    """
    p = Path(secret_file)
    if not p.is_file():
        raise ValueError(f"门禁密钥文件不存在: {p}（请先运行 scripts/install_dsh.sh 生成）")
    if enforce_600:
        ok, _mode = check_permission(p)
        if not ok:
            p.chmod(0o600)
    secret = p.read_text(encoding="utf-8").strip()
    if not secret:
        raise ValueError(f"门禁密钥文件为空: {p}")
    return secret


def _generate_secret() -> str:
    """生成 32 字节随机密钥（openssl rand -hex 32，回退 /dev/urandom 同 install 逻辑）。

    Returns:
        hex 密钥字符串。
    """
    try:
        out = subprocess.run(
            ["openssl", "rand", "-hex", "32"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        token = out.stdout.decode("utf-8").strip()
        if token:
            return token
    except (OSError, subprocess.SubprocessError):
        pass
    # 回退：/dev/urandom 64 字节 → 128 hex（与 install_dsh.sh 回退分支等价）
    return secrets.token_hex(64)


def rotate_secret(secret_file, force: bool = False) -> Path:
    """轮换门禁密钥（原子写入 + chmod 600；旧闸 token 自然失效）。

    Args:
        secret_file: 密钥文件路径。
        force: True 时跳过权限前置检查（权限非 600 也轮换）；
            False 时权限非 600 直接拒绝（提示先修正）。

    Returns:
        密钥文件路径（已更新）。

    Raises:
        ValueError: 权限非 600 且未指定 force；写入失败。
    """
    p = Path(secret_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file() and not force:
        ok, mode = check_permission(p)
        if not ok:
            raise ValueError(
                f"密钥文件权限非 600（当前 {oct(mode)}）：请先 chmod 600 或使用 --force"
            )
    new_secret = _generate_secret() + "\n"
    # 原子写入：临时文件 + rename（防半写损坏），文件权限 600
    tmp = p.with_name(p.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, new_secret.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)
    os.chmod(p, 0o600)
    return p
