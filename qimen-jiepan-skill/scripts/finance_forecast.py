"""Reproducible FINANCE_FIXED_CHART_V1 baseline, daily overlays and return scales."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from collections import defaultdict
import sys

from chart_validation import validate_chart
from daily_overlay import BRANCH_CLASH, interactions, locate, overlay
from finance_common import (METHOD, SCHEMA, VERSION, calendar_for, dates, digest, instant,
                            need, nonempty, number, profiles, read_json, validate_asset, write_new)
from finance_market import amplitude, history_scale, summarize
from inspect_patterns import inspect_chart, relation, resolve_pillar_stem, seasonal
from qimen.rules import BRANCH_PALACE, PALACES

LABELS = {-2:'偏跌较强', -1:'偏跌', 0:'震荡／相持', 1:'偏涨', 2:'偏涨较强'}
SUPPORT = {'A生B': 1, '比和': 1, 'A克B': -1, 'B生A': -1, 'B克A': 0}


def roles_for(chart, asset, config):
    hour = locate(chart, 'stem', resolve_pillar_stem(chart['calendar']['hour_pillar']))
    sector = config['sectors'].get(asset.get('sector'))
    sector_role = locate(chart, sector['kind'], sector['value']) if sector else None
    use_sector = bool(sector_role) and asset['instrument'] != 'stock' and asset.get('exposure', 'sector') == 'sector'
    result = {'primary': dict(sector_role if use_sector else hour), 'hour_background': hour,
              'capital': locate(chart, 'stem', '戊'), 'profit': locate(chart, 'door', '生门')}
    result['primary']['binding'] = 'registered_sector' if use_sector else 'original_hour_stem'
    primary_palace = next(p for p in chart['palaces'] if p['number'] == result['primary']['palace'])
    result['direction_door'] = locate(chart, 'door', primary_palace['door'])
    if sector_role:
        result['sector'] = sector_role
    return result


def role_fact(role, facts):
    palace = next(p for p in facts['palaces'] if p['number'] == role['palace'])
    if role['kind'] == 'door':
        return palace['human']
    group, key = ('stems', 'stem') if role['kind'] == 'stem' else ('stars', 'star')
    return next(v for v in palace['heaven'][group] if v[key] == role['value'])


def validate_context(chart, asset, roles, facts):
    context = asset.get('role_context', {})
    need(isinstance(context, dict), 'role_context 必须为对象')
    for name, item in context.items():
        need(name in roles, f'未登记角色 {name}')
        need(isinstance(item, dict) and set(item) <= {'void_active','void_branch','void_evidence','tomb_active','tomb_branch','tomb_evidence','other_suspensions'}, '角色条件含未知字段')
        role = roles[name]
        for flag in ('void_active', 'tomb_active'):
            need(type(item.get(flag, False)) is bool, f'{flag} 必须为布尔值')
        if item.get('void_active'):
            branch = item.get('void_branch')
            need(branch in chart['xun']['void_branches'] and BRANCH_PALACE.get(branch) == role['palace'], '空亡必须绑定本角色原盘的具体空支')
            nonempty(item.get('void_evidence'), '空亡实际作用依据')
        if item.get('tomb_active'):
            tomb = role_fact(role, facts)['tomb']
            need(tomb['matches'] and item.get('tomb_branch') == tomb['branch'], '实际墓条件与原盘角色位置不符')
            nonempty(item.get('tomb_evidence'), '入墓实际作用依据与采用口径')
        need(isinstance(item.get('other_suspensions', []), list), 'other_suspensions 必须为数组')
        for reason in item.get('other_suspensions', []):
            nonempty(reason, '独立悬置依据')


def role_state(name, role, context, day=None):
    item = context.get(name, {})
    reasons, activations = list(item.get('other_suspensions', [])), []
    branch = day['branch'] if day else None
    if item.get('void_active'):
        if branch == item['void_branch']:
            activations.append({'rule': 'F06', 'role': name, 'branch': branch, 'condition': '填实原绑定空支'})
        else:
            reasons.append('原绑定空支未填实')
    if item.get('tomb_active'):
        if branch and BRANCH_CLASH[branch] == item['tomb_branch']:
            activations.append({'rule': 'F08', 'role': name, 'branch': item['tomb_branch'], 'condition': '冲原绑定墓支'})
        else:
            reasons.append('原绑定墓条件未解除')
    for event in activations:
        event['restores_role'] = not reasons
    return {'role': role, 'suspended': bool(reasons), 'reasons': reasons, 'activations': activations}


def baseline(palace, anchor, suspended, door_pressure, door_suspended=False):
    pair = palace['heaven_stems'][0]+palace['earth_stems'][0]
    identity_door = anchor['kind'] == 'door'
    door = palace['door']
    if suspended:
        return {'value': 0, 'rule': 'F06/F08', 'reason': '主角色作用悬置', 'pair': pair}
    if pair == '辛丁':
        return {'value': 1, 'rule': 'F01', 'reason': '主干辛加丁', 'pair': pair}
    if pair == '辛戊' or (pair == '戊辛' and not identity_door and door in ('死门','惊门','伤门') and not door_pressure and not door_suspended):
        return {'value': -1, 'rule': 'F02', 'reason': '主干辛加戊' if pair == '辛戊' else f'主干戊加辛并临非身份{door}', 'pair': pair}
    if identity_door:
        return {'value': 0, 'rule': 'F04', 'reason': '身份门不重复充当涨跌证据', 'pair': pair}
    if door_pressure or door_suspended:
        return {'value': 0, 'rule': 'F03', 'reason': '门迫或门的实际空墓使门势分支不启用', 'pair': pair}
    value = 1 if door in ('生门','开门','休门') else -1 if door in ('死门','惊门') else 0
    return {'value': value, 'rule': 'F03', 'reason': f'非身份门势：{door}', 'pair': pair}


def daily_force(details):
    values = [SUPPORT[details[k]] for k in ('stem_palace_to_target','branch_palace_to_target')]
    nonzero = set(values)-{0}
    return 'conflict' if len(nonzero) > 1 else next(iter(nonzero), 0)


def grade_for(base, force):
    if force == 'conflict':
        return 0
    if base == 0:
        return force
    return 2*base if base == force else base if force == 0 else 0


def decide(chart, asset, roles, facts, day):
    primary = roles['primary']
    palace = next(p for p in chart['palaces'] if p['number'] == primary['palace'])
    fact_palace = next(p for p in facts['palaces'] if p['number'] == primary['palace'])
    context = asset.get('role_context', {})
    states = {key: role_state(key, role, context, day) for key, role in roles.items()}
    base = baseline(palace, primary, states['primary']['suspended'], fact_palace['human']['door_pressure'], states['direction_door']['suspended'])
    detail = interactions(day, primary, chart)
    force = daily_force(detail)
    grade = grade_for(base['value'], force)
    opposing, seasonal_caps, auxiliary = [], [], {}
    target_element = PALACES[primary['palace']][2]
    keys = list(dict.fromkeys(['capital','profit']+asset.get('key_relation_roles', [])))
    need(all(key in roles and key not in ('primary','direction_door') for key in keys), '关键关系须事前绑定到现有辅助角色')
    for key in keys:
        role = roles[key]
        own_element = PALACES[role['palace']][2]
        direct = relation(own_element, target_element)
        sign = SUPPORT[direct]
        own_state = states[key]
        auxiliary[key] = {'role': role, 'relation_to_primary': direct, 'state': own_state,
                          'daily_contacts': interactions(day, role, chart)}
        # Coincident roles are the same observation, never independent votes.
        if role['palace'] == primary['palace'] or own_state['suspended']:
            continue
        if grade and sign and sign*grade < 0:
            opposing.append(key)
        original = seasonal(own_element, facts['global']['month_element'])['state']
        current = seasonal(own_element, day['month_element'])['state']
        auxiliary[key]['seasonal_change'] = {'original': original, 'day': current}
        if sign*grade > 0 and original in ('旺','相') and current not in ('旺','相'):
            seasonal_caps.append(key)
    primary_old = seasonal(target_element, facts['global']['month_element'])['state']
    primary_new = seasonal(target_element, day['month_element'])['state']
    if primary_old in ('旺','相') and primary_new not in ('旺','相'):
        seasonal_caps.append('primary')
    caps = []
    if abs(grade) == 2:
        if opposing:
            caps.append({'rule':'F09', 'opposing_roles': opposing})
        if seasonal_caps:
            caps.append({'rule':'F10', 'weakened_roles': seasonal_caps})
        if caps:
            grade //= 2
    return {'grade': grade, 'label': LABELS[grade], 'effective_baseline': base, 'daily_force': force,
            'relations': detail, 'role_states': states, 'auxiliary': auxiliary, 'caps': caps,
            'opposing_roles': opposing, 'seasonal_weakening': seasonal_caps,
            'activations': [a for state in states.values() for a in state['activations']],
            'shape_contacts': detail['target_branch_contacts'],
            'motion': {'original_horse': chart['horse'], 'day_horse': day['day_horse'],
                       'original_star_plate': facts['global']['star_plate']['state'],
                       'original_door_plate': facts['global']['door_plate']['state']}}


def normalize_request(request):
    result = deepcopy(request)
    instant(result['issued_at'])
    interval = dates(result['start'], result['end'])
    horizon = result['horizon']
    need(horizon in ('day','week','month'), 'horizon 须为 day/week/month')
    need(horizon != 'day' or len(interval) == 1, '日预测必须指定一个日期')
    need(horizon != 'week' or len(interval) <= 14, '周预测最多覆盖 14 个自然日；需明确实际范围')
    need(horizon != 'month' or len(interval) <= 31, '月预测最多覆盖 31 个自然日')
    result.setdefault('period_style', 'rolling')
    result.setdefault('star_season', 'tongzong')
    need(result['star_season'] in ('tongzong','yanyi_prose'), '九星旺衰配置无效')
    need(result['period_style'] in ('rolling','natural'), 'period_style 须为 natural/rolling')
    if horizon == 'month' and result['period_style'] == 'natural':
        need(interval[0].month == interval[-1].month and interval[0].year == interval[-1].year, '自然月阶段不能跨月')
    need(isinstance(result.get('assets'), list) and bool(result['assets']), '至少需要一个标的')
    ids = set()
    for asset in result['assets']:
        validate_asset(asset)
        need(asset['id'] not in ids, '标的 id 重复')
        ids.add(asset['id'])
        need(asset.get('exposure', 'sector') in ('sector','broad','single'), 'exposure 无效')
        asset['calendar'] = calendar_for(asset)
    return result


def build_forecast(chart, request, *, created_at=None, config=None):
    validate_chart(chart)
    original_hash = digest(chart)
    request = normalize_request(request)
    config = deepcopy(config or profiles())
    need(config['method_id'] == METHOD and config['version'] == VERSION, '方法版本不匹配，须使用对应版本复算')
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    instant(created_at)
    need(instant(chart['input']['captured_at']) <= instant(request['issued_at']), '原盘时刻晚于声明发布时刻')
    facts = inspect_chart(chart, star_season=request['star_season'])
    assets = []
    for asset in request['assets']:
        roles = roles_for(chart, asset, config)
        validate_context(chart, asset, roles, facts)
        state = role_state('primary', roles['primary'], asset.get('role_context', {}))
        palace = next(p for p in chart['palaces'] if p['number'] == roles['primary']['palace'])
        fact = next(p for p in facts['palaces'] if p['number'] == palace['number'])
        door_state = role_state('direction_door', roles['direction_door'], asset.get('role_context', {}))
        base = baseline(palace, roles['primary'], state['suspended'], fact['human']['door_pressure'], door_state['suspended'])
        scale = history_scale(asset, request['issued_at'], config)
        sequence = overlay(chart, asset, request['start'], request['end'], request['issued_at'])
        rows = []
        for row in sequence['days']:
            if row['forecast_scope'] == 'closed':
                row.update(grade=None, decision=None, amplitude=None)
            else:
                decision = decide(chart, asset, roles, facts, row['day'])
                row.update(grade=decision['grade'], decision=decision, amplitude=amplitude(decision['grade'], scale))
                # Preserve any already observed component; never infer it from the chart.
                row['observed_component'] = asset.get('observed_components', {}).get(row['date'])
                row['remaining_amplitude'] = None
                if row['observed_component']:
                    observed = row['observed_component']
                    need(row['forecast_scope'] == 'partial', '已发生部分只用于盘中／采价中预测')
                    value = number(observed['return_pct'], '已发生收益百分比')
                    need(value > -100, '已发生部分须大于 -100% 才可换算后续收益')
                    observed_at = instant(observed['as_of'])
                    need(instant(row['valuation_window']['start']) <= observed_at <= instant(request['issued_at']), '已发生部分的时点须在采价开始与发布时间之间')
                    nonempty(observed.get('source'), '已发生行情来源')
                    if row['amplitude']:
                        row['remaining_amplitude'] = {key: ((1+row['amplitude'][key]/100)/(1+value/100)-1)*100
                                                      for key in ('lower_pct','upper_pct','scenario_midpoint_pct')}
                        row['remaining_amplitude']['kind'] = 'conditional_remainder_of_full_day_scenario'
            rows.append(row)
        assets.append({'asset_id': asset['id'], 'name': asset['name'], 'market': asset['market'],
                       'currency': asset['currency'], 'return_basis': asset['return_basis'],
                       'roles': roles, 'baseline': base, 'scale': scale, 'days': rows,
                       'summary': summarize(rows, scale, base['value'], request['horizon'], request['start'], request['end'], request['period_style'])})
    need(digest(chart) == original_hash, '金融计算修改了原盘')
    record = {'schema_version': SCHEMA, 'skill_version': VERSION, 'method_id': METHOD,
              'created_at': created_at, 'issued_at': request['issued_at'], 'chart_sha256': original_hash,
              'chart_snapshot': deepcopy(chart), 'request_snapshot': request, 'method_snapshot': config,
              'method_sha256': digest(config), 'calibration_status': 'pending_observations', 'assets': assets}
    groups = defaultdict(list)
    for asset in assets:
        for row in asset['days']:
            if row['grade'] is not None:
                key = (row['date'], asset['market'], asset['currency'], asset['return_basis'])
                groups[key].append({'asset_id':asset['asset_id'], 'grade':row['grade']})
    record['rankings'] = []
    for (day, market, currency, basis), items in groups.items():
        if len(items) < 2:
            continue
        grades = sorted({i['grade'] for i in items}, reverse=True)
        for item in items:
            item['rank'] = grades.index(item['grade'])+1
        record['rankings'].append({'date':day,'market':market,'currency':currency,'return_basis':basis,
                                   'basis':'direction_grade_with_ties','items':sorted(items,key=lambda r:(r['rank'],r['asset_id']))})
    record['record_sha256'] = digest(record)
    return record


def markdown(record):
    request = record['request_snapshot']
    lines = [f"# {request['start']} 至 {request['end']} 金融推演", '']
    for asset in record['assets']:
        summary = asset['summary']
        anchor = asset['roles']['primary']
        qualification = '原盘基调' if summary.get('trend_basis','').startswith('原盘') else ''
        lines.extend([f"## {asset['name']}：{qualification}{summary['trend']}", '',
                      f"主对象取{anchor['value']}落{anchor['palace']}宫；原盘基调：{LABELS[asset['baseline']['value']]}（{asset['baseline']['reason']}）。", ''])
        if request['horizon'] == 'month':
            for phase in summary.get('phases', []):
                lines.append(f"- {phase['start']}—{phase['end']}：{phase['trend']}。")
            lines.append('')
        else:
            lines.extend(['| 日期 | 日干支与原宫 | 干宫／支宫作用 | 主判 | 幅度参考 |', '|---|---|---|---|---|'])
            for row in asset['days']:
                day = row['day']
                location = f"{day['day_pillar']}，{day['resolved_stem']}落{day['stem_location']['palace']}；支落{day['branch_palace']}"
                if row['grade'] is None:
                    lines.append(f"| {row['date']} | {location} | — | 休市 | — |")
                    continue
                decision, band = row['decision'], row['amplitude']
                meanings = {'A生B':'来生','比和':'比和','A克B':'来克','B生A':'对象耗泄','B克A':'对象克来方（中性）'}
                relation_text = '/'.join(meanings[decision['relations'][k]] for k in ('stem_palace_to_target','branch_palace_to_target'))
                span = f"{band['lower_pct']:+.2f}%～{band['upper_pct']:+.2f}%" if band else '待补历史尺度'
                scope = {'full':'','partial':'（部分时段）','retrospective':'（事后）','timing_unverified':'（采价窗口待核）'}[row['forecast_scope']]
                lines.append(f"| {row['date']} | {location} | {relation_text} | {decision['label']}{scope} | {span} |")
            lines.extend(['', '干宫、支宫分别作用于主对象宫；来生、比和为扶，来克或对象耗泄为压。', ''])
        if summary['path']:
            path = summary['path']
            lines.append(f"区间路径情景：{path['lower_pct']:+.2f}%～{path['upper_pct']:+.2f}%；情景中点 {path['scenario_midpoint_pct']:+.2f}%。")
        else:
            lines.append('幅度尺度待补；保留方向判断。')
        for row in asset['days']:
            if row.get('observed_component'):
                lines.append(f"{row['date']} 截至 {row['observed_component']['as_of']} 已发生 {row['observed_component']['return_pct']:+.2f}%。")
                rest = row.get('remaining_amplitude')
                if rest:
                    lines.append(f"对应后续时段情景：{rest['lower_pct']:+.2f}%～{rest['upper_pct']:+.2f}%。")
        if asset['scale'].get('proxy'):
            lines.append(f"幅度采用跟踪指数 {asset['scale']['asset_id']} 的同币种同口径历史尺度。")
        if summary['turning_windows']:
            lines.append('转折窗口：'+'；'.join(f"{v['start']}—{v['end']} {v['direction']}" for v in summary['turning_windows'])+'。')
        role_names = {'capital':'资金','profit':'财利','hour_background':'原时干背景','sector':'行业辅助'}
        reasons = sorted({'、'.join(role_names.get(k,k) for k in r['decision']['opposing_roles']) for r in asset['days'] if r['decision'] and r['decision']['opposing_roles']})
        if reasons:
            lines.append('相反依据：'+ '；'.join(reasons)+'与主判存在反向关系，逐日强弱已一并核对。')
        if any(s != 'full' for s in summary['forecast_scopes']):
            scope_names = {'full':'完整时段','partial':'部分时段','retrospective':'事后推演','timing_unverified':'采价窗口待核'}
            lines.append('时点范围：'+ '、'.join(scope_names[s] for s in summary['forecast_scopes'])+'；完整区间数值包含这些时段，分时记录见原始文件。')
        lines.append('')
    lines.append(f"方法 {METHOD}；方向采用登记规则，幅度来自发布前的历史波动。")
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chart', required=True)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--markdown')
    parser.add_argument('--mode', choices=('legacy','multi_role'), default='legacy',
                        help='CLI兼容默认legacy；新综合流程用multi_role生成证据与待填草稿')
    parser.add_argument('--draft', help='multi_role模式的综合判断草稿输出')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'multi_role':
            from finance_context import build_context, markdown as context_markdown
            from finance_synthesis import init_record
            record = build_context(read_json(args.chart), read_json(args.request))
            render = context_markdown
        else:
            need(not args.draft, '--draft仅用于multi_role模式')
            record = build_forecast(read_json(args.chart), read_json(args.request))
            render = markdown
        write_new(args.output, record, [args.chart, args.request])
        if args.draft:
            write_new(args.draft, init_record(record), [args.chart,args.request,args.output])
        if args.markdown:
            write_new(args.markdown, render(record), [args.chart, args.request, args.output])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'金融推演失败：{exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
