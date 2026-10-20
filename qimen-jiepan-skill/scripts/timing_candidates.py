"""Match branch-only calendar windows from a validated, unchanged source chart."""
import argparse
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from inspect_patterns import inspect_chart
from file_outputs import ensure_distinct_output
from qimen.calendar import calendar_data

VERSION = "qimen_timing_candidates_v2.0.0"
UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _aware(value, label):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{label} 必须为含偏移的 ISO 日期时间") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} 必须包含时区偏移")
    # ZoneInfo can construct a nonexistent wall time without complaining.
    normalized = value.astimezone(UTC).astimezone(value.tzinfo)
    if normalized.replace(tzinfo=None) != value.replace(tzinfo=None) or normalized.utcoffset() != value.utcoffset():
        raise ValueError(f"{label} 是所选时区不存在的地方钟面")
    return value


def _offset_transition(left, right, tz):
    """Find the actual jump bracketed by the two folds of a wall boundary.

    TZif offsets and transitions have integral-second precision.  A nonexistent
    or repeated local boundary supplies the two surrounding offsets itself, so
    this does not assume a one-hour jump or search at a fixed sampling cadence.
    """
    lower, upper = sorted((left, right))
    before = lower.astimezone(tz).utcoffset()
    if before == upper.astimezone(tz).utcoffset():
        raise ValueError("无法可靠定位该历史时区的折叠跳变；不生成可能跨柱的候选区间")
    # Arithmetic also works before 1970 on Windows, whose C timestamp range can
    # otherwise reject valid historical IANA instants.
    lo, hi = (lower - EPOCH) // timedelta(seconds=1), (upper - EPOCH) // timedelta(seconds=1)
    while hi - lo > 1:
        middle = (lo + hi) // 2
        if (EPOCH + timedelta(seconds=middle)).astimezone(tz).utcoffset() == before:
            lo = middle
        else:
            hi = middle
    return EPOCH + timedelta(seconds=hi)


def period_boundaries(start, end, unit, day_boundary):
    """UTC segments of constant day/hour pillar under the selected civil clock.

    Keep both folds of real local boundaries.  If a clock jump crosses such a
    boundary, also add the actual jump instant: omitting an imaginary midnight
    alone would incorrectly extend the preceding day's pillar into the new day.
    Offset changes contained entirely within one pillar need no extra segment.
    """
    if unit not in ("day", "hour") or day_boundary not in ("midnight", "zi_start"):
        raise ValueError("无效分段单位或换日口径")
    start, end = _aware(start, "start"), _aware(end, "end")
    tz = start.tzinfo
    lower, upper = start.astimezone(UTC), end.astimezone(UTC)
    if upper <= lower:
        raise ValueError("end 必须晚于 start")
    values = {lower, upper}
    hours = [0 if day_boundary == "midnight" else 23] if unit == "day" else list(range(1, 24, 2))
    if unit == "hour" and day_boundary == "midnight":
        hours = [0] + hours
    current = start.date() - timedelta(days=1)
    last = end.astimezone(tz).date() + timedelta(days=1)
    while current <= last:
        for hour in hours:
            wall = datetime.combine(current, time(hour))
            folds = [wall.replace(tzinfo=tz, fold=fold).astimezone(UTC) for fold in (0, 1)]
            if folds[0] != folds[1]:
                transition = _offset_transition(*folds, tz)
                if transition is not None and lower < transition < upper:
                    values.add(transition)
            for instant in folds:
                if instant.astimezone(tz).replace(tzinfo=None) == wall and lower < instant < upper:
                    values.add(instant)
        current += timedelta(days=1)
    return sorted(values)


def _window_end(start, days, duration_mode, gap_policy, fold):
    if duration_mode == "elapsed_24h":
        return (start.astimezone(UTC) + timedelta(days=days)).astimezone(start.tzinfo), False
    wall = start.replace(tzinfo=None) + timedelta(days=days)
    proposed = wall.replace(tzinfo=start.tzinfo, fold=fold)
    normalized = proposed.astimezone(UTC).astimezone(start.tzinfo)
    if normalized.replace(tzinfo=None) == wall:
        return normalized, False
    if gap_policy == "raise":
        raise ValueError("日历日窗口的结束钟面不存在；可选择 shift_forward 或 elapsed_24h")
    # Retain minutes/seconds by advancing through the size of the gap.  Both
    # folds are tried because fold=1 maps a gap backwards instead of forwards.
    shifted = [wall.replace(tzinfo=start.tzinfo, fold=f).astimezone(UTC).astimezone(start.tzinfo)
               for f in (0, 1)]
    forward = [value for value in shifted if value.replace(tzinfo=None) > wall]
    if not forward:
        raise ValueError("无法规范化不存在的日历日结束钟面")
    return min(forward, key=lambda value: value.astimezone(UTC)), True


def triggers_for(palace, horse):
    events = []
    for branch in palace["activation"]["fill_void_branches"]:
        events.append({"kind": "填实", "trigger_branch": branch, "underlying_branch": branch,
                       "layer": "hour_xun_void", "source_id": "SK-1"})
    for original, clash in zip(palace["void_branches"], palace["activation"]["clash_void_branches"]):
        events.append({"kind": "冲空", "trigger_branch": clash, "underlying_branch": original,
                       "layer": "hour_xun_void", "source_id": "SK-1"})
    for tomb in palace["activation"]["tomb_triggers"]:
        events.append({"kind": "冲墓", "trigger_branch": tomb["clash_branch"],
                       "underlying_branch": tomb["tomb_branch"], "layer": tomb["layer"],
                       "item": tomb["item"], "role": tomb["role"], "source_id": "SK-1"})
    if palace["horse"]:
        events.append({"kind": "马星同支", "trigger_branch": horse["branch"],
                       "underlying_branch": horse["branch"], "layer": "horse", "source_id": "SK-1"})
    return [{"palace": palace["number"], **event} for event in events]


def candidates(chart, palaces, *, unit, days=14, search_start=None,
               duration_mode="calendar_days", end_gap_policy="shift_forward", calendar_end_fold=0):
    """Match source-chart branches; no result is a prediction or success date.

    days is explicit: calendar_days advances the local calendar retaining the
    wall clock, whereas elapsed_24h advances UTC by days * 86400 seconds.  For
    calendar_days an imaginary endpoint is shifted forward by the clock gap
    (or rejected), and an ambiguous endpoint uses the requested fold (0/1).
    search_start is an independent aware instant; it never edits the chart.
    """
    if unit not in ("day", "hour"):
        raise ValueError("unit 必须为 day 或 hour")
    if type(days) is not int or not 1 <= days <= 366:
        raise ValueError("days 必须为 1 至 366 的整数")
    if not palaces or any(type(n) is not int or n not in (1, 2, 3, 4, 6, 7, 8, 9) for n in palaces):
        raise ValueError("palaces 须为外八宫编号")
    if len(palaces) != len(set(palaces)):
        raise ValueError("palaces 不得重复")
    if duration_mode not in ("calendar_days", "elapsed_24h"):
        raise ValueError("duration_mode 必须为 calendar_days 或 elapsed_24h")
    if end_gap_policy not in ("shift_forward", "raise"):
        raise ValueError("end_gap_policy 必须为 shift_forward 或 raise")
    if type(calendar_end_fold) is not int or calendar_end_fold not in (0, 1):
        raise ValueError("calendar_end_fold 必须为 0 或 1")
    derived = inspect_chart(chart)
    options = chart["input"]
    if options.get("time_mode") != "standard_time":
        raise ValueError("候选工具仅支持标准时；真太阳时须按明确口径另核")
    boundary = options["day_boundary"]
    if boundary not in ("midnight", "zi_start"):
        raise ValueError("无效换日口径")
    # inspect_chart performs strict frozen-chart validation, including agreement
    # of every input/calendar timestamp.  Never trust an independently changed
    # input.datetime as a new search origin.
    source_instant = _aware(options["captured_at_utc"], "原盘 UTC 时间").astimezone(UTC)
    instant = source_instant if search_start is None else _aware(search_start, "search_start")
    start = instant.astimezone(ZoneInfo(options["timezone"]))
    end, end_adjusted = _window_end(start, days, duration_mode, end_gap_policy, calendar_end_fold)
    if start.year < 1901 or end.year > 2099:
        raise ValueError("候选窗口须在 1901 至 2099 年内")
    selected = [p for p in derived["palaces"] if p["number"] in palaces]
    events = [e for p in selected for e in triggers_for(p, derived["global"]["horse"])]
    bounds = period_boundaries(start, end, unit, boundary)
    windows = []
    for left, right in zip(bounds, bounds[1:]):
        local = left.astimezone(start.tzinfo)
        calendar, _ = calendar_data(local, options["longitude"], "standard_time", boundary)
        pillar = calendar["day_pillar" if unit == "day" else "hour_pillar"]
        matches = [e for e in events if e["trigger_branch"] == pillar[1]]
        if matches:
            windows.append({"start": local.isoformat(), "end_exclusive": right.astimezone(start.tzinfo).isoformat(),
                            "start_utc": left.isoformat(), "end_utc_exclusive": right.isoformat(),
                            "duration_seconds": (right - left).total_seconds(),
                            "pillar": pillar, "branch": pillar[1], "triggers": matches})
    total_seconds = (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds()
    candidate_seconds = sum(row["duration_seconds"] for row in windows)
    return {
        "version": VERSION, "source_captured_at": options["captured_at"],
        "source_chart_instant_utc": source_instant.isoformat(),
        "window": {"start": start.isoformat(), "end_exclusive": end.isoformat(),
                   "start_utc": start.astimezone(UTC).isoformat(), "end_utc_exclusive": end.astimezone(UTC).isoformat(),
                   "unit": unit, "days": days, "duration_mode": duration_mode,
                   "end_gap_policy": end_gap_policy, "calendar_end_fold": calendar_end_fold,
                   "end_adjusted_for_gap": end_adjusted, "search_start_explicit": search_start is not None,
                   "timezone": options["timezone"], "day_boundary": boundary},
        "palaces": list(palaces), "candidates": windows,
        "statistics": {"window_seconds": total_seconds, "candidate_union_seconds": candidate_seconds,
                       "coverage_fraction": candidate_seconds / total_seconds,
                       "segment_count": len(bounds) - 1, "candidate_segment_count": len(windows),
                       "meaning": "候选区间并集占搜索总时长的比例；不是命中率、概率或预测置信度"},
        "scope": "原盘相关支的日历候选；未排新局、未筛选成事日",
        "not_computed": ["事件阶段和时间单位选择", "出空跨旬推断", "月级及真太阳时日期", "成败与最终应期"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chart", type=Path)
    parser.add_argument("--palaces", required=True, help="Comma-separated outer palace numbers")
    parser.add_argument("--unit", choices=("day", "hour"), required=True)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--search-start", help="Independent ISO timestamp with UTC offset; source chart remains unchanged")
    parser.add_argument("--duration-mode", choices=("calendar_days", "elapsed_24h"), default="calendar_days")
    parser.add_argument("--end-gap-policy", choices=("shift_forward", "raise"), default="shift_forward")
    parser.add_argument("--calendar-end-fold", type=int, choices=(0, 1), default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        chart = json.loads(args.chart.read_text(encoding="utf-8-sig"))
        result = candidates(chart, [int(n.strip()) for n in args.palaces.split(",")], unit=args.unit, days=args.days,
                            search_start=args.search_start, duration_mode=args.duration_mode,
                            end_gap_policy=args.end_gap_policy, calendar_end_fold=args.calendar_end_fold)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            ensure_distinct_output(args.chart, args.output)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            print(rendered, end="")
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"应期候选生成失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
