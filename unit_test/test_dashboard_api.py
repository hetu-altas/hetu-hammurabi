# -*- coding: utf-8 -*-
"""看板 API 与统计口径测试

用 fixture 事件库 + 历史任务目录验证：
- overview/nodes/gates/tasks/detail 聚合口径
- 历史任务静态解析并入统计（source=history）
- 周期过滤、404 处理
"""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from harness.core import history as history_mod
from harness.core import recorder, stats
from harness.core.api import create_app

LIVE_RUN = "20260814任务X"


def _seed_live_events(runlog_root: Path) -> None:
    """写入 live 事件 fixture（5 节点 start/end + 门禁 block/pass）。"""
    t = datetime(2026, 8, 14, 10, 0, 0)
    seq = [
        (-1, "任务书生成", "node_start", "running", 1),
        (-1, "任务书生成", "node_end", "pass", 1),
        (0, "校验", "node_start", "running", 1),
        (0, "校验", "node_end", "pass", 1),
        (3, "单元测试", "node_start", "running", 1),
        (3, "单元测试", "gate_block", "blocked", 1),
        (3, "单元测试", "gate_pass", "pass", 1),
        (3, "单元测试", "node_end", "pass", 1),
        (5, "研发日志", "node_start", "running", 1),
        (5, "研发日志", "node_end", "pass", 1),
        (6, "资产沉淀", "node_start", "running", 1),
        (6, "资产沉淀", "node_end", "fail", 1),
    ]
    for i, (node, name, etype, status, round_) in enumerate(seq):
        recorder.record_event(
            runlog_root,
            run_id=LIVE_RUN,
            node=node,
            node_name=name,
            event_type=etype,
            status=status,
            project="hetu-hammurabi",
            round_=round_,
            detail={"msg": f"fixture {i}", "file": f"f{i}.md"} if etype == "node_end" else {"msg": f"fixture {i}"},
            ts=t.replace(minute=0, second=i),
        )


def _seed_history_task(schedule_root: Path) -> None:
    """构造历史任务目录（状态文件 + .gate.json v1）。"""
    task_dir = schedule_root / "20260804" / "20260804任务1河图Logo设计"
    task_dir.mkdir(parents=True)
    status_text = (
        "# 研发流程状态\n\n"
        "| 时间 | 节点 | 状态 | 说明 |\n"
        "|------|------|------|------|\n"
        "| 2026-08-04 | -1 任务书生成 | 通过 | 生成任务书 |\n"
        "| 2026-08-04 | 0 校验 | 通过 | 校验通过 |\n"
        "| 2026-08-04 | 1 分析 | 通过 | 实施计划 |\n"
        "| 2026-08-04 | 2 编码 | 通过 | 实现完成 |\n"
        "| 2026-08-04 | 3 单元测试 | 通过 | 20/20 |\n"
        "| 2026-08-04 | 4 代码评审 | 通过 | APPROVE |\n"
        "| 2026-08-04 | 5 研发日志 | 通过 | 日志完成 |\n"
        "| 2026-08-04 | 6 资产沉淀 | 通过 | 沉淀完成 |\n"
        "| 2026-08-04 | 7 通知 | 通过 | 钉钉成功 |\n"
    )
    (task_dir / "研发流程状态.md").write_text(status_text, encoding="utf-8")
    (task_dir / ".gate.json").write_text(
        json.dumps({"test_passed": True, "total": 20, "passed": 20,
                    "updated_at": "2026-08-04 10:00:00"}),
        encoding="utf-8",
    )


class TestStatsCore(unittest.TestCase):
    """聚合统计口径（stats 模块）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.runlog = self.root / "runlog"
        self.schedule = self.root / "opencode_schedule"
        _seed_live_events(self.runlog)
        _seed_history_task(self.schedule)
        self.events = list(recorder.iter_events(self.runlog)) + history_mod.scan_schedule(self.schedule)

    def tearDown(self):
        self._tmp.cleanup()

    def test_overview_metrics(self):
        """总览口径：任务数/运行次数/成功率/门禁拦截率。"""
        ov = stats.overview(self.events)
        self.assertEqual(ov["total_tasks"], 2)  # live 1 + history 1
        # node_start: live 5 + history 9 状态行 start（discover 为元事件不计入）= 14
        self.assertEqual(ov["total_node_runs"], 14)
        # node_end: live 5(4 pass) + history 9(pass) → 13/14
        self.assertAlmostEqual(ov["success_rate"], 13 / 14, places=4)
        # gate: live block1+pass1, history pass1 → 1/3
        self.assertAlmostEqual(ov["gate_block_rate"], 1 / 3, places=4)
        self.assertEqual(ov["gate_block_count"], 1)
        self.assertEqual(ov["gate_pass_count"], 2)

    def test_nodes_stats(self):
        """按节点统计：单元测试节点 2 次运行（live+history）2 次成功。"""
        nodes = stats.nodes_stats(self.events)
        node3 = next(n for n in nodes if n["node"] == "3")
        self.assertEqual(node3["runs"], 2)
        self.assertEqual(node3["success"], 2)
        self.assertEqual(node3["success_rate"], 1.0)

    def test_gates_stats(self):
        """门禁拦截统计：拦截事件含原因明细。"""
        gs = stats.gates_stats(self.events)
        self.assertEqual(gs["count"], 1)
        self.assertEqual(gs["events"][0]["detail"]["msg"], "fixture 5")

    def test_tasks_stats(self):
        """任务列表：live 与 history 并存且标注来源。"""
        tasks = stats.tasks_stats(self.events)
        by_run = {t["run_id"]: t for t in tasks}
        self.assertIn(LIVE_RUN, by_run)
        self.assertIn("20260804任务1河图Logo设计", by_run)
        self.assertEqual(by_run[LIVE_RUN]["source"], "live")
        self.assertEqual(by_run["20260804任务1河图Logo设计"]["source"], "history")

    def test_task_detail(self):
        """任务详情：时间线含门禁链、事件升序。"""
        detail = stats.task_detail(self.events, LIVE_RUN)
        self.assertIsNotNone(detail)
        node3 = next(t for t in detail["timeline"] if t["node"] == "3")
        self.assertEqual(node3["gate"], "gate_pass")
        self.assertEqual(node3["status"], "pass")
        ts_list = [e["ts"] for e in detail["events"]]
        self.assertEqual(ts_list, sorted(ts_list))


    def test_history_running_status_mapped(self):
        """状态文件「进行中」→ 只产出 node_start，不产出 node_end（未完成节点）。"""
        rows = history_mod.parse_status_rows("| 2026-08-14 | 4 代码评审 | 进行中 | 评审中 |")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "进行中")
        with tempfile.TemporaryDirectory() as td:
            task_dir = Path(td) / "20260814任务Y"
            task_dir.mkdir()
            (task_dir / "研发流程状态.md").write_text(
                "| 时间 | 节点 | 状态 | 说明 |\n| 2026-08-14 | 4 代码评审 | 进行中 | 评审中 |",
                encoding="utf-8",
            )
            events = history_mod.parse_task_dir(task_dir, project="hetu-hammurabi")
            starts = [e for e in events if e["event_type"] == "node_start" and e["node"] == "4"]
            ends = [e for e in events if e["event_type"] == "node_end" and e["node"] == "4"]
            self.assertEqual(len(starts), 1)
            self.assertEqual(ends, [])
            # discover 为元事件类型（不参与节点统计）
            discovers = [e for e in events if e["event_type"] == "discover"]
            self.assertEqual(len(discovers), 1)

    def test_status_text_mapping(self):
        """状态列判定：✅ 完成/通过 → pass；🔄 进行中 → running；⏭️ 不适用 → skip。"""
        self.assertEqual(history_mod._map_status_text("✅ 完成"), "pass")
        self.assertEqual(history_mod._map_status_text("通过"), "pass")
        self.assertEqual(history_mod._map_status_text("完成"), "pass")
        self.assertEqual(history_mod._map_status_text("🔄 进行中"), "running")
        self.assertEqual(history_mod._map_status_text("进行中"), "running")
        self.assertEqual(history_mod._map_status_text("⏭️ 不适用"), "skip")
        self.assertEqual(history_mod._map_status_text("失败"), "fail")

    def test_model_status_file_parsed(self):
        """模型（/cc）写的状态文件：✅ 完成 → pass；不适用节点不产出事件。"""
        with tempfile.TemporaryDirectory() as td:
            task_dir = Path(td) / "20260815任务X"
            task_dir.mkdir()
            (task_dir / "研发流程状态.md").write_text(
                "| 时间 | 节点 | 状态 | 说明 |\n"
                "| 2026-08-15 | -1 任务书生成 | ✅ 完成 | 生成任务书 |\n"
                "| 2026-08-15 | 2 编码 | 🔄 进行中 | 编码中 |\n"
                "| 2026-08-15 | 7 通知 | ⏭️ 不适用 | 无需通知 |",
                encoding="utf-8",
            )
            events = history_mod.parse_task_dir(task_dir, project="hetu-mercury")
            ends = {e["node"]: e for e in events if e["event_type"] == "node_end"}
            self.assertEqual(ends["-1"]["status"], "pass")
            self.assertNotIn("2", ends)  # 进行中无 end
            self.assertNotIn("7", ends)  # 不适用无 end

    def test_node_end_dedup(self):
        """同一任务节点多次落闸（seal-gate 重落闸）只计最后一次。"""
        with tempfile.TemporaryDirectory() as td:
            rl = Path(td) / "runlog"
            import datetime
            for i, msg in enumerate(("首次落闸", "重落闸1", "重落闸2")):
                recorder.record_event(
                    rl, "R1", 3, "单元测试", "node_end", "pass",
                    detail={"msg": msg}, project="hetu-x",
                    ts=datetime.datetime(2026, 8, 15, 10, 0, i),
                )
            recorder.record_event(rl, "R1", 3, "单元测试", "node_start", "running",
                                  project="hetu-x",
                                  ts=datetime.datetime(2026, 8, 15, 9, 59, 0))
            ev = list(recorder.iter_events(rl))
            nodes = stats.nodes_stats(ev)
            node3 = next(n for n in nodes if n["node"] == "3")
            self.assertEqual(node3["runs"], 1)
            self.assertEqual(node3["success"], 1)
            self.assertEqual(node3["fail"], 0)
            self.assertEqual(node3["success_rate"], 1.0)

    def test_scan_all_schedule_multi_project(self):
        """全项目扫描：同父目录多个 hetu-* 项目各自统计（project 区分）。"""
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            proj_a = ws / "hetu-alpha" / "opencode_schedule" / "20260801" / "20260801任务1A"
            proj_b = ws / "hetu-beta" / "opencode_schedule" / "20260801" / "20260801任务1B"
            proj_a.mkdir(parents=True)
            proj_b.mkdir(parents=True)
            for d, title in ((proj_a, "A任务"), (proj_b, "B任务")):
                (d / "研发流程状态.md").write_text(
                    f"| 2026-08-01 | 1 分析 | 通过 | {title}完成 |", encoding="utf-8"
                )
            events = history_mod.scan_all_schedule(ws)
            runs = {e["run_id"]: e for e in events if e["event_type"] == "node_end"}
            self.assertEqual(set(runs.keys()), {"20260801任务1A", "20260801任务1B"})
            self.assertEqual(runs["20260801任务1A"]["project"], "hetu-alpha")
            self.assertEqual(runs["20260801任务1B"]["project"], "hetu-beta")

    def test_scan_all_filters_non_task_dirs(self):
        """空日期目录/备份目录（无任务书/状态文件/gate）不产生假任务。"""
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            proj = ws / "hetu-mercury"
            empty_day = proj / "opencode_schedule" / "20260507" / "bak"
            empty_day.mkdir(parents=True)
            events = history_mod.scan_all_schedule(ws)
            self.assertEqual(events, [])

    def test_is_charter_task_dir(self):
        """任务目录判定：状态文件/同名任务书/gate 任一命中即真任务。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "任务A"; a.mkdir()
            (a / "研发流程状态.md").write_text("x", encoding="utf-8")
            self.assertTrue(history_mod.is_charter_task_dir(a))
            b = root / "任务B"; b.mkdir()
            (b / "任务B.md").write_text("x", encoding="utf-8")
            self.assertTrue(history_mod.is_charter_task_dir(b))
            c = root / "任务C"; c.mkdir()
            (c / ".gate.json").write_text("{}", encoding="utf-8")
            self.assertTrue(history_mod.is_charter_task_dir(c))
            d = root / "bak"; d.mkdir()
            (d / "notes.txt").write_text("x", encoding="utf-8")
            self.assertFalse(history_mod.is_charter_task_dir(d))


    def test_task_detail_missing(self):
        """不存在的任务 → None。"""
        self.assertIsNone(stats.task_detail(self.events, "nope"))

    def test_engine_benchmark(self):
        """引擎对比：DSH（20260815 前缀）与 opencode 分组、剔除规则、比率。"""
        import datetime as _dt
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            # DSH 任务（20260815 前缀，runlog 事件）
            rl = ws / "runlog"
            recorder.record_event(rl, "20260815任务A", -1, "任务书生成", "node_start", "running",
                                  project="hetu-x", ts=_dt.datetime(2026, 8, 15, 10, 0))
            recorder.record_event(rl, "20260815任务A", 7, "通知", "node_end", "pass",
                                  project="hetu-x", ts=_dt.datetime(2026, 8, 15, 10, 10))
            # opencode 任务（状态文件）
            oc_dir = ws / "hetu-y" / "opencode_schedule" / "20260801" / "20260801任务B"
            oc_dir.mkdir(parents=True)
            (oc_dir / "研发流程状态.md").write_text(
                "| 2026-08-01 10:00 | -1 任务书生成 | 通过 | x |\n"
                "| 2026-08-01 11:00 | 7 通知 | 通过 | x |", encoding="utf-8")
            # 跨天异常任务
            ab_dir = ws / "hetu-y" / "opencode_schedule" / "20260801" / "20260801任务C"
            ab_dir.mkdir(parents=True)
            (ab_dir / "研发流程状态.md").write_text(
                "| 2026-08-01 10:00 | -1 任务书生成 | 通过 | x |\n"
                "| 2026-08-03 10:00 | 7 通知 | 通过 | x |", encoding="utf-8")
            ev = list(recorder.iter_events(rl))
            b = stats.engine_benchmark(ev, ws)
            self.assertEqual(b["dsh"]["count"], 1)
            self.assertEqual(b["dsh"]["avg_min"], 10.0)
            self.assertEqual(b["opencode"]["count"], 1)
            self.assertEqual(b["opencode"]["avg_min"], 60.0)
            self.assertAlmostEqual(b["ratio_avg"], 0.17, places=2)  # round(10/60, 2)
            self.assertEqual(len(b["excluded"]), 1)
            self.assertIn("跨多天", b["excluded"][0]["reason"])

    def test_gates_verification_flag(self):
        """验证性拦截标记：冒烟验证拦截 verification=true，其余为 false。"""
        import json as _json
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rl = root / "runlog"
            # 两条拦截：一条冒烟验证（含关键词），一条真实（无关键词）
            for msg in ("冒烟验证：门禁未开时写日志被拦截", "真实违规：无备份删除数据"):
                recorder.record_event(
                    rl, "R1", 3, "单元测试", "gate_block", "blocked",
                    detail={"msg": msg}, project="hetu-hammurabi",
                )
            recorder.record_event(rl, "R1", 3, "单元测试", "gate_pass", "pass",
                                  detail={"msg": "开闸"}, project="hetu-hammurabi")
            ev = list(recorder.iter_events(rl))
            g = stats.gates_stats(ev)
            self.assertEqual(g["count"], 2)
            self.assertEqual(g["verification_count"], 1)
            by_msg = {e["detail"]["msg"]: e["verification"] for e in g["events"]}
            self.assertTrue(by_msg["冒烟验证：门禁未开时写日志被拦截"])
            self.assertFalse(by_msg["真实违规：无备份删除数据"])

    def test_period_filter_day(self):
        """周期过滤 day：只留最近一天（live 20260814），历史 20260804 被过滤。"""
        ov = stats.overview(self.events, period="day")
        self.assertEqual(ov["total_tasks"], 1)
        self.assertEqual(ov["total_node_runs"], 5)


class TestDashboardAPI(unittest.TestCase):
    """看板 API（TestClient）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _seed_live_events(self.root / "runlog")
        _seed_history_task(self.root / "opencode_schedule")
        self.client = TestClient(create_app(
            runlog_root=self.root / "runlog",
            schedule_root=self.root / "opencode_schedule",
            cache_ttl=0,
        ))

    def tearDown(self):
        self._tmp.cleanup()

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertGreaterEqual(r.json()["events"], 20)

    def test_overview_endpoint(self):
        r = self.client.get("/api/stats/overview")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total_tasks"], 2)
        self.assertAlmostEqual(data["gate_block_rate"], 1 / 3, places=4)

    def test_overview_period_param(self):
        r = self.client.get("/api/stats/overview", params={"period": "day"})
        self.assertEqual(r.json()["total_tasks"], 1)

    def test_nodes_endpoint(self):
        r = self.client.get("/api/stats/nodes")
        self.assertEqual(r.status_code, 200)
        node3 = next(n for n in r.json()["nodes"] if n["node"] == "3")
        self.assertEqual(node3["node_name"], "单元测试")

    def test_gates_endpoint(self):
        r = self.client.get("/api/stats/gates")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)

    def test_tasks_endpoint(self):
        r = self.client.get("/api/tasks")
        runs = [t["run_id"] for t in r.json()["tasks"]]
        self.assertIn(LIVE_RUN, runs)

    def test_task_detail_endpoint(self):
        r = self.client.get(f"/api/tasks/{LIVE_RUN}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["run_id"], LIVE_RUN)
        self.assertEqual(len(r.json()["timeline"]), 5)  # -1,0,3,5,6

    def test_task_detail_404(self):
        r = self.client.get("/api/tasks/not-exist")
        self.assertEqual(r.status_code, 404)

    def test_dashboard_index(self):
        """看板前端首页可访问（存在 dashboard 目录时）。"""
        r = self.client.get("/")
        # 若未配置 dashboard 目录，则返回 404 也属预期（由真实部署提供前端）
        self.assertIn(r.status_code, (200, 404))


if __name__ == "__main__":
    unittest.main()
