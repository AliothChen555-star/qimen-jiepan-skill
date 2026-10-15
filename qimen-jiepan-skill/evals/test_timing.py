"""Check calendar windows, exact branch triggers, and original-chart preservation."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from timing_candidates import candidates, period_boundaries


class TimingChecks(unittest.TestCase):
    def setUp(self):
        self.chart = json.loads((Path(__file__).parent / "fixtures/base.json").read_text(encoding="utf-8"))

    def test_daily_candidates_match_frozen_day_cycle(self):
        result = candidates(self.chart, [4], unit="day", days=10)
        rows = {r["start"][:10]: r for r in result["candidates"]}
        self.assertEqual(set(rows), {"2026-10-15", "2026-10-16", "2026-10-21", "2026-10-22"})
        self.assertEqual(rows["2026-10-15"]["pillar"], "壬戌")
        self.assertEqual(rows["2026-10-21"]["pillar"], "戊辰")
        self.assertEqual(rows["2026-10-22"]["pillar"], "己巳")
        self.assertTrue(any(t["kind"] == "冲墓" and t["underlying_branch"] == "辰"
                            for t in rows["2026-10-15"]["triggers"]))
        self.assertEqual(rows["2026-10-16"]["triggers"][0]["kind"], "冲空")
        self.assertTrue(any(t["kind"] == "马星同支" for t in rows["2026-10-22"]["triggers"]))

    def test_output_does_not_mutate_or_recast_source(self):
        before = deepcopy(self.chart)
        output = candidates(self.chart, [4, 9], unit="hour", days=1)
        self.assertEqual(self.chart, before)
        self.assertEqual(output["source_captured_at"], "2026-10-14T13:27:13+08:00")
        self.assertNotIn("palaces_chart", output)
        self.assertTrue(all(t["palace"] in (4, 9) for r in output["candidates"] for t in r["triggers"]))

    def test_half_void_does_not_expand_to_other_branch_of_opposite_palace(self):
        chart = json.loads((Path(__file__).parent / "fixtures/support.json").read_text(encoding="utf-8"))
        output = candidates(chart, [2], unit="day", days=12)
        void_events = [t for r in output["candidates"] for t in r["triggers"] if t["kind"] in ("填实", "冲空")]
        self.assertEqual({t["trigger_branch"] for t in void_events}, {"申", "寅"})

    def test_zi_start_uses_2300_day_boundary(self):
        tz = ZoneInfo("Asia/Shanghai")
        start = datetime(2026, 1, 13, 22, 30, tzinfo=tz)
        end = start + timedelta(hours=3)
        values = period_boundaries(start, end, "day", "zi_start")
        self.assertEqual([d.astimezone(tz).strftime("%H:%M") for d in values], ["22:30", "23:00", "01:30"])

    def test_midnight_hour_mode_splits_stem_change_inside_zi(self):
        tz = ZoneInfo("Asia/Shanghai")
        start = datetime(2026, 1, 13, 23, 30, tzinfo=tz)
        end = start + timedelta(hours=2)
        values = period_boundaries(start, end, "hour", "midnight")
        self.assertEqual([d.astimezone(tz).strftime("%H:%M") for d in values], ["23:30", "00:00", "01:00", "01:30"])

    def test_dst_repeated_hour_is_retained_as_distinct_instants(self):
        tz = ZoneInfo("America/New_York")
        start = datetime(2026, 11, 1, 0, 30, tzinfo=tz)
        end = datetime(2026, 11, 1, 3, 30, tzinfo=tz)
        values = period_boundaries(start, end, "hour", "midnight")
        repeated = [d.astimezone(tz) for d in values if d.astimezone(tz).hour == 1]
        self.assertEqual(len(repeated), 2)
        self.assertNotEqual(repeated[0].utcoffset(), repeated[1].utcoffset())
        self.assertEqual(sum((b-a).total_seconds() for a,b in zip(values, values[1:])), 4 * 3600)

    def test_window_is_clipped_and_end_exclusive(self):
        output = candidates(self.chart, [4], unit="hour", days=1)
        start = datetime.fromisoformat(output["window"]["start"])
        end = datetime.fromisoformat(output["window"]["end_exclusive"])
        for row in output["candidates"]:
            self.assertGreaterEqual(datetime.fromisoformat(row["start"]), start)
            self.assertLess(datetime.fromisoformat(row["start"]), end)
            self.assertLessEqual(datetime.fromisoformat(row["end_exclusive"]), end)

    def test_unsupported_or_ambiguous_inputs_fail(self):
        for kwargs in ({"unit": "month"}, {"unit": "day", "days": 0},
                       {"unit": "day", "days": 367}, {"unit": "day", "days": True}):
            with self.assertRaises(ValueError):
                candidates(self.chart, [4], **kwargs)
        for targets in ([], [5], [4, 4], [True]):
            with self.assertRaises(ValueError):
                candidates(self.chart, targets, unit="day")
        solar = deepcopy(self.chart)
        solar["input"]["time_mode"] = "true_solar_time"
        with self.assertRaisesRegex(ValueError, "标准时"):
            candidates(solar, [4], unit="day")


if __name__ == "__main__":
    unittest.main()
