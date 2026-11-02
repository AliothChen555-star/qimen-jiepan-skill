"""Collect and check mainland price observations; ETF proxies never become fund NAV."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import json
import re
import sys
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from finance_common import instant, need, nonempty, number, read_json, write_new

ZONE = ZoneInfo('Asia/Shanghai')
SYMBOL = re.compile(r'^(sh|sz)(\d{6})$')


def positive(value,label):
    result = float(value)
    need(number(result,label)>0,label+'须为正数')
    return result


def parse_tencent_quote(text,symbol):
    match = re.search(r'v_'+re.escape(symbol)+r'="([^"\r\n]*)"',text)
    need(match is not None,'腾讯报价没有请求代码')
    fields = match[1].split('~')
    need(len(fields)>37 and fields[2]==symbol[2:],'腾讯代码或字段不符')
    at = datetime.strptime(fields[30],'%Y%m%d%H%M%S').replace(tzinfo=ZONE)
    result = {'code':fields[2],'name':fields[1],'timestamp':at.isoformat(),
            'last':positive(fields[3],'现价'),'previous_close':positive(fields[4],'前收'),
            'open':positive(fields[5],'开盘'),'high':positive(fields[33],'最高'),
            'low':positive(fields[34],'最低'),'return_pct':float(fields[32])}
    number(result['return_pct'],'报价涨跌幅')
    need(abs(result['return_pct']-100*(result['last']/result['previous_close']-1))<=.020000001,
         '报价价格与涨跌幅矛盾')
    return result


def parse_eastmoney_daily(payload,symbol):
    data = payload.get('data')
    need(isinstance(data,dict) and data.get('code')==symbol[2:],'东方财富日线代码不符')
    need(data.get('market') == (1 if symbol.startswith('sh') else 0),'东方财富交易所不符')
    result = []
    for line in data['klines']:
        f = line.split(',')
        need(len(f)>=10,'日线字段不足')
        row = {'date':date.fromisoformat(f[0]).isoformat(),'open':positive(f[1],'开盘'),
               'close':positive(f[2],'收盘'),'high':positive(f[3],'最高'),'low':positive(f[4],'最低'),
               'volume':float(f[5]),'amount':float(f[6]),'reported_return_pct':float(f[8]),
               'previous_close':positive(float(f[2])-float(f[9]),'前收')}
        check_bar(row)
        result.append(row)
    need(len({r['date'] for r in result})==len(result),'日线日期重复')
    need(result==sorted(result,key=lambda r:r['date']),'日线日期无序')
    return {'code':data['code'],'name':data['name'],'rows':result}


def parse_tencent_daily(payload,symbol):
    data = payload['data'][symbol]
    lines = data.get('day',data.get('qfqday',[]))
    result = []
    for f in lines:
        row = {'date':date.fromisoformat(f[0]).isoformat(),'open':positive(f[1],'开盘'),
               'close':positive(f[2],'收盘'),'high':positive(f[3],'最高'),'low':positive(f[4],'最低'),
               'volume':float(f[5])}
        check_bar(row,require_previous=False)
        result.append(row)
    need(len({r['date'] for r in result})==len(result),'腾讯日线日期重复')
    return {'rows':result}


def check_bar(row,require_previous=True):
    for name in ('open','high','low','close'):
        positive(row[name],name)
    need(row['low']<=min(row['open'],row['close'])<=max(row['open'],row['close'])<=row['high'], 'OHLC高低顺序错误')
    if require_previous:
        positive(row['previous_close'],'前收')
    for field in ('volume','amount'):
        if field in row:
            need(number(row[field],field)>=0,'成交量额不能为负')


def parse_tencent_minutes(payload,symbol):
    data = payload['data'][symbol]['data']
    day = datetime.strptime(data['date'],'%Y%m%d').date().isoformat()
    rows = []
    for line in data['data']:
        f = line.split()
        clock = datetime.strptime(f[0],'%H%M').strftime('%H:%M')
        rows.append({'time':day+'T'+clock+':00+08:00','price':positive(f[1],'分钟价')})
    return rows


def parse_eastmoney_minutes(payload,symbol):
    data = payload.get('data')
    need(isinstance(data,dict) and data['code']==symbol[2:],'东方财富分时代码不符')
    need(data.get('market')==(1 if symbol.startswith('sh') else 0),'东方财富分时交易所不符')
    rows = []
    for line in data['trends']:
        f = line.split(',')
        row = {'time':datetime.strptime(f[0],'%Y-%m-%d %H:%M').replace(tzinfo=ZONE).isoformat(),
               'price':positive(f[2],'分钟收价')}
        # Some historical feeds omit intraminute fields as zero: keep them unknown.
        if float(f[3])>0 and float(f[4])>0:
            row.update(high=positive(f[3],'分钟最高'),low=positive(f[4],'分钟最低'))
        rows.append(row)
    return rows


def minute_map(rows,day,*,observed_at=None):
    result = {}
    previous = None
    for row in rows:
        at = instant(row['time'])
        if at.astimezone(ZONE).date().isoformat()!=day:
            continue
        need(previous is None or at>previous,'同源分钟时间重复或无序')
        if observed_at:
            need(at<=instant(observed_at)+timedelta(minutes=2),'分时含未来时间')
        previous = at
        price = positive(row['price'],'分钟价')
        if 'high' in row and 'low' in row:
            need(positive(row['low'],'分钟最低')<=price<=positive(row['high'],'分钟最高'), '分钟高低顺序错误')
        result[at.isoformat()] = price
    return result


def compare_minutes(left,right,day,tolerance=.01):
    a,b = minute_map(left,day),minute_map(right,day)
    common = sorted(set(a)&set(b))
    errors = [abs(a[k]-b[k]) for k in common]
    return {'common_points':len(common),'left_points':len(a),'right_points':len(b),
            'max_price_difference':max(errors) if errors else None,
            'mismatched_points':sum(v>tolerance+1e-9 for v in errors),
            'status':'consistent' if common and max(errors)<=tolerance+1e-9 else 'no_common_points' if not common else 'disputed',
            'policy':'比较共同时间点；不要求不同来源时间网格或点数相等'}


def bar_metrics(row,previous=None,minutes=None):
    check_bar(row)
    o,h,l,c,p = [row[k] for k in ('open','high','low','close','previous_close')]
    width = h-l
    metrics = {'return_pct':100*(c/p-1),'gap_pct':100*(o/p-1),
               'intraday_return_pct':100*(c/o-1),'amplitude_pct':100*width/p,
               'body_range_pct':100*abs(c-o)/width if width else 0,
               'close_position_in_range_pct':100*(c-l)/width if width else 50,
               'upper_shadow_points':h-max(o,c),'lower_shadow_points':min(o,c)-l}
    bases = {k:'ohlc' for k in metrics}
    bases['return_pct'] = 'same_asset_return'
    for field in ('volume','amount'):
        if previous and previous.get(field,0)>0 and field in row:
            metrics[field+'_change_pct'] = 100*(row[field]/previous[field]-1)
            bases[field+'_change_pct'] = field
    if minutes:
        points = minute_map(minutes,row['date'])
        first = instant(row['date']+'T14:30:00+08:00').isoformat()
        last = instant(row['date']+'T15:00:00+08:00').isoformat()
        window = [v for k,v in points.items() if first<=k<=last]
        if first in points and last in points and window:
            metrics['last_30m_return_pct'] = 100*(points[last]/points[first]-1)
            bases['last_30m_return_pct'] = 'minutes'
            expected = [(instant(first)+timedelta(minutes=i)).isoformat() for i in range(31)]
            detail = {instant(r['time']).isoformat():r for r in minutes}
            if all(k in detail and 'high' in detail[k] and 'low' in detail[k] for k in expected):
                # Minute-close ranges can understate the actual high-low range.
                metrics['last_30m_range_points'] = max(detail[k]['high'] for k in expected)-min(detail[k]['low'] for k in expected)
                bases['last_30m_range_points'] = 'minutes'
    return {'metrics':metrics,'metric_bases':bases}


def validate_product(product):
    symbol = nonempty(product.get('symbol'),'行情代码')
    need(SYMBOL.fullmatch(symbol),'目前自动采集仅支持显式sh/sz六位证券代码')
    nonempty(product.get('asset_id'),'标的id')
    nonempty(product.get('metadata_source'),'代码名称对应来源')
    names = product.get('expected_name_fragments')
    need(isinstance(names,list) and names,'须给出已核名称片段，阻断同码异市场或错误目标ETF')
    for name in names:
        nonempty(name,'名称片段')
    need(product.get('observation_kind') in ('exact','proxy'),'须显式标明exact或proxy')
    need(product.get('return_basis')=='price_return' and product.get('currency')=='CNY','自动行情仅为人民币价格口径，不生成基金净值')
    need(0<number(product.get('price_tolerance'),'报价价格容差')<=.01,
         '须按已核报价精度填写price_tolerance，不能统一宽容所有产品')
    if product['observation_kind']=='proxy':
        nonempty(product.get('reference_for'),'ETF参考对应基金id')
    return product


def fetch(url,encoding='utf-8'):
    request = Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'})
    with urlopen(request,timeout=15) as response:
        return response.read().decode(encoding)


def source_urls(symbol,day):
    secid = ('1.' if symbol.startswith('sh') else '0.')+symbol[2:]
    start = (date.fromisoformat(day)-timedelta(days=21)).isoformat()
    end = day.replace('-','')
    return {
        'quote':('https://qt.gtimg.cn/q='+symbol,'gb18030'),
        'eastmoney_daily':('https://push2his.eastmoney.com/api/qt/stock/kline/get?secid='+secid+'&klt=101&fqt=0&beg='+start.replace('-','')+'&end='+end+'&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61','utf-8'),
        'tencent_daily':('https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param='+symbol+',day,'+start+','+day+',30,qfq','utf-8'),
        'tencent_minutes':('https://web.ifzq.gtimg.cn/appstock/app/minute/query?code='+symbol,'utf-8'),
        'eastmoney_minutes':('https://push2his.eastmoney.com/api/qt/stock/trends2/get?secid='+secid+'&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58&ndays=1&iscr=0','utf-8'),
    }


def analyze_product(product,sources,day,mode,collected_at):
    validate_product(product)
    symbol = product['symbol']
    parsed,errors = {},{}
    parsers = {'quote':lambda s:parse_tencent_quote(s,symbol),
               'eastmoney_daily':lambda s:parse_eastmoney_daily(json.loads(s),symbol),
               'tencent_daily':lambda s:parse_tencent_daily(json.loads(s),symbol),
               'tencent_minutes':lambda s:parse_tencent_minutes(json.loads(s),symbol),
               'eastmoney_minutes':lambda s:parse_eastmoney_minutes(json.loads(s),symbol)}
    for key,value in sources.items():
        try:
            need('error' not in value,value.get('error','读取失败'))
            parsed[key] = parsers[key](value['raw'])
        except (ValueError,KeyError,TypeError,IndexError) as error:
            errors[key] = str(error)
    result = {'product':product,'date':day,'mode':mode,'errors':errors,'data_status':'unavailable',
              'is_formal_fund_nav':False,'account_value_computed':False}
    quote = parsed.get('quote')
    named = parsed.get('eastmoney_daily')
    for item in (quote,named):
        if item:
            need(any(n in item['name'] for n in product['expected_name_fragments']), '请求代码与已核名称不符：'+symbol)
    if mode=='intraday':
        if quote:
            at = instant(quote['timestamp'])
            need(at.astimezone(ZONE).date().isoformat()==day,'快照不是请求交易日')
            age = (instant(collected_at)-at).total_seconds()
            need(-120<=age<=600,'盘中快照过期或含未来时间')
            need(at.astimezone(ZONE).hour<15,'收盘后报价不能作为新增盘中交易')
            check_bar(dict(quote,close=quote['last']))
            result.update(data_status='single_source_snapshot',quote=quote)
    else:
        need(instant(collected_at)>=instant(day+'T15:00:00+08:00'),'尚未收盘不能输出完整日线')
        if named:
            row = next((r for r in named['rows'] if r['date']==day),None)
            if row:
                ref = next((r for r in parsed.get('tencent_daily',{}).get('rows',[]) if r['date']==day),None)
                comparison = {k:abs(row[k]-ref[k]) for k in ('open','high','low','close')} if ref else None
                consistent = comparison is not None and max(comparison.values())<=product['price_tolerance']+1e-9
                status = 'cross_checked' if consistent else 'disputed' if ref else 'single_source_daily'
                result.update(data_status=status,daily=row,daily_comparison=comparison)
                if status!='disputed':
                    older = [r for r in named['rows'] if r['date']<day]
                    minutes = parsed.get('eastmoney_minutes',[])
                    minute_map(minutes,day,observed_at=collected_at)
                    result.update(bar_metrics(row,older[-1] if older else None,minutes))
                    if parsed.get('tencent_minutes') and minutes:
                        check = compare_minutes(parsed['tencent_minutes'],minutes,day,product['price_tolerance'])
                        result['minute_comparison'] = check
                        if check['status']=='disputed':
                            for metric in ('last_30m_return_pct','last_30m_range_points'):
                                result['metrics'].pop(metric,None)
                                result['metric_bases'].pop(metric,None)
    return result


def collect(request):
    day = date.fromisoformat(request['date']).isoformat()
    mode = request['mode']
    need(mode in ('intraday','closed'),'mode须为intraday或closed')
    now = datetime.now(timezone.utc).isoformat()
    need(day<=instant(now).astimezone(ZONE).date().isoformat(),'不能采集未来行情')
    need(isinstance(request['products'],list) and request['products'],'行情产品列表为空')
    products = [validate_product(p) for p in request['products']]
    need(len({p['asset_id'] for p in products})==len(products),'行情标的id重复')
    bundles = []
    for product in products:
        urls = source_urls(product['symbol'],day)
        if mode=='intraday':
            urls = {'quote':urls['quote']}
        def get(item):
            key,(url,encoding) = item
            try:
                return key,{'url':url,'raw':fetch(url,encoding),'retrieved_at':datetime.now(timezone.utc).isoformat()}
            except (OSError,ValueError) as error:
                return key,{'url':url,'error':str(error),'retrieved_at':datetime.now(timezone.utc).isoformat()}
        with ThreadPoolExecutor(max_workers=5) as pool:
            sources = dict(pool.map(get,urls.items()))
        end = datetime.now(timezone.utc).isoformat()
        try:
            observation = analyze_product(product,sources,day,mode,end)
        except (ValueError,KeyError,TypeError,IndexError) as error:
            observation = {'data_status':'rejected','reason':str(error),'is_formal_fund_nav':False}
        bundles.append({'product':product,'sources':sources,'observation':observation})
    return {'schema_version':'qimen_finance_observations_v1','request':request,'started_at':now,
            'collected_at':datetime.now(timezone.utc).isoformat(),'products':bundles,
            'limitations':'第三方行情；ETF为价格参考；场外基金净值与个人收益另核；采集失败保持未知'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args(argv)
    try:
        write_new(args.output,collect(read_json(args.request)),[args.request])
    except (ValueError,OSError,KeyError,TypeError) as error:
        print('行情采集失败：'+str(error),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
