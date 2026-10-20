"""Strict frozen-chart validation; synthetic geometry has a separate explicit API.

This verifies internal agreement with the declared implementation.  Recomputing
with the same calendar provider is not an independent astronomical reference.
Neither API reads a clock, installs dependencies, or changes the supplied chart.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from qimen.chart import arrange, cast_chart, earth_plate
from qimen.rules import PALACES, RULE_VERSION, SEXAGENARY


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} 必须为对象")
    return value


def _required(mapping, key, label):
    if key not in mapping:
        raise ValueError(f"缺少 {label}.{key}")
    return mapping[key]


def _same(actual, expected, label):
    # bool is an int subclass, but must not pass a numeric field (or vice versa).
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"{label} 与声明的排盘规则不一致")


def validate_structure(chart):
    """Validate a complete arrangement, not a real calendar instant.

    Intended only for explicitly synthetic library tests.  Missing calendar
    metadata never causes the full validator to select this API automatically.
    """
    chart = _mapping(chart, "chart")
    if chart.get("rule_version") != RULE_VERSION:
        raise ValueError("仅支持 chai_bu_v1.0.0 的完整内置盘面")
    inputs = _mapping(chart.get("input"), "input")
    if inputs.get("center_policy") != "kun2":
        raise ValueError("仅支持中五寄坤二的完整内置盘面")
    calendar = _mapping(chart.get("calendar"), "calendar")
    for key in ("year_pillar", "month_pillar", "day_pillar", "hour_pillar"):
        if calendar.get(key) not in SEXAGENARY:
            raise ValueError(f"calendar.{key} 不是有效干支")
    palaces = chart.get("palaces")
    if not isinstance(palaces, list) or len(palaces) != 9:
        raise ValueError("盘面必须有不重复的九宫")
    by_number = {}
    for palace in palaces:
        palace = _mapping(palace, "palace")
        number = palace.get("number")
        if type(number) is not int or number not in PALACES or number in by_number:
            raise ValueError("盘面必须有不重复的九宫整数编号")
        by_number[number] = palace
        stems = palace.get("earth_stems")
        if not isinstance(stems, list) or not stems:
            raise ValueError(f"{number}宫 earth_stems 必须为非空列表")

    # The complete earth plate fixes both dun and ju, even in synthetic tests.
    earth = {n: p["earth_stems"][0] for n, p in by_number.items()}
    methods = [(ju, dun) for dun in ("yang", "yin") for ju in range(1, 10)
               if earth_plate(ju, dun) == earth]
    if len(methods) != 1:
        raise ValueError("地盘不是唯一合法阴阳遁局数的整体飞布")
    horse = _mapping(chart.get("horse"), "horse")
    basis = horse.get("basis")
    if basis not in ("hour", "day"):
        raise ValueError("horse.basis 必须为 hour 或 day")
    ju, dun = methods[0]
    expected = arrange(ju, dun, calendar["hour_pillar"], calendar["day_pillar"], basis)
    # Comparing every generated arrangement field checks a *single* common
    # star/stem rotation, door rotation, spirit direction, native chief origin,
    # hosted raw targets, all flags, and display strings rather than counts only.
    for group in ("xun", "chief", "horse"):
        actual = _mapping(chart.get(group), group)
        for key, value in expected[group].items():
            _same(_required(actual, key, group), value, f"{group}.{key}")
    for expected_palace in expected["palaces"]:
        number = expected_palace["number"]
        actual = by_number[number]
        for key, value in expected_palace.items():
            _same(_required(actual, key, f"palaces[{number}]"), value,
                  f"{number}宫.{key}（星干耦合、整体旋转或符使语义）")
    return by_number


def _aware(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须为含偏移的 ISO 8601 字符串")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 不是有效 ISO 8601 时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.microsecond:
        raise ValueError(f"{label} 必须含时区偏移且精确到整秒")
    return parsed


def validate_chart(chart):
    """Validate frozen time metadata, calendar and the declared full arrangement."""
    by_number = validate_structure(chart)
    if chart.get("chart_schema_version", "qimen_chart_v1.0") not in (
            "qimen_chart_v1.0", "qimen_chart_v1.1"):
        raise ValueError("不支持的 chart_schema_version")
    inputs, calendar = chart["input"], chart["calendar"]
    if chart.get("chart_schema_version") == "qimen_chart_v1.1":
        _required(inputs, "chart_instant_utc", "input")
        runtime = _mapping(_required(chart, "runtime", "chart"), "runtime")
        for key in ("python", "lunar_python", "timezone_database_policy"):
            if not isinstance(runtime.get(key), str) or not runtime[key]:
                raise ValueError(f"runtime.{key} 必须为实际运行版本或策略说明")
        if not isinstance(runtime.get("zoneinfo_tzpath"), list):
            raise ValueError("runtime.zoneinfo_tzpath 必须为列表")
        if runtime.get("tzdata") is not None and not isinstance(runtime["tzdata"], str):
            raise ValueError("runtime.tzdata 必须为版本字符串或 null")
        if chart.get("solar_term", {}).get("provider") != f'lunar-python {runtime["lunar_python"]}':
            raise ValueError("solar_term.provider 与 runtime.lunar_python 冲突")
    zone_name = _required(inputs, "timezone", "input")
    if not isinstance(zone_name, str):
        raise ValueError("input.timezone 必须为 IANA 时区名")
    try:
        zone = ZoneInfo(zone_name)
    except (ValueError, KeyError) as exc:
        raise ValueError("input.timezone 不是可用的 IANA 时区") from exc
    anchor = _aware(_required(inputs, "captured_at_utc", "input"), "input.captured_at_utc")
    if anchor.utcoffset().total_seconds() != 0:
        raise ValueError("input.captured_at_utc 必须使用 UTC 偏移")
    utc = anchor.astimezone(timezone.utc)
    local = utc.astimezone(zone)
    for field in ("datetime", "captured_at"):
        value = _aware(_required(inputs, field, "input"), f"input.{field}")
        if value.astimezone(timezone.utc) != utc or value.utcoffset() != local.utcoffset():
            raise ValueError(f"input.{field} 与原盘 UTC 时刻或声明时区冲突")
    value = _aware(_required(calendar, "solar_datetime", "calendar"), "calendar.solar_datetime")
    if value.astimezone(timezone.utc) != utc or value.utcoffset() != local.utcoffset():
        raise ValueError("calendar.solar_datetime 与原盘时刻或声明时区冲突")
    if "chart_instant_utc" in inputs:
        canonical = _aware(inputs["chart_instant_utc"], "input.chart_instant_utc")
        if canonical.utcoffset().total_seconds() != 0 or canonical != utc:
            raise ValueError("input.chart_instant_utc 与原盘 UTC 时刻冲突")
    now = _required(inputs, "use_current_time", "input")
    if type(now) is not bool or inputs.get("time_source") != ("runtime_clock" if now else "explicit"):
        raise ValueError("input.use_current_time 与 time_source 不一致")
    options = {key: _required(inputs, key, "input") for key in
               ("longitude", "latitude", "time_mode", "day_boundary", "horse_basis",
                "yuan_strategy", "center_policy")}
    # Explicit frozen input only: this path cannot fetch the current time.
    expected = cast_chart(local, use_current_time=False, timezone_name=zone_name, **options)
    for key, value in expected["calendar"].items():
        if key == "effective_time_kind":
            # v1.0 called the same civil wall clock “standard”; accept that
            # old label without changing the imported original.
            allowed = {value}
            if options["time_mode"] == "standard_time":
                allowed.add("所选时区标准钟面")
            if calendar.get(key) not in allowed:
                raise ValueError("calendar.effective_time_kind 与时间模式冲突")
        else:
            _same(_required(calendar, key, "calendar"), value, f"calendar.{key}")
    term = _mapping(chart.get("solar_term"), "solar_term")
    for key, value in expected["solar_term"].items():
        if key == "provider":
            # A historical provider declaration is not proof of an independent
            # calendar oracle.  Algorithmic values above/below must still match.
            if not isinstance(term.get(key), str) or not term[key]:
                raise ValueError("solar_term.provider 必须保留")
            continue
        _same(_required(term, key, "solar_term"), value, f"solar_term.{key}")
    for group in ("xun", "chief", "horse"):
        _same(chart[group], expected[group], group)
    for palace in expected["palaces"]:
        actual = by_number[palace["number"]]
        for key, value in palace.items():
            _same(actual[key], value, f"{palace['number']}宫.{key}")
    return by_number


def chart_instant_utc(chart):
    """Return the sole frozen instant after full validation, with no clock read."""
    validate_chart(chart)
    return _aware(chart["input"]["captured_at_utc"], "input.captured_at_utc").astimezone(timezone.utc)
