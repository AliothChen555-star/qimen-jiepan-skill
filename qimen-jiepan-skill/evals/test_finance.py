"""Financial invariants: frozen chart, time availability, binding and replay."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from daily_overlay import day_state, locate, overlay
from finance_common import calendar_for, digest, local_clock, profiles, session, write_new
from finance_forecast import (baseline, build_forecast, daily_force, grade_for, markdown,
                             role_state, roles_for, validate_context)
from finance_market import amplitude, compound, history_scale, summarize, turning_windows
from finance_record import evaluate, validate_record
from inspect_patterns import inspect_chart
from qimen.chart import cast_chart


def product(**kwargs):
    result = {'id':'TEST:INDEX', 'name':'合成指数', 'market':'XSHG', 'code':'TEST',
              'currency':'CNY', 'instrument':'index', 'return_basis':'price_return', 'metadata_source':'synthetic-test-only'}
    result.update(kwargs)
    return result


def historical(asset, count=60):
    calendar = calendar_for(asset)
    rows = []
    day = date(2026, 10, 29)
    while len(rows) < count:
        if session(day, calendar)['status'] != 'closed':
            rows.append({'date':day.isoformat(), 'available_at':day.isoformat()+'T17:00:00+08:00',
                         'return_pct':(-1 if len(rows)%2 else 1)*(.1+len(rows)/100)})
        day -= timedelta(days=1)
    return {'asset_id':asset['id'],'currency':asset['currency'],'return_basis':asset['return_basis'],
            'source':'synthetic-returns-not-real-prices','rows':list(reversed(rows))}


def request(asset=None, **kwargs):
    result = {'issued_at':'2026-10-31T10:00:00+08:00', 'start':'2026-11-02', 'end':'2026-11-08',
              'horizon':'week', 'assets':[asset or product()]}
    result.update(kwargs)
    return result


class FinancialChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = cast_chart(datetime.fromisoformat('2026-10-30T09:00:00+08:00'))
        cls.config = profiles()
        asset = product()
        asset['history'] = historical(asset)
        cls.record = build_forecast(cls.chart, request(asset), created_at='2026-10-31T10:01:00+08:00')

    def test_frozen_daily_pillars_and_independent_jia(self):
        before = digest(self.chart)
        rows = overlay(self.chart, product(), '2026-11-02','2026-11-08','2026-10-31T10:00+08:00')['days']
        self.assertEqual([r['day']['day_pillar'] for r in rows], ['庚辰','辛巳','壬午','癸未','甲申','乙酉','丙戌'])
        self.assertEqual(rows[4]['day']['resolved_stem'], '庚')
        self.assertEqual(rows[4]['day']['stem_location']['palace'], 1)
        self.assertEqual(rows[4]['day']['branch_palace'], 2)
        self.assertEqual(digest(self.chart), before)
        self.assertEqual(rows[-1]['day']['month_pillar'], '己亥')
        self.assertEqual(rows[-1]['day']['original']['month_pillar'], self.chart['calendar']['month_pillar'])

    def test_center_duplicate_is_not_second_heaven_location(self):
        center = next(p for p in self.chart['palaces'] if p['number'] == 5)
        location = locate(self.chart, 'stem', center['heaven_stems'][0])
        self.assertNotEqual(location['palace'], 5)
        self.assertEqual(location['position'], 'hosted')

    def test_market_holidays_half_day_and_unsupported_year(self):
        hk = calendar_for(product(market='XHKG'))
        self.assertEqual(session(date(2026,12,24),hk)['close_at'], '2026-12-24T12:10:00+08:00')
        self.assertEqual(session(date(2026,12,25),hk)['status'], 'closed')
        self.assertEqual(session(date(2026,10,19),hk)['status'], 'closed')
        with self.assertRaises(ValueError):
            session(date(2027,1,4),hk)
        with self.assertRaises(ValueError):
            calendar_for(product(market='XNYS'))

    def test_closed_rows_have_no_return_but_continue_day_cycle(self):
        rows = self.record['assets'][0]['days']
        self.assertTrue(all(r['grade'] is None and r['amplitude'] is None for r in rows[-2:]))
        self.assertEqual(rows[-1]['day']['day_pillar'], '丙戌')

    def test_partial_and_retrospective_are_not_full(self):
        start = '2026-11-02'
        for issued, expected in [('2026-11-02T10:00+08:00','partial'),('2026-11-02T16:00+08:00','retrospective')]:
            row = overlay(self.chart,product(),start,start,issued)['days'][0]
            self.assertEqual(row['forecast_scope'],expected)

    def test_otc_valuation_date_and_window_have_separate_roles(self):
        asset = product(instrument='fund',return_basis='nav_total_return',share_class='A',valuation_timezone='Asia/Shanghai')
        asset['valuation_windows']={'2026-11-02':{'start':'2026-11-02T14:30:00-05:00','end':'2026-11-02T16:00:00-05:00','source':'synthetic-window'}}
        row = overlay(self.chart,asset,'2026-11-02','2026-11-02','2026-11-02T09:00+08:00')['days'][0]
        self.assertEqual(row['day']['day_pillar'], '庚辰')
        self.assertEqual(row['forecast_scope'], 'full')
        self.assertTrue(row['day']['anchor_at'].startswith('2026-11-02T12:00'))
        asset.pop('valuation_windows')
        row = overlay(self.chart,asset,'2026-11-02','2026-11-02','2026-11-02T09:00+08:00')['days'][0]
        self.assertEqual(row['forecast_scope'], 'timing_unverified')

    def test_custom_market_crosses_original_day_boundary(self):
        asset = product(market='XNYS',currency='USD',calendar={'timezone':'America/New_York','valid_from':'2026-11-01','valid_to':'2026-11-30','open':'09:30','close':'16:00','source':'synthetic-calendar','holidays':[]})
        row = overlay(self.chart,asset,'2026-11-02','2026-11-02','2026-10-31T10:00+08:00')['days'][0]
        self.assertEqual(len(row['day_boundaries_in_session']),1)
        self.assertEqual(row['day_boundaries_in_session'][0]['from'],'庚辰')
        self.assertEqual(row['day_boundaries_in_session'][0]['to'],'辛巳')

    def test_dst_gap_and_repeated_local_time_rejected(self):
        with self.assertRaises(ValueError):
            local_clock(date(2026,3,8),'02:30','America/New_York')
        with self.assertRaises(ValueError):
            local_clock(date(2026,11,1),'01:30','America/New_York')

    def test_candidate_pool_cannot_change_identity_or_grade(self):
        target = product(sector='transport',classification_source='synthetic-industry')
        alone = build_forecast(self.chart,request(target),created_at='2026-10-31T10:01+08:00')
        group = build_forecast(self.chart,request(assets=[product(id='OTHER'),target]),created_at='2026-10-31T10:01+08:00')
        self.assertEqual(alone['assets'][0],group['assets'][1])
        self.assertEqual(alone['assets'][0]['roles']['primary']['value'],'伤门')
        stock = roles_for(self.chart,product(instrument='stock',sector='transport',classification_source='synthetic'),self.config)
        self.assertEqual(stock['primary']['binding'],'original_hour_stem')

    def test_identity_door_and_direct_pair_precedence(self):
        palace = {'heaven_stems':['乙'], 'earth_stems':['丙'], 'door':'生门'}
        self.assertEqual(baseline(palace,{'kind':'door'},False,False)['value'],0)
        palace.update(heaven_stems=['辛'],earth_stems=['丁'])
        self.assertEqual(baseline(palace,{'kind':'door'},False,False)['value'],1)
        self.assertEqual(baseline(palace,{'kind':'door'},True,False)['value'],0)
        palace.update(heaven_stems=['戊'],earth_stems=['辛'],door='伤门')
        self.assertEqual(baseline(palace,{'kind':'door'},False,False)['value'],0)
        self.assertEqual(baseline(palace,{'kind':'stem'},False,False)['value'],-1)
        self.assertEqual(baseline(palace,{'kind':'stem'},False,False,True)['value'],0)

    def test_daily_relations_keep_conflict_and_object_control_neutral(self):
        self.assertEqual(daily_force({'stem_palace_to_target':'A生B','branch_palace_to_target':'A克B'}),'conflict')
        self.assertEqual(daily_force({'stem_palace_to_target':'B克A','branch_palace_to_target':'比和'}),1)
        self.assertEqual(grade_for(-1,1),0)
        self.assertEqual(grade_for(-1,-1),-2)
        self.assertEqual(grade_for(0,'conflict'),0)

    def test_exact_void_binding_and_independent_suspension(self):
        role = {'kind':'stem','value':'壬','palace':3}
        context = {'primary':{'void_active':True,'void_branch':'卯'}}
        self.assertTrue(role_state('primary',role,context,{'branch':'午'})['suspended'])
        self.assertFalse(role_state('primary',role,context,{'branch':'卯'})['suspended'])
        context['primary']['other_suspensions']=['synthetic independent condition']
        state = role_state('primary',role,context,{'branch':'卯'})
        self.assertTrue(state['suspended'])
        self.assertFalse(state['activations'][0]['restores_role'])
        context = {'primary':{'tomb_active':True,'tomb_branch':'辰'}}
        self.assertFalse(role_state('primary',role,context,{'branch':'戌'})['suspended'])
        self.assertTrue(role_state('primary',role,context,{'branch':'酉'})['suspended'])

    def test_invalid_void_or_tomb_binding_rejected(self):
        asset = product(role_context={'primary':{'void_active':True,'void_branch':'卯','void_evidence':'synthetic'}})
        with self.assertRaises(ValueError):
            validate_context(self.chart,asset,roles_for(self.chart,asset,self.config),inspect_chart(self.chart))
        asset['role_context']={'primary':{'tomb_active':True,'tomb_branch':'辰','tomb_evidence':'synthetic'}}
        with self.assertRaises(ValueError):
            validate_context(self.chart,asset,roles_for(self.chart,asset,self.config),inspect_chart(self.chart))

    def test_quantiles_and_asymmetric_signed_bands(self):
        asset = product()
        asset['history'] = historical(asset)
        scale = history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        positive, negative = amplitude(2,scale), amplitude(-2,scale)
        self.assertEqual(positive['lower_pct'],-negative['upper_pct'])
        self.assertEqual(positive['upper_pct'],-negative['lower_pct'])
        self.assertAlmostEqual(scale['quantiles']['A50'],.395)

    def test_unavailable_future_history_never_changes_scale(self):
        asset = product()
        asset['history']=historical(asset)
        initial=history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        asset['history']['rows'].append({'date':'2026-11-02','available_at':'2026-11-02T17:00+08:00','return_pct':999})
        future=history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        self.assertEqual(initial['quantiles'],future['quantiles'])
        self.assertEqual(future['excluded_not_available'],1)

    def test_duplicate_nonfinite_and_early_history_rejected(self):
        for mutate in (lambda rows: rows.append(deepcopy(rows[0])),
                       lambda rows: rows[0].update(return_pct=float('nan')),
                       lambda rows: rows[0].update(available_at=rows[0]['date']+'T10:00+08:00')):
            asset=product()
            asset['history']=historical(asset)
            mutate(asset['history']['rows'])
            with self.assertRaises(ValueError):
                history_scale(asset,'2026-10-31T10:00+08:00',self.config)

    def test_nav_distributions_and_share_changes(self):
        asset=product(instrument='fund',return_basis='nav_total_return',share_class='A',valuation_timezone='Asia/Shanghai')
        asset['history']={'asset_id':asset['id'],'currency':'CNY','return_basis':'nav_total_return','source':'synthetic','mode':'values','rows':[
            {'date':'2026-10-28','available_at':'2026-10-28T20:00+08:00','value':1},
            {'date':'2026-10-29','available_at':'2026-10-29T20:00+08:00','value':.5,'share_factor':2,'cash_distribution':.01}]}
        scale=history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        self.assertAlmostEqual(scale['rows'][0]['return_pct'],1)
        asset['history']['rows'][1]['cumulative_nav']=1.7
        with self.assertRaises(ValueError):
            history_scale(asset,'2026-10-31T10:00+08:00',self.config)

    def test_proxy_requires_explicit_index_currency_and_basis(self):
        asset=product()
        asset['history']=historical(asset)
        asset['history']['asset_id']='INDEX:PROXY'
        with self.assertRaises(ValueError):
            history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        asset.update(tracked_index_id='INDEX:PROXY')
        asset['history']['proxy_reason']='synthetic product history too short'
        self.assertTrue(history_scale(asset,'2026-10-31T10:00+08:00',self.config)['proxy'])
        asset['history']['currency']='HKD'
        with self.assertRaises(ValueError):
            history_scale(asset,'2026-10-31T10:00+08:00',self.config)

    def test_insufficient_history_keeps_direction(self):
        asset=product()
        asset['history']=historical(asset,19)
        record=build_forecast(self.chart,request(asset))
        self.assertEqual(record['assets'][0]['scale']['status'],'insufficient')
        self.assertIsNotNone(record['assets'][0]['days'][0]['grade'])
        self.assertIsNone(record['assets'][0]['days'][0]['amplitude'])

    def test_week_path_is_compounded_not_summed(self):
        asset=self.record['assets'][0]
        values=[r['amplitude']['scenario_midpoint_pct'] for r in asset['days'] if r['amplitude']]
        self.assertAlmostEqual(asset['summary']['path']['scenario_midpoint_pct'],compound(values))
        self.assertAlmostEqual(compound([10,-10]),-1)

    def test_month_has_phases_but_no_daily_percent_table(self):
        record=build_forecast(self.chart,request(end='2026-11-30',horizon='month',period_style='natural'))
        self.assertEqual(len(record['assets'][0]['summary']['phases']),3)
        self.assertNotIn('| 日期 |',markdown(record))
        self.assertGreater(len(record['assets'][0]['days']),20)

    def test_turning_windows_require_persistence(self):
        rows=[{'date':f'2026-11-{i+2:02d}','grade':g,'decision':{'activations':[]}} for i,g in enumerate([1,1,-1,0,-1,-1])]
        windows=turning_windows(rows)
        self.assertEqual(len(windows),1)
        self.assertEqual(windows[0]['start'],'2026-11-06')

    def test_record_replay_detects_rehashed_numeric_tampering(self):
        self.assertTrue(validate_record(self.record,self.chart)['valid'])
        forged=deepcopy(self.record)
        forged['assets'][0]['days'][0]['grade']=2
        forged.pop('record_sha256')
        forged['record_sha256']=digest(forged)
        with self.assertRaises(ValueError):
            validate_record(forged,self.chart)

    def test_outcome_sidecar_and_post_event_creation_exclusion(self):
        record=deepcopy(self.record)
        outcome={'record_sha256':record['record_sha256'],'asset_id':'TEST:INDEX','date':'2026-11-02',
                 'currency':'CNY','return_basis':'price_return','return_pct':0,'available_at':'2026-11-02T17:00+08:00','source':'synthetic-outcome'}
        signature=digest(record)
        result=evaluate([record],[outcome])
        self.assertEqual(result['eligible_rows'],1)
        self.assertEqual(result['excluded_rows']['outcome_missing'],4)
        self.assertEqual(result['chart_clusters'],1)
        self.assertEqual(digest(record),signature)
        late=build_forecast(self.chart,record['request_snapshot'],created_at='2026-12-01T10:00+08:00')
        outcome['record_sha256']=late['record_sha256']
        self.assertEqual(evaluate([late],[outcome])['eligible_rows'],0)
        with self.assertRaises(ValueError):
            evaluate([late],[outcome,outcome])

    def test_new_outputs_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'record.json'
            write_new(path,{'first':True})
            with self.assertRaises(FileExistsError):
                write_new(path,{'first':False})
            self.assertIn('true',path.read_text(encoding='utf-8'))

    def test_missing_price_session_is_not_one_daily_return(self):
        asset=product()
        asset['history']={'asset_id':asset['id'],'currency':'CNY','return_basis':'price_return','source':'synthetic','mode':'values','rows':[
            {'date':'2026-10-26','available_at':'2026-10-26T17:00+08:00','value':100},
            {'date':'2026-10-28','available_at':'2026-10-28T17:00+08:00','value':110}]}
        with self.assertRaises(ValueError):
            history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        asset['history']['rows'][1]['reference_value']=108
        scale=history_scale(asset,'2026-10-31T10:00+08:00',self.config)
        self.assertAlmostEqual(scale['rows'][0]['return_pct'],(110/108-1)*100)

    def test_intraday_remainder_and_observed_future_rejection(self):
        asset=product()
        asset['history']=historical(asset)
        asset['observed_components']={'2026-11-02':{'return_pct':.5,'as_of':'2026-11-02T10:00+08:00','source':'synthetic-intraday'}}
        req=request(asset,start='2026-11-02',end='2026-11-02',horizon='day',issued_at='2026-11-02T10:01+08:00')
        record=build_forecast(self.chart,req)
        row=record['assets'][0]['days'][0]
        rest=row['remaining_amplitude']['scenario_midpoint_pct']
        self.assertAlmostEqual(compound([.5,rest]),row['amplitude']['scenario_midpoint_pct'])
        req['assets'][0]['observed_components']['2026-11-02']['as_of']='2026-11-02T11:00+08:00'
        with self.assertRaises(ValueError):
            build_forecast(self.chart,req)

    def test_rankings_preserve_ties_and_market_separation(self):
        record=build_forecast(self.chart,request(assets=[product(id='A'),product(id='B'),product(id='HK',market='XHKG',currency='HKD')]))
        self.assertEqual(len(record['rankings']),5)
        self.assertEqual({i['rank'] for i in record['rankings'][0]['items']},{1})
        self.assertEqual({i['asset_id'] for i in record['rankings'][0]['items']},{'A','B'})

    def test_day_without_scale_uses_daily_direction_in_heading(self):
        record=build_forecast(self.chart,request(start='2026-11-03',end='2026-11-03',horizon='day'))
        asset=record['assets'][0]
        self.assertEqual(asset['days'][0]['grade'],0)
        self.assertEqual(asset['summary']['trend'],'震荡')
        self.assertNotIn('## 合成指数：偏跌',markdown(record))


if __name__ == '__main__':
    unittest.main()
