# -*- coding: utf-8 -*-
"""通知唯一出口回归测试（notify.py）

覆盖：正确调用 util_dingtalk 的 DingTalkAgent.send_markdown 形态、
配置缺失降级、返回码透传（errcode）。
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness.core import notify


class FakeDingTalkModule:
    """模拟 util_dingtalk 模块。"""

    class DingTalkConfig:
        @classmethod
        def from_config_file(cls, config_path=None):
            return cls()

    class DingTalkAgent:
        def __init__(self, config=None):
            self.config = config
            self.calls = []

        def send_markdown(self, title, text):
            self.calls.append((title, text))
            return {"errcode": 0, "errmsg": "ok"}


class TestNotifyExit(unittest.TestCase):
    """通知唯一出口（D4）。"""

    def test_send_markdown_success(self):
        """成功路径：errcode=0 → ok=True。"""
        fake = FakeDingTalkModule()
        with mock.patch.object(notify, "_load_dingtalk_util", return_value=fake):
            result = notify.send_markdown(title="T", text="X", run_id="R1")
        self.assertTrue(result["ok"])
        self.assertEqual(result["errcode"], 0)

    def test_agent_call_shape(self):
        """调用形态：DingTalkAgent(config).send_markdown(title, text)。"""
        fake = FakeDingTalkModule()
        agent = fake.DingTalkAgent()
        with mock.patch.object(fake, "DingTalkAgent", return_value=agent):
            with mock.patch.object(notify, "_load_dingtalk_util", return_value=fake):
                notify.send_markdown(title="标题", text="正文", run_id="R1")
        self.assertEqual(agent.calls, [("标题", "正文")])

    def test_config_missing_degraded(self):
        """配置缺失 → 降级为 ok=False + 明确 msg，不抛异常。"""
        fake = FakeDingTalkModule()
        with mock.patch.object(
            fake.DingTalkConfig, "from_config_file",
            side_effect=FileNotFoundError("no config"),
        ):
            with mock.patch.object(notify, "_load_dingtalk_util", return_value=fake):
                result = notify.send_markdown(title="T", text="X", run_id="R1")
        self.assertFalse(result["ok"])
        self.assertIn("配置加载失败", result["msg"])

    def test_util_missing_raises(self):
        """util_dingtalk 定位失败 → RuntimeError。"""
        with mock.patch.object(notify, "_load_dingtalk_util", return_value=None):
            with self.assertRaises(RuntimeError):
                notify.send_markdown(title="T", text="X", run_id="R1")

    def test_errcode_nonzero_reported(self):
        """钉钉返回非 0 errcode → ok=False 且透传。"""
        fake = FakeDingTalkModule()

        class _Agent(fake.DingTalkAgent):
            def send_markdown(self, title, text):
                return {"errcode": 310000, "errmsg": "keywords not in content"}

        with mock.patch.object(fake, "DingTalkAgent", _Agent):
            with mock.patch.object(notify, "_load_dingtalk_util", return_value=fake):
                result = notify.send_markdown(title="T", text="X", run_id="R1")
        self.assertFalse(result["ok"])
        self.assertEqual(result["errcode"], 310000)


if __name__ == "__main__":
    unittest.main()
