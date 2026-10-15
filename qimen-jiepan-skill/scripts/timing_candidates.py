"""Generate calendar windows for explicitly selected palaces in an existing chart."""
import argparse
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from inspect_patterns import inspect_chart
from qimen.calendar import calendar_data

VERSION = "qimen_timing_candidates_v1.0.0"
UTC = timezone.utc


def period_boundaries(start, end, unit, day_boundary):
    """Build valid local boundaries, retaining both folds and skipping gaps."""
    tz = start.tzinfo
    values = {start.astimezone(UTC), end.astimezone(UTC)}
    hours = [0 if day_boundary == "midnight" else 23] if unit == "day" else list(range(1, 24, 2))
    if unit == "hour" and day_boundary == "midnight":
        hours = [0] + hours
    current = start.date() - timedelta(days=1)
    last = end.date() + timedelta(days=1)
    lower, upper = start.astimezone(UTC), end.astimezone(UTC)
    while current <= last:
        for hour in hours:
            wall = datetime.combine(current, time(hour))
            for fold in (0, 1):
                local = wall.replace(tzinfo=tz, fold=fold)
                instant = local.astimezone(UTC)
                if instant.astimezone(tz).replace(tzinfo=None) == wall and lower < instant < upper:
                    values.add(instant)
        current += timedelta(days=1)
    return sorted(values)


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


def candidates(chart, palaces, *, unit, days=14):
    if unit not in ("day", "hour"):
        raise ValueError("unit 必须为 day 或 hour")
    if type(days) is not int or not 1 <= days <= 366:
        raise ValueError("days 必须为 1 至 366 的整数")
    if not palaces or any(type(n) is not int or n not in (1, 2, 3, 4, 6, 7, 8, 9) for n in palaces):
        raise ValueError("palaces 须为外八宫编号")
    if len(palaces) != len(set(palaces)):
        raise ValueError("palaces 不得重复")
    derived = inspect_chart(chart)
    options = chart["input"]
    if options.get("time_mode") != "standard_time":
        raise ValueError("候选工具仅支持标准时；真太阳时须按明确口径另核")
    boundary = options["day_boundary"]
    if boundary not in ("midnight", "zi_start"):
        raise ValueError("无效换日口径")
    instant = datetime.fromisoformat(options["datetime"])
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("原盘时间必须包含时区")
    start = instant.astimezone(ZoneInfo(options["timezone"]))
    end = start + timedelta(days=days)
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
                            "pillar": pillar, "branch": pillar[1], "triggers": matches})
    return {
        "version": VERSION, "source_captured_at": options["captured_at"],
        "window": {"start": start.isoformat(), "end_exclusive": end.isoformat(),
                   "unit": unit, "days": days, "timezone": options["timezone"], "day_boundary": boundary},
        "palaces": list(palaces), "candidates": windows,
        "scope": "原盘相关支的日历候选；未排新局、未筛选成事日",
        "not_computed": ["事件阶段和时间单位选择", "出空跨旬推断", "月级及真太阳时日期", "成败与最终应期"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chart", type=Path)
    parser.add_argument("--palaces", required=True, help="Comma-separated outer palace numbers")
    parser.add_argument("--unit", choices=("day", "hour"), required=True)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        chart = json.loads(args.chart.read_text(encoding="utf-8-sig"))
        result = candidates(chart, [int(n.strip()) for n in args.palaces.split(",")], unit=args.unit, days=args.days)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
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
