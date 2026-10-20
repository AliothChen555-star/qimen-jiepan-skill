"""Regression checks for discontinuous civil clocks and explicit search windows."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qimen.calendar import calendar_data
from qimen.chart import cast_chart
from timing_candidates import candidates, period_boundaries

UTC = timezone.utc


class TimingBoundaryChecks(unittest.TestCase):
    def assert_constant_segments(self, values, tz, unit, boundary="midnight"):
        key = "day_pillar" if unit == "day" else "hour_pillar"
        for left, right in zip(values, values[1:]):
            self.assertLess(left, right)
            expected = calendar_data(left.astimezone(tz), 120, "standard_time", boundary)[0][key]
            for fraction in (0.01, 0.25, 0.5, 0.75, 0.99):
                instant = left + (right - left) * fraction
                actual = calendar_data(instant.astimezone(tz), 120, "standard_time", boundary)[0][key]
                self.assertEqual(actual, expected, (left, right, instant))

    def test_sao_paulo_missing_midnight_splits_at_real_day_start(self):
        tz = ZoneInfo("America/Sao_Paulo")
        start, end = datetime(2018, 11, 3, 12, tzinfo=tz), datetime(2018, 11, 5, 12, tzinfo=tz)
        values = period_boundaries(start, end, "day", "midnight")
        self.assertIn(datetime(2018, 11, 4, 3, tzinfo=UTC), values)
        self.assert_constant_segments(values, tz, "day")

    def test_kathmandu_fifteen_minute_gap_splits_both_pillars(self):
        tz = ZoneInfo("Asia/Kathmandu")
        start, end = datetime(1985, 12, 31, 22, tzinfo=tz), datetime(1986, 1, 1, 3, tzinfo=tz)
        for unit in ("day", "hour"):
            values = period_boundaries(start, end, unit, "midnight")
            self.assertIn(datetime(1985, 12, 31, 18, 30, tzinfo=UTC), values)
            self.assert_constant_segments(values, tz, unit)

    def test_repeated_hour_and_repeated_midnight_have_distinct_instants(self):
        for zone, start, end in (
            ("America/New_York", "2026-11-01T00:30:00", "2026-11-01T03:30:00"),
            ("America/Havana", "2020-10-31T23:30:00", "2020-11-01T02:30:00"),
            ("Australia/Lord_Howe", "2026-04-05T00:30:00", "2026-04-05T03:30:00"),
        ):
            tz = ZoneInfo(zone)
            first, last = datetime.fromisoformat(start).replace(tzinfo=tz), datetime.fromisoformat(end).replace(tzinfo=tz)
            for unit in ("day", "hour"):
                values = period_boundaries(first, last, unit, "midnight")
                self.assertEqual(len(values), len(set(values)))
                self.assert_constant_segments(values, tz, unit)
            if zone == "America/New_York":
                values = period_boundaries(first, last, "hour", "midnight")
                repeated = [v.astimezone(tz) for v in values if v.astimezone(tz).hour == 1]
                self.assertEqual(len(repeated), 2)
                self.assertNotEqual(repeated[0].utcoffset(), repeated[1].utcoffset())

    def test_skipped_civil_day_does_not_create_nonexistent_segments(self):
        tz = ZoneInfo("Pacific/Apia")
        start, end = datetime(2011, 12, 29, 12, tzinfo=tz), datetime(2011, 12, 31, 12, tzinfo=tz)
        for unit in ("day", "hour"):
            values = period_boundaries(start, end, unit, "midnight")
            self.assert_constant_segments(values, tz, unit)
            self.assertFalse(any(v.astimezone(tz).date().isoformat() == "2011-12-30" for v in values))

    def test_calendar_day_gap_end_is_normalized_and_policy_is_explicit(self):
        chart = cast_chart("2018-11-03T00:30:00-03:00", timezone_name="America/Sao_Paulo")
        output = candidates(chart, [4], unit="hour", days=1, duration_mode="calendar_days")
        self.assertEqual(output["window"]["end_exclusive"], "2018-11-04T01:30:00-02:00")
        self.assertEqual(output["window"]["end_gap_policy"], "shift_forward")
        self.assertTrue(output["window"]["end_adjusted_for_gap"])
        with self.assertRaisesRegex(ValueError, "不存在"):
            candidates(chart, [4], unit="hour", days=1, end_gap_policy="raise")

    def test_calendar_days_and_elapsed_24h_have_different_declared_duration(self):
        chart = cast_chart("2026-03-07T12:00:00-05:00", timezone_name="America/New_York")
        civil = candidates(chart, [4], unit="hour", days=1, duration_mode="calendar_days")
        elapsed = candidates(chart, [4], unit="hour", days=1, duration_mode="elapsed_24h")
        self.assertEqual(civil["window"]["end_exclusive"], "2026-03-08T12:00:00-04:00")
        self.assertEqual(elapsed["window"]["end_exclusive"], "2026-03-08T13:00:00-04:00")
        self.assertEqual(civil["statistics"]["window_seconds"], 23 * 3600)
        self.assertEqual(elapsed["statistics"]["window_seconds"], 24 * 3600)

    def test_ambiguous_calendar_end_uses_explicit_fold(self):
        chart = cast_chart("2026-10-31T01:30:00-04:00", timezone_name="America/New_York")
        earlier = candidates(chart, [4], unit="hour", days=1, calendar_end_fold=0)
        later = candidates(chart, [4], unit="hour", days=1, calendar_end_fold=1)
        self.assertEqual(earlier["window"]["end_exclusive"], "2026-11-01T01:30:00-04:00")
        self.assertEqual(later["window"]["end_exclusive"], "2026-11-01T01:30:00-05:00")
        self.assertEqual(later["statistics"]["window_seconds"] - earlier["statistics"]["window_seconds"], 3600)

    def test_pre_epoch_transition_and_both_day_boundary_methods(self):
        tz = ZoneInfo("America/New_York")
        start, end = datetime(1918, 10, 26, 22, tzinfo=tz), datetime(1918, 10, 28, 3, tzinfo=tz)
        for boundary in ("midnight", "zi_start"):
            for unit in ("day", "hour"):
                self.assert_constant_segments(period_boundaries(start, end, unit, boundary), tz, unit, boundary)

    def test_inconsistent_source_timestamp_is_not_a_search_start(self):
        chart = json.loads((Path(__file__).parent / "fixtures/base.json").read_text(encoding="utf-8"))
        chart["input"]["datetime"] = "2026-11-14T13:27:13+08:00"
        with self.assertRaises(ValueError):
            candidates(chart, [4], unit="day", days=1)

    def test_independent_search_start_preserves_chart_and_has_union_coverage(self):
        chart = json.loads((Path(__file__).parent / "fixtures/base.json").read_text(encoding="utf-8"))
        original = deepcopy(chart)
        output = candidates(chart, [4, 9], unit="hour", days=2, search_start="2026-10-20T00:00:00+08:00")
        self.assertEqual(chart, original)
        self.assertEqual(output["source_captured_at"], original["input"]["captured_at"])
        self.assertEqual(output["window"]["start"], "2026-10-20T00:00:00+08:00")
        self.assertTrue(output["window"]["search_start_explicit"])
        seconds = sum((datetime.fromisoformat(row["end_utc_exclusive"]) - datetime.fromisoformat(row["start_utc"])).total_seconds()
                      for row in output["candidates"])
        self.assertEqual(output["statistics"]["candidate_union_seconds"], seconds)
        self.assertLessEqual(seconds, output["statistics"]["window_seconds"])
        self.assertAlmostEqual(output["statistics"]["coverage_fraction"], seconds / output["statistics"]["window_seconds"])
        for row in output["candidates"]:
            self.assertGreater(row["duration_seconds"], 0)
            for key in ("start", "end_exclusive"):
                value = datetime.fromisoformat(row[key])
                self.assertEqual(value.isoformat(), value.astimezone(ZoneInfo(output["window"]["timezone"])).isoformat())

    def test_invalid_window_options_and_naive_start_are_rejected(self):
        chart = json.loads((Path(__file__).parent / "fixtures/base.json").read_text(encoding="utf-8"))
        for options in ({"search_start": "2026-10-20T00:00:00"}, {"duration_mode": "maybe"},
                        {"end_gap_policy": "maybe"}, {"calendar_end_fold": 2}, {"calendar_end_fold": True}):
            with self.assertRaises(ValueError):
                candidates(chart, [4], unit="day", days=1, **options)


if __name__ == "__main__":
    unittest.main()
