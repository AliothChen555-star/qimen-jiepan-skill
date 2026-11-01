"""Comparable, point-in-time return scales and compounded scenario paths."""
from datetime import date
from math import prod, sqrt
from statistics import mean
from zoneinfo import ZoneInfo

from finance_common import calendar_for, dates, instant, need, nonempty, number, session


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered)-1)*probability
    lower = int(position)
    upper = min(lower+1, len(ordered)-1)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(position-lower)


def history_scale(asset, issued_at, config):
    history = asset.get('history')
    empty = {'status': 'missing', 'count': 0, 'quantiles': None, 'source': None}
    if not history:
        return empty
    for key in ('asset_id', 'currency', 'return_basis', 'source'):
        nonempty(history.get(key), f'history.{key}')
    need(history['currency'] == asset['currency'], '历史币种须与产品一致；汇率转换后再输入')
    need(history['return_basis'] == asset['return_basis'], '历史收益口径须与产品一致')
    proxy = history['asset_id'] != asset['id']
    if proxy:
        need(history['asset_id'] == asset.get('tracked_index_id'), '代理幅度只能使用档案明确登记的跟踪指数')
        nonempty(history.get('proxy_reason'), '代理尺度原因')
    rows = history.get('rows', [])
    need(isinstance(rows, list), '历史 rows 须为数组')
    mode = history.get('mode', 'returns')
    need(mode in ('returns', 'values'), '历史 mode 须为 returns 或 values；不接收累计净值')
    calendar = calendar_for(asset)
    issued = instant(issued_at)
    seen, usable, excluded, prior, prior_day = set(), [], 0, None, None
    for row in sorted(rows, key=lambda r: r['date']):
        day = date.fromisoformat(row['date'])
        need(day not in seen, '历史日期重复')
        seen.add(day)
        available = instant(row['available_at'])
        need(available.astimezone(ZoneInfo(calendar['timezone'])).date() >= day, '历史可得时间早于归属日期')
        if available >= issued:
            excluded += 1
            continue
        if asset['instrument'] != 'fund' and calendar['valid_from'] <= row['date'] <= calendar['valid_to']:
            market = session(day, calendar)
            need(market['status'] != 'closed', '历史日收益落在休市日')
            need(available >= instant(market['close_at']), '完整日收益的可得时间早于收市')
        if mode == 'returns':
            need('value' not in row and 'cumulative_nav' not in row, '不得混合收益与价格／累计净值')
            value = number(row['return_pct'], '日收益百分比')
        else:
            need('return_pct' not in row and 'cumulative_nav' not in row, 'values 模式只能接收可比价格／单位净值')
            current = number(row['value'], '价格或单位净值')
            need(current > 0, '价格或单位净值须大于零')
            reference = row.get('reference_value', prior)
            if reference is not None and 'reference_value' not in row and prior_day:
                between = dates(prior_day, row['date'])[1:-1]
                need(all(session(d, calendar)['status'] == 'closed' for d in between),
                     '价格序列缺少交易／估值日；补齐数据或提供该日可比 reference_value')
            prior, prior_day = current, row['date']
            if reference is None:
                continue
            reference = number(reference, '可比前值')
            need(reference > 0, '可比前值须大于零')
            cash, factor = 0, 1
            if asset['return_basis'] != 'price_return':
                cash = number(row['cash_distribution'], '按期初份额计的现金分配')
                factor = number(row['share_factor'], '份额调整因子')
                need(cash >= 0 and factor > 0, '分配或份额因子无效')
            value = ((current*factor+cash)/reference-1)*100
        need(value >= -100, '日收益不能小于 -100%')
        usable.append({'date': row['date'], 'return_pct': value, 'available_at': row['available_at']})
    selected = usable[-config['history_window']:]
    output = {'status': 'ready' if len(selected) >= config['minimum_history'] else 'insufficient',
              'count': len(selected), 'excluded_not_available': excluded, 'source': history['source'],
              'asset_id': history['asset_id'], 'currency': history['currency'], 'return_basis': history['return_basis'],
              'proxy': proxy, 'proxy_reason': history.get('proxy_reason'), 'rows': selected, 'quantiles': None}
    if output['status'] == 'ready':
        values = [r['return_pct'] for r in selected]
        output['quantiles'] = {f'A{int(p*100)}': quantile([abs(v) for v in values], p) for p in (.2,.5,.8,.95)}
        output['historical_mean_pct'] = mean(values)
        output['last_return_pct'] = values[-1]
    return output


def amplitude(grade, scale):
    if scale['status'] != 'ready':
        return None
    q = scale['quantiles']
    bands = {2: (q['A50'], q['A95']), 1: (q['A20'], q['A80']), 0: (-q['A50'], q['A50']),
             -1: (-q['A80'], -q['A20']), -2: (-q['A95'], -q['A50'])}
    lower, upper = bands[grade]
    lower, upper = max(-100, lower), max(-100, upper)
    return {'lower_pct': lower, 'upper_pct': upper, 'scenario_midpoint_pct': (lower+upper)/2,
            'kind': 'historical_scale_scenario', 'scale_asset_id': scale['asset_id'], 'proxy': scale['proxy']}


def compound(values):
    return (prod(1+v/100 for v in values)-1)*100


def turning_windows(rows):
    runs = []
    for row in rows:
        sign = (row['grade'] > 0)-(row['grade'] < 0)
        if not runs or sign != runs[-1]['sign']:
            runs.append({'sign': sign, 'rows': []})
        runs[-1]['rows'].append(row)
    candidates, previous = [], None
    for run in runs:
        if run['sign'] == 0:
            continue
        if previous and run['sign'] != previous['sign'] and len(run['rows']) >= 2:
            candidates.append({'start': run['rows'][0]['date'], 'end': run['rows'][1]['date'],
                               'direction': '转强' if run['sign'] > 0 else '转弱', 'persistence_sessions': len(run['rows']),
                               'direct_trigger': any(r['decision']['activations'] for r in run['rows'][:2])})
        if len(run['rows']) >= 2:
            previous = run
    selected = sorted(candidates, key=lambda r: (-r['direct_trigger'], -r['persistence_sessions'], r['start']))[:3]
    return sorted(selected, key=lambda r: r['start'])


def summarize(rows, scale, baseline, horizon, start, end, period_style):
    trading = [r for r in rows if r['grade'] is not None]
    result = {'sessions': len(trading), 'baseline': baseline, 'path': None,
              'turning_windows': turning_windows(trading), 'forecast_scopes': sorted({r['forecast_scope'] for r in trading})}
    if not trading:
        result['trend'] = '无交易／估值日'
        return result
    if scale['status'] == 'ready':
        result['path'] = {key: compound([r['amplitude'][key] for r in trading])
                          for key in ('lower_pct', 'upper_pct', 'scenario_midpoint_pct')}
        result['path']['kind'] = 'compounded_path_scenario_envelope'
        threshold = .2*scale['quantiles']['A50']*sqrt(len(trading))
        middle = result['path']['scenario_midpoint_pct']
        result['trend'] = '偏涨' if middle > threshold else '偏跌' if middle < -threshold else '震荡'
        result['near_zero_threshold_pct'] = threshold
    else:
        direction = (trading[0]['grade'] > 0)-(trading[0]['grade'] < 0) if horizon == 'day' else baseline
        result['trend'] = {1:'偏涨', 0:'震荡', -1:'偏跌'}[direction]
        result['trend_basis'] = '当日档位；幅度尺度待补' if horizon == 'day' else '原盘基调；幅度尺度待补'
    if horizon == 'month':
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        phase_rows = [[], [], []]
        for row in trading:
            day = date.fromisoformat(row['date'])
            index = min(2, (day.day-1)//10) if period_style == 'natural' else min(2, (day-first).days*3//((last-first).days+1))
            phase_rows[index].append(row)
        result['phases'] = []
        for label, items in zip(('前段', '中段', '后段'), phase_rows):
            if items:
                sub = summarize(items, scale, baseline, 'phase', start, end, period_style)
                result['phases'].append({'phase': label, 'start': items[0]['date'], 'end': items[-1]['date'],
                                         'trend': sub['trend'], 'path': sub['path']})
    return result
