"""Semantic regression cases for sourced-rule geometry and three-state use.

These tests check interpretation contracts, not divination outcomes.  Small local
palaces are intentional condition fixtures, not claimed independently valid full
charts.  Full-chart integrity is tested by the arrangement suite.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pattern_readings import pair_reading
from rule_evaluator import (
    PURPOSES, evaluate_application, geometry_matches, local_rule_matches,
    registry, rule_by_id,
)


def local_palace(number=4, *, heaven=None, earth=None, door="生门",
                 spirit="九天", chief=False):
    return {
        "number": number,
        "heaven_stems": ["丙"] if heaven is None else heaven,
        "earth_stems": ["丁"] if earth is None else earth,
        "door": door, "spirit": spirit, "zhi_fu": chief, "zhi_shi": False,
    }


def actual_pair(heaven="丙", earth="丁", **extra):
    return {"heaven": heaven, "earth": earth,
            "heaven_role": "主干", "earth_role": "主干", **extra}


def condition(result, condition_id):
    return next(item for item in result["conditions"] if item["id"] == condition_id)


def domain_context(rule_id, value=True, basis="本次结果为经营助益；按本条事类和已绑定角色核实"):
    return {"checks": {rule_id: {"domain_scope_confirmed": {
        "value": value, "basis": basis,
    }}}}


def qi_context(rule_id="DUN_TIAN", stem="丙", layer="heaven"):
    return {"qi_tomb_bindings": {rule_id: [{
        "stem": stem, "layer": layer, "source_id": "ZG-4",
        "basis": "本次采用天盘丙为该条受检奇，按ZG-4丙临乾核墓",
    }]}}


def relief_context(rule_id="GEOM_乙辛", *, source="MJ-P", role="主"):
    return {
        "checks": {rule_id: {"host_guest_role_bound": {
            "value": True,
            "basis": "按本次往访关系法确认我留守为主；另行选用MJ-P凡例不害口径",
        }}},
        "exception_bindings": {rule_id: {"host_guest_relief": {
            "source_id": source, "role": role,
            "basis": "已选择该例外来源并核对现实主客身份；仅限不害，不据此判胜",
        }}},
    }


class RuleEvaluatorSemanticChecks(unittest.TestCase):
    def test_invalid_geometry_cannot_be_promoted_from_unknown_to_interpretation(self):
        card, palace = rule_by_id("DUN_TIAN"), local_palace()
        for value in ("false", "true", "unknown", 0, 1, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_application(card, palace, geometry=value)
        unknown = evaluate_application(card, palace, geometry=None)
        self.assertEqual(unknown["geometry_match"], "unknown")
        self.assertEqual(unknown["eligibility"]["interpretation"], "unknown")

    def test_invalid_context_cannot_silently_become_an_empty_confirmation(self):
        card, palace = rule_by_id("DUN_TIAN"), local_palace()
        for value in (False, "", [], "confirmed"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_application(card, palace, context=value)

    def test_tian_dun_geometry_does_not_invent_missing_qi_object(self):
        card = rule_by_id("DUN_TIAN")
        palace, pair = local_palace(), actual_pair()
        self.assertTrue(geometry_matches(card, palace, pair=pair))
        result = evaluate_application(card, palace, pair=pair)
        self.assertEqual(condition(result, "no_qi_tomb")["state"], "unknown")
        self.assertEqual(condition(result, "no_door_pressure")["state"], "true")
        self.assertEqual(result["eligibility"]["interpretation"], "true")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "unknown")
        self.assertEqual(result["eligibility"]["event_judgment"], "unknown")

    def test_tian_dun_pressure_blocks_favorable_use_with_geometry_preserved(self):
        # 生门 is earth and 克坎水: the combination remains, favorable use fails.
        card, pair = rule_by_id("DUN_TIAN"), actual_pair()
        palace = local_palace(1)
        self.assertTrue(geometry_matches(card, palace, pair=pair))
        result = evaluate_application(card, palace, pair=pair)
        self.assertEqual(condition(result, "no_door_pressure")["state"], "false")
        self.assertEqual(result["geometry_match"], "true")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "false")
        self.assertEqual(result["eligibility"]["interpretation"], "true")

    def test_explicit_verified_qi_binding_allows_only_corresponding_structural_check(self):
        card, pair = rule_by_id("DUN_TIAN"), actual_pair()
        context = qi_context()
        result = evaluate_application(card, local_palace(4), pair=pair, context=context)
        self.assertEqual(condition(result, "no_qi_tomb")["state"], "true")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "true")
        # A completed favorable-use condition is still not an event verdict.
        self.assertEqual(result["eligibility"]["event_judgment"], "unknown")
        self.assertTrue(result["not_an_event_verdict"])

    def test_tomb_binding_detects_actual_qi_tomb_without_deleting_name(self):
        result = evaluate_application(
            rule_by_id("DUN_TIAN"), local_palace(6), pair=actual_pair(),
            context=qi_context(),
        )
        self.assertEqual(condition(result, "no_qi_tomb")["state"], "false")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "false")
        self.assertEqual(result["geometry_match"], "true")
        self.assertEqual(result["eligibility"]["interpretation"], "true")

    def test_earth_layer_and_unverified_stem_are_not_automatically_certified(self):
        for stem, layer in (("丁", "earth"), ("戊", "heaven")):
            with self.subTest(stem=stem, layer=layer):
                result = evaluate_application(
                    rule_by_id("DUN_TIAN"), local_palace(),
                    pair=actual_pair(), context=qi_context(stem=stem, layer=layer),
                )
                self.assertEqual(condition(result, "no_qi_tomb")["state"], "unknown")

    def test_qi_binding_for_an_absent_stem_is_unknown(self):
        context = qi_context(stem="乙")
        result = evaluate_application(rule_by_id("DUN_TIAN"), local_palace(),
                                      pair=actual_pair(), context=context)
        self.assertEqual(condition(result, "no_qi_tomb")["state"], "unknown")

    def test_hosted_qi_is_checked_at_actual_palace_and_role_is_retained(self):
        palace = local_palace(6, heaven=["戊", "丙"])
        results = local_rule_matches(palace, context=qi_context())
        tian = next(r for r in results if r["rule_id"] == "DUN_TIAN")
        self.assertEqual(tian["bindings"]["heaven_role"], "寄干")
        self.assertEqual(condition(tian, "no_qi_tomb")["state"], "false")

    def test_missing_compound_geometry_is_not_a_rule_match(self):
        palace = local_palace(4, door="开门")
        self.assertFalse(geometry_matches(rule_by_id("DUN_TIAN"), palace,
                                          pair=actual_pair()))
        self.assertFalse(any(r["rule_id"] == "DUN_TIAN" for r in local_rule_matches(palace)))

    def test_conflicted_envoy_requires_the_chief_star_not_the_spirit(self):
        card, pair = rule_by_id("QI_ENVOY"), actual_pair("乙", "辛")
        for flag, wanted in ((True, "true"), (False, "false"), (None, "unknown")):
            with self.subTest(chief=flag):
                palace = local_palace(4, heaven=["乙"], earth=["辛"],
                                       spirit="值符", chief=flag)
                self.assertTrue(geometry_matches(card, palace, pair=pair))
                result = evaluate_application(card, palace, pair=pair)
                self.assertEqual(condition(result, "chief_star_same_palace")["state"], wanted)
                self.assertEqual(result["eligibility"]["use_as_favorable"], wanted)
                self.assertEqual(result["eligibility"]["interpretation"], "true")

    def test_nonconflicted_envoy_does_not_inherit_the_three_conflicted_pair_condition(self):
        result = evaluate_application(
            rule_by_id("QI_ENVOY"),
            local_palace(4, heaven=["乙"], earth=["己"], chief=False),
            pair=actual_pair("乙", "己"),
        )
        self.assertNotIn("chief_star_same_palace", [c["id"] for c in result["conditions"]])
        self.assertNotEqual(result["eligibility"]["use_as_favorable"], "false")

    def test_geng_chief_blocks_favorable_dragon_and_keeps_literal_pattern(self):
        card = rule_by_id("DRAGON_CHIEF")
        palace, pair = local_palace(4, heaven=["庚"], earth=["丙"]), actual_pair("庚", "丙")
        chart = {"xun": {"hidden_stem": "庚"}}
        self.assertTrue(geometry_matches(card, palace, chart=chart, pair=pair))
        result = evaluate_application(card, palace, chart=chart, pair=pair)
        self.assertEqual(condition(result, "chief_hidden_not_geng")["state"], "false")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "false")
        self.assertEqual(result["eligibility"]["interpretation"], "true")

    def test_non_geng_chief_is_not_silently_replaced_by_wu(self):
        card = rule_by_id("DRAGON_CHIEF")
        palace, pair = local_palace(4, heaven=["辛"], earth=["丙"]), actual_pair("辛", "丙")
        chart = {"xun": {"hidden_stem": "辛"}}
        self.assertTrue(geometry_matches(card, palace, chart=chart, pair=pair))
        result = evaluate_application(card, palace, chart=chart, pair=pair)
        self.assertEqual(result["eligibility"]["use_as_favorable"], "true")
        self.assertEqual(geometry_matches(rule_by_id("DRAGON_WU"), palace,
                                          chart=chart, pair=pair), False)

    def test_missing_chief_metadata_is_unknown_instead_of_lucky(self):
        card = rule_by_id("DRAGON_CHIEF")
        palace = local_palace(4, heaven=["庚"], earth=["丙"])
        pair = actual_pair("庚", "丙")
        geometry = geometry_matches(card, palace, pair=pair)
        self.assertIsNone(geometry)
        result = evaluate_application(card, palace, pair=pair, geometry=geometry)
        self.assertEqual(result["eligibility"]["interpretation"], "unknown")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "unknown")

    def test_manual_domain_check_without_nonempty_basis_remains_unknown(self):
        card, palace, pair = rule_by_id("DUN_TIAN"), local_palace(), actual_pair()
        checks = [None, True, {"value": True}, {"value": True, "basis": ""},
                  {"value": True, "basis": "   "}, {"value": True, "basis": 123}]
        for record in checks:
            with self.subTest(record=record):
                context = {"checks": {"DUN_TIAN": {"domain_scope_confirmed": record}}}
                result = evaluate_application(card, palace, pair=pair, context=context)
                self.assertEqual(result["eligibility"]["event_judgment"], "unknown")

    def test_domain_confirmation_and_rejection_are_distinct_from_favorable_use(self):
        card, pair, palace = rule_by_id("DUN_TIAN"), actual_pair(), local_palace()
        for value, wanted in ((True, "true"), (False, "false")):
            with self.subTest(value=value):
                result = evaluate_application(card, palace, pair=pair,
                                              context=domain_context("DUN_TIAN", value))
                self.assertEqual(result["eligibility"]["event_judgment"], wanted)
                self.assertEqual(result["eligibility"]["use_as_favorable"], "unknown")

    def test_wrong_manual_value_type_is_unknown_instead_of_a_known_rejection(self):
        for value in ("true", "false", 1, 0, [], {}):
            with self.subTest(value=value):
                context = domain_context("DUN_TIAN", value)
                result = evaluate_application(rule_by_id("DUN_TIAN"), local_palace(),
                                              pair=actual_pair(), context=context)
                self.assertEqual(result["eligibility"]["event_judgment"], "unknown")

    def test_invalid_qi_binding_basis_cannot_certify_an_object(self):
        for basis in ("", "   ", 1, {"claimed": "checked"}):
            with self.subTest(basis=basis):
                context = qi_context()
                context["qi_tomb_bindings"]["DUN_TIAN"][0]["basis"] = basis
                result = evaluate_application(rule_by_id("DUN_TIAN"), local_palace(),
                                              pair=actual_pair(), context=context)
                self.assertEqual(condition(result, "no_qi_tomb")["state"], "unknown")

    def test_strict_and_extended_punishment_are_distinct_choices(self):
        palace, pair = local_palace(3, heaven=["戊"], earth=["丙"]), actual_pair("戊", "丙")
        card, chart = rule_by_id("DRAGON_WU"), {"xun": {"hidden_stem": "辛"}}
        states = {}
        for method in ("strict_current_xun", "all_heaven_extended"):
            result = evaluate_application(card, palace, chart=chart, pair=pair,
                                          context={"punishment_method": method})
            states[method] = condition(result, "no_sixyi_punishment")["state"]
        self.assertEqual(states, {"strict_current_xun": "true", "all_heaven_extended": "false"})
        missing = evaluate_application(card, palace, chart=chart, pair=pair)
        self.assertEqual(condition(missing, "no_sixyi_punishment")["state"], "unknown")

    def test_verified_literal_reading_is_available_without_an_event_forecast(self):
        reading = pair_reading("乙", "丁")
        self.assertIsNotNone(reading)
        result = evaluate_application(rule_by_id("PAIR_乙丁"), local_palace(),
                                      pair=actual_pair("乙", "丁"))
        self.assertEqual(result["eligibility"]["interpretation"], "true")
        self.assertEqual(result["eligibility"]["event_judgment"], "unknown")
        self.assertEqual(result["eligibility"]["use_as_favorable"], "unknown")

    def test_partial_legacy_tomb_table_is_not_certified_by_three_verified_qi_items(self):
        result = evaluate_application(rule_by_id("STEM_TOMB_LEGACY"), local_palace(),
                                      pair=actual_pair())
        self.assertEqual(result["verification"]["status"], "partial")
        self.assertEqual(result["eligibility"]["interpretation"], "unknown")
        self.assertEqual(rule_by_id("STEM_TOMB_QI_ZG4")["verification"]["status"], "verified")

    def test_unlisted_pair_remains_unlisted_not_a_positive_fallback(self):
        self.assertIsNone(pair_reading("庚", "辛"))
        results = local_rule_matches(local_palace(4, heaven=["庚"], earth=["辛"]))
        self.assertFalse(any(r["rule_id"].startswith("PAIR_") for r in results))

    def test_source_registry_and_input_records_are_not_mutated_by_evaluation(self):
        card, palace, pair, context = rule_by_id("DUN_TIAN"), local_palace(), actual_pair(), qi_context()
        before = deepcopy((card, palace, pair, context))
        result = evaluate_application(card, palace, pair=pair, context=context)
        result["bindings"]["heaven"] = "壬"
        result["verification"]["status"] = "invented"
        self.assertEqual((card, palace, pair, context), before)

    def test_host_guest_exception_without_selected_variant_remains_unknown(self):
        result = evaluate_application(rule_by_id("GEOM_乙辛"), local_palace(),
                                      pair=actual_pair("乙", "辛"))
        self.assertEqual(result["source_id"], "ZG-4")
        self.assertEqual(result["exception_checks"][0]["source_id"], "MJ-P")
        self.assertEqual(result["exception_checks"][0]["state"], "unknown")
        self.assertEqual(result["eligibility"]["exception"], "unknown")
        self.assertEqual(result["eligibility"]["interpretation"], "true")

    def test_domain_approval_does_not_choose_another_source_host_guest_exception(self):
        result = evaluate_application(rule_by_id("GEOM_乙辛"), local_palace(),
                                      pair=actual_pair("乙", "辛"),
                                      context=domain_context("GEOM_乙辛"))
        self.assertEqual(result["eligibility"]["event_judgment"], "true")
        self.assertEqual(result["eligibility"]["exception"], "unknown")

    def test_explicit_selected_host_guest_relief_works_only_for_its_actual_role(self):
        for pair, role in (("乙辛", "主"), ("丁癸", "主"), ("辛乙", "客"), ("癸丁", "客")):
            with self.subTest(pair=pair, role=role):
                card = rule_by_id("GEOM_" + pair)
                result = evaluate_application(card, local_palace(),
                                              pair=actual_pair(*pair),
                                              context=relief_context(card["id"], role=role))
                self.assertEqual(result["exception_checks"][0]["state"], "true")
                self.assertEqual(result["exception_checks"][0]["binding"]["role"], role)
                self.assertEqual(result["eligibility"]["exception"], "true")
                self.assertTrue(result["exception_checks"][0]["does_not_reverse_verdict"])

    def test_wrong_source_or_role_does_not_activate_host_guest_relief(self):
        for source, role in (("ZG-4", "主"), ("MJ-P", "客"), (None, "主"), ("MJ-P", None)):
            with self.subTest(source=source, role=role):
                result = evaluate_application(rule_by_id("GEOM_乙辛"), local_palace(),
                                              pair=actual_pair("乙", "辛"),
                                              context=relief_context(source=source, role=role))
                self.assertEqual(result["exception_checks"][0]["state"], "false")
                self.assertEqual(result["eligibility"]["exception"], "false")

    def test_relief_needs_basis_for_both_identity_and_explicit_variant(self):
        for field in ("identity", "variant"):
            with self.subTest(field=field):
                context = relief_context()
                if field == "identity":
                    context["checks"]["GEOM_乙辛"]["host_guest_role_bound"].pop("basis")
                else:
                    context["exception_bindings"]["GEOM_乙辛"]["host_guest_relief"]["basis"] = "  "
                result = evaluate_application(rule_by_id("GEOM_乙辛"), local_palace(),
                                              pair=actual_pair("乙", "辛"), context=context)
                self.assertEqual(result["eligibility"]["exception"], "unknown")

    def test_relief_cannot_activate_when_pattern_geometry_is_false_or_unknown(self):
        for geometry, wanted in ((False, "false"), (None, "unknown")):
            with self.subTest(geometry=geometry):
                result = evaluate_application(rule_by_id("GEOM_乙辛"), local_palace(),
                                              pair=actual_pair("乙", "辛"),
                                              context=relief_context(), geometry=geometry)
                self.assertEqual(result["eligibility"]["exception"], wanted)

    def test_relief_does_not_change_event_verdict_or_remove_original_scope(self):
        card, palace, pair = rule_by_id("GEOM_乙辛"), local_palace(), actual_pair("乙", "辛")
        baseline = evaluate_application(card, palace, pair=pair)
        relief = evaluate_application(card, palace, pair=pair, context=relief_context())
        for purpose in ("interpretation", "use_as_favorable", "event_judgment"):
            self.assertEqual(baseline["eligibility"][purpose], relief["eligibility"][purpose])
        self.assertEqual(relief["source_id"], "ZG-4")
        self.assertEqual(baseline["meaning"], relief["meaning"])
        self.assertTrue(relief["not_an_event_verdict"])

    def test_all_nested_critical_exception_conditions_are_actually_evaluated(self):
        for card in registry()["rules"]:
            nested = [e for e in card["exceptions"] if isinstance(e, dict)
                      and e.get("condition", {}).get("critical", True)]
            if not nested:
                continue
            result = evaluate_application(card, local_palace())
            observed = {e["condition_id"] for e in result["exception_checks"]}
            expected = {e["condition"]["id"] for e in nested}
            self.assertEqual(observed, expected, card["id"])
            self.assertTrue(all(e["state"] == "unknown" for e in result["exception_checks"]))

    def test_all_critical_condition_purposes_are_known_including_nested_exceptions(self):
        seen = set()
        for card in registry()["rules"]:
            conditions = list(card["required_conditions"])
            conditions.extend(
                item["condition"] for item in card["exceptions"]
                if isinstance(item, dict) and "condition" in item
            )
            for item in conditions:
                if not item.get("critical", True):
                    continue
                purposes = item.get("applies_to", "event_judgment")
                purposes = purposes if isinstance(purposes, list) else [purposes]
                seen.update(purposes)
                self.assertTrue(all(p in PURPOSES for p in purposes),
                                (card["id"], item["id"], purposes))
        self.assertEqual(seen, set(PURPOSES))

    def test_list_purpose_conditions_propagate_the_same_known_failure(self):
        # Contract supports a condition affecting more than one explicit purpose.
        card = deepcopy(rule_by_id("PAIR_乙丁"))
        card["required_conditions"] = [{
            "id": "scope_pair", "description": "scope mismatch",
            "evaluator": "manual", "expected": True, "critical": True,
            "applies_to": ["interpretation", "event_judgment"],
        }]
        context = {"checks": {card["id"]: {"scope_pair": {
            "value": False, "basis": "对象不符，不能引用这一分事句",
        }}}}
        result = evaluate_application(card, local_palace(), context=context)
        self.assertEqual(result["eligibility"]["interpretation"], "false")
        self.assertEqual(result["eligibility"]["event_judgment"], "false")


if __name__ == "__main__":
    unittest.main()
