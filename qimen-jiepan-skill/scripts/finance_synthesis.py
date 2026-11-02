"""Draft, publish and evaluate explicit multi-role judgments without rewriting evidence."""
from copy import deepcopy
from datetime import datetime, timezone
from collections import defaultdict
import operator

from finance_common import digest, instant, need, nonempty, number
from finance_context import METHOD, METHOD_VERSION, SKILL_VERSION, effective_scope, validate_context

SCHEMA = 'qimen_finance_synthesis_v2'
OPERATORS = {'<':operator.lt, '<=':operator.le, '>':operator.gt, '>=':operator.ge, '==':operator.eq}
METRICS = {
    'return_pct':'same_asset_return', 'gap_pct':'ohlc', 'intraday_return_pct':'ohlc',
    'amplitude_pct':'ohlc', 'body_range_pct':'ohlc', 'close_position_in_range_pct':'ohlc',
    'upper_shadow_points':'ohlc', 'lower_shadow_points':'ohlc',
    'last_30m_return_pct':'minutes', 'last_30m_range_points':'minutes',
    'volume_change_pct':'volume', 'amount_change_pct':'amount',
}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def claim_index(context):
    return {(asset['asset_id'], row['date']):(asset,row)
            for asset in context['assets'] for row in asset['days']
            if row['market_session']['status'] != 'closed'}


def seal(record):
    record.pop('record_sha256',None)
    record['record_sha256'] = digest(record)
    return record


def init_record(context, *, created_at=None):
    validate_context(context)
    created_at = created_at or timestamp()
    need(instant(created_at) >= instant(context['created_at']), '草稿创建不能早于证据创建')
    claims = []
    for (asset_id, day), (asset,row) in claim_index(context).items():
        claims.append({'asset_id':asset_id,'date':day,'currency':asset['currency'],
                       'return_basis':asset['return_basis'], 'forecast_scope':effective_scope(row,created_at),
                       'direction':None,'supporting_roles':[],'opposing_roles':[],
                       'rationale':'','conflict_resolution':'','conditions':[], 'unresolved':[],
                       'shape_forecasts':[]})
    return {'schema_version':SCHEMA,'method_id':METHOD,'method_version':METHOD_VERSION,
            'skill_version':SKILL_VERSION,'status':'draft','created_at':created_at,'published_at':None,
            'context_sha256':context['context_sha256'],'context_snapshot':deepcopy(context),'claims':claims,
            'calibration_status':'uncalibrated','authoring':'explicit_synthesis_not_automatic_price_model'}


def check_claims(record, *, published):
    context = record['context_snapshot']
    expected = claim_index(context)
    seen = set()
    need(isinstance(record['claims'],list), '综合判断须为数组')
    for claim in record['claims']:
        key = (claim['asset_id'],claim['date'])
        need(key in expected and key not in seen, '判断标的日期不符或重复')
        seen.add(key)
        asset, row = expected[key]
        need(claim['currency']==asset['currency'] and claim['return_basis']==asset['return_basis'], '判断收益口径不符')
        roles = asset['roles']
        for field in ('supporting_roles','opposing_roles'):
            values = claim.get(field)
            need(isinstance(values,list) and all(isinstance(v,str) and v in roles for v in values), '证据角色未在本标的登记')
            need(len(values)==len(set(values)), '证据角色重复')
        for field in ('conditions','unresolved'):
            need(isinstance(claim.get(field),list), field+'须为数组')
            for value in claim[field]:
                nonempty(value,field)
        need(isinstance(claim.get('shape_forecasts'),list), '形态判据须为数组')
        shapes = set()
        for shape in claim['shape_forecasts']:
            name = nonempty(shape.get('id'),'形态判据id')
            need(name not in shapes,'形态判据id重复')
            shapes.add(name)
            metric = shape.get('metric')
            need(metric in METRICS and shape.get('basis')==METRICS[metric], '形态指标或采价口径未登记')
            need(shape.get('operator') in OPERATORS, '不支持的判据运算符')
            number(shape.get('value'),'形态阈值')
            nonempty(shape.get('reason'),'事前形态标准依据')
        if published:
            need(claim.get('direction') in ('up','down','undetermined'), '发布前须明确涨、跌或方向未明')
            nonempty(claim.get('rationale'),'综合判断理由')
            nonempty(claim.get('conflict_resolution'),'主辅冲突与裁决')
            if claim['direction'] != 'undetermined':
                need('product.primary' in roles, '主题未核的基金不能自动继承大盘方向')
                need(claim['supporting_roles'] and claim['conditions'], '明确方向须有支持角色与成立条件')
            at = max((record['published_at'],context['issued_at']),key=instant)
            need(claim['forecast_scope']==effective_scope(row,at), '发布时序与采价窗口不符')
    need(seen==set(expected), '交易日判断缺项，不能静默删除不利样本')


def publish_record(draft, *, published_at=None):
    need(draft.get('status')=='draft', '只能从草稿发布新记录，修订另建版本')
    validate_record(draft)
    result = deepcopy(draft)
    at = published_at or timestamp()
    context = result['context_snapshot']
    need(instant(at)>=instant(result['created_at']), '发布早于草稿创建')
    need(instant(at)>=instant(context['issued_at']), '声明发布时间尚未到达')
    result['published_at'], result['status'] = at,'published'
    indexed = claim_index(context)
    for claim in result['claims']:
        claim['forecast_scope'] = effective_scope(indexed[(claim['asset_id'],claim['date'])][1],at)
    check_claims(result,published=True)
    return seal(result)


def validate_record(record, chart=None):
    need(record.get('schema_version')==SCHEMA, '综合记录模式错误')
    need(record.get('method_id')==METHOD and record.get('method_version')==METHOD_VERSION, '综合方法版本不符')
    need(record.get('status') in ('draft','published'), '综合记录状态不符')
    context = record['context_snapshot']
    validate_context(context,chart)
    need(context['context_sha256']==record['context_sha256'], '证据引用哈希不符')
    need(instant(record['created_at'])>=instant(context['created_at']), '草稿创建早于证据')
    published = record['status']=='published'
    if published:
        at = instant(record['published_at'])
        need(at>=instant(record['created_at']) and at>=instant(context['issued_at']), '发布时点错误')
        body = deepcopy(record)
        signature = body.pop('record_sha256',None)
        need(signature==digest(body), '综合记录哈希不符')
    else:
        need(record.get('published_at') is None and 'record_sha256' not in record, '草稿不能冒充冻结预测')
    check_claims(record,published=published)
    return {'valid':True,'assets':len(context['assets']),'status':record['status'],
            'validation_scope':'证据复算与判断结构核验；不表示判断由算法推导或价格预测已验证'}


def evaluate(records, outcomes):
    need(isinstance(outcomes,list),'结局文件须为数组')
    indexed, observed = {},{}
    excluded = defaultdict(int)
    for record in records:
        validate_record(record)
        need(record['status']=='published','草稿不能参加预测评分')
        key = record['record_sha256']
        need(key not in indexed,'预测记录重复')
        indexed[key] = record
    for outcome in outcomes:
        key = (outcome['record_sha256'],outcome['asset_id'],outcome['date'])
        need(key not in observed and key[0] in indexed, '结局重复或没有对应预测')
        context = indexed[key[0]]['context_snapshot']
        candidates = claim_index(context)
        need(key[1:] in candidates, '结局标的日期不符')
        asset,row = candidates[key[1:]]
        nonempty(outcome.get('source'),'结局来源')
        instant(outcome['available_at'])
        need(outcome.get('observation_kind','exact') in ('exact','proxy'), '结局类型须为exact或proxy')
        if outcome.get('observation_kind','exact')=='exact':
            need(outcome['currency']==asset['currency'] and outcome['return_basis']==asset['return_basis'], '结局币种或收益口径不符')
            need(number(outcome['return_pct'],'结局收益')>=-100,'结局收益不合理')
        if row.get('valuation_window'):
            need(instant(outcome['available_at'])>=instant(row['valuation_window']['end']), '完整日结局早于采价完成')
        for name,value in outcome.get('metrics',{}).items():
            need(name in METRICS,'未知结局指标')
            number(value,'结局指标')
        observed[key] = outcome
    K = P = C = registered = 0
    confusion, shapes, clusters = defaultdict(int),defaultdict(lambda:{'scored':0,'correct':0,'missing':0}),set()
    missing = 0
    for key,record in indexed.items():
        context = record['context_snapshot']
        for claim in record['claims']:
            if context['evaluation_role']!='prospective':
                excluded['development_sample'] += 1
                continue
            if claim['forecast_scope']!='full':
                excluded[claim['forecast_scope']] += 1
                continue
            registered += 1
            outcome = observed.get((key,claim['asset_id'],claim['date']))
            if outcome is None:
                missing += 1
                excluded['outcome_missing'] += 1
                continue
            if outcome.get('observation_kind','exact')=='proxy':
                excluded['proxy_is_not_exact_outcome'] += 1
                continue
            K += 1
            value = outcome['return_pct']
            actual = 'up' if value>0 else 'down' if value<0 else 'flat'
            prediction = claim['direction']
            confusion[prediction+':'+actual] += 1
            if prediction!='undetermined':
                P += 1
                C += prediction==actual
            clusters.add(context['chart_sha256'])
            for shape in claim['shape_forecasts']:
                metric = shape['metric']
                item = shapes[metric]
                metrics = dict(outcome.get('metrics',{}),return_pct=value)
                bases = dict(outcome.get('metric_bases',{}),return_pct='same_asset_return')
                if metric not in metrics or bases.get(metric)!=shape['basis']:
                    item['missing'] += 1
                    continue
                item['scored'] += 1
                item['correct'] += OPERATORS[shape['operator']](metrics[metric],shape['value'])
    return {'schema_version':'qimen_finance_evaluation_v2','method_id':METHOD,'records':len(records),
            'eligible_registered_rows':registered,'eligible_observed_rows':K,'outcomes_missing':missing,
            'counts':{'K':K,'P':P,'C':C},'direction_accuracy':C/P if P else None,
            'direction_coverage':P/K if K else None,'correct_per_observed_row':C/K if K else None,
            'excluded_rows':dict(excluded),'direction_confusion':dict(confusion),
            'shape_scores':{k:dict(v,accuracy=v['correct']/v['scored'] if v['scored'] else None) for k,v in shapes.items()},
            'chart_clusters':len(clusters),'calibration_status':'descriptive_only',
            'definition':'K=有同口径结局的完整前瞻行；P=其中明确涨跌的行；C=其中方向正确行；方向未明不等于窄幅',
            'registration_policy':'发布时点参与筛选；本地哈希并非第三方时间戳；同盘样本不独立'}


def markdown(record):
    labels = {'up':'偏涨','down':'偏跌','undetermined':'方向未明',None:'待综合'}
    lines = ['# 金融综合判断','','状态：'+record['status']+'；方法未经价格预测校准。','',
             '| 标的 | 日期 | 方向 | 时序 | 理由与反证裁决 |','|---|---|---|---|---|']
    for claim in record['claims']:
        rationale = (claim['rationale']+'；'+claim['conflict_resolution']).replace('|','／').replace('\n',' ')
        lines.append(f"| {claim['asset_id']} | {claim['date']} | {labels[claim['direction']]} | {claim['forecast_scope']} | {rationale} |")
    return '\n'.join(lines)+'\n'
