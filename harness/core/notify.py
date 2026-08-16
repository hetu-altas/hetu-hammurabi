# -*- coding: utf-8 -*-
"""通知唯一出口（钉钉，受门禁管控）

缺陷修复对照（20260814任务1）：
- D4 绕过面：全部通知必须经本出口发送；gate 判定中命中
  harness.core.notify / HARNESS_NOTIFY 标记才放行，curl/requests 直连钉钉被拦。

用法（门禁放行约定，二选一）：
    HARNESS_NOTIFY=1 <venv>/bin/python -m harness.core.notify \
        --run-id <run_id> --project <项目> --title <标题> --text <文本>
    # 或直接：python -m harness.core.notify ...
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def _load_dingtalk_util(aether_dir: Optional[str]):
    """加载 hetu-aether 的 util_dingtalk（延迟导入，避免本模块不可测）。

    Args:
        aether_dir: hetu-aether 项目绝对路径；None 时按相对约定
            （当前文件 ../../../../hetu-aether）尝试定位。

    Returns:
        util_dingtalk 模块；定位失败返回 None。
    """
    candidates = []
    if aether_dir:
        candidates.append(Path(aether_dir) / "utils" / "util_dingtalk.py")
    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "hetu-aether" / "utils" / "util_dingtalk.py")
    candidates.append(here.parents[4] / "hetu-aether" / "utils" / "util_dingtalk.py")
    for c in candidates:
        if c.is_file():
            sys.path.insert(0, str(c.parent))
            import util_dingtalk  # type: ignore
            return util_dingtalk
    return None


def send_markdown(
    title: str,
    text: str,
    run_id: str,
    project: str = "",
    aether_dir: Optional[str] = None,
    config_path: Optional[str] = None,
) -> dict:
    """通过唯一出口发送钉钉 markdown 通知。

    Args:
        title: 通知标题。
        text: markdown 正文。
        run_id: 任务目录名（run_id 契约，写入事件）。
        project: 业务项目名。
        aether_dir: hetu-aether 绝对路径（None 时自动定位）。
        config_path: 钉钉配置路径（None 时用默认）。

    Returns:
        {"ok": bool, "errcode": int|None, "msg": str}。

    Raises:
        RuntimeError: util_dingtalk 定位失败。
    """
    util = _load_dingtalk_util(aether_dir)
    if util is None:
        raise RuntimeError("无法定位 hetu-aether/utils/util_dingtalk.py")

    try:
        config = util.DingTalkConfig.from_config_file(
            Path(config_path) if config_path else None
        )
    except Exception as exc:  # noqa: BLE001 - 配置缺失时给明确错误
        return {"ok": False, "errcode": None, "msg": f"钉钉配置加载失败: {exc}"}

    agent = util.DingTalkAgent(config)
    resp = agent.send_markdown(title=title, text=text)
    # send_markdown 返回钉钉 API 响应 dict（含 errcode）
    errcode = resp.get("errcode") if isinstance(resp, dict) else None
    ok = errcode == 0
    return {"ok": ok, "errcode": errcode, "msg": str(resp) if not ok else "ok"}


def main(argv=None) -> int:
    """命令行入口：python -m harness.core.notify。

    Args:
        argv: 命令行参数（默认 sys.argv[1:]）。

    Returns:
        退出码（0=成功）。
    """
    parser = argparse.ArgumentParser(description="宪章通知唯一出口")
    parser.add_argument("--run-id", required=True, help="任务目录名")
    parser.add_argument("--project", default="", help="业务项目名")
    parser.add_argument("--title", required=True, help="通知标题")
    parser.add_argument("--text", required=True, help="markdown 正文")
    parser.add_argument("--aether-dir", default=None, help="hetu-aether 绝对路径")
    parser.add_argument("--config", default=None, help="钉钉配置 JSON 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args(argv)

    result = send_markdown(
        title=args.title,
        text=args.text,
        run_id=args.run_id,
        project=args.project,
        aether_dir=args.aether_dir,
        config_path=args.config,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"[notify] {result['msg']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
