"""Shared frozen inputs, product identities and dated market calendars."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

from file_outputs import ensure_distinct_output

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
METHOD = 'FINANCE_FIXED_CHART_V1'
VERSION = '0.8.0'
SCHEMA = 'qimen_finance_record_v1'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value, label):
    need(isinstance(value, str) and bool(value.strip()), f'{label} 必须为非空文本')
    return value


def number(value, label):
    need(type(value) in (int, float) and isfinite(value), f'{label} 必须为有限数值')
    return value


def instant(value):
    result = datetime.fromisoformat(value)
    need(result.tzinfo is not None and result.utcoffset() is not None, '时间须含 UTC 偏移')
    return result.astimezone(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_new(path, value, inputs=()):
    path = Path(path)
    for original in inputs:
        ensure_distinct_output(original, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def profiles():
    return read_json(ASSETS / 'finance_profiles.json')


def dates(start, end):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    need(0 <= (end-start).days <= 365, '日期范围须按先后排列且不超过 366 个自然日')
    return [start + timedelta(days=i) for i in range((end-start).days+1)]


def local_clock(day, clock, zone):
    result = datetime.combine(day, time.fromisoformat(clock), ZoneInfo(zone))
    restored = result.astimezone(timezone.utc).astimezone(result.tzinfo)
    need(restored.replace(tzinfo=None) == result.replace(tzinfo=None), '市场钟面落在夏令时缺失时段')
    other = result.replace(fold=1)
    need(other.utcoffset() == result.utcoffset(), '市场钟面存在重复时刻，需提供绝对估值窗口')
    return result


def calendar_for(asset):
    if 'calendar' in asset:
        result = deepcopy(asset['calendar'])
    else:
        key = asset.get('calendar_market', asset['market'])
        calendars = read_json(ASSETS / 'market_calendars_2026.json')['calendars']
        need(key in calendars, f'{key} 需要补充带来源的交易／估值日历')
        result = deepcopy(calendars[key])
    for key in ('timezone', 'valid_from', 'valid_to', 'open', 'close', 'source'):
        nonempty(result.get(key), f'calendar.{key}')
    ZoneInfo(result['timezone'])
    need(date.fromisoformat(result['valid_from']) <= date.fromisoformat(result['valid_to']), '日历有效期颠倒')
    for day in result.get('holidays', []):
        date.fromisoformat(day)
    return result


def session(day, calendar):
    text = day.isoformat()
    need(calendar['valid_from'] <= text <= calendar['valid_to'], f'{text} 超出已核日历范围，请更新日历快照')
    override = calendar.get('overrides', {}).get(text, {})
    closed = override.get('closed', day.weekday() >= 5 or text in calendar.get('holidays', []))
    need(type(closed) is bool, 'calendar.closed 必须为布尔值')
    if closed:
        return {'date': text, 'status': 'closed', 'open_at': None, 'close_at': None}
    half_close = calendar.get('half_days', {}).get(text)
    opening = local_clock(day, override.get('open', calendar['open']), calendar['timezone'])
    closing = local_clock(day, override.get('close', half_close or calendar['close']), calendar['timezone'])
    need(opening < closing, '日市开盘必须早于收盘；跨午夜产品须提供专用日历适配')
    return {'date': text, 'status': 'half_day' if half_close else 'open',
            'open_at': opening.isoformat(), 'close_at': closing.isoformat()}


def validate_asset(asset):
    need(isinstance(asset, dict), '标的档案必须为对象')
    for key in ('id', 'name', 'market', 'code', 'currency', 'instrument', 'return_basis', 'metadata_source'):
        nonempty(asset.get(key), f'asset.{key}')
    need(asset['instrument'] in ('index', 'stock', 'etf', 'fund'), 'instrument 须为 index/stock/etf/fund')
    need(asset['return_basis'] in ('price_return', 'nav_total_return', 'total_return'), '未知收益口径')
    need(asset['instrument'] != 'fund' or asset['return_basis'] == 'nav_total_return', '场外基金使用单位净值含分红口径')
    if asset.get('sector'):
        nonempty(asset.get('classification_source'), '行业分类出处')
        need(asset['sector'] in profiles()['sectors'], '行业代码未登记；复合主题应先锁定主营分类')
    if asset['instrument'] == 'fund':
        nonempty(asset.get('share_class'), '基金份额类别')
        ZoneInfo(nonempty(asset.get('valuation_timezone'), '基金估值时区'))
    calendar_for(asset)
    return asset
