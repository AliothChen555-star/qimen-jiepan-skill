"""Selected directional readings, backed by the single maintained rule registry.

PAIR_READINGS and pair_reading retain the original public interfaces.  A selected
reading is not an event verdict.  Unknown pairs return None and require source
lookup; no five-element fallback invents a missing reading.
"""
from copy import deepcopy
import json
from pathlib import Path


_RULE_FILE = Path(__file__).resolve().parents[1] / "assets" / "rules.json"
with _RULE_FILE.open(encoding="utf-8") as _stream:
    _REGISTRY = json.load(_stream)
_PAIR_CARDS = {
    card["selected_pair"]: card
    for card in _REGISTRY["rules"]
    if card.get("selected_pair")
}

# Compatibility labels are imagery prompts, never asserted facts or rule effects.
_LABELS = {
    "乙丁": (("文书", "协作"), ("信息相佐", "协调")),
    "乙庚": (("交涉", "关系"), ("牵制", "争议")),
    "丙丙": (("文书", "资源"), ("重复牵迫", "耗损")),
    "丙丁": (("文书", "求名"), ("身份有别", "文书")),
    "丁丁": (("文书", "消息"), ("消息",)),
    "丁辛": (("身份", "文书"), ("释囚或失位须分身份",)),
    "丁壬": (("文书", "交涉"), ("恩诏与讼狱用途",)),
    "戊乙": (("谋事",), ("因门定助阻",)),
    "戊丁": (("求名", "文书"), ("助成受墓迫限制",)),
    "戊辛": (("推进", "资源"), ("推进受限",)),
    "戊壬": (("推进",), ("拘束", "难展")),
    "戊癸": (("谋事",), ("因门定助阻",)),
    "己丁": (("文书", "争议"), ("先曲后直",)),
    "己辛": (("状态",), ("不宁",)),
    "己癸": (("疾病", "词讼"), ("相关事类受限",)),
    "庚丁": (("交涉", "文书"), ("私昵词讼原义",)),
    "辛戊": (("谋事", "财利"), ("破财受抑", "妄动不利")),
    "辛丁": (("交易", "处境"), ("经商与囚人用途有别",)),
    "辛庚": (("竞争",), ("相残", "退让")),
    "壬辛": (("谋事",), ("缠绕不安", "谋望受欺")),
    "壬壬": (("人事",), ("内外缠绕",)),
    "癸己": (("消息", "避藏"), ("消息受阻", "避藏")),
}

READING_CONDITIONS = {
    condition["id"]: condition["description"]
    for card in _PAIR_CARDS.values()
    for condition in card["required_conditions"]
}

PAIR_READINGS = {
    pair: (
        card["name"], _LABELS[pair][0], _LABELS[pair][1],
        tuple(condition["id"] for condition in card["required_conditions"]),
        card["source_id"],
    )
    for pair, card in _PAIR_CARDS.items()
}

# Short excerpts retained for callers using the v0.6 interface.
PAIR_SOURCE_EXCERPTS = {
    "辛戊": "官司破财，屈抑守分，妄动祸殃。",
    "壬辛": "纵得吉门，亦不能安，若有谋望，被人欺瞒。",
}


def pair_reading(heaven, earth):
    """Return verified selected text and its limits; do not determine eligibility."""
    pair = heaven + earth
    row = PAIR_READINGS.get(pair)
    if row is None:
        return None
    name, topics, images, checks, source = row
    card = _PAIR_CARDS[pair]
    result = {
        "table_name": name,
        "topics": list(topics),
        "possible_images": list(images),
        "application_conditions": [
            condition["description"] for condition in card["required_conditions"]
        ],
        "source_id": source,
        "source_url": card["source_url"],
        "rule_id": card["id"],
        "scope": card["scope"],
        "meaning": card["meaning"],
        "verification": deepcopy(card["verification"]),
        "required_conditions": deepcopy(card["required_conditions"]),
        "exceptions": deepcopy(card["exceptions"]),
        "interpretation_boundary": (
            "已核干格原义与事件适用分开；未核身份、事类或必要条件不当成立。"
            "缺精确应期不抹去已核格义，也不据此制造期限结论。"
        ),
    }
    excerpt = PAIR_SOURCE_EXCERPTS.get(pair)
    if excerpt:
        result["source_excerpt"] = excerpt
    return result
