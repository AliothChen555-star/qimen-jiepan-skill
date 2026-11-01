"""Replay financial records and score immutable outcome sidecars."""
import argparse
from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from statistics import mean
import sys

from finance_common import SCHEMA, digest, instant, need, nonempty, number, profiles, read_json, write_new
from finance_forecast import build_forecast


def validate_record(record, chart=None):
    need(record.get('schema_version') == SCHEMA, '金融记录模式错误')
    body = deepcopy(record)
    signature = body.pop('record_sha256', None)
    need(signature == digest(body), '金融记录哈希不匹配')
    need(record['chart_sha256'] == digest(record['chart_snapshot']), '原盘快照哈希不匹配')
    if chart is not None:
        need(digest(chart) == record['chart_sha256'], '外部原盘与记录不一致')
    need(record['method_snapshot'] == profiles(), '方法快照与当前版本不一致；请用原版本复算')
    expected = build_forecast(record['chart_snapshot'], record['request_snapshot'], created_at=record['created_at'], config=record['method_snapshot'])
    need(expected == record, '金融记录与冻结输入的复算不一致')
    return {'valid': True, 'record_sha256': signature, 'assets': len(record['assets'])}


def sign(value):
    return (value > 0)-(value < 0)


def evaluate(records, outcomes):
    need(isinstance(outcomes, list), '结局文件须为数组')
    indexed, observed, eligible, excluded = {}, {}, [], defaultdict(int)
    for record in records:
        validate_record(record)
        key = record['record_sha256']
        need(key not in indexed, '预测记录重复')
        indexed[key] = record
    for outcome in outcomes:
        key = (outcome['record_sha256'], outcome['asset_id'], outcome['date'])
        need(key not in observed, '结局记录重复')
        need(key[0] in indexed, '结局没有对应原预测')
        record = indexed[key[0]]
        assets = {a['asset_id']: a for a in record['assets']}
        need(key[1] in assets, '结局标的与预测不符')
        asset = assets[key[1]]
        row = next((r for r in asset['days'] if r['date'] == key[2]), None)
        need(row is not None and row['grade'] is not None, '结局日期不属于原预测交易日')
        need(outcome['currency'] == asset['currency'] and outcome['return_basis'] == asset['return_basis'], '结局币种／口径不一致')
        nonempty(outcome.get('source'), '结局来源')
        value = number(outcome['return_pct'], '实际收益')
        need(value >= -100, '实际收益不能小于 -100%')
        available = instant(outcome['available_at'])
        if row['valuation_window']:
            need(available >= instant(row['valuation_window']['end']), '结局可得时点早于采价完成')
        observed[key] = outcome
    for key, record in indexed.items():
        for asset in record['assets']:
            for row in asset['days']:
                if row['grade'] is None:
                    continue
                identity = (key, asset['asset_id'], row['date'])
                if row['forecast_scope'] != 'full':
                    excluded[row['forecast_scope']] += 1
                    continue
                # Actual file creation is distinct from a user-supplied historical issue date.
                if instant(record['created_at']) >= instant(row['valuation_window']['start']):
                    excluded['created_after_window_start'] += 1
                    continue
                if identity not in observed:
                    excluded['outcome_missing'] += 1
                    continue
                outcome = observed[identity]
                eligible.append((record, asset, row, outcome))
    direction, neutral, errors, coverage, widths = [], [], [], [], []
    bases = defaultdict(list)
    rankings, clusters = defaultdict(list), defaultdict(set)
    confusion = defaultdict(int)
    for record, asset, row, outcome in eligible:
        value, prediction = outcome['return_pct'], sign(row['grade'])
        actual = sign(value)
        direction.append(prediction == actual)
        confusion[f'{prediction}:{actual}'] += 1
        scale = asset['scale']
        group = (record['chart_sha256'], asset['market'], row['date'], asset['currency'], asset['return_basis'])
        rankings[group].append((asset['asset_id'], row['grade'], value))
        clusters[record['chart_sha256']].add((asset['asset_id'], row['date']))
        bases['always_up_direction'].append(actual == 1)
        bases['always_zero_direction'].append(actual == 0)
        band = row['amplitude']
        if band:
            threshold = .2*scale['quantiles']['A50']
            category = 0 if abs(value) <= threshold else sign(value)
            neutral.append(prediction == category)
            errors.append(abs(band['scenario_midpoint_pct']-value))
            coverage.append(band['lower_pct'] <= value <= band['upper_pct'])
            widths.append(band['upper_pct']-band['lower_pct'])
            bases['zero_mae'].append(abs(value))
            bases['historical_mean_mae'].append(abs(scale['historical_mean_pct']-value))
            bases['momentum_mae'].append(abs(scale['last_return_pct']-value))
            bases['momentum_direction'].append(sign(scale['last_return_pct']) == actual)
    concordant, comparable, predicted_ties, actual_ties = 0, 0, 0, 0
    for items in rankings.values():
        unique = {a: (g,v) for a,g,v in items}
        for (ga,va), (gb,vb) in combinations(unique.values(), 2):
            if ga == gb:
                predicted_ties += 1
            if va == vb:
                actual_ties += 1
            if ga != gb and va != vb:
                comparable += 1
                concordant += sign(ga-gb) == sign(va-vb)
    average = lambda values: mean(values) if values else None
    return {'schema_version':'qimen_finance_evaluation_v1', 'records':len(records),
            'eligible_rows':len(eligible), 'excluded_rows':dict(excluded),
            'direction_accuracy':average(direction), 'direction_confusion':dict(confusion),
            'neutral_band_accuracy':average(neutral), 'neutral_scored_rows':len(neutral),
            'midpoint_mae_pct':average(errors), 'scenario_band_coverage':average(coverage),
            'mean_band_width_pct':average(widths), 'amplitude_scored_rows':len(errors),
            'baseline_comparisons':{k:{'value':average(v),'rows':len(v)} for k,v in bases.items()},
            'ranking':{'comparable_pairs':comparable,'concordance':concordant/comparable if comparable else None,
                       'predicted_ties':predicted_ties,'actual_ties':actual_ties},
            'chart_clusters':len(clusters), 'cluster_sizes':{k:len(v) for k,v in clusters.items()},
            'dependence_policy':'同盘及重叠标的日期分组；此报告为描述统计，不将行数当独立样本数',
            'registration_policy':'按记录创建时刻筛选；本地哈希不提供第三方时间戳证明'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('validate')
    check.add_argument('record')
    check.add_argument('--chart')
    score = commands.add_parser('evaluate')
    score.add_argument('--records', nargs='+', required=True)
    score.add_argument('--outcomes', required=True)
    score.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            result = validate_record(read_json(args.record), read_json(args.chart) if args.chart else None)
            print(f"金融记录复算通过，{result['assets']} 个标的")
        else:
            result = evaluate([read_json(p) for p in args.records], read_json(args.outcomes))
            write_new(args.output, result, args.records+[args.outcomes])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'金融记录处理失败：{exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
