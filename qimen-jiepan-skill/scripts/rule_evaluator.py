"""Attach sourced rule conditions to facts; never select roles or predict events."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from qimen.rules import DOORS, GAN_SEQUENCE, PALACES, SEXAGENARY, STEMS

RULE_FILE = Path(__file__).resolve().parents[1] / "assets" / "rules.json"
PURPOSES = ("interpretation", "use_as_favorable", "event_judgment", "exception")
ELEMENTS = dict(zip(STEMS, "木木火火土土金金水水"))
CONTROL = dict(zip("木火土金水", "土金水木火"))
DOOR_ELEMENTS = dict(zip(DOORS.values(), "水土木木火土金金"))
QI_TOMBS_ZG4 = {"乙": 2, "丙": 6, "丁": 8}
PUNISHMENTS = {"戊": 3, "己": 2, "庚": 8, "辛": 9, "壬": 4, "癸": 4}


@lru_cache(maxsize=1)
def registry():
    data = json.loads(RULE_FILE.read_text(encoding="utf-8"))
    rules = data["rules"]
    ids = [r["id"] for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("规则卡 id 重复")
    sources = {s["id"] for s in data["sources"]}
    for card in rules:
        for key in ("name", "scope", "geometry", "required_conditions", "exceptions", "verification"):
            if key not in card:
                raise ValueError(f"规则 {card['id']} 缺 {key}")
        if card["source_id"] not in sources:
            raise ValueError(f"规则 {card['id']} 来源未登记")
    return data


def rule_by_id(rule_id):
    return next((r for r in registry()["rules"] if r["id"] == rule_id), None)


def _resolve(value, chart):
    if not isinstance(value, str) or not value.startswith("$"):
        return value
    if value == "$current_hidden_jia":
        return chart.get("xun", {}).get("hidden_stem")
    if value.startswith("$resolved_") and value.endswith("_stem"):
        field = value[len("$resolved_"):-len("_stem")]
        pillar = chart.get("calendar", {}).get(field + "_pillar")
        if pillar not in SEXAGENARY:
            return None
        return GAN_SEQUENCE[SEXAGENARY.index(pillar) // 10] if pillar[0] == "甲" else pillar[0]
    return None


def geometry_matches(card, palace, *, chart=None, pair=None):
    """Return bool/None for the registry's local pattern geometry only."""
    geometry, chart = card["geometry"], chart or {}
    kind = geometry["type"]
    if kind not in ("compound", "stem_pair", "stem_pairs", "dynamic_pair", "time_pattern"):
        return None
    if kind == "stem_pairs":
        return None if pair is None else pair["heaven"] + pair["earth"] in geometry["pairs"]
    checks = []
    for key in ("heaven", "earth", "door", "spirit", "palace", "zhi_shi"):
        if key not in geometry:
            continue
        wanted = _resolve(geometry[key], chart)
        if wanted is None:
            checks.append(None)
            continue
        if key in ("heaven", "earth"):
            actual = None if pair is None else pair.get(key)
        elif key == "palace":
            actual = palace.get("number")
        else:
            actual = palace.get(key)
        checks.append(None if actual is None else actual in wanted if isinstance(wanted, list) else actual == wanted)
    return False if False in checks else None if None in checks else True


def _manual_value(context, rule_id, condition):
    check = context.get("checks", {}).get(rule_id, {}).get(condition["id"])
    if not isinstance(check, dict) or not isinstance(check.get("basis"), str) or not check["basis"].strip():
        return None, "须有本次对象、来源及核验依据；无记录不作成立"
    actual = check.get("value")
    if type(actual) not in (bool, str) or (isinstance(actual, str) and not actual):
        return None, "核验值无效"
    expected = condition.get("expected", True)
    if type(actual) is not type(expected):
        return None, "核验值类型与规则要求不符，不把文字true当布尔核实"
    return actual == expected, check["basis"]


def _condition_value(condition, card, palace, chart, pair, context):
    evaluator = condition["evaluator"]
    if evaluator == "manual":
        return _manual_value(context, card["id"], condition)
    if evaluator == "no_door_pressure":
        door, number = palace.get("door"), palace.get("number")
        if door not in DOOR_ELEMENTS or number not in PALACES:
            return None, "缺门宫字段"
        return CONTROL[DOOR_ELEMENTS[door]] != PALACES[number][2], "据实际门五行克宫核门迫"
    if evaluator == "chief_star_same_palace":
        actual = palace.get("zhi_fu")
        return (actual if type(actual) is bool else None), "本旬值符星同宫；不是神盘值符"
    if evaluator == "chief_hidden_not_geng":
        hidden = chart.get("xun", {}).get("hidden_stem")
        return (None if hidden is None else hidden != "庚"), "据本时旬遁仪，不以戊简法替代"
    if evaluator == "no_qi_tomb":
        bindings = context.get("qi_tomb_bindings", {}).get(card["id"])
        if not isinstance(bindings, list) or not bindings:
            return None, "原法所指奇及层次未绑定；不自动全层套墓表"
        states = []
        for binding in bindings:
            if (not isinstance(binding, dict) or binding.get("source_id") != "ZG-4"
                    or not isinstance(binding.get("basis"), str) or not binding["basis"].strip()):
                return None, "须说明对象绑定依据及已核墓法来源"
            stem, layer = binding.get("stem"), binding.get("layer")
            if stem not in QI_TOMBS_ZG4 or layer != "heaven":
                return None, "当前仅自动核已绑定的天盘三奇；地盘或六仪不自行扩展"
            if stem not in palace.get("heaven_stems", []):
                return None, "绑定对象不在该宫实际天盘"
            states.append(palace["number"] != QI_TOMBS_ZG4[stem])
        return all(states), "据本次明确绑定对象及ZG-4三奇墓子集；不认证整张六仪墓表"
    if evaluator == "no_sixyi_punishment":
        stem = (pair or {}).get("heaven")
        method = context.get("punishment_method")
        if stem is None or method not in ("strict_current_xun", "all_heaven_extended"):
            return None, "须固定击刑对象与严格旬首或扩展口径"
        hit = PUNISHMENTS.get(stem) == palace.get("number")
        if method == "strict_current_xun":
            hidden = chart.get("xun", {}).get("hidden_stem")
            if hidden is None:
                return None, "缺本旬遁仪"
            hit = hit and stem == hidden
        return not hit, "仅对已绑定天盘仪与已选击刑口径核验"
    return None, "尚未实现的条件必须人工核验，不能默认成立"


def _state(value):
    return "true" if value is True else "false" if value is False else "unknown"


def _exception_checks(card, context):
    results = []
    for exception in card["exceptions"]:
        if not isinstance(exception, dict) or not exception.get("condition"):
            continue
        condition = exception["condition"]
        value, reason = _manual_value(context, card["id"], condition)
        binding = context.get("exception_bindings", {}).get(card["id"], {}).get(exception["id"])
        if (not isinstance(binding, dict) or not isinstance(binding.get("basis"), str)
                or not binding["basis"].strip()):
            value, reason = None, "未明确选择例外来源、主客身份及本事适用"
        elif (binding.get("source_id") != exception["source_id"] or
              binding.get("role") != exception.get("relieved_role")):
            value, reason = False, "所选来源或主客身份与本例外不符"
        results.append({"id": exception["id"], "source_id": exception["source_id"],
                        "description": exception["description"], "state": _state(value),
                        "condition_id": condition["id"], "basis": reason,
                        "binding": deepcopy(binding), "does_not_reverse_verdict": True})
    return results


def evaluate_application(card, palace, *, chart=None, pair=None, context=None, geometry=True):
    """Separate text interpretation, favorable use, event judgment, and exceptions."""
    if geometry is not None and type(geometry) is not bool:
        raise ValueError("geometry 必须为 true、false 或 null 三态")
    if context is not None and not isinstance(context, dict):
        raise ValueError("context 必须为对象或 null")
    chart, context = chart or {}, context or {}
    checks = []
    pair_key = (pair["heaven"] + pair["earth"] if pair and
                isinstance(pair.get("heaven"), str) and isinstance(pair.get("earth"), str) else None)
    for condition in card["required_conditions"]:
        if condition.get("when_pairs") and pair_key not in condition["when_pairs"]:
            continue
        value, basis = _condition_value(condition, card, palace, chart, pair, context)
        checks.append({"id": condition["id"], "description": condition["description"],
                       "state": _state(value), "critical": condition.get("critical", True),
                       "applies_to": condition.get("applies_to", "event_judgment"), "basis": basis})
    eligibility = {}
    for purpose in PURPOSES:
        relevant = [c for c in checks if c["critical"] and
                    (c["applies_to"] == purpose or isinstance(c["applies_to"], list) and purpose in c["applies_to"])]
        if geometry is False or any(c["state"] == "false" for c in relevant):
            state = "false"
        elif (geometry is None or card["verification"]["status"] != "verified"
              or purpose != "interpretation" and not relevant
              or any(c["state"] == "unknown" for c in relevant)):
            state = "unknown"
        else:
            state = "true"
        eligibility[purpose] = state
    exception_checks = _exception_checks(card, context)
    if exception_checks:
        states = [c["state"] for c in exception_checks]
        eligibility["exception"] = ("false" if geometry is False else "unknown" if geometry is None
                                    else "true" if "true" in states else "unknown" if "unknown" in states else "false")
    return {"rule_id": card["id"], "name": card["name"], "source_id": card["source_id"],
            "source_url": card["source_url"], "geometry_match": _state(geometry),
            "bindings": deepcopy(pair or {}), "eligibility": eligibility, "conditions": checks,
            "scope": card["scope"], "meaning": card["meaning"],
            "exceptions": deepcopy(card["exceptions"]), "exception_checks": exception_checks,
            "verification": deepcopy(card["verification"]),
            "not_an_event_verdict": True}


def local_rule_matches(palace, *, chart=None, context=None, types=None):
    """Match local registry cards, retaining actual main/hosted pair bindings."""
    chart, result, seen = chart or {}, [], set()
    types = set(types or ("compound", "stem_pair", "stem_pairs", "dynamic_pair", "time_pattern"))
    for card in registry()["rules"]:
        if card["geometry"]["type"] not in types:
            continue
        geometry = card["geometry"]
        need_h = "heaven" in geometry or geometry["type"] == "stem_pairs"
        need_e = "earth" in geometry or geometry["type"] == "stem_pairs"
        heavens = list(enumerate(palace.get("heaven_stems", []))) if need_h else [(None, None)]
        earths = list(enumerate(palace.get("earth_stems", []))) if need_e else [(None, None)]
        for hi, h in heavens:
            for ei, e in earths:
                pair = {"heaven": h, "earth": e,
                        "heaven_role": None if hi is None else "主干" if hi == 0 else "寄干",
                        "earth_role": None if ei is None else "主干" if ei == 0 else "寄干"}
                if geometry_matches(card, palace, chart=chart, pair=pair) is not True:
                    continue
                key = (card["id"], h, e, hi, ei)
                if key in seen:
                    continue
                seen.add(key)
                match = evaluate_application(card, palace, chart=chart, pair=pair, context=context)
                match["evidence_key"] = f"palace:{palace['number']}|rule:{card['id']}|heaven:{hi}:{h}|earth:{ei}:{e}"
                result.append(match)
    return result
