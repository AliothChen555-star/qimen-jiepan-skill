"""Overlay civil days and market sessions on one immutable Qimen chart."""
import argparse
from datetime import datetime, timedelta, timezone
import sys
from zoneinfo import ZoneInfo

from chart_validation import validate_chart
from finance_common import (calendar_for, dates, digest, instant, local_clock, need,
                            read_json, session, validate_asset, write_new)
from inspect_patterns import (BRANCH_CLASH, BRANCH_ELEMENTS, STEM_ELEMENTS,
                              relation, resolve_pillar_stem)
from qimen.calendar import calendar_data
from qimen.rules import BRANCHES, BRANCH_PALACE, GAN_SEQUENCE, PALACES, SEXAGENARY

BRANCH_UNION = dict(zip('子丑寅亥卯戌辰酉巳申午未', '丑子亥寅戌卯酉辰申巳未午'))
STEM_UNION = dict(zip('甲己乙庚丙辛丁壬戊癸', '己甲庚乙辛丙壬丁癸戊'))


def locate(chart, kind, value):
    field = {'stem': 'heaven_stems', 'star': 'stars', 'door': 'door'}[kind]
    found = []
    for p in chart['palaces']:
        if p['number'] == 5:
            continue
        values = p[field] if isinstance(p[field], list) else [p[field]]
        if value in values:
            found.append({'kind': kind, 'value': value, 'palace': p['number'],
                          'position': 'main' if values.index(value) == 0 else 'hosted'})
    need(len(found) == 1, f'{kind}:{value} 在原盘外八宫的落点不唯一')
    return found[0]


def day_state(chart, at):
    inputs = chart['input']
    local = at.astimezone(ZoneInfo(inputs['timezone']))
    cal, term = calendar_data(local, inputs['longitude'], inputs['time_mode'], inputs['day_boundary'])
    pillar = cal['day_pillar']
    stem, branch = pillar
    ix = SEXAGENARY.index(pillar) // 10
    head = SEXAGENARY[ix*10]
    start = (BRANCHES.index(head[1])+10) % 12
    void = [BRANCHES[start], BRANCHES[(start+1) % 12]]
    horse = next(result for group, result in [('申子辰','寅'), ('寅午戌','申'), ('巳酉丑','亥'), ('亥卯未','巳')] if branch in group)
    resolved = resolve_pillar_stem(pillar)
    where = locate(chart, 'stem', resolved)
    touches = []
    for original in BRANCHES:
        kind = '同支' if branch == original else '六冲' if BRANCH_CLASH[branch] == original else '六合' if BRANCH_UNION[branch] == original else None
        if kind:
            touches.append({'kind': kind, 'day_branch': branch, 'original_branch': original,
                            'palace': BRANCH_PALACE[original],
                            'original_void': original in chart['xun']['void_branches']})
    return {'anchor_at': local.isoformat(), 'day_pillar': pillar,
            'day_stem': stem, 'resolved_stem': resolved, 'stem_location': where,
            'branch': branch, 'branch_palace': BRANCH_PALACE[branch],
            'day_xun': {'head': head, 'hidden_stem': GAN_SEQUENCE[ix], 'void_branches': void},
            'day_horse': {'branch': horse, 'palace': BRANCH_PALACE[horse]},
            'month_pillar': cal['month_pillar'], 'month_element': BRANCH_ELEMENTS[cal['month_pillar'][1]],
            'solar_term': term, 'branch_contacts': touches,
            'stem_union_with': STEM_UNION[stem],
            'original': {'void_branches': list(chart['xun']['void_branches']), 'horse': dict(chart['horse']),
                         'month_pillar': chart['calendar']['month_pillar']}}


def overlay(chart, asset, start, end, issued_at):
    validate_chart(chart)
    validate_asset(asset)
    captured_hash = digest(chart)
    calendar = calendar_for(asset)
    issued = instant(issued_at)
    output = []
    for day in dates(start, end):
        market = session(day, calendar)
        if asset['instrument'] == 'fund':
            at = local_clock(day, '12:00', asset['valuation_timezone'])
        else:
            at = local_clock(day, calendar['open'], calendar['timezone']) if market['status'] == 'closed' else datetime.fromisoformat(market['open_at'])
        state = day_state(chart, at)
        if market['status'] == 'closed':
            phase, window = 'closed', None
        elif asset['instrument'] == 'fund':
            window = asset.get('valuation_windows', {}).get(day.isoformat())
            if window:
                first, last = instant(window['start']), instant(window['end'])
                need(first < last, '基金采价窗口颠倒')
                need(bool(window.get('source')), '基金采价窗口需要来源')
                phase = 'full' if issued < first else 'partial' if issued < last else 'retrospective'
            else:
                phase = 'timing_unverified'
        else:
            window = {'start': market['open_at'], 'end': market['close_at'], 'source': calendar['source']}
            phase = 'full' if issued < instant(market['open_at']) else 'partial' if issued < instant(market['close_at']) else 'retrospective'
        boundaries = []
        if window:
            # Reuse the existing DST/day-boundary implementation. The original
            # chart clock (including true-solar correction) remains authoritative.
            first, last = instant(window['start']), instant(window['end'])
            cursor = first
            previous = day_state(chart, cursor)['day_pillar']
            while cursor < last:
                probe = min(cursor+timedelta(hours=1), last)
                current = day_state(chart, probe)['day_pillar']
                if current != previous:
                    lo, hi = cursor, probe
                    while (hi-lo).total_seconds() > 1:
                        mid = lo+(hi-lo)/2
                        if day_state(chart, mid)['day_pillar'] == previous:
                            lo = mid
                        else:
                            hi = mid
                    boundaries.append({'at_utc': hi.isoformat(), 'from': previous, 'to': current})
                previous, cursor = current, probe
        output.append({'date': day.isoformat(), 'market_session': market, 'day': state,
                       'forecast_scope': phase, 'valuation_window': window,
                       'day_boundaries_in_session': boundaries})
    need(digest(chart) == captured_hash, '原盘被修改')
    return {'schema_version': 'qimen_daily_overlay_v1', 'chart_sha256': captured_hash,
            'asset_id': asset['id'], 'calendar_snapshot': calendar,
            'chart_timezone': chart['input']['timezone'], 'days': output}


def interactions(day, anchor, chart):
    target = PALACES[anchor['palace']][2]
    obj = next(p for p in chart['palaces'] if p['number'] == anchor['palace'])
    return {'stem_palace_to_target': relation(PALACES[day['stem_location']['palace']][2], target),
            'branch_palace_to_target': relation(PALACES[day['branch_palace']][2], target),
            'stem_element_to_target': relation(STEM_ELEMENTS[day['day_stem']], target),
            'stem_to_object_stem': relation(STEM_ELEMENTS[day['day_stem']], STEM_ELEMENTS[obj['heaven_stems'][0]]),
            'stem_union_hits': [s for s in obj['heaven_stems'] if s == day['stem_union_with']],
            'target_branch_contacts': [c for c in day['branch_contacts'] if c['palace'] == anchor['palace']]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chart', type=str, required=True)
    parser.add_argument('--asset', type=str, required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--issued-at', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        result = overlay(read_json(args.chart), read_json(args.asset), args.start, args.end, args.issued_at)
        write_new(args.output, result, [args.chart, args.asset])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'逐日对照失败：{exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
