"""Selected stem-pair readings. Interpretive references stay separate from geometry."""

# Names belong to the directional stem table, not to independent spirits or tombs.
# Topics and images are concise modern paraphrases, not asserted real events.
PAIR_READINGS = {
    "乙丁": ("奇仪相佐", ("文书", "协作"), ("信息相佐", "协调推进"), (), "MJ-2"),
    "乙庚": ("日奇被刑", ("交涉", "关系"), ("合中有制", "牵连"), (), "MJ-2"),
    "丙丙": ("月奇孛师", ("文书", "资源"), ("重复牵迫", "消耗"), (), "MJ-2"),
    "丙丁": ("星奇朱雀", ("文书", "求名"), ("信息助成",), (), "MJ-2"),
    "丁丁": ("奇入太阴", ("文书", "消息"), ("消息有应",), (), "MJ-2"),
    "丁辛": ("朱雀入狱", ("身份", "文书"), ("处境转换", "约束"), (), "MJ-2"),
    "丁壬": ("五神互合", ("文书", "交涉"), ("牵连和合",), (), "MJ-2"),
    "戊乙": ("青龙合灵", ("谋事",), ("因门定助阻",), ("door_quality",), "MJ-2"),
    "戊丁": ("青龙耀明", ("求名", "文书"), ("得照应",), ("avoid_tomb_pressure",), "MJ-2"),
    "戊辛": ("青龙折足", ("推进", "资源"), ("推进受限",), ("good_door_support",), "MJ-2"),
    "戊壬": ("龙入天牢", ("推进",), ("拘束", "难展"), (), "MJ-2"),
    "戊癸": ("青龙华盖", ("谋事",), ("因门定助阻",), ("door_quality",), "MJ-2"),
    "己丁": ("朱雀入墓", ("文书", "争议"), ("过程曲折", "前后有别"), (), "ZG-5"),
    "己辛": ("游魂入墓", ("状态",), ("不定", "内困"), (), "ZG-5"),
    "己癸": ("地刑玄武", ("交涉",), ("受限", "隐蔽牵连"), (), "ZG-5"),
    "庚丁": ("亭亭之格", ("交涉", "文书"), ("私事牵连",), ("good_door_support",), "ZG-5"),
    "辛丁": ("狱神得奇", ("交易", "处境"), ("得助", "处境松动"), (), "MJ-2"),
    "辛庚": ("白虎出力", ("竞争",), ("强硬相持",), ("retreat_preferred",), "MJ-2"),
    "壬壬": ("蛇入地罗", ("人事",), ("内外缠绕",), ("good_star_door",), "ZG-5"),
    "癸己": ("华盖地户", ("消息", "避藏"), ("消息受阻", "宜藏"), (), "MJ-2"),
}

READING_CONDITIONS = {
    "door_quality": "分别结合实际门的事类用途判断助阻",
    "avoid_tomb_pressure": "墓位和门迫会限制原有助成作用",
    "good_door_support": "原条目以吉门扶助为缓解条件",
    "retreat_preferred": "原条目倾向退让，强进容易加剧相持",
    "good_star_door": "原条目以门星条件作缓解参照",
}


def pair_reading(heaven, earth):
    row = PAIR_READINGS.get(heaven + earth)
    if row is None:
        return None
    name, topics, images, checks, source = row
    return {
        "table_name": name,
        "topics": list(topics),
        "possible_images": list(images),
        "application_conditions": [READING_CONDITIONS[c] for c in checks],
        "source_id": source,
        "scope": "干表克应；表名不替代实际神、墓位或全盘动静",
    }
