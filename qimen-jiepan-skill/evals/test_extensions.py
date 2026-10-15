"""Regression checks for the 0.4.0 rule extensions."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_patterns import (elemental_tomb, inspect_chart, pair_detail, resolve_pillar_stem,
                              seasonal, time_patterns)
from test_patterns import fixture, palace


class ExtensionChecks(unittest.TestCase):
    def test_two_star_methods_match_separate_source_formulas(self):
        expected = {"木": ("旺", "相"), "水": ("相", "旺"), "金": ("死", "休"),
                    "土": ("囚", "囚"), "火": ("废", "死")}
        for month, (tongzong, yanyi) in expected.items():
            self.assertEqual(seasonal("水", month, star=True)["state"], tongzong)
            self.assertEqual(seasonal("水", month, star=True, star_season="yanyi_prose")["state"], yanyi)

    def test_star_option_does_not_change_door_stem_or_raw_chart(self):
        raw = fixture("丙寅")
        before = deepcopy(raw)
        a = inspect_chart(raw)
        b = inspect_chart(raw, star_season="yanyi_prose")
        self.assertEqual(raw, before)
        for x, y in zip(a["palaces"], b["palaces"]):
            self.assertEqual(x["human"], y["human"])
            self.assertEqual(x["heaven"]["stems"], y["heaven"]["stems"])
            self.assertEqual(x["earth"], y["earth"])
        self.assertNotEqual(a["methods"]["star_season"], b["methods"]["star_season"])
        with self.assertRaises(ValueError):
            inspect_chart(raw, star_season="unknown")

    def test_open_door_can_be_supported_and_in_its_own_tomb(self):
        p = palace(inspect_chart(fixture("丙寅")), 8)
        self.assertEqual(p["human"]["door"], "开门")
        self.assertEqual(p["human"]["relation_A_to_palace"], "B生A")
        self.assertTrue(p["human"]["tomb"]["matches"])
        self.assertEqual(p["human"]["tomb"]["branch"], "丑")
        self.assertFalse(elemental_tomb("金", 4, "门")["matches"])

    def test_star_door_tombs_are_not_yin_stem_tombs(self):
        source_cases = [("木", 2, "未"), ("火", 6, "戌"), ("土", 4, "辰"),
                        ("金", 8, "丑"), ("水", 4, "辰")]
        for element, number, branch in source_cases:
            value = elemental_tomb(element, number, "星")
            self.assertTrue(value["matches"])
            self.assertEqual(value["branch"], branch)
            self.assertEqual(value["source_id"], "ZG-4")

    def test_pair_reading_and_geometry_remain_distinct(self):
        yi_ding = pair_detail("乙", "丁", 0, 0, "戊")
        self.assertEqual(yi_ding["traditional_reading"]["table_name"], "奇仪相佐")
        ding_ding = pair_detail("丁", "丁", 0, 0, "戊")
        self.assertIn("局部干伏吟", ding_ding["named_patterns"])
        self.assertEqual(ding_ding["traditional_reading"]["table_name"], "奇入太阴")
        self.assertNotIn("人遁", ding_ding["named_patterns"])
        self.assertNotIn("天盘干入墓", pair_detail("己", "丁", 0, 0, "戊")["named_patterns"])

    def test_geng_chief_exception_keeps_geometric_match(self):
        pair = pair_detail("庚", "丙", 0, 0, "庚")
        self.assertIn("青龙返首（旬首法）", pair["named_patterns"])
        check = next(c for c in pair["application_checks"] if c["rule_id"] == "dragon_bird_geng_chief")
        self.assertTrue(check["matches"])
        normal = pair_detail("戊", "丙", 0, 0, "戊")
        self.assertFalse(next(c for c in normal["application_checks"] if c["rule_id"] == check["rule_id"])["matches"])

    def test_conflicted_envoy_records_met_and_unknown_requirements(self):
        for flag in (True, False, None):
            pair = pair_detail("乙", "辛", 0, 0, "辛", chief_here=flag)
            check = next(c for c in pair["application_checks"] if c["rule_id"] == "qualified_qi_gets_envoy")
            self.assertIs(check["requirement_met"], flag)
            self.assertEqual(next(c for c in pair["application_checks"] if c["rule_id"] == "host_guest_relief")["role"], "主")

    def test_each_jia_pillar_resolves_its_own_instrument(self):
        self.assertEqual([resolve_pillar_stem(p) for p in ("甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅")],
                         list("戊己庚辛壬癸"))
        cal = {"year_pillar": "甲申", "month_pillar": "甲寅", "day_pillar": "甲辰", "hour_pillar": "甲子"}
        paradox = time_patterns({"heaven": "丙", "earth": "庚"}, cal)
        self.assertEqual([(m["name"], m["target"], m["resolved_stem"]) for m in paradox], [("悖格", "year", "庚")])
        flying = time_patterns({"heaven": "壬", "earth": "庚"}, cal)
        self.assertEqual(flying[0]["name"], "飞干格")

    def test_month_pattern_uses_the_declared_pillar_method(self):
        cal = {"year_pillar": "乙巳", "month_pillar": "丁亥", "day_pillar": "丙寅", "hour_pillar": "戊子"}
        matches = time_patterns({"heaven": "庚", "earth": "丁"}, cal)
        self.assertEqual([(m["name"], m["target"]) for m in matches], [("月格", "month")])
        self.assertIn("月朔干法未计算", inspect_chart(fixture())["methods"]["month_pattern"])

    def test_half_void_uses_exact_branch_clash(self):
        result = inspect_chart(fixture("甲戌"))
        kun = palace(result, 2)
        self.assertEqual(kun["activation"]["void_coverage"], "一支空")
        self.assertEqual(kun["activation"]["fill_void_branches"], ["申"])
        self.assertEqual(kun["activation"]["clash_void_branches"], ["寅"])
        self.assertEqual(palace(result, 7)["activation"]["void_coverage"], "全空")

    def test_native_star_is_fixed_beneath_a_moving_star(self):
        p = palace(inspect_chart(fixture("丙寅")), 3)
        self.assertEqual(p["earth"]["native_stars"], ["天冲"])
        self.assertNotEqual(p["heaven"]["stars"][0]["star"], "天冲")

    def test_frozen_charts_keep_known_geometry(self):
        cases = {"base": (4, "辛", "惊门"), "support": (1, "乙", "生门"),
                 "hosted": (1, "丁", "景门"), "geng": (2, "庚", "杜门")}
        directory = Path(__file__).parent / "fixtures"
        for name, (number, stem, door) in cases.items():
            chart = json.loads((directory / (name + ".json")).read_text(encoding="utf-8"))
            p = palace(inspect_chart(chart), number)
            self.assertIn(stem, [s["stem"] for s in p["heaven"]["stems"]])
            self.assertEqual(p["human"]["door"], door)


if __name__ == "__main__":
    unittest.main()
