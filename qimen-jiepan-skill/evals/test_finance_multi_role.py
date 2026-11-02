"""Financial workflow invariants, with synthetic products and observations only."""
from copy import deepcopy
from datetime import datetime,timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from finance_common import digest,read_json
from finance_context import build_context,validate_context
from finance_synthesis import init_record,publish_record,validate_record,evaluate
from finance_forecast import main as forecast_main
from finance_observe import (bar_metrics,compare_minutes,minute_map,parse_eastmoney_daily,
    parse_tencent_quote,analyze_product,validate_product)
from inspect_patterns import resolve_pillar_stem
from qimen.chart import cast_chart


def product(theme='ai',**kwargs):
    value = {'id':'SYNTH:'+theme,'name':'Synthetic '+theme,'market':'XSHG','code':'TEST',
             'currency':'CNY','instrument':'fund','share_class':'C','valuation_timezone':'Asia/Shanghai',
             'return_basis':'nav_total_return','metadata_source':'synthetic-only',
             'theme':theme,'theme_source':'synthetic-product-research',
             'valuation_windows':{f'2026-11-0{i}':{'start':f'2026-11-0{i}T09:30:00+08:00',
                 'end':f'2026-11-0{i}T15:00:00+08:00','source':'synthetic-calendar'} for i in range(2,7)}}
    value.update(kwargs)
    return value


def request(assets=None,**kwargs):
    value = {'issued_at':'2026-11-02T14:54:31+08:00','start':'2026-11-02','end':'2026-11-08',
             'horizon':'week','evaluation_role':'prospective','assets':assets or [product()]}
    value.update(kwargs)
    return value


def fill(draft,direction='up'):
    for claim in draft['claims']:
        claim.update(direction=direction,supporting_roles=['product.primary'],opposing_roles=['market.capital'],
                     rationale='Synthetic judgment for structural test; not a price forecast.',
                     conflict_resolution='Synthetic resolution retains capital constraint.',
                     conditions=['Synthetic observation condition.'])
    return draft


class MultiRoleChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = cast_chart('2026-11-02T14:54:31+08:00')
        cls.context = build_context(cls.chart,request(),created_at='2026-11-02T16:00:00+08:00')
        cls.draft = fill(init_record(cls.context,created_at='2026-11-02T16:01:00+08:00'))
        cls.record = publish_record(cls.draft,published_at='2026-11-02T16:02:00+08:00')

    def test_exact_original_roles_and_hosted_capital(self):
        roles = self.context['assets'][0]['roles']
        expected = {'market.index':9,'market.trend':9,'market.capital':7,'market.profit':8,
                    'market.participation':6,'market.process':4,'market.issue':2}
        self.assertEqual({k:roles[k]['location']['palace'] for k in expected},expected)
        self.assertEqual(roles['market.capital']['location']['position'],'hosted')
        self.assertIn('market.trend',self.context['assets'][0]['coincident_role_groups']['9'])
        self.assertFalse(self.context['automatic_final_direction'])

    def test_jia_resolves_own_pillar_not_original_xun(self):
        pillars = ['甲子','甲戌','甲申','甲午','甲辰','甲寅']
        self.assertEqual([resolve_pillar_stem(v) for v in pillars],list('戊己庚辛壬癸'))
        friday = self.context['assets'][0]['days'][4]['day']
        self.assertEqual((friday['day_pillar'],friday['resolved_stem'],friday['stem_location']['palace']),('甲申','庚',4))
        self.assertEqual(friday['branch_palace'],2)
        friday_relations=self.context['assets'][0]['days'][4]['role_relations']['product.primary']
        self.assertEqual(friday_relations['day_stem_element_to_target'],'A生B')
        self.assertEqual(friday_relations['resolved_stem_element_to_target'],'B克A')
        self.assertFalse(any(c['kind']=='六冲' and c['original_branch']=='丑' for c in friday['branch_contacts']))

    def test_branch_element_and_branch_palace_element_are_distinct(self):
        tuesday=self.context['assets'][0]['days'][1]
        self.assertEqual(tuesday['element_layers']['day_branch'],'火')
        self.assertEqual(tuesday['element_layers']['branch_palace'],'木')
        relation=tuesday['role_relations']['product.primary']
        self.assertEqual(relation['branch_palace_to_target'],'A生B')
        self.assertEqual(relation['branch_element_to_target'],'比和')

    def test_explicit_void_is_bound_to_exact_branch(self):
        asset = product(analysis_conditions={'market.capital':{'void_branch':'酉','evidence':'Synthetic exact branch binding.'}})
        context = build_context(self.chart,request([asset]),created_at='2026-11-02T16:00:00+08:00')
        days = context['assets'][0]['days']
        self.assertTrue(days[4]['bound_conditions']['market.capital']['void_active'])
        self.assertFalse(days[5]['bound_conditions']['market.capital']['void_active'])
        asset['analysis_conditions']['market.capital']['void_branch']='申'
        with self.assertRaises(ValueError):
            build_context(self.chart,request([asset]))

    def test_theme_keeps_compound_exposures_and_unknown_weights(self):
        themes = ['ai','nonferrous_metals','power_generation','power_equipment','dividend_low_volatility']
        assets = [product(t) for t in themes]
        assets[0]['sector']='manufacturing'
        assets[0]['classification_source']='Synthetic broad accounting category.'
        assets[0]['exposures']=[{'id':'hardware','theme':'semiconductor','source':'synthetic','as_of':'2026-10-30'},
                                {'id':'applications','theme':'software','source':'synthetic','as_of':'2026-10-30','weight_pct':20}]
        context = build_context(self.chart,request(assets))
        values = {a['theme']:a for a in context['assets']}
        self.assertEqual(values['ai']['roles']['product.primary']['location']['value'],'景门')
        self.assertEqual(values['nonferrous_metals']['roles']['product.primary']['location']['value'],7)
        self.assertEqual(values['power_generation']['roles']['product.primary']['location']['value'],9)
        self.assertEqual(values['power_equipment']['roles']['product.primary']['location']['value'],'天冲')
        self.assertEqual(values['dividend_low_volatility']['roles']['product.primary']['location']['value'],'天任')
        self.assertIsNone(values['ai']['roles']['exposure.hardware']['weight_pct'])
        self.assertFalse(values['ai']['weighted_return_computed'])

    def test_future_exposure_and_overweight_rejected(self):
        for row in ({'as_of':'2026-11-03'},{'as_of':'2026-10-30','available_at':'2026-11-03T10:00:00+08:00'},
                    {'as_of':'2026-10-30','weight_pct':101}):
            row.update(id='part',theme='software',source='synthetic')
            with self.subTest(row=row),self.assertRaises(ValueError):
                build_context(self.chart,request([product(exposures=[row])]))

    def test_context_replay_rejects_rehashed_tampering(self):
        altered = deepcopy(self.context)
        altered['assets'][0]['roles']['product.primary']['location']['palace']=7
        altered.pop('context_sha256')
        altered['context_sha256']=digest(altered)
        with self.assertRaises(ValueError):
            validate_context(altered)

    def test_context_does_not_change_chart_or_legacy_baseline(self):
        from finance_forecast import build_forecast
        self.assertEqual(digest(self.chart),self.context['chart_sha256'])
        expected = build_forecast(self.chart,request(),created_at=self.context['created_at'])
        self.assertEqual(self.context['legacy_baseline'],expected)

    def test_draft_is_not_a_forecast_and_is_required_to_be_complete(self):
        draft = init_record(self.context,created_at='2026-11-02T16:01:00+08:00')
        self.assertIsNone(draft['claims'][0]['direction'])
        with self.assertRaises(ValueError):
            publish_record(draft,published_at='2026-11-02T16:02:00+08:00')
        with self.assertRaises(ValueError):
            evaluate([draft],[])
        draft = deepcopy(self.draft)
        draft['claims'].pop()
        with self.assertRaises(ValueError):
            publish_record(draft)

    def test_publication_rechecks_actual_window(self):
        record = publish_record(self.draft,published_at='2026-11-03T14:30:00+08:00')
        self.assertEqual(record['claims'][0]['forecast_scope'],'retrospective')
        self.assertEqual(record['claims'][1]['forecast_scope'],'partial')
        self.assertEqual(record['claims'][2]['forecast_scope'],'full')
        self.assertTrue(validate_record(record)['valid'])

    def test_unresolved_fund_cannot_inherit_broad_direction(self):
        asset = product()
        asset.pop('theme')
        context = build_context(self.chart,request([asset]),created_at='2026-11-02T16:00:00+08:00')
        self.assertNotIn('product.primary',context['assets'][0]['roles'])
        draft = fill(init_record(context,created_at='2026-11-02T16:01:00+08:00'))
        for claim in draft['claims']:
            claim['supporting_roles']=['market.index']
        with self.assertRaises(ValueError):
            publish_record(draft,published_at='2026-11-02T16:02:00+08:00')

    def test_separate_direction_coverage_and_shape(self):
        draft = deepcopy(self.draft)
        draft['claims'][2]['direction']='undetermined'
        draft['claims'][1]['shape_forecasts']=[{'id':'small-body','metric':'body_range_pct','basis':'ohlc',
                                              'operator':'<=','value':10,'reason':'Synthetic predeclared threshold.'}]
        record = publish_record(draft,published_at='2026-11-02T16:02:00+08:00')
        outcomes = [self.outcome(record,1,1),self.outcome(record,2,-2)]
        outcomes[0].update(metrics={'body_range_pct':44},metric_bases={'body_range_pct':'ohlc'})
        result = evaluate([record],outcomes)
        self.assertEqual(result['counts'],{'K':2,'P':1,'C':1})
        self.assertEqual(result['direction_coverage'],.5)
        self.assertEqual(result['shape_scores']['body_range_pct']['correct'],0)
        self.assertEqual(result['outcomes_missing'],2)

    def outcome(self,record,day,value):
        claim = record['claims'][day]
        return {'record_sha256':record['record_sha256'],'asset_id':claim['asset_id'],'date':claim['date'],
                'currency':'CNY','return_basis':'nav_total_return','return_pct':value,
                'available_at':claim['date']+'T22:00:00+08:00','source':'synthetic-outcome'}

    def test_proxy_cannot_count_as_nav_outcome(self):
        outcome = self.outcome(self.record,1,3)
        outcome.update(observation_kind='proxy',return_basis='price_return')
        result = evaluate([self.record],[outcome])
        self.assertEqual(result['counts']['K'],0)
        self.assertEqual(result['excluded_rows']['proxy_is_not_exact_outcome'],1)

    def test_development_samples_cannot_report_prospective_accuracy(self):
        req = request(evaluation_role='development')
        context = build_context(self.chart,req,created_at='2026-11-02T16:00:00+08:00')
        draft = fill(init_record(context,created_at='2026-11-02T16:01:00+08:00'))
        record = publish_record(draft,published_at='2026-11-02T16:02:00+08:00')
        result = evaluate([record],[self.outcome(record,1,2)])
        self.assertEqual(result['counts']['K'],0)
        self.assertEqual(result['excluded_rows']['development_sample'],5)

    def test_cli_generates_context_and_editable_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'chart.json').write_text(json.dumps(self.chart),encoding='utf-8')
            (root/'request.json').write_text(json.dumps(request()),encoding='utf-8')
            result = forecast_main(['--mode','multi_role','--chart',str(root/'chart.json'),'--request',str(root/'request.json'),
                                    '--output',str(root/'context.json'),'--draft',str(root/'draft.json')])
            self.assertEqual(result,0)
            self.assertIsNone(read_json(root/'draft.json')['claims'][0]['direction'])


class ObservationChecks(unittest.TestCase):
    def setUp(self):
        self.bar={'date':'2026-11-02','previous_close':100,'open':98,'high':104,'low':96,'close':103,'volume':120,'amount':210}
        self.product={'asset_id':'SYNTH:ETF','symbol':'sh512345','expected_name_fragments':['合成'],
                      'metadata_source':'synthetic','currency':'CNY','return_basis':'price_return',
                      'observation_kind':'proxy','reference_for':'SYNTH:FUND','price_tolerance':.001}

    def test_metrics_do_not_confuse_gap_daily_return_and_body(self):
        result=bar_metrics(self.bar,{'volume':100,'amount':200})['metrics']
        self.assertAlmostEqual(result['return_pct'],3)
        self.assertAlmostEqual(result['gap_pct'],-2)
        self.assertAlmostEqual(result['intraday_return_pct'],100*5/98)
        self.assertAlmostEqual(result['amplitude_pct'],8)
        self.assertAlmostEqual(result['body_range_pct'],62.5)
        self.assertAlmostEqual(result['volume_change_pct'],20)

    def test_minute_grids_may_differ_and_one_cent_rounding_is_tolerated(self):
        left=[{'time':'2026-11-02T09:30:00+08:00','price':100},{'time':'2026-11-02T09:31:00+08:00','price':101}]
        right=[{'time':'2026-11-02T09:31:00+08:00','price':101.01}]
        result=compare_minutes(left,right,'2026-11-02')
        self.assertEqual(result['status'],'consistent')
        self.assertEqual(result['common_points'],1)
        right[0]['price']=101.02
        self.assertEqual(compare_minutes(left,right,'2026-11-02')['status'],'disputed')

    def test_missing_tail_endpoint_does_not_invent_tail_shape(self):
        points=[{'time':'2026-11-02T14:31:00+08:00','price':101},{'time':'2026-11-02T15:00:00+08:00','price':103}]
        self.assertNotIn('last_30m_return_pct',bar_metrics(self.bar,minutes=points)['metrics'])

    def test_sparse_tail_cannot_estimate_full_range(self):
        points=[{'time':'2026-11-02T14:30:00+08:00','price':101},{'time':'2026-11-02T15:00:00+08:00','price':103}]
        metrics=bar_metrics(self.bar,minutes=points)['metrics']
        self.assertIn('last_30m_return_pct',metrics)
        self.assertNotIn('last_30m_range_points',metrics)

    def test_etf_comparison_uses_its_price_precision(self):
        left=[{'time':'2026-11-02T14:30:00+08:00','price':.70}]
        right=[{'time':'2026-11-02T14:30:00+08:00','price':.705}]
        self.assertEqual(compare_minutes(left,right,'2026-11-02',.001)['status'],'disputed')

    def test_tail_range_uses_intraminute_high_low(self):
        start=datetime.fromisoformat('2026-11-02T14:30:00+08:00')
        points=[{'time':(start+timedelta(minutes=i)).isoformat(),'price':101,
                 'high':104 if i==10 else 102,'low':99 if i==20 else 100} for i in range(31)]
        self.assertEqual(bar_metrics(self.bar,minutes=points)['metrics']['last_30m_range_points'],5)

    def test_duplicate_minutes_and_future_minutes_are_rejected(self):
        row={'time':'2026-11-02T15:00:00+08:00','price':103}
        with self.assertRaises(ValueError):
            minute_map([row,row],'2026-11-02')
        with self.assertRaises(ValueError):
            minute_map([row],'2026-11-02',observed_at='2026-11-02T14:30:00+08:00')

    def test_wrong_code_exchange_and_invalid_ohlc_are_rejected(self):
        payload={'data':{'code':'512345','market':0,'name':'合成ETF','klines':[]}}
        with self.assertRaises(ValueError):
            parse_eastmoney_daily(payload,'sh512345')
        invalid=dict(self.bar,low=105)
        with self.assertRaises(ValueError):
            bar_metrics(invalid)
        with self.assertRaises(ValueError):
            validate_product(dict(self.product,return_basis='nav_total_return'))

    def test_stale_snapshot_and_post_close_update_are_not_new_trades(self):
        fields=['0']*38
        for k,v in {1:'合成ETF',2:'512345',3:'103',4:'100',5:'98',30:'20261102143000',32:'3',33:'104',34:'96'}.items():
            fields[k]=v
        raw='v_sh512345="'+'~'.join(fields)+'";'
        sources={'quote':{'raw':raw}}
        with self.assertRaises(ValueError):
            analyze_product(self.product,sources,'2026-11-02','intraday','2026-11-02T14:50:00+08:00')
        fields[30]='20261102153900'
        sources['quote']['raw']='v_sh512345="'+'~'.join(fields)+'";'
        with self.assertRaises(ValueError):
            analyze_product(self.product,sources,'2026-11-02','intraday','2026-11-02T15:40:00+08:00')


if __name__=='__main__':
    unittest.main()
