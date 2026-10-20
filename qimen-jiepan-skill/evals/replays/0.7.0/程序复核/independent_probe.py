from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.resources
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo, available_timezones
from zoneinfo._common import load_data

ROOT = Path(r'X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from chart_validation import validate_chart, validate_structure
from qimen.chart import cast_chart
from timing_candidates import period_boundaries
from reading_record import init_record, validate_record
from rule_evaluator import evaluate_application, rule_by_id

UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def clock_key(instant, zone, unit, boundary):
    local = instant.astimezone(zone)
    day = local.date() + (timedelta(days=1) if boundary == 'zi_start' and local.hour == 23 else timedelta())
    return day if unit == 'day' else (day, ((local.hour + 1) // 2) % 12)


def check_transition(zone_name, instant):
    zone = ZoneInfo(zone_name)
    start = (instant - timedelta(days=2)).astimezone(zone)
    end = (instant + timedelta(days=2)).astimezone(zone)
    failures = []
    for unit in ('day', 'hour'):
        for boundary in ('midnight', 'zi_start'):
            try:
                bounds = period_boundaries(start, end, unit, boundary)
            except Exception as exc:
                failures.append({'zone': zone_name, 'at': instant.isoformat(), 'unit': unit,
                                 'boundary': boundary, 'error': repr(exc)})
                continue
            for left, right in zip(bounds, bounds[1:]):
                expected = clock_key(left, zone, unit, boundary)
                for point in (left + (right - left) / 2, right - timedelta(microseconds=1),
                              instant - timedelta(microseconds=1), instant):
                    if left <= point < right and clock_key(point, zone, unit, boundary) != expected:
                        failures.append({'zone': zone_name, 'at': instant.isoformat(), 'unit': unit,
                                         'boundary': boundary, 'left': left.isoformat(), 'right': right.isoformat(),
                                         'mismatch_at': point.isoformat(), 'expected': str(expected),
                                         'actual': str(clock_key(point, zone, unit, boundary))})
    return failures


def historical_segments():
    count = 0
    failures = []
    for name in sorted(available_timezones()):
        resource = importlib.resources.files('tzdata.zoneinfo').joinpath(name)
        try:
            with resource.open('rb') as f:
                indices, transitions, offsets, _, _, _ = load_data(f)
        except (FileNotFoundError, ValueError):
            continue
        # Deduplicate identical clock histories so alias names do not multiply time.
        signature = (tuple(indices), tuple(transitions), tuple(offsets))
        if signature in seen_histories:
            continue
        seen_histories.add(signature)
        for seconds in transitions:
            instant = EPOCH + timedelta(seconds=seconds)
            if not 1901 <= instant.year <= 2099:
                continue
            count += 1
            failures.extend(check_transition(name, instant))
        if failures:
            break
    return {'transition_count': count, 'failures': failures, 'unique_histories': len(seen_histories)}


def validation_checks():
    chart = cast_chart('2026-10-14T13:27:13+08:00')
    accepted = []
    for field in ('datetime', 'captured_at', 'captured_at_utc', 'chart_instant_utc'):
        other = deepcopy(chart)
        other['input'][field] = '2026-10-15T13:27:13+08:00'
        try:
            validate_chart(other)
            accepted.append(field)
        except ValueError:
            pass
    synthetic = deepcopy(chart)
    for field in ('datetime', 'captured_at', 'captured_at_utc', 'chart_instant_utc', 'timezone'):
        synthetic['input'].pop(field, None)
    synthetic['calendar'].pop('solar_datetime')
    validate_structure(synthetic)
    try:
        validate_chart(synthetic)
        accepted.append('synthetic_full')
    except ValueError:
        pass
    return {'invalid_time_fields_accepted': accepted, 'synthetic_structure_accepted': True}


def typed_geometry_probe():
    outputs = []
    for geometry in (None, False, True, 'false', 'unknown', 0, 1):
        result = evaluate_application(rule_by_id('PAIR_乙丁'), {}, geometry=geometry)
        outputs.append({'input': geometry, 'geometry_match': result['geometry_match'], 'eligibility': result['eligibility']})
    return outputs


if __name__ == '__main__':
    seen_histories = set()
    result = {'validation': validation_checks(), 'typed_geometry': typed_geometry_probe(),
              'historical_segments': historical_segments()}
    (OUT / 'independent-probe-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
