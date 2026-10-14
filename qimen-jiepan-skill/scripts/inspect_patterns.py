"""Read an existing kun2 chart and derive pattern facts, without recasting or divination."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from qimen.rules import (BRANCHES, BRANCH_PALACE, DOORS, GAN_SEQUENCE, PALACES,
                         RING, RULE_VERSION, SEXAGENARY, SPIRITS, STARS, STEMS)

ANALYSIS_VERSION = "qimen_patterns_v1.0.0"
GENERATES = dict(zip("木火土金水", "火土金水木"))
CONTROLS = dict(zip("木火土金水", "土金水木火"))
STEM_ELEMENTS = dict(zip(STEMS, "木木火火土土金金水水"))
BRANCH_ELEMENTS = dict(zip(BRANCHES, "水土木木土火火土金金土水"))
DOOR_ELEMENTS = dict(zip(DOORS.values(), "水土木木火土金金"))
STAR_ELEMENTS = {star: PALACES[p][2] for p, star in STARS.items()}
OPPOSITE = {1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4}
TOMBS = {"乙": (2, "未"), "癸": (2, "未"), "丙": (6, "戌"),
         "戊": (6, "戌"), "丁": (8, "丑"), "己": (8, "丑"),
         "庚": (8, "丑"), "辛": (4, "辰"), "壬": (4, "辰")}
PUNISHMENTS = {"戊": (3, "卯", "甲子"), "己": (2, "未", "甲戌"),
               "庚": (8, "寅", "甲申"), "辛": (9, "午", "甲午"),
               "壬": (4, "辰", "甲辰"), "癸": (4, "巳", "甲寅")}
COMBINATIONS = {frozenset(pair) for pair in ("乙庚", "丙辛", "丁壬", "戊癸")}
NAMED_PAIRS = {"乙辛": "青龙逃走", "辛乙": "白虎猖狂", "丁癸": "朱雀投江",
               "癸丁": "腾蛇夭矫", "庚丙": "太白入荧", "丙庚": "荧入太白",
               "庚癸": "大格", "庚己": "刑格", "庚壬": "上格/小格"}


def relation(a, b):
    """Directed relation of element A to element B."""
    if a == b:
        return "比和"
    if GENERATES[a] == b:
        return "A生B"
    if GENERATES[b] == a:
        return "B生A"
    if CONTROLS[a] == b:
        return "A克B"
    return "B克A"


def seasonal(element, month_element, *, star=False):
    key = relation(element, month_element)
    table = ({"比和": "相", "A生B": "旺", "B生A": "死", "A克B": "废", "B克A": "囚"}
             if star else
             {"比和": "旺", "A生B": "休", "B生A": "相", "A克B": "囚", "B克A": "死"})
    return {"state": table[key], "element": element, "month_element": month_element,
            "relation_A_to_month": key, "method": "统宗九星法" if star else "一般五行节月法"}


def plate_motion(movements):
    if all(m["origin"] == m["destination"] for m in movements):
        state = "伏吟"
    elif all(OPPOSITE[m["origin"]] == m["destination"] for m in movements):
        state = "反吟"
    else:
        state = "转动（非整体反伏吟）"
    return {"state": state, "evidence": movements}


def validate_chart(chart):
    if chart.get("rule_version") != RULE_VERSION or chart["input"]["center_policy"] != "kun2":
        raise ValueError("仅支持 chai_bu_v1.0.0 / kun2 的完整内置盘面")
    for key in ("year_pillar", "month_pillar", "day_pillar", "hour_pillar"):
        if chart["calendar"][key] not in SEXAGENARY:
            raise ValueError(f"calendar.{key} 不是有效干支")
    palaces = chart["palaces"]
    if len(palaces) != 9 or {p["number"] for p in palaces} != set(range(1, 10)):
        raise ValueError("盘面必须有不重复的九宫")
    by_number = {p["number"]: p for p in palaces}
    for p in palaces:
        n = p["number"]
        if (p["name"], p["direction"], p["element"]) != PALACES[n]:
            raise ValueError(f"{n}宫的名称、方位或五行不符")
        for field in ("earth_stems", "heaven_stems", "stars", "void_branches"):
            if not isinstance(p[field], list):
                raise ValueError(f"{n}宫 {field} 必须为列表")
        for field in ("void", "horse", "zhi_fu", "zhi_shi"):
            if type(p[field]) is not bool:
                raise ValueError(f"{n}宫 {field} 必须为布尔值")
        if any(s not in GAN_SEQUENCE for s in p["earth_stems"] + p["heaven_stems"]):
            raise ValueError(f"{n}宫含无效奇仪")
        if len(p["earth_stems"]) != (2 if n == 2 else 1):
            raise ValueError(f"{n}宫地盘寄干数量不符 kun2")
        if n == 5:
            if p["stars"] or p["door"] or p["spirit"] or p["heaven_stems"] != p["earth_stems"]:
                raise ValueError("中宫展示及留空字段不符 kun2")
        else:
            if p["door"] not in DOORS.values() or p["spirit"] not in SPIRITS:
                raise ValueError(f"{n}宫门或神缺失/无效")
            if not p["stars"] or p["stars"][0] == "天禽":
                raise ValueError(f"{n}宫主星缺失/无效")
            expected_stars = [p["stars"][0]] + (["天禽"] if p["stars"][0] == "天芮" else [])
            if p["stars"] != expected_stars or len(p["heaven_stems"]) != len(expected_stars):
                raise ValueError(f"{n}宫星及寄天干数量不符 kun2")
    if by_number[2]["earth_stems"][1] != by_number[5]["earth_stems"][0]:
        raise ValueError("坤二寄地干必须等于中五地干")
    earth = [p["earth_stems"][0] for p in palaces]
    heaven = [s for p in palaces if p["number"] != 5 for s in p["heaven_stems"]]
    stars = [s for p in palaces if p["number"] != 5 for s in p["stars"]]
    if Counter(earth) != Counter(GAN_SEQUENCE) or Counter(heaven) != Counter(GAN_SEQUENCE):
        raise ValueError("九干在地盘原宫和天盘外宫必须各出现一次（寄干计一次）")
    if Counter(stars) != Counter(STARS.values()):
        raise ValueError("九星必须各出现一次")
    if Counter(p["door"] for p in palaces if p["number"] != 5) != Counter(DOORS.values()):
        raise ValueError("八门必须各出现一次")
    if Counter(p["spirit"] for p in palaces if p["number"] != 5) != Counter(SPIRITS):
        raise ValueError("八神必须各出现一次")
    xun = chart["xun"]
    hour_index = SEXAGENARY.index(chart["calendar"]["hour_pillar"])
    head_index = hour_index // 10 * 10
    expected_void = [BRANCHES[(BRANCHES.index(SEXAGENARY[head_index][1]) + i) % 12] for i in (10, 11)]
    if (xun["head"] != SEXAGENARY[head_index] or xun["hidden_stem"] != GAN_SEQUENCE[hour_index // 10]
            or xun["void_branches"] != expected_void):
        raise ValueError("旬首、遁仪或旬空与时柱不符")
    chief = chart["chief"]
    for field in ("zhi_fu_palace", "zhi_shi_palace"):
        if chief[field] not in RING:
            raise ValueError(f"{field} 必须为实际外宫寄宫")
    if (chief["zhi_fu"] not in by_number[chief["zhi_fu_palace"]]["stars"]
            or chief["zhi_shi"] != by_number[chief["zhi_shi_palace"]]["door"]):
        raise ValueError("值符星或值使门与宫内字段不符")
    horse = chart["horse"]
    if horse["basis"] not in ("hour", "day"):
        raise ValueError("horse.basis 必须为 hour 或 day")
    basis = chart["calendar"]["hour_pillar" if horse["basis"] == "hour" else "day_pillar"][1]
    horse_branch = next(b for group, b in (("申子辰", "寅"), ("寅午戌", "申"),
                                         ("巳酉丑", "亥"), ("亥卯未", "巳")) if basis in group)
    if horse["basis_branch"] != basis or horse["branch"] != horse_branch or horse["palace"] != BRANCH_PALACE[horse_branch]:
        raise ValueError("马星与所用日支/时支不符")
    for p in palaces:
        n = p["number"]
        expected = [b for b in expected_void if BRANCH_PALACE[b] == n]
        if (p["void_branches"] != expected or p["void"] != bool(expected)
                or p["horse"] != (n == horse["palace"])
                or p["zhi_fu"] != (n == chief["zhi_fu_palace"])
                or p["zhi_shi"] != (n == chief["zhi_shi_palace"])):
            raise ValueError(f"{n}宫空马或符使标记与盘面总字段不符")
    return by_number


def stem_detail(stem, index, number, month, hidden, *, heaven):
    tomb_palace, tomb_branch = TOMBS[stem]
    data = {"stem": stem, "role": "主干" if index == 0 else "寄干",
            "seasonal": seasonal(STEM_ELEMENTS[stem], month),
            "relation_A_to_palace": relation(STEM_ELEMENTS[stem], PALACES[number][2]),
            "tomb": {"matches": number == tomb_palace, "palace": tomb_palace,
                     "branch": tomb_branch, "scope": "天盘干入墓" if heaven else "地盘墓位"}}
    if heaven:
        target, branch, hidden_jia = PUNISHMENTS.get(stem, (None, None, None))
        data["punishment"] = {"matches": number == target, "palace": target, "branch": branch,
                              "hidden_jia": hidden_jia, "is_current_xun": stem == hidden,
                              "method": "逐天盘六仪扩展法；严格旬首法须同时 is_current_xun"}
    return data


def pair_detail(h, e, hi, ei, hidden):
    names = []
    if h + e in NAMED_PAIRS:
        names.append(NAMED_PAIRS[h + e])
    if h == e:
        names.append("局部干伏吟")
    if h == hidden and e == "丙":
        names.append("青龙返首（旬首法）")
    if h == "丙" and e == hidden:
        names.append("飞鸟跌穴（旬首法）")
    if h == "戊" and e == "丙":
        names.append("青龙返首（戊丙简法）")
    if h == "丙" and e == "戊":
        names.append("飞鸟跌穴（丙戊简法）")
    if (h == "乙" and e in "己辛") or (h == "丙" and e in "戊庚") or (h == "丁" and e in "壬癸"):
        names.append("三奇得使（加六甲法）")
    if h == "庚" and e == hidden:
        names.append("伏宫格")
    if h == hidden and e == "庚":
        names.append("飞宫格")
    return {"heaven": h, "earth": e, "heaven_role": "主干" if hi == 0 else "寄干",
            "earth_role": "主干" if ei == 0 else "寄干", "condition": f"天{h}加地{e}",
            "relation_A_to_B": relation(STEM_ELEMENTS[h], STEM_ELEMENTS[e]),
            "five_combination": frozenset((h, e)) in COMBINATIONS,
            "named_patterns": names}


def compound_patterns(p):
    door, god, n = p["door"], p["spirit"], p["number"]
    matches = []
    for hi, h in enumerate(p["heaven_stems"]):
        prefix = f"天{h}（{'主干' if hi == 0 else '寄干'}）"
        for name, condition, text in (
            ("人遁", door == "休门" and h == "丁" and god == "太阴", "休门+太阴"),
            ("神遁", door == "生门" and h == "丙" and god == "九天", "生门+九天"),
            ("鬼遁", door == "杜门" and h == "乙" and god == "九地", "杜门+九地"),
            ("风遁", door in ("开门", "休门", "生门") and h == "乙" and n == 4, f"{door}+巽四"),
            ("龙遁", door == "休门" and h == "乙" and n == 1, "休门+坎一")):
            if condition:
                matches.append({"name": name, "condition": prefix + "+" + text})
        if door in ("开门", "休门", "生门") and h in "乙丙丁" and god in ("太阴", "六合", "九地"):
            matches.append({"name": {"太阴": "真诈", "六合": "休诈", "九地": "重诈"}[god],
                            "condition": prefix + f"+{door}+{god}"})
        for ei, e in enumerate(p["earth_stems"]):
            suffix = f"地{e}（{'主干' if ei == 0 else '寄干'}）"
            for name, condition in (
                ("天遁（演义丙丁法）", door == "生门" and h == "丙" and e == "丁"),
                ("地遁", door == "开门" and h == "乙" and e == "己"),
                ("云遁", door in ("开门", "休门", "生门") and h == "乙" and e == "辛"),
                ("虎遁", door == "休门" and h == "乙" and e == "辛" and n == 8)):
                if condition:
                    matches.append({"name": name, "condition": prefix + f"+{door}+" + suffix})
    if p["zhi_shi"] and "丁" in p["earth_stems"]:
        ei = p["earth_stems"].index("丁")
        matches.append({"name": "玉女守门", "condition": f"值使{door}+地丁（{'主干' if ei == 0 else '寄干'}）"})
    return matches


def inspect_chart(chart):
    by_number = validate_chart(chart)
    hidden = chart["xun"]["hidden_stem"]
    month_branch = chart["calendar"]["month_pillar"][1]
    month = BRANCH_ELEMENTS[month_branch]
    earth_origins = {p["earth_stems"][0]: (2 if p["number"] == 5 else p["number"])
                     for p in chart["palaces"]}
    star_origins = {star: (2 if n == 5 else n) for n, star in STARS.items()}
    door_origins = {door: n for n, door in DOORS.items()}
    star_moves, door_moves, stem_moves, details = [], [], [], []
    for n in RING:
        p = by_number[n]
        star_moves.extend({"item": s, "origin": star_origins[s], "destination": n} for s in p["stars"])
        door_moves.append({"item": p["door"], "origin": door_origins[p["door"]], "destination": n})
        stem_moves.extend({"item": s, "origin": earth_origins[s], "destination": n} for s in p["heaven_stems"])
        pairs = [pair_detail(h, e, hi, ei, hidden)
                 for hi, h in enumerate(p["heaven_stems"]) for ei, e in enumerate(p["earth_stems"])]
        for pair in pairs:
            h, e = pair["heaven"], pair["earth"]
            for key, label in (("year", "岁格"), ("month", "月格"), ("day", "日格/伏干格"), ("hour", "时格")):
                raw = chart["calendar"][key + "_pillar"][0]
                # A raw 甲 cannot be assigned to this hour's hidden stem for every pillar.
                if raw != "甲" and h == "庚" and e == raw:
                    pair["named_patterns"].append(label)
            raw_day = chart["calendar"]["day_pillar"][0]
            if raw_day != "甲" and h == raw_day and e == "庚":
                pair["named_patterns"].append("飞干格")
        door_relation = relation(DOOR_ELEMENTS[p["door"]], p["element"])
        details.append({"number": n, "name": p["name"], "element": p["element"],
            "palace_seasonal": seasonal(p["element"], month),
            "heaven": {"stars": [{"star": s, "seasonal": seasonal(STAR_ELEMENTS[s], month, star=True),
                                     "relation_A_to_palace": relation(STAR_ELEMENTS[s], p["element"])} for s in p["stars"]],
                       "stems": [stem_detail(s, i, n, month, hidden, heaven=True) for i, s in enumerate(p["heaven_stems"])]},
            "earth": {"stems": [stem_detail(s, i, n, month, hidden, heaven=False) for i, s in enumerate(p["earth_stems"])]},
            "human": {"door": p["door"], "seasonal": seasonal(DOOR_ELEMENTS[p["door"]], month),
                      "relation_A_to_palace": door_relation, "door_pressure": door_relation == "A克B",
                      "door_controlled": door_relation == "B克A"},
            "spirit": {"name": p["spirit"]}, "stem_pairs": pairs,
            "compound_patterns": compound_patterns(p), "void_branches": p["void_branches"],
            "horse": p["horse"], "zhi_fu": p["zhi_fu"], "zhi_shi": p["zhi_shi"]})
    day, hour = (chart["calendar"][k + "_pillar"][0] for k in ("day", "hour"))
    fu, shi = (chart["chief"][k + "_palace"] for k in ("zhi_fu", "zhi_shi"))
    return {"analysis_version": ANALYSIS_VERSION, "chart_rule_version": chart["rule_version"],
        "captured_at": chart["input"]["captured_at"],
        "methods": {"season": "月支五行；辰戌丑未土", "star_season": "统宗：子月旺、本月相、父母月死、鬼月囚、妻月废",
                    "punishment": "天盘六仪逐仪扩展法，同时标旬首；地盘不套击刑",
                    "tomb": "乙癸坤、丙戊乾、丁己庚艮、辛壬巽；地盘墓位与天盘入墓分开",
                    "compound": "演义九遁口径；天遁采用生门丙丁", "dragon_bird": "旬首法与戊丙简法分别标记"},
        "global": {"month_branch": month_branch, "month_element": month,
            "star_plate": plate_motion(star_moves), "door_plate": plate_motion(door_moves),
            "stem_plate": plate_motion(stem_moves),
            "five_not_meeting": {"matches": CONTROLS[STEM_ELEMENTS[hour]] == STEM_ELEMENTS[day]
                                     and STEMS.index(hour) % 2 == STEMS.index(day) % 2,
                                 "day_stem": day, "hour_stem": hour,
                                 "condition": "原时干克原日干且阴阳同性"},
            "chief_relation": {"A_zhi_fu_palace": fu, "B_zhi_shi_palace": shi,
                "relation_A_to_B": relation(PALACES[fu][2], PALACES[shi][2]),
                "same_palace": fu == shi, "opposite": OPPOSITE[fu] == shi},
            "void_branches": chart["xun"]["void_branches"], "horse": chart["horse"]},
        "palaces": details,
        "center": {"number": 5, "hosted_at": 2, "earth_stem": by_number[5]["earth_stems"][0],
                   "note": "中宫展示天干不作为独立天盘落点；随天禽的寄天干在外宫核验"},
        "not_computed": ["用神选择和问事结论", "应期", "未列明的其他门派格局",
                         "含甲的岁月日时格/飞伏干格（需另核对应六甲遁仪）"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chart", type=Path, help="Existing chart JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = inspect_chart(json.loads(args.chart.read_text(encoding="utf-8-sig")))
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            print(rendered, end="")
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        print(f"格局核验失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
