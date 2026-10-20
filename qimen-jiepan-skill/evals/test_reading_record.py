"""Ledger consistency checks use a fictional context, never a real outcome."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from reading_record import canonical_chart_hash, init_record, main, validate_record


def example(chart):
    """Valid fictional current-state ledger; it is not a forecast fixture."""
    record = init_record(chart, "虚构演练：如何描述当下协作安排的状态？")
    record["status"] = "final"
    record["method_profile"]["method_id"] = "MODERN_WORKLOAD"
    record["known_facts"] = [{"id": "f1", "text": "这是一份无实际项目和结局的演练。", "basis": "provided_before_reading"}]
    # Select an actual symbol; its favorable/adverse meaning is supplied as a
    # declared modern hypothesis, never produced by the ledger validator.
    palace = next(p for p in chart["palaces"] if p["number"] != 5)
    record["roles"] = [{"id": "r1", "object": "当事人（虚构）", "kind": "stem",
                        "value": palace["heaven_stems"][0], "layer": "heaven",
                        "palace": palace["number"], "position": "main", "primary": True,
                        "source_id": "SK-1"}]
    horizon = {"state": "current", "at": chart["input"]["captured_at_utc"]}
    record["results"] = [{"id": "o1", "target": "当下协作安排", "stage": "现状描述",
                          "success_criteria": "描述能否保持节奏，仅作演练假设", "horizon": horizon,
                          "state": "assessed"}]
    record["evidence"] = [{"id": "e1", "result_id": "o1", "role_ids": ["r1"],
                           "source_id": "SK-1", "rule_id": "MODERN_WORKLOAD",
                           "applicability": "true", "polarity": "supports", "critical": False,
                           "fact": "角色所指天盘干确在所记宫位。",
                           "inference": "虚构的有限现代解释；没有现实效验声明。", "dedup_key": "current-modern-inference"}]
    record["conclusions"] = [{"id": "c1", "result_id": "o1", "horizon": deepcopy(horizon),
                              "judgment": "favorable", "claim": "在演练限定下，当前安排有可协调的一面。",
                              "support_ids": ["e1"], "counter_ids": [], "excluded_ids": [],
                              "dispositions": [], "synthesis_reason": "只采用已登记的当前状态假设，未外推持续期限。"}]
    record["imagery"] = [{"role_ids": ["r1"], "interpretation": "也许与任务节奏有关。",
                          "status": "hypothesis", "verification": "需要询问具体任务安排，不能据此认定事实。"}]
    record["timing"] = [{"result_id": "o1", "state": "not_applicable", "windows": [],
                         "reason": "该分项仅描述现状，没有预测时间窗口。"}]
    return record


class ReadingRecordChecks(unittest.TestCase):
    def setUp(self):
        self.chart = json.loads((ROOT / "evals" / "fixtures" / "base.json").read_text(encoding="utf-8"))
        self.record = example(self.chart)

    def test_fictional_complete_record_passes_without_mutation(self):
        before = deepcopy(self.record)
        self.assertEqual(validate_record(self.record, self.chart)["status"], "valid_final_record")
        self.assertEqual(self.record, before)

    def test_init_is_a_draft_and_is_not_final_validation(self):
        record = init_record(self.chart, "虚构问题")
        self.assertEqual(validate_record(record, self.chart, final=False)["status"], "draft_checked")
        with self.assertRaises(ValueError):
            validate_record(record, self.chart)
        record["status"] = "final"
        record["method_profile"]["method_id"] = "MODERN_WORKLOAD"
        with self.assertRaises(ValueError):
            validate_record(record, self.chart)

    def test_chart_hash_ignores_format_but_detects_replacement(self):
        reordered = {key: self.chart[key] for key in reversed(self.chart)}
        self.assertEqual(canonical_chart_hash(reordered), canonical_chart_hash(self.chart))
        other = json.loads((ROOT / "evals" / "fixtures" / "support.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            validate_record(self.record, other)

    def test_role_palace_layer_and_hosting_are_checked(self):
        for field, value in (("palace", 5), ("layer", "human"), ("position", "hosted"), ("value", "甲")):
            record = deepcopy(self.record)
            record["roles"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_record(record, self.chart)

    def test_door_star_spirit_and_native_star_roles_use_actual_layer(self):
        actual = self.chart["palaces"][0]
        for kind, value, layer in (("door", actual["door"], "human"),
                                   ("star", actual["stars"][0], "heaven"),
                                   ("spirit", actual["spirit"], "deity"),
                                   ("star", "天蓬", "earth")):
            record = deepcopy(self.record)
            record["roles"][0].update(kind=kind, value=value, layer=layer)
            self.assertEqual(validate_record(record, self.chart)["role_count"], 1)
            record["roles"][0]["layer"] = "human" if layer != "human" else "deity"
            with self.assertRaises(ValueError):
                validate_record(record, self.chart)

    def test_hosted_center_stem_uses_actual_host_palace(self):
        actual = next(p for p in self.chart["palaces"] if len(p["heaven_stems"]) == 2 and p["number"] != 5)
        self.record["roles"][0].update(value=actual["heaven_stems"][1], palace=actual["number"], position="hosted")
        validate_record(self.record, self.chart)
        self.record["roles"][0]["position"] = "main"
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_final_record_cannot_have_only_auxiliary_roles(self):
        self.record["roles"][0]["primary"] = False
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_missing_evidence_role_rule_or_source_is_rejected(self):
        for group, field, value in (("conclusions", "support_ids", ["missing"]),
                                    ("evidence", "role_ids", ["missing"]),
                                    ("evidence", "source_id", "MJ-2"),
                                    ("evidence", "rule_id", "invented-rule")):
            record = deepcopy(self.record)
            record[group][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_record(record, self.chart)

    def test_unknown_and_false_cannot_be_used_as_established_support(self):
        for state in ("unknown", "false"):
            self.record["evidence"][0]["applicability"] = state
            with self.subTest(state=state), self.assertRaises(ValueError):
                validate_record(self.record, self.chart)

    def test_critical_unknown_blocks_direction_even_when_excluded(self):
        unknown = deepcopy(self.record["evidence"][0])
        unknown.update(id="e2", applicability="unknown", critical=True, dedup_key="unresolved-condition")
        self.record["evidence"].append(unknown)
        conclusion = self.record["conclusions"][0]
        conclusion["excluded_ids"] = ["e2"]
        conclusion["dispositions"] = [{"evidence_id": "e2", "reason": "还未核实该关键条件。"}]
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)
        self.record["results"][0].update(state="undetermined", reason="关键条件未知")
        conclusion.update(judgment="undetermined", reason="关键条件未知")
        validate_record(self.record, self.chart)

    def test_conclusion_cannot_drift_from_declared_result_horizon(self):
        self.record["conclusions"][0]["horizon"] = {"state": "fixed", "start": "2026-10-14T05:27:13+00:00", "end": "2026-11-14T05:27:13+00:00"}
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_unknown_horizon_requires_undetermined_not_date_specific_direction(self):
        horizon = {"state": "unknown", "reason": "题目要求截止时间但尚未提供。"}
        self.record["results"][0]["horizon"] = horizon
        self.record["conclusions"][0]["horizon"] = deepcopy(horizon)
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_current_horizon_must_use_original_instant(self):
        horizon = {"state": "current", "at": "2026-10-15T05:27:13+00:00"}
        self.record["results"][0]["horizon"] = horizon
        self.record["conclusions"][0]["horizon"] = deepcopy(horizon)
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_every_declared_result_requires_its_own_conclusion(self):
        second = deepcopy(self.record["results"][0])
        second.update(id="o2", target="后续期限", state="undetermined", reason="未找到有完整条件的应期方法")
        self.record["results"].append(second)
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_counter_evidence_needs_disposition_and_joint_reason(self):
        opposite = deepcopy(self.record["evidence"][0])
        opposite.update(id="e2", polarity="opposes", dedup_key="opposite-fact")
        self.record["evidence"].append(opposite)
        conclusion = self.record["conclusions"][0]
        conclusion["counter_ids"] = ["e2"]
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)
        conclusion["dispositions"] = [{"evidence_id": "e2", "reason": "限定为另一层面的提示，不改变当前分项。"}]
        conclusion["synthesis_reason"] = ""
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)
        conclusion["synthesis_reason"] = "按事类范围比较两条依据，只对当前安排作有限判断。"
        validate_record(self.record, self.chart)

    def test_same_source_fact_cannot_be_counted_as_two_independent_supports(self):
        duplicate = deepcopy(self.record["evidence"][0])
        duplicate["id"] = "e2"
        self.record["evidence"].append(duplicate)
        self.record["conclusions"][0]["support_ids"].append("e2")
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_mixed_cannot_pass_with_only_one_side(self):
        self.record["conclusions"][0]["judgment"] = "mixed"
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_imagery_cannot_be_declared_verified_without_prior_fact(self):
        self.record["imagery"][0].update(status="verified_context", known_fact_id="later-outcome")
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_real_outcome_fields_are_kept_outside_the_pre_reading_ledger(self):
        self.record["actual_outcome"] = {"success": True}
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_external_method_needs_registered_url_and_limited_scope(self):
        self.record["external_sources"] = [{"id": "EXT-1", "url": "https://example.org/edition/page", "location": "虚构示例章节", "scope": "演示外部出处登记，非真实证据"}]
        self.record["external_methods"] = [{"id": "EXT-M", "source_id": "EXT-1", "scope": "仅示范方法注册", "limitations": "未核实际正文，不能宣称古法效验"}]
        self.record["method_profile"]["method_id"] = "EXT-M"
        validate_record(self.record, self.chart)
        self.record["external_sources"][0]["url"] = "arbitrary-untraceable-source"
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def _set_candidate_window(self):
        horizon = {"state": "fixed", "start": "2026-10-14T05:27:13+00:00", "end": "2026-11-14T05:27:13+00:00"}
        self.record["results"][0]["horizon"] = horizon
        self.record["conclusions"][0]["horizon"] = deepcopy(horizon)
        self.record["timing"] = [{"result_id": "o1", "state": "candidate", "reason": "虚构窗口",
                                  "source_id": "SK-1", "rule_id": "MODERN_WORKLOAD", "evidence_ids": ["e1"],
                                  "windows": [{"start": "2026-10-15T00:00:00+00:00", "end": "2026-10-16T00:00:00+00:00", "kind": "primary"}]}]

    def test_general_method_cannot_be_used_as_an_enabled_date_rule(self):
        self._set_candidate_window()
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_explicit_external_date_method_stays_inside_declared_result_window(self):
        self._set_candidate_window()
        self.record["external_rules"] = [{"id": "EXT-TIME", "source_id": "SK-1",
                                          "scope": "仅为测试外部显式应期条件，不是真实术理规则。",
                                          "requirements": ["虚构的已核触发条件"], "exceptions": [],
                                          "timing": {"status": "enabled", "event_scope": "虚构事件",
                                                     "exact_date_rule": "演示一个主窗口；无现实预测依据。"}}]
        self.record["timing"][0]["rule_id"] = "EXT-TIME"
        validate_record(self.record, self.chart)
        self.record["timing"][0]["windows"][0]["end"] = "2027-01-01T00:00:00+00:00"
        with self.assertRaises(ValueError):
            validate_record(self.record, self.chart)

    def test_cli_init_does_not_overwrite_and_validate_rejects_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            chart_path, record_path = Path(directory) / "chart.json", Path(directory) / "reading.json"
            chart_path.write_text(json.dumps(self.chart, ensure_ascii=False), encoding="utf-8")
            args = ["init", "--chart", str(chart_path), "--question", "虚构问题", "--output", str(record_path)]
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 0)
                first = record_path.read_bytes()
                self.assertEqual(main(args), 1)
                self.assertEqual(record_path.read_bytes(), first)
                self.assertEqual(main(["validate", str(record_path), "--chart", str(chart_path)]), 1)
                record_path.write_text(json.dumps(self.record, ensure_ascii=False), encoding="utf-8")
                self.assertEqual(main(["validate", str(record_path), "--chart", str(chart_path)]), 0)


if __name__ == "__main__":
    unittest.main()
