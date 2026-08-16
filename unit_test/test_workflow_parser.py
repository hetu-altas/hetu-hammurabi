# -*- coding: utf-8 -*-
"""D5 回归测试：workflow.yaml 流程定义解析与校验

覆盖：真实 workflow.yaml 加载、非法定义报错（重复 id / retry 悬空 /
requires 悬空 / 非法 gate）、节点推进规则（按序 + requires）。
"""

import tempfile
import unittest
from pathlib import Path

from harness.core import workflow

HARNESS_ROOT = Path(__file__).resolve().parents[1] / "harness"
WORKFLOW_PATH = HARNESS_ROOT / "workflow.yaml"


class TestWorkflowParser(unittest.TestCase):
    """workflow.yaml 解析与校验（D5）。"""

    def test_load_real_workflow(self):
        """加载真实 workflow.yaml 且校验通过。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        errors = workflow.validate_workflow(wf)
        self.assertEqual(errors, [])

    def test_node_ids_present(self):
        """节点 -1~7 齐全。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        ids = workflow.sorted_node_ids(wf)
        self.assertEqual(ids, [-1, 0, 1, 2, 3, 4, 5, 6, 7])

    def test_duplicate_id_rejected(self):
        """重复节点 id → 报错。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        wf["nodes"].append(dict(wf["nodes"][0]))
        errors = workflow.validate_workflow(wf)
        self.assertTrue(any("重复" in e for e in errors))

    def test_retry_hanging_rejected(self):
        """retry.to 指向不存在的节点 → 报错。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        for n in wf["nodes"]:
            if n["id"] == 3:
                n["retry"] = {"to": 99, "max_rounds": 3}
        errors = workflow.validate_workflow(wf)
        self.assertTrue(any("retry.to" in e for e in errors))

    def test_requires_hanging_rejected(self):
        """requires 指向不存在的节点 → 报错。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        for n in wf["nodes"]:
            if n["id"] == 5:
                n["requires"] = [99]
        errors = workflow.validate_workflow(wf)
        self.assertTrue(any("requires" in e for e in errors))

    def test_invalid_gate_rejected(self):
        """非法 gate 类型 → 报错。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        for n in wf["nodes"]:
            if n["id"] == 3:
                n["gate"] = "magic"
        errors = workflow.validate_workflow(wf)
        self.assertTrue(any("gate" in e for e in errors))

    def test_invalid_agent_rejected(self):
        """非法 agent 名 → 报错。"""
        wf = workflow.load_workflow(WORKFLOW_PATH)
        for n in wf["nodes"]:
            if n["id"] == 1:
                n["agent"] = "random-agent"
        errors = workflow.validate_workflow(wf)
        self.assertTrue(any("agent" in e for e in errors))

    def test_missing_file_raises(self):
        """文件不存在 → ValueError。"""
        with self.assertRaises(ValueError):
            workflow.load_workflow("/nonexistent/workflow.yaml")

    def test_bad_yaml_raises(self):
        """非法 YAML → ValueError。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.yaml"
            p.write_text("nodes: [unclosed", encoding="utf-8")
            with self.assertRaises(ValueError):
                workflow.load_workflow(p)


class TestWorkflowAdvance(unittest.TestCase):
    """节点推进规则（按序 + requires）。"""

    @classmethod
    def setUpClass(cls):
        cls.wf = workflow.load_workflow(WORKFLOW_PATH)

    def test_first_node_is_minus_one(self):
        """初始可执行节点为 -1（任务书生成）。"""
        allowed = workflow.next_allowed(self.wf, [])
        self.assertEqual(allowed, [-1])

    def test_sequential_advance(self):
        """无 requires 节点按 id 升序推进。"""
        allowed = workflow.next_allowed(self.wf, [-1, 0])
        self.assertEqual(allowed, [1])

    def test_gate_chain(self):
        """节点 3/4 通过后 5/6/7 才可执行（requires 门禁链）。"""
        allowed = workflow.next_allowed(self.wf, [-1, 0, 1, 2, 3, 4])
        self.assertEqual(allowed, [5, 6, 7])

    def test_requires_not_met(self):
        """requires 未满足时不可执行（单测未过不能写日志）。"""
        allowed = workflow.next_allowed(self.wf, [-1, 0, 1, 2, 3])
        self.assertNotIn(5, allowed)
        self.assertNotIn(6, allowed)
        self.assertNotIn(7, allowed)
        self.assertEqual(allowed, [4])

    def test_retry_definition(self):
        """单测节点 retry 回退编码、最多 3 轮（外置定义）。"""
        node3 = workflow.node_by_id(self.wf, 3)
        self.assertEqual(node3["retry"], {"to": 2, "max_rounds": 3})
        node4 = workflow.node_by_id(self.wf, 4)
        self.assertEqual(node4["retry"], {"to": 2, "max_rounds": 2})


if __name__ == "__main__":
    unittest.main()
