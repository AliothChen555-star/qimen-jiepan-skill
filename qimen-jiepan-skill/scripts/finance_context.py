"""Frozen multi-role financial evidence; prices and final judgments are separate."""
import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import sys

from chart_validation import validate_chart
from daily_overlay import interactions, locate, overlay
from finance_common import ASSETS, digest, instant, need, nonempty, number, read_json, write_new
from finance_forecast import build_forecast, normalize_request
from inspect_patterns import BRANCH_ELEMENTS, STEM_ELEMENTS, inspect_chart, relation, resolve_pillar_stem
from qimen.rules import BRANCH_PALACE, PALACES

SCHEMA = 'qimen_finance_context_v2'
METHOD = 'FINANCE_MULTI_ROLE_V2_CANDIDATE'
METHOD_VERSION = '0.1.0'
SKILL_VERSION = '0.10.0'


def multi_profiles():
    return read_json(ASSETS / 'finance_multi_role.json')


def location(chart, spec):
    kind = spec['kind']
    if kind == 'chief_star':
        return locate(chart, 'star', chart['chief']['zhi_fu'])
    if kind == 'chief_door':
        return locate(chart, 'door', chart['chief']['zhi_shi'])
    if kind == 'hour_stem':
        return locate(chart, 'stem', resolve_pillar_stem(chart['calendar']['hour_pillar']))
    if kind == 'palace':
        value = spec['value']
        need(type(value) is int and value in PALACES and value != 5, '固定宫须为外八宫')
        return {'kind': 'palace', 'value': value, 'palace': value, 'position': 'fixed'}
    return locate(chart, kind, spec['value'])


def effective_scope(row, at):
    if row['market_session']['status'] == 'closed':
        return 'closed'
    window = row.get('valuation_window')
    if not window:
        return 'timing_unverified'
    moment = instant(at)
    return 'full' if moment < instant(window['start']) else 'partial' if moment < instant(window['end']) else 'retrospective'


def theme_for(asset, config):
    if asset['instrument'] == 'index' and not asset.get('theme'):
        return 'index', asset['metadata_source']
    if asset['instrument'] == 'stock' and not asset.get('theme'):
        return None, asset['metadata_source']
    theme = asset.get('theme')
    if theme is None:
        return None, None
    need(theme in config['themes'], '复合主题未登记，须先选择已登记主题或另立方法')
    source = nonempty(asset.get('theme_source'), '主题与产品的对应来源')
    return theme, source


def check_exposures(asset, config, issued_at):
    rows = asset.get('exposures', [])
    need(isinstance(rows, list), 'exposures 必须为数组')
    seen, total = set(), 0
    for item in rows:
        key = nonempty(item.get('id'), '敞口id')
        need(key not in seen, '敞口id重复')
        seen.add(key)
        need(item.get('theme') in config['themes'], '敞口主题未登记')
        nonempty(item.get('source'), '敞口资料来源')
        period = date.fromisoformat(nonempty(item.get('as_of'), '敞口归属日'))
        need(period <= datetime.fromisoformat(issued_at).date(), '敞口归属日晚于声明时点')
        if item.get('available_at'):
            need(instant(item['available_at']) <= instant(issued_at), '敞口资料在声明时点尚不可得')
        if item.get('weight_pct') is not None:
            value = number(item['weight_pct'], '敞口权重百分比')
            need(0 <= value <= 100, '敞口权重须在0—100之间')
            total += value
    need(total <= 100.000001, '同一组敞口权重超过100%')
    return deepcopy(rows)


def role_geometry(where, facts):
    palace = next(p for p in facts['palaces'] if p['number'] == where['palace'])
    if where['kind'] == 'door':
        item = palace['human']
    elif where['kind'] in ('stem', 'star'):
        plural, singular = ('stems', 'stem') if where['kind'] == 'stem' else ('stars', 'star')
        item = next(v for v in palace['heaven'][plural] if v[singular] == where['value'])
    else:
        item = None
    return {'palace_fact_number': where['palace'], 'void_branches': palace['void_branches'],
            'void_coverage': palace['activation']['void_coverage'],
            'item_fact': deepcopy(item), 'conditions_are_not_automatically_active': True}


def checked_conditions(asset, roles, facts, chart):
    conditions = asset.get('analysis_conditions', {})
    need(isinstance(conditions, dict), 'analysis_conditions须为对象')
    for name, item in conditions.items():
        need(name in roles, '条件引用了未知角色：'+name)
        need(isinstance(item, dict) and set(item) <= {'void_branch','tomb_branch','evidence'}, '角色条件字段错误')
        nonempty(item.get('evidence'), '已绑定限制的依据')
        need(item.get('void_branch') or item.get('tomb_branch'), '角色限制未给具体支')
        where = roles[name]['location']
        if item.get('void_branch'):
            branch = item['void_branch']
            need(branch in chart['xun']['void_branches'] and BRANCH_PALACE.get(branch) == where['palace'], '空亡必须对应原盘本角色的具体空支')
        if item.get('tomb_branch'):
            fact = role_geometry(where, facts)['item_fact']
            need(fact and fact.get('tomb', {}).get('matches') and fact['tomb']['branch'] == item['tomb_branch'], '墓条件与本角色实际结构不符')
            verification = fact['tomb'].get('verification')
            need(verification != 'partial', '未核整表墓不能自动升级为实际作用')
    return deepcopy(conditions)


def build_context(chart, request, *, created_at=None, config=None):
    validate_chart(chart)
    before = digest(chart)
    request = normalize_request(request)
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    instant(created_at)
    need(instant(chart['input']['captured_at']) <= instant(request['issued_at']), '原盘晚于声明发布时间')
    config = deepcopy(config or multi_profiles())
    need(config['method_id'] == METHOD and config['version'] == METHOD_VERSION, '综合方法版本不符')
    evaluation_role = request.get('evaluation_role', 'prospective')
    need(evaluation_role in ('prospective','development'), 'evaluation_role须为prospective或development')
    facts = inspect_chart(chart, star_season=request['star_season'])
    assets = []
    for asset in request['assets']:
        if asset.get('target_etf') is not None:
            target = asset['target_etf']
            need(isinstance(target,dict), '目标ETF档案须为对象')
            for field in ('id','market','code','name','metadata_source'):
                nonempty(target.get(field),'target_etf.'+field)
        roles = {}
        for name, spec in config['market_roles'].items():
            roles[name] = {'location': location(chart, spec), 'purpose': spec['purpose'], 'mapping_source': config['source_id']}
        theme, source = theme_for(asset, config)
        if theme:
            profile = config['themes'][theme]
            roles['product.primary'] = {'location': location(chart, profile['primary']), 'purpose': profile['label'], 'mapping_source': config['source_id'], 'product_source': source}
            for i, spec in enumerate(profile['secondary']):
                roles[f'product.secondary.{i}'] = {'location': location(chart, spec), 'purpose': '已固定主题辅助；不重复计票', 'mapping_source': config['source_id']}
        elif asset['instrument'] == 'stock':
            roles['product.primary'] = {'location': location(chart, {'kind':'hour_stem'}), 'purpose':'单只股票问题主对象', 'mapping_source':config['source_id']}
        exposures = check_exposures(asset, config, request['issued_at'])
        for item in exposures:
            spec = config['themes'][item['theme']]['primary']
            roles['exposure.'+item['id']] = {'location':location(chart, spec), 'purpose':item['theme'], 'product_source':item['source'], 'weight_pct':item.get('weight_pct'), 'mapping_source':config['source_id']}
        for value in roles.values():
            value['geometry'] = role_geometry(value['location'], facts)
        conditions = checked_conditions(asset, roles, facts, chart)
        coordinate = overlay(chart, asset, request['start'], request['end'], request['issued_at'])
        days = []
        for row in coordinate['days']:
            actual_scope = effective_scope(row, created_at)
            # The later of declaration and creation never upgrades a historical run.
            at = max((request['issued_at'], created_at), key=instant)
            declared_scope = row['forecast_scope']
            row = deepcopy(row)
            row['declared_scope'] = declared_scope
            row['scope_at_creation'] = actual_scope
            row['forecast_scope'] = effective_scope(row, at)
            day = row['day']
            row['element_layers'] = {'day_stem':STEM_ELEMENTS[day['day_stem']],
                                     'resolved_stem':STEM_ELEMENTS[day['resolved_stem']],
                                     'day_branch':BRANCH_ELEMENTS[day['branch']],
                                     'stem_palace':PALACES[day['stem_location']['palace']][2],
                                     'branch_palace':PALACES[day['branch_palace']][2]}
            row['role_relations'] = {name: interactions(row['day'], value['location'], chart) for name, value in roles.items()}
            for name,value in roles.items():
                target_element = PALACES[value['location']['palace']][2]
                row['role_relations'][name]['branch_element_to_target'] = relation(BRANCH_ELEMENTS[day['branch']],target_element)
                row['role_relations'][name]['day_stem_element_to_target'] = relation(STEM_ELEMENTS[day['day_stem']],target_element)
                row['role_relations'][name]['resolved_stem_element_to_target'] = relation(STEM_ELEMENTS[day['resolved_stem']],target_element)
            row['bound_conditions'] = {}
            for name, item in conditions.items():
                contacts = row['role_relations'][name]['target_branch_contacts']
                void_active = bool(item.get('void_branch')) and row['day']['branch'] != item['void_branch']
                tomb_active = bool(item.get('tomb_branch')) and not any(c['kind']=='六冲' and c['original_branch']==item['tomb_branch'] for c in contacts)
                row['bound_conditions'][name] = {'suspended':void_active or tomb_active, 'void_active':void_active, 'tomb_active':tomb_active, 'binding':item}
            days.append(row)
        groups = {}
        for name, role in roles.items():
            groups.setdefault(str(role['location']['palace']), []).append(name)
        relation_rows = []
        primary = roles.get('product.primary')
        if primary:
            target = PALACES[primary['location']['palace']][2]
            for name, role in roles.items():
                origin = role['location']['palace']
                relation_rows.append({'role':name,'to':'product.primary','relation':relation(PALACES[origin][2],target),'coincident':origin==primary['location']['palace']})
        assets.append({'asset_id':asset['id'], 'name':asset['name'], 'market':asset['market'], 'currency':asset['currency'], 'return_basis':asset['return_basis'], 'instrument':asset['instrument'],
                       'theme':theme, 'theme_source':source, 'theme_limit':config['themes'][theme].get('limit') if theme else '基金主题尚未绑定，不能用大盘方向自动填充',
                       'exposures':exposures, 'weighted_return_computed':False, 'roles':roles, 'coincident_role_groups':groups,
                       'relations_to_product':relation_rows, 'analysis_conditions':conditions,
                       'legacy_conditions_not_transferred':bool(asset.get('role_context')), 'days':days})
    baseline = build_forecast(chart, request, created_at=created_at)
    result = {'schema_version':SCHEMA,'skill_version':SKILL_VERSION,'method_id':METHOD,'method_version':METHOD_VERSION,
              'created_at':created_at,'issued_at':request['issued_at'],'evaluation_role':evaluation_role,'chart_sha256':before,'chart_snapshot':deepcopy(chart),
              'request_snapshot':request,'method_snapshot':config,'method_sha256':digest(config),'facts':facts,'assets':assets,
              'legacy_baseline':baseline,'calibration_status':'pending_observations','automatic_final_direction':False}
    need(digest(chart) == before, '综合上下文修改了原盘')
    result['context_sha256'] = digest(result)
    return result


def validate_context(context, chart=None):
    need(context.get('schema_version') == SCHEMA, '综合上下文模式错误')
    body = deepcopy(context)
    signature = body.pop('context_sha256', None)
    need(signature == digest(body), '综合上下文哈希错误')
    need(context['method_snapshot'] == multi_profiles(), '综合方法快照不符，须用相同版本复核')
    if chart is not None:
        need(digest(chart) == context['chart_sha256'], '外部原盘不一致')
    expected = build_context(context['chart_snapshot'],context['request_snapshot'],created_at=context['created_at'],config=context['method_snapshot'])
    need(expected == context, '综合证据与原盘或冻结输入不一致')
    return {'valid':True,'assets':len(context['assets']),'context_sha256':signature}


def markdown(context):
    lines = ['# 金融综合解盘证据', '', '以下为冻结证据与旧基线，最终综合判断另填记录，不把草稿当预测。', '']
    for asset in context['assets']:
        lines.extend(['## '+asset['name'],'', '主题：'+str(asset['theme'] or '待核')+'。', '', '| 角色 | 符号 | 宫 | 用途 |','|---|---|---:|---|'])
        for name, role in asset['roles'].items():
            where = role['location']
            lines.append(f"| {name} | {where['value']} | {where['palace']} | {role['purpose']} |")
        lines.extend(['','| 日期 | 日柱 | 流干原宫 | 日支五行／本宫五行 | 时序 |','|---|---|---:|---|---|'])
        for row in asset['days']:
            day = row['day']
            elements = row['element_layers']
            lines.append(f"| {row['date']} | {day['day_pillar']} | {day['stem_location']['palace']}（{elements['stem_palace']}） | {day['branch']}{elements['day_branch']}／{day['branch_palace']}宫{elements['branch_palace']} | {row['forecast_scope']} |")
        lines.append('')
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chart',required=True)
    parser.add_argument('--request',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--draft')
    parser.add_argument('--markdown')
    args = parser.parse_args(argv)
    try:
        context = build_context(read_json(args.chart),read_json(args.request))
        write_new(args.output,context,[args.chart,args.request])
        if args.draft:
            from finance_synthesis import init_record
            write_new(args.draft,init_record(context),[args.chart,args.request,args.output])
        if args.markdown:
            write_new(args.markdown,markdown(context),[args.chart,args.request,args.output])
    except (ValueError,OSError,KeyError,TypeError) as error:
        print('综合证据生成失败：'+str(error),file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
