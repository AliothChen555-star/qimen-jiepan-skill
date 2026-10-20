"""Create and validate an interpretation ledger; never predict or rate fortune."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from chart_validation import validate_chart
from qimen.rules import STARS

SCHEMA_VERSION = "qimen_reading_record_v1"
PROFILE_FIELDS = ("timezone", "longitude", "latitude", "time_mode", "day_boundary",
                  "horse_basis", "yuan_strategy", "center_policy")


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value, label):
    _need(isinstance(value, str) and bool(value.strip()), f"{label} 必须为非空文本")
    return value


def _list(value, label):
    _need(isinstance(value, list), f"{label} 必须为列表")
    return value


def _index(items, label):
    result = {}
    for item in _list(items, label):
        _need(isinstance(item, dict), f"{label} 条目必须为对象")
        key = _text(item.get("id"), f"{label}.id")
        _need(key not in result, f"{label} ID 重复：{key}")
        result[key] = item
    return result


def _instant(value, label):
    _text(value, label)
    try:
        date = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 不是 ISO 8601 时间") from exc
    _need(date.tzinfo is not None and date.utcoffset() is not None, f"{label} 必须含时区偏移")
    return date.astimezone(timezone.utc)


def canonical_chart_hash(chart):
    """Hash full original JSON data independently of whitespace/key ordering."""
    canonical = json.dumps(chart, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def init_record(chart, question):
    validate_chart(chart)
    _text(question, "question")
    return {"schema_version": SCHEMA_VERSION, "status": "draft",
            "chart_ref": {"sha256": canonical_chart_hash(chart),
                          "instant_utc": chart["input"]["captured_at_utc"],
                          "rule_version": chart["rule_version"]},
            "method_profile": {"chart": {k: chart["input"][k] for k in PROFILE_FIELDS},
                               "star_season": "tongzong", "method_id": None},
            "question": question, "known_facts": [], "external_sources": [],
            "external_methods": [], "external_rules": [], "roles": [], "results": [],
            "evidence": [], "conclusions": [], "imagery": [], "timing": []}


def _registry(record):
    data = json.loads((Path(__file__).resolve().parents[1] / "assets" / "rules.json").read_text(encoding="utf-8-sig"))
    sources = _index(data["sources"], "sources")
    methods = _index(data["methods"], "methods")
    rules = _index(data["rules"], "rules")
    for sid, source in _index(record["external_sources"], "external_sources").items():
        _need(sid not in sources, f"external source 覆盖现有来源：{sid}")
        url = urlparse(_text(source.get("url"), f"{sid}.url"))
        _need(url.scheme in ("https", "http") and bool(url.netloc), f"{sid}.url 必须为 http(s) 来源页面")
        for field in ("location", "scope"):
            _text(source.get(field), f"{sid}.{field}")
        sources[sid] = source
    for key, target in (("external_methods", methods), ("external_rules", rules)):
        for rid, item in _index(record[key], key).items():
            _need(rid not in target and rid not in (rules if target is methods else methods), f"外部方法或规则 ID 冲突：{rid}")
            _need(item.get("source_id") in sources, f"{rid} 缺少登记来源")
            _text(item.get("scope"), f"{rid}.scope")
            if key == "external_methods":
                _text(item.get("limitations"), f"{rid}.limitations")
            else:
                for field in ("requirements", "exceptions"):
                    for text in _list(item.get(field), f"{rid}.{field}"):
                        _text(text, f"{rid}.{field}")
                _need(bool(item["requirements"]), f"{rid} 必须列完整前提")
            target[rid] = item
    return sources, methods, {**methods, **rules}


def _horizon(value, anchor, label):
    _need(isinstance(value, dict), f"{label} 必须为对象")
    state = value.get("state")
    if state == "fixed":
        _need(set(value) == {"state", "start", "end"}, f"{label} fixed 字段不完整或混用状态")
        start, end = (_instant(value[k], f"{label}.{k}") for k in ("start", "end"))
        _need(end > start, f"{label} 结束须晚于开始")
        return state, start, end
    if state == "current":
        _need(set(value) == {"state", "at"}, f"{label} current 仅使用 at")
        _need(_instant(value["at"], f"{label}.at") == anchor, f"{label} 现状时刻须等于原盘绝对时刻")
        return state, anchor, anchor
    _need(state == "unknown" and set(value) == {"state", "reason"}, f"{label} 须选 fixed/current/unknown")
    _text(value.get("reason"), f"{label}.reason")
    return state, None, None


def _role(role, palaces, sources):
    rid = role["id"]
    for field in ("object", "value"):
        _text(role.get(field), f"roles.{rid}.{field}")
    _need(role.get("source_id") in sources, f"角色 {rid} 缺少登记取用来源")
    _need(type(role.get("primary")) is bool, f"角色 {rid}.primary 必须为布尔值")
    number = role.get("palace")
    _need(type(number) is int and number in palaces, f"角色 {rid} 落宫不存在")
    palace, kind, layer, value = palaces[number], role.get("kind"), role.get("layer"), role["value"]
    position = role.get("position")
    _need(position in ("main", "hosted"), f"角色 {rid} 须注明主寄")
    if kind == "stem":
        _need(layer in ("earth", "heaven"), f"角色 {rid} 干的层次不符")
        _need(not (layer == "heaven" and number == 5), f"角色 {rid} 中五展示干不能作独立天盘角色")
        stems = palace[f"{layer}_stems"]
        index = 0 if position == "main" else 1
        _need(len(stems) > index and stems[index] == value, f"角色 {rid} 干、宫或主寄不符原盘")
    elif kind == "star":
        _need(layer in ("heaven", "earth"), f"角色 {rid} 星的层次不符")
        stars = palace["stars"] if layer == "heaven" else (
            [] if number == 5 else [STARS[number]] + (["天禽"] if number == 2 else []))
        index = 0 if position == "main" else 1
        _need(len(stars) > index and stars[index] == value, f"角色 {rid} 星、宫或主寄不符原盘")
    else:
        _need(kind in ("door", "spirit"), f"角色 {rid} 不支持该符号种类")
        _need(layer == ("human" if kind == "door" else "deity"), f"角色 {rid} 门神层次不符")
        _need(position == "main" and palace[kind] == value and bool(value), f"角色 {rid} 门神落宫不符")


def _refs(value, evidence, result_id, label):
    refs = _list(value, label)
    _need(all(isinstance(x, str) for x in refs) and len(refs) == len(set(refs)), f"{label} 引用重复或类型错误")
    for eid in refs:
        _need(eid in evidence and evidence[eid]["result_id"] == result_id, f"{label} 引用缺失或跨分项：{eid}")
    return set(refs)


def validate_record(record, chart, *, final=True):
    """Check a ledger's declared structure, not truth of facts or forecast validity."""
    palaces = validate_chart(chart)
    template = init_record(chart, "schema")
    _need(isinstance(record, dict) and set(record) == set(template), "记录顶层字段不完整或夹带结局等未定义字段")
    _need(record.get("schema_version") == SCHEMA_VERSION, "记录 schema_version 不支持")
    _need(record.get("status") in ("draft", "final"), "status 须为 draft/final")
    _need(not final or record["status"] == "final", "draft 不是完成的事前判断")
    _need(record["chart_ref"] == template["chart_ref"], "记录原盘 hash、时刻或规则版本不符；不得换盘")
    _text(record["question"], "question")
    profile = record["method_profile"]
    _need(isinstance(profile, dict) and set(profile) == {"chart", "star_season", "method_id"}, "method_profile 字段不符")
    _need(profile["chart"] == template["method_profile"]["chart"], "method_profile 与原盘方法配置不符")
    _need(profile["star_season"] in ("tongzong", "yanyi_prose"), "九星月令方法未支持")
    sources, methods, rules = _registry(record)
    _need(not final or profile["method_id"] in methods, "final 必须选已登记或有出处范围限制的外部方法")
    facts = _index(record["known_facts"], "known_facts")
    for fid, fact in facts.items():
        _text(fact.get("text"), f"known_facts.{fid}.text")
        _need(fact.get("basis") == "provided_before_reading", f"known_facts.{fid} 只记录判断前已知背景")
    roles = _index(record["roles"], "roles")
    for role in roles.values():
        _role(role, palaces, sources)
    _need(not final or any(role["primary"] for role in roles.values()), "final 至少应有一个明确的主要角色")
    results = _index(record["results"], "results")
    anchor = _instant(template["chart_ref"]["instant_utc"], "chart_ref.instant_utc")
    horizons = {}
    for rid, result in results.items():
        for key in ("target", "stage", "success_criteria"):
            _text(result.get(key), f"results.{rid}.{key}")
        horizons[rid] = _horizon(result.get("horizon"), anchor, f"results.{rid}.horizon")
        _need(result.get("state") in ("assessed", "undetermined"), f"结果 {rid} 须声明判断状态")
        if result["state"] == "undetermined":
            _text(result.get("reason"), f"results.{rid}.reason")
    evidence = _index(record["evidence"], "evidence")
    for eid, item in evidence.items():
        _need(item.get("result_id") in results, f"证据 {eid} 指向不存在的分项结果")
        role_ids = _list(item.get("role_ids"), f"evidence.{eid}.role_ids")
        _need(bool(role_ids) and all(isinstance(r, str) for r in role_ids)
              and len(role_ids) == len(set(role_ids)) and all(r in roles for r in role_ids), f"证据 {eid} 角色缺失或重复")
        rule_id = item.get("rule_id")
        _need(rule_id in rules and item.get("source_id") == rules[rule_id]["source_id"], f"证据 {eid} 来源、规则未登记或不一致")
        _need(item.get("applicability") in ("true", "false", "unknown"), f"证据 {eid} 须给三态适用结果")
        _need(item.get("polarity") in ("supports", "opposes", "neutral"), f"证据 {eid} 须相对成功标准注明方向")
        _need(type(item.get("critical")) is bool, f"证据 {eid}.critical 必须为布尔值")
        for key in ("fact", "inference", "dedup_key"):
            _text(item.get(key), f"evidence.{eid}.{key}")
    conclusions = _index(record["conclusions"], "conclusions")
    covered = set()
    for cid, conclusion in conclusions.items():
        rid = conclusion.get("result_id")
        _need(rid in results and rid not in covered, f"结论 {cid} 分项缺失或重复主判")
        covered.add(rid)
        _need(conclusion.get("horizon") == results[rid]["horizon"], f"结论 {cid} 主判期限/现状范围漂移")
        judgment = conclusion.get("judgment")
        _need(judgment in ("favorable", "adverse", "mixed", "undetermined"), f"结论 {cid} 判断状态不支持")
        _text(conclusion.get("claim"), f"conclusions.{cid}.claim")
        _text(conclusion.get("synthesis_reason"), f"conclusions.{cid}.synthesis_reason")
        _need((judgment == "undetermined") == (results[rid]["state"] == "undetermined"), f"结论 {cid} 与结果判断状态冲突")
        if judgment == "undetermined":
            _text(conclusion.get("reason"), f"conclusions.{cid}.reason")
        _need(horizons[rid][0] != "unknown" or judgment == "undetermined", f"结论 {cid} 期限未知时不能判定该期限内方向")
        groups = {key: _refs(conclusion.get(key), evidence, rid, f"{cid}.{key}")
                  for key in ("support_ids", "counter_ids", "excluded_ids")}
        support, counter, excluded = (groups[k] for k in ("support_ids", "counter_ids", "excluded_ids"))
        _need(not (support & counter or support & excluded or counter & excluded), f"结论 {cid} 同一证据多重计数")
        relevant = {eid for eid, e in evidence.items() if e["result_id"] == rid}
        _need(support | counter | excluded == relevant, f"结论 {cid} 遗漏证据处置")
        for eid in support | counter:
            _need(evidence[eid]["applicability"] == "true", f"结论 {cid} 把 false/unknown 当成立证据")
        keys = [evidence[eid]["dedup_key"] for eid in support | counter]
        _need(len(keys) == len(set(keys)), f"结论 {cid} 同源证据不能按独立依据重复计入")
        _need(not any(e["critical"] and e["applicability"] == "unknown" for e in evidence.values() if e["result_id"] == rid)
              or judgment == "undetermined", f"结论 {cid} 有关键 unknown，不能给确定方向")
        if judgment in ("favorable", "adverse"):
            expected = "supports" if judgment == "favorable" else "opposes"
            _need(bool(support) and any(evidence[e]["polarity"] == expected for e in support), f"结论 {cid} 缺少对应方向的成立依据")
            _need(all(evidence[e]["polarity"] in (expected, "neutral") for e in support), f"结论 {cid} 支持证据方向冲突")
            opposite = "opposes" if judgment == "favorable" else "supports"
            _need(all(evidence[e]["polarity"] == opposite for e in counter), f"结论 {cid} 反向证据方向不符")
        if judgment == "mixed":
            _need({evidence[e]["polarity"] for e in support | counter} >= {"supports", "opposes"},
                  f"结论 {cid} mixed 须有成立的正反两面依据")
        dispositions = conclusion.get("dispositions")
        _list(dispositions, f"{cid}.dispositions")
        handled = set()
        for disposition in dispositions:
            _need(isinstance(disposition, dict), f"{cid}.dispositions 须为对象")
            eid = disposition.get("evidence_id")
            _need(eid in counter | excluded and eid not in handled, f"结论 {cid} 反向/排除处置引用不符")
            handled.add(eid)
            _text(disposition.get("reason"), f"{cid}.dispositions.reason")
        _need(handled == counter | excluded, f"结论 {cid} 反向或排除证据未说明处置理由")
    _need(not final or (bool(roles) and bool(results) and covered == set(results)), "final 必须有真实角色及覆盖全部分项的结论")
    for item in _list(record["imagery"], "imagery"):
        _need(isinstance(item, dict), "imagery 条目须为对象")
        role_ids = _list(item.get("role_ids"), "imagery.role_ids")
        _need(bool(role_ids) and all(r in roles for r in role_ids), "imagery 角色未登记")
        _text(item.get("interpretation"), "imagery.interpretation")
        _need(item.get("status") in ("hypothesis", "verified_context"), "取象只可标假设或已知背景")
        if item["status"] == "verified_context":
            _need(item.get("known_fact_id") in facts, "取象证实必须指向事前已知背景；真实后验结果另存")
        else:
            _text(item.get("verification"), "imagery.verification")
    timing_seen = set()
    for item in _list(record["timing"], "timing"):
        _need(isinstance(item, dict), "timing 条目须为对象")
        rid = item.get("result_id")
        _need(rid in results and rid not in timing_seen, "timing 分项不存在或重复")
        timing_seen.add(rid)
        state = item.get("state")
        _need(state in ("candidate", "undetermined", "not_applicable"), "timing 状态不支持")
        _text(item.get("reason"), "timing.reason")
        windows = _list(item.get("windows"), "timing.windows")
        if state != "candidate":
            _need(not windows, "未定/不适用应期不能夹带日期窗口")
            continue
        _need(results[rid]["state"] == "assessed" and horizons[rid][0] == "fixed", "应期候选须有已评估的固定结果范围")
        _need(item.get("rule_id") in rules and item.get("source_id") == rules[item["rule_id"]]["source_id"], "应期须有登记的事类规则来源")
        timing_rule = rules[item["rule_id"]].get("timing", {})
        _need(isinstance(timing_rule, dict) and timing_rule.get("status") == "enabled",
              "所引规则没有启用完整应期方法；日历匹配或一般格局不能作日期证据")
        _text(timing_rule.get("exact_date_rule"), "timing rule.exact_date_rule")
        _text(timing_rule.get("event_scope"), "timing rule.event_scope")
        refs = _refs(item.get("evidence_ids"), evidence, rid, "timing.evidence_ids")
        _need(bool(refs) and all(evidence[e]["applicability"] == "true" for e in refs), "应期不能由未知/不成立条件支撑")
        primary = 0
        for window in windows:
            _need(isinstance(window, dict) and window.get("kind") in ("primary", "alternative"), "日期窗口须标主选或备选")
            primary += window["kind"] == "primary"
            start, end = (_instant(window.get(k), f"timing.windows.{k}") for k in ("start", "end"))
            _need(horizons[rid][1] <= start < end <= horizons[rid][2], "应期窗口越出对应主判范围")
        _need(primary == 1, "应期须且只能有一个主窗口")
    return {"status": "valid_final_record" if final else "draft_checked",
            "schema_version": SCHEMA_VERSION, "chart_sha256": template["chart_ref"]["sha256"],
            "role_count": len(roles), "result_count": len(results),
            "scope": "仅校记录引用、层次、条件与范围一致性；不证明事实真实或预测有效"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--chart", type=Path, required=True)
    init.add_argument("--question", required=True)
    init.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("record", type=Path)
    validate.add_argument("--chart", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        chart = json.loads(args.chart.read_text(encoding="utf-8-sig"))
        if args.command == "init":
            record = init_record(chart, args.question)
            # Never overwrite an earlier ledger, including its prior predictions.
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            result = {"status": "draft_created", "output": str(args.output)}
        else:
            result = validate_record(json.loads(args.record.read_text(encoding="utf-8-sig")), chart)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"解盘记录校验失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
