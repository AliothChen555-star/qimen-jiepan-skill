"""Input-integrity regressions; no forecast or independent calendar claim."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
from importlib.metadata import version
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from chart_validation import chart_instant_utc, validate_chart, validate_structure
from qimen.chart import arrange, cast_chart
from qimen.cli import main as cli_main
from qimen.rules import SEXAGENARY


class IntegrityChecks(unittest.TestCase):
    def setUp(self):
        self.chart = cast_chart("2026-10-18T12:00:00+08:00")

    def test_legacy_complete_fixtures_remain_readable_without_mutation(self):
        for name in ("base", "support", "geng", "hosted"):
            chart = json.loads((ROOT / "evals" / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))
            before = deepcopy(chart)
            self.assertEqual(set(validate_chart(chart)), set(range(1, 10)))
            self.assertEqual(chart, before)

    def test_new_metadata_records_actual_dependencies(self):
        self.assertEqual(self.chart["runtime"]["lunar_python"], version("lunar-python"))
        self.assertEqual(self.chart["runtime"]["tzdata"], version("tzdata"))
        self.assertEqual(self.chart["input"]["chart_instant_utc"], "2026-10-18T04:00:00+00:00")
        self.assertEqual(chart_instant_utc(self.chart), datetime(2026, 10, 18, 4, tzinfo=timezone.utc))

    def test_same_count_star_swap_is_rejected(self):
        a, b = [p for p in self.chart["palaces"] if p["number"] in (1, 3)]
        a["stars"], b["stars"] = b["stars"], a["stars"]
        a["star"], b["star"] = "/".join(a["stars"]), "/".join(b["stars"])
        with self.assertRaisesRegex(ValueError, "星干耦合"):
            validate_chart(self.chart)

    def test_stem_door_and_spirit_swaps_each_fail(self):
        for field, display in (("heaven_stems", "heaven_stem"), ("door", None), ("spirit", None)):
            chart = deepcopy(self.chart)
            a, b = [p for p in chart["palaces"] if p["number"] in (1, 3)]
            a[field], b[field] = b[field], a[field]
            if display:
                a[display], b[display] = "/".join(a[field]), "/".join(b[field])
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_chief_origin_raw_target_and_elapsed_are_not_just_flags(self):
        for group, key in (("chief", "origin_palace"), ("chief", "zhi_fu_raw_palace"),
                           ("chief", "zhi_shi_raw_palace"), ("xun", "elapsed_hours")):
            chart = deepcopy(self.chart)
            chart[group][key] = chart[group][key] % 9 + 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_display_and_hosting_metadata_are_checked(self):
        for key, value in (("star", "天冲"), ("hosting", {"hosted_at": 1}), ("void", 0)):
            chart = deepcopy(self.chart)
            chart["palaces"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_duplicate_and_boolean_palace_numbers_fail(self):
        for number in (2, True):
            chart = deepcopy(self.chart)
            chart["palaces"][0]["number"] = number
            with self.subTest(number=number), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_each_frozen_time_field_must_agree(self):
        for group, key, value in (("input", "datetime", "2026-11-18T12:00:00+08:00"),
                                  ("input", "captured_at", "2026-10-18T11:00:00+08:00"),
                                  ("input", "captured_at_utc", "2026-10-19T04:00:00+00:00"),
                                  ("input", "chart_instant_utc", "2026-10-19T04:00:00+00:00"),
                                  ("calendar", "solar_datetime", "2026-10-19T12:00:00+08:00")):
            chart = deepcopy(self.chart)
            chart[group][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_wrong_local_offset_rejected_even_for_same_instant(self):
        self.chart["input"]["datetime"] = "2026-10-18T04:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "时区"):
            validate_chart(self.chart)

    def test_new_schema_cannot_omit_canonical_utc_or_runtime(self):
        for group, key in (("input", "chart_instant_utc"), (None, "runtime")):
            chart = deepcopy(self.chart)
            del (chart[group] if group else chart)[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_calendar_and_term_cannot_be_replaced_by_other_valid_values(self):
        for group, key, value in (("calendar", "year_pillar", "丁未"),
                                  ("calendar", "effective_wall_time", "2026-10-18T13:00:00"),
                                  ("solar_term", "ju", 1)):
            chart = deepcopy(self.chart)
            chart[group][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_time_source_and_provider_cannot_conflict(self):
        for group, key, value in (("input", "time_source", "runtime_clock"),
                                  ("solar_term", "provider", "lunar-python 0.0")):
            chart = deepcopy(self.chart)
            chart[group][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_chart(chart)

    def test_full_validation_does_not_fall_back_for_partial_charts(self):
        chart = arrange(1, "yang", "甲子", "甲子", "hour")
        chart.update(rule_version="chai_bu_v1.0.0", input={"center_policy": "kun2"},
                     calendar={"year_pillar": "丙午", "month_pillar": "戊戌",
                               "day_pillar": "甲子", "hour_pillar": "甲子"})
        self.assertEqual(len(validate_structure(chart)), 9)
        with self.assertRaises(ValueError):
            validate_chart(chart)

    def test_synthetic_arrangements_explicitly_check_all_1080_geometries(self):
        for dun in ("yang", "yin"):
            for ju in range(1, 10):
                for hour in SEXAGENARY:
                    chart = arrange(ju, dun, hour, "甲子", "hour")
                    chart.update(rule_version="chai_bu_v1.0.0", input={"center_policy": "kun2"},
                                 calendar={"year_pillar": "丙午", "month_pillar": "戊戌",
                                           "day_pillar": "甲子", "hour_pillar": hour})
                    self.assertEqual(len(validate_structure(chart)), 9)

    def test_full_validation_only_replays_explicit_frozen_time(self):
        from chart_validation import cast_chart as original
        with patch("chart_validation.cast_chart", wraps=original) as replay:
            validate_chart(self.chart)
            self.assertIs(replay.call_args.kwargs["use_current_time"], False)
            self.assertIsInstance(replay.call_args.args[0], datetime)

    def test_true_solar_and_other_calendar_profiles_still_validate(self):
        for kwargs in ({"time_mode": "true_solar_time", "longitude": 105.5},
                       {"day_boundary": "zi_start", "horse_basis": "day"},
                       {"timezone_name": "America/New_York"}):
            chart = cast_chart("2026-10-18T23:30:00+08:00", **kwargs)
            self.assertEqual(len(validate_chart(chart)), 9)

    def test_library_requires_an_explicit_time_mode(self):
        with self.assertRaisesRegex(ValueError, "显式"):
            cast_chart()

    def test_supplied_zoneinfo_gap_is_rendered_as_a_real_local_time(self):
        imaginary = datetime(2018, 11, 4, 0, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
        chart = cast_chart(imaginary, timezone_name="America/Sao_Paulo")
        self.assertEqual(chart["input"]["datetime"], "2018-11-04T01:30:00-02:00")
        validate_chart(chart)

    def test_cli_requires_one_and_only_one_time_argument(self):
        for argv in (["chart"], ["chart", "--now", "--datetime", "2026-10-18T12:00:00+08:00"]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit:
                cli_main(argv)
            self.assertEqual(exit.exception.code, 2)

    def test_cli_explicit_and_injected_now_record_different_provenance(self):
        for argv, expected_now in ((["--datetime", "2026-10-18T12:00:00+08:00"], False), (["--now"], True)):
            stream = io.StringIO()
            clock = lambda: datetime.fromisoformat("2026-10-18T12:00:00+08:00")
            with patch("qimen.cli.cast_chart", partial(cast_chart, clock=clock)), redirect_stdout(stream):
                self.assertEqual(cli_main(["chart", *argv, "--format", "json"]), 0)
            result = json.loads(stream.getvalue())
            self.assertIs(result["input"]["use_current_time"], expected_now)
            self.assertEqual(len(validate_chart(result)), 9)

    def test_launcher_missing_dependency_returns_without_install_or_env_creation(self):
        spec = importlib.util.spec_from_file_location("qimen_readonly_launcher", ROOT / "scripts" / "qimen_cli.py")
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with patch.object(launcher.Path, "is_file", return_value=False), \
                patch.object(launcher.importlib.util, "find_spec", return_value=None), \
                patch.object(launcher.os, "execv") as reexec, \
                redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(launcher.main(), 2)
        reexec.assert_not_called()
        self.assertIn("显式运行", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
