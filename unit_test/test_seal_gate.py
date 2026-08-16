# -*- coding: utf-8 -*-
"""H3 落闸可信回归测试：seal-gate 自动解析 result 核对数字

覆盖：
- 八格式解析（测试总数/成功/失败/错误 四数字）
- unittest 原生格式解析（Ran N tests + OK）
- 数字与 result 不符拒绝（八格式含失败/错误）
- 原生格式 FAILED 拒绝
- 无法解析（任意文本）拒绝（fail-closed）
- 落闸后 .gate.json 的 total/passed 与 result 一致，token 校验通过
- result 文件缺失拒绝
- 混合文件列表「任一拒绝即整体拒绝」
- 双格式交叉核对不一致拒绝
- 真实样例（八格式 + 原生格式共存文件）正常解析
"""

import json
import tempfile
import unittest
from pathlib import Path

from harness.core import gate, seal

SECRET = "test-secret-for-seal"

# 八格式样例（constitution/unit_test/unit_test.md 定义）
EIGHT_FMT_PASS = """\
============================
demo 单元测试结果
============================
测试总数: 20
成功: 20
失败: 0
错误: 0
============================
测试结果: 全部通过
============================
"""
EIGHT_FMT_FAIL = """\
测试总数: 20
成功: 19
失败: 1
错误: 0
"""
# unittest 原生格式样例
NATIVE_FMT_PASS = """\
..........................................................
----------------------------------------------------------------------
Ran 30 tests in 0.123s

OK
"""
NATIVE_FMT_FAIL = """\
.....F...
----------------------------------------------------------------------
Ran 10 tests in 0.051s

FAILED (failures=1)
"""


class TestParseFormats(unittest.TestCase):
    """双格式解析（正常/反例/边界）。"""

    def test_parse_eight_format_pass(self):
        """正常案例：八格式全过 → (total, passed)。"""
        self.assertEqual(seal.parse_unit_test_format(EIGHT_FMT_PASS), (20, 20))

    def test_parse_eight_format_fail_detail(self):
        """反案例：八格式含失败 → detail 可见失败数。"""
        d = seal.parse_unit_test_detail(EIGHT_FMT_FAIL)
        self.assertEqual(d, (20, 19, 1, 0))

    def test_parse_eight_format_missing_number(self):
        """反案例：八格式缺「错误」行 → 无法解析（None）。"""
        text = "测试总数: 5\n成功: 5\n失败: 0\n"
        self.assertIsNone(seal.parse_unit_test_format(text))

    def test_parse_native_format_pass(self):
        """正常案例：原生格式 OK → (total, total)。"""
        self.assertEqual(seal.parse_unittest_native_format(NATIVE_FMT_PASS), (30, 30))

    def test_parse_native_format_failed(self):
        """反案例：原生格式 FAILED → 简版返回 None（拒绝）。"""
        self.assertIsNone(seal.parse_unittest_native_format(NATIVE_FMT_FAIL))
        detail = seal.parse_unittest_native_detail(NATIVE_FMT_FAIL)
        self.assertEqual(detail[1], "FAILED")

    def test_parse_arbitrary_text_none(self):
        """反案例：任意文本 → 两种格式均无法解析。"""
        text = "hello world, nothing here"
        self.assertIsNone(seal.parse_unit_test_format(text))
        self.assertIsNone(seal.parse_unittest_native_format(text))

    def test_parse_native_missing_ran(self):
        """边界：有 OK 但无 Ran 行 → 不识别为原生格式。"""
        self.assertIsNone(seal.parse_unittest_native_detail("everything OK here"))


class TestParseResultFile(unittest.TestCase):
    """parse_result_file 单文件解析（含交叉核对）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_rejected(self):
        """反案例：result 文件缺失 → 拒绝。"""
        with self.assertRaises(seal.SealError):
            seal.parse_result_file(self.tmp / "not_exist.txt")

    def test_eight_format_file(self):
        """正常案例：八格式文件 → (total, passed, 八格式)。"""
        f = self.tmp / "r1.txt"
        f.write_text(EIGHT_FMT_PASS, encoding="utf-8")
        self.assertEqual(seal.parse_result_file(f), (20, 20, seal.FMT_UNIT_TEST))

    def test_native_format_file(self):
        """正常案例：原生格式文件 → (total, total, 原生)。"""
        f = self.tmp / "r2.txt"
        f.write_text(NATIVE_FMT_PASS, encoding="utf-8")
        self.assertEqual(seal.parse_result_file(f), (30, 30, seal.FMT_UNITTEST_NATIVE))

    def test_eight_format_with_failures_rejected(self):
        """反案例：八格式声明含失败 → 拒绝（声明与内容不符）。"""
        f = self.tmp / "r3.txt"
        f.write_text(EIGHT_FMT_FAIL, encoding="utf-8")
        with self.assertRaises(seal.SealError) as ctx:
            seal.parse_result_file(f)
        self.assertIn("不符", str(ctx.exception))

    def test_native_failed_rejected(self):
        """反案例：原生 FAILED → 拒绝。"""
        f = self.tmp / "r4.txt"
        f.write_text(NATIVE_FMT_FAIL, encoding="utf-8")
        with self.assertRaises(seal.SealError):
            seal.parse_result_file(f)

    def test_unrecognized_rejected(self):
        """反案例：任意文本 → 拒绝（格式无法识别，fail-closed）。"""
        f = self.tmp / "r5.txt"
        f.write_text("nothing useful", encoding="utf-8")
        with self.assertRaises(seal.SealError) as ctx:
            seal.parse_result_file(f)
        self.assertIn("无法识别", str(ctx.exception))

    def test_dual_format_consistent(self):
        """正常案例：同一文件同时含八格式与原生格式且一致 → 通过（八格式优先）。"""
        f = self.tmp / "r6.txt"
        f.write_text(
            "Ran 20 tests in 0.01s\n\nOK\n" + EIGHT_FMT_PASS, encoding="utf-8"
        )
        self.assertEqual(seal.parse_result_file(f), (20, 20, seal.FMT_UNIT_TEST))

    def test_dual_format_conflict_rejected(self):
        """反案例：双格式交叉核对不一致（八格式 20 vs 原生 99）→ 拒绝。"""
        f = self.tmp / "r7.txt"
        f.write_text("Ran 99 tests in 0.01s\n\nOK\n" + EIGHT_FMT_PASS, encoding="utf-8")
        with self.assertRaises(seal.SealError) as ctx:
            seal.parse_result_file(f)
        self.assertIn("交叉核对不一致", str(ctx.exception))

    def test_dual_format_body_contains_failed_word(self):
        """边界：正文含 FAILED 字样但汇总 OK → 不应误判拒绝（H3 回归）。

        真实场景：unittest -v 输出中反案例测试的 docstring/测试名可能含
        "FAILED"（如本文件 test_parse_native_format_failed），双格式核对若
        全文搜索 FAILED 字样，会把合法 result 误判为失败并拒绝落闸。
        """
        f = self.tmp / "r8.txt"
        f.write_text(
            "测试总数: 3\n成功: 3\n失败: 0\n错误: 0\n\n"
            "反案例：原生格式 FAILED → 简版返回 None（拒绝）。 ... ok\n"
            "反案例：原生 FAILED → 拒绝。 ... ok\n\n"
            "----------------------------------------------------------------------\n"
            "Ran 3 tests in 0.001s\n\nOK\n",
            encoding="utf-8",
        )
        self.assertEqual(seal.parse_result_file(f), (3, 3, seal.FMT_UNIT_TEST))


class TestSealGate(unittest.TestCase):
    """seal_gate 落闸集成（数字核对 + 落盘一致 + 整体拒绝）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260815" / "20260815任务Z"
        self.task.mkdir(parents=True)
        self.run_id = "20260815任务Z"

    def tearDown(self):
        self._tmp.cleanup()

    def _write_result(self, name: str, text: str) -> Path:
        f = self.task / "unit_test" / "test" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        return f

    def _gate_file(self) -> Path:
        return self.task / gate.GATE_FILENAME

    def test_seal_eight_format(self):
        """正常案例：八格式 result 落闸，total/passed 与 result 一致。"""
        self._write_result("r.txt", EIGHT_FMT_PASS)
        g = seal.seal_gate(self.task, self.run_id, [self.task / "unit_test/test/r.txt"], SECRET)
        self.assertEqual(g["total"], 20)
        self.assertEqual(g["passed"], 20)
        self.assertTrue(g["test_passed"])
        self.assertEqual(g["schema_version"], 2)
        # 落盘内容一致且 token 校验通过（build_gate_v2 契约）
        on_disk = json.loads(self._gate_file().read_text(encoding="utf-8"))
        self.assertEqual(on_disk["total"], 20)
        self.assertTrue(gate.verify_gate_token(on_disk, SECRET))
        opened, code = gate.gate_open(self.task, self.run_id, SECRET)
        self.assertTrue(opened)
        self.assertEqual(code, gate.RC_GATE_PASS)

    def test_seal_multiple_files_sum(self):
        """正常案例：多 result 文件 → total/passed 合计。"""
        self._write_result("a.txt", EIGHT_FMT_PASS)          # 20/20
        self._write_result("b.txt", NATIVE_FMT_PASS)         # 30/30
        g = seal.seal_gate(
            self.task, self.run_id,
            [self.task / "unit_test/test/a.txt", self.task / "unit_test/test/b.txt"],
            SECRET,
        )
        self.assertEqual(g["total"], 50)
        self.assertEqual(g["passed"], 50)

    def test_seal_failed_result_rejected_no_gate_written(self):
        """反案例：任一 result 含失败 → 整体拒绝，且不落闸。"""
        self._write_result("ok.txt", EIGHT_FMT_PASS)
        self._write_result("bad.txt", EIGHT_FMT_FAIL)
        with self.assertRaises(seal.SealError):
            seal.seal_gate(
                self.task, self.run_id,
                [self.task / "unit_test/test/ok.txt", self.task / "unit_test/test/bad.txt"],
                SECRET,
            )
        self.assertFalse(self._gate_file().exists())

    def test_seal_unrecognized_rejected(self):
        """反案例：无法解析的 result → 拒绝（fail-closed）。"""
        self._write_result("junk.txt", "random content")
        with self.assertRaises(seal.SealError):
            seal.seal_gate(self.task, self.run_id, [self.task / "unit_test/test/junk.txt"], SECRET)

    def test_seal_missing_result_rejected(self):
        """反案例：result 文件缺失 → 拒绝。"""
        with self.assertRaises(seal.SealError):
            seal.seal_gate(self.task, self.run_id, [self.task / "unit_test/test/ghost.txt"], SECRET)

    def test_seal_no_results_rejected(self):
        """反案例：未提供任何 result → 拒绝。"""
        with self.assertRaises(seal.SealError):
            seal.seal_gate(self.task, self.run_id, [], SECRET)

    def test_seal_real_dual_format_sample(self):
        """正常案例：真实样例（test_harness_topology_result.txt 八格式+原生共存）→ 20/20。"""
        sample = (
            Path(__file__).resolve().parent / "test" / "test_harness_topology_result.txt"
        )
        if not sample.is_file():
            self.skipTest("真实样例文件不存在")
        g = seal.seal_gate(self.task, self.run_id, [sample], SECRET)
        self.assertEqual(g["total"], 20)
        self.assertEqual(g["passed"], 20)


if __name__ == "__main__":
    unittest.main()
