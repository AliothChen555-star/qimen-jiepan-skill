"""Deterministic pattern checks using synthetic plates; no predictive claims."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_patterns import (compound_patterns, inspect_chart, pair_detail,
                              relation, seasonal)
from qimen.chart import arrange


def fixture(hour="甲子", day="甲子"):
    chart = arrange(1, "yang", hour, day, "hour")
    chart.update(rule_version="chai_bu_v1.0.0",
                 input={"center_policy": "kun2", "captured_at": "synthetic fixture"},
                 calendar={"year_pillar": "丙午", "month_pillar": "戊戌",
                           "day_pillar": day, "hour_pillar": hour})
    return chart


def palace(result, number):
    return next(p for p in result["palaces"] if p["number"] == number)


class PatternChecks(unittest.TestCase):
    def test_native_plate_has_three_separate_fuyin_results(self):
        result = inspect_chart(fixture())
        for layer in ("star_plate", "door_plate", "stem_plate"):
            self.assertEqual(result["global"][layer]["state"], "伏吟")
        self.assertEqual(len(result["global"]["stem_plate"]["evidence"]), 9)
        self.assertEqual(result["center"]["hosted_at"], 2)
        self.assertEqual(result["global"]["void_branches"], ["戌", "亥"])

    def test_star_and_stem_fanyin_do_not_imply_door_fanyin(self):
        # Yang 1: 乙 is originally at 離九, opposite the 戊/天蓬 origin 坎一.
        result = inspect_chart(fixture("乙丑"))
        self.assertEqual(result["global"]["star_plate"]["state"], "反吟")
        self.assertEqual(result["global"]["stem_plate"]["state"], "反吟")
        self.assertEqual(result["global"]["door_plate"]["state"], "转动（非整体反伏吟）")

    def test_door_fanyin_can_be_independent(self):
        # Ninth hour from 甲子 sends 休门 from 坎一 to 離九.
        result = inspect_chart(fixture("壬申"))
        self.assertEqual(result["global"]["door_plate"]["state"], "反吟")
        self.assertNotEqual(result["global"]["star_plate"]["state"], "反吟")

    def test_open_door_wood_palace_is_pressure(self):
        result = inspect_chart(fixture("丁卯"))
        human = palace(result, 3)["human"]
        self.assertEqual(human["door"], "开门")
        self.assertTrue(human["door_pressure"])
        self.assertFalse(human["door_controlled"])

    def test_rest_door_earth_palace_is_controlled_not_pressure(self):
        result = inspect_chart(fixture("戊辰"))
        human = palace(result, 2)["human"]
        self.assertEqual(human["door"], "休门")
        self.assertTrue(human["door_controlled"])
        self.assertFalse(human["door_pressure"])
        self.assertEqual(result["global"]["star_plate"]["state"], "伏吟")
        self.assertEqual(result["global"]["door_plate"]["state"], "转动（非整体反伏吟）")

    def test_original_stem_polarity_is_required_for_five_not_meeting(self):
        self.assertTrue(inspect_chart(fixture("庚午"))["global"]["five_not_meeting"]["matches"])
        self.assertFalse(inspect_chart(fixture("辛未"))["global"]["five_not_meeting"]["matches"])

    def test_direction_and_overlapping_patterns_are_retained(self):
        forward = pair_detail("乙", "辛", 0, 0, "辛")
        reverse = pair_detail("辛", "乙", 0, 0, "辛")
        self.assertIn("青龙逃走", forward["named_patterns"])
        self.assertIn("三奇得使（加六甲法）", forward["named_patterns"])
        self.assertIn("白虎猖狂", reverse["named_patterns"])
        self.assertEqual(forward["relation_A_to_B"], "B克A")
        self.assertEqual(reverse["relation_A_to_B"], "A克B")

    def test_hidden_jia_and_modern_dragon_shorthand_are_distinct(self):
        chief = pair_detail("庚", "丙", 0, 0, "庚")
        shorthand = pair_detail("戊", "丙", 0, 0, "庚")
        self.assertIn("青龙返首（旬首法）", chief["named_patterns"])
        self.assertIn("太白入荧", chief["named_patterns"])
        self.assertNotIn("青龙返首（旬首法）", shorthand["named_patterns"])
        self.assertIn("青龙返首（戊丙简法）", shorthand["named_patterns"])

    def test_nine_dun_requires_all_selected_conditions(self):
        base = {"door": "生门", "spirit": "九天", "number": 1,
                "heaven_stems": ["丙"], "earth_stems": ["丁"], "zhi_shi": False}
        names = {p["name"] for p in compound_patterns(base)}
        self.assertIn("天遁（演义丙丁法）", names)
        self.assertIn("神遁", names)
        alternate = dict(base, earth_stems=["戊"])
        self.assertNotIn("天遁（演义丙丁法）", {p["name"] for p in compound_patterns(alternate)})
        tiger = dict(base, door="休门", number=8, heaven_stems=["乙"], earth_stems=["辛"])
        self.assertIn("虎遁", {p["name"] for p in compound_patterns(tiger)})
        self.assertNotIn("虎遁", {p["name"] for p in compound_patterns(dict(tiger, number=2))})

    def test_yunu_uses_earth_ding_and_chief_door(self):
        base = {"door": "开门", "spirit": "六合", "number": 7,
                "heaven_stems": ["丁"], "earth_stems": ["乙"], "zhi_shi": True}
        self.assertNotIn("玉女守门", {p["name"] for p in compound_patterns(base)})
        self.assertIn("玉女守门", {p["name"] for p in compound_patterns(dict(base, earth_stems=["丁"]))})
        self.assertNotIn("玉女守门", {p["name"] for p in compound_patterns(dict(base, earth_stems=["丁"], zhi_shi=False))})

    def test_hosted_stems_are_crossed_once_and_center_not_duplicated(self):
        result = inspect_chart(fixture())
        kun = palace(result, 2)
        self.assertEqual(len(kun["stem_pairs"]), 4)
        self.assertEqual({(p["heaven"], p["earth"]) for p in kun["stem_pairs"]},
                         {("己", "己"), ("己", "壬"), ("壬", "己"), ("壬", "壬")})
        self.assertEqual({p["number"] for p in result["palaces"]}, {1, 2, 3, 4, 6, 7, 8, 9})
        self.assertEqual(len(result["global"]["star_plate"]["evidence"]), 9)

    def test_star_season_is_distinct_from_ordinary_elements(self):
        self.assertEqual(seasonal("水", "木", star=True)["state"], "旺")
        self.assertEqual(seasonal("水", "木")["state"], "休")
        self.assertEqual(seasonal("水", "金", star=True)["state"], "死")
        self.assertEqual(seasonal("水", "金")["state"], "相")

    def test_tombs_distinguish_heaven_from_earth(self):
        result = inspect_chart(fixture())
        xun = palace(result, 4)
        heaven, earth = xun["heaven"]["stems"][0], xun["earth"]["stems"][0]
        self.assertEqual(heaven["stem"], "辛")
        self.assertTrue(heaven["tomb"]["matches"])
        self.assertEqual(heaven["tomb"]["scope"], "天盘干入墓")
        self.assertTrue(earth["tomb"]["matches"])
        self.assertEqual(earth["tomb"]["scope"], "地盘墓位")
        self.assertNotIn("punishment", earth)
        self.assertFalse(palace(result, 2)["heaven"]["stems"][0]["tomb"]["matches"])

    def test_punishment_marks_whether_the_instrument_is_current_xun(self):
        native = palace(inspect_chart(fixture()), 2)["heaven"]["stems"][0]
        self.assertEqual(native["stem"], "己")
        self.assertTrue(native["punishment"]["matches"])
        self.assertFalse(native["punishment"]["is_current_xun"])
        current = palace(inspect_chart(fixture("庚午")), 3)["heaven"]["stems"][0]
        self.assertEqual(current["stem"], "戊")
        self.assertTrue(current["punishment"]["matches"])
        self.assertTrue(current["punishment"]["is_current_xun"])

    def test_all_supported_ju_and_hour_arrangements_keep_center_invariants(self):
        from qimen.rules import SEXAGENARY
        for dun in ("yang", "yin"):
            for ju in range(1, 10):
                for hour in SEXAGENARY:
                    chart = fixture()
                    chart.update(arrange(ju, dun, hour, "甲子", "hour"))
                    chart["calendar"]["hour_pillar"] = hour
                    result = inspect_chart(chart)
                    self.assertEqual(len(result["global"]["stem_plate"]["evidence"]), 9)
                    self.assertEqual(len(result["global"]["star_plate"]["evidence"]), 9)
                    self.assertEqual(len(result["global"]["door_plate"]["evidence"]), 8)
                    self.assertEqual(result["center"]["hosted_at"], 2)

    def test_all_81_pairs_preserve_direction_and_combination_symmetry(self):
        stems = "乙丙丁戊己庚辛壬癸"
        inverse = {"比和": "比和", "A生B": "B生A", "B生A": "A生B", "A克B": "B克A", "B克A": "A克B"}
        for h in stems:
            for e in stems:
                forward, reverse = pair_detail(h, e, 0, 0, "戊"), pair_detail(e, h, 0, 0, "戊")
                self.assertEqual(inverse[forward["relation_A_to_B"]], reverse["relation_A_to_B"])
                self.assertEqual(forward["five_combination"], reverse["five_combination"])
        self.assertEqual(relation("木", "土"), "A克B")
        self.assertTrue(pair_detail("丁", "壬", 0, 0, "戊")["five_combination"])

    def test_rejects_incomplete_or_conflicting_chart(self):
        original = fixture()
        conflicts = []
        item = deepcopy(original)
        item["rule_version"] = "another_method"
        conflicts.append(item)
        item = deepcopy(original)
        del item["palaces"][0]["void_branches"]
        conflicts.append(item)
        item = deepcopy(original)
        item["palaces"][0]["horse"] = not item["palaces"][0]["horse"]
        conflicts.append(item)
        item = deepcopy(original)
        item["palaces"][1]["earth_stems"][1] = "乙"
        conflicts.append(item)
        for item in conflicts:
            with self.assertRaises((ValueError, KeyError)):
                inspect_chart(item)
        self.assertEqual(original, fixture())


if __name__ == "__main__":
    unittest.main(verbosity=2)
