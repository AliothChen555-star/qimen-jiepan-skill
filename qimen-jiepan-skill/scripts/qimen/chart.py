"""符头定元，地盘九宫顺逆飞布，天盘/星/门外八宫转动。"""
from datetime import datetime, timezone
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .calendar import calendar_data
from .rules import (BRANCHES, SEXAGENARY, GAN_SEQUENCE, RING, STARS, DOORS,
                    SPIRITS, PALACES, BRANCH_PALACE, JU_TABLE, RULE_VERSION)

def yuan_for(day_pillar):
    index = SEXAGENARY.index(day_pillar)
    head = SEXAGENARY[index - index % 5]
    yuan = 'upper' if head[1] in '子午卯酉' else 'middle' if head[1] in '寅申巳亥' else 'lower'
    return yuan, head, index % 5

def earth_plate(ju, dun):
    step = 1 if dun == 'yang' else -1
    return {(ju - 1 + step*i) % 9 + 1: stem for i, stem in enumerate(GAN_SEQUENCE)}

def _host(palace):
    return 2 if palace == 5 else palace

def _rotate(origin, target, source):
    shift = RING.index(target) - RING.index(origin)
    return {RING[(RING.index(p)+shift) % 8]: value for p, value in source.items()}

def arrange(ju, dun, hour_pillar, day_pillar, horse_basis):
    earth = earth_plate(ju, dun)
    xun_index, elapsed = divmod(SEXAGENARY.index(hour_pillar), 10)
    head, hidden = SEXAGENARY[xun_index*10], GAN_SEQUENCE[xun_index]
    origin = next(p for p, stem in earth.items() if stem == hidden)
    hour_stem = hidden if hour_pillar[0] == '甲' else hour_pillar[0]
    target_raw = next(p for p, stem in earth.items() if stem == hour_stem)
    target = _host(target_raw)
    door_raw = (origin - 1 + (1 if dun == 'yang' else -1)*elapsed) % 9 + 1
    door_target = _host(door_raw)
    native_stars = {p: [STARS[p]] + (['天禽'] if p == 2 else []) for p in RING}
    native_stems = {p: [earth[p]] + ([earth[5]] if p == 2 else []) for p in RING}
    stars = _rotate(_host(origin), target, native_stars)
    heaven = _rotate(_host(origin), target, native_stems)
    doors = _rotate(_host(origin), door_target, DOORS)
    step = 1 if dun == 'yang' else -1
    spirits = {RING[(RING.index(target)+step*i) % 8]: spirit for i, spirit in enumerate(SPIRITS)}
    void_start = (BRANCHES.index(head[1])+10) % 12
    void = [BRANCHES[void_start], BRANCHES[(void_start+1) % 12]]
    basis = hour_pillar[1] if horse_basis == 'hour' else day_pillar[1]
    horse = next(result for group, result in [('申子辰','寅'),('寅午戌','申'),('巳酉丑','亥'),('亥卯未','巳')] if basis in group)
    palaces = []
    for p, (name, direction, element) in PALACES.items():
        palace_stars, palace_stems = stars.get(p, []), heaven.get(p, [])
        earth_stems = [earth[p]]
        if p == 2:
            earth_stems.append(earth[5])
        if p == 5:
            # 中宫不直接安置天盘、人盘、神盘；相关内容由寄宫规则解释。
            center_stem = earth[5]
            palace_stems = [center_stem]
            palace_stars = []
        void_here = [b for b in void if BRANCH_PALACE[b] == p]
        palaces.append({
            'number': p, 'name': name, 'direction': direction, 'element': element,
            'earth_stems': earth_stems, 'earth_stem': '/'.join(earth_stems),
            'heaven_stems': palace_stems, 'heaven_stem': '/'.join(palace_stems),
            'stars': palace_stars, 'star': '/'.join(palace_stars), 'door': doors.get(p, '') if p != 5 else '', 'spirit': spirits.get(p, '') if p != 5 else '',
            'zhi_fu': p == target, 'zhi_shi': p == door_target, 'void': bool(void_here), 'void_branches': void_here,
            'horse': p == BRANCH_PALACE[horse],
            'hosting': {'earth_center_stem': earth[5]} if p == 2 else {'hosted_at': 2} if p == 5 else {},
            'heaven_center_host': '天禽' in palace_stars,
        })
    return {
        'xun': {'head': head, 'hidden_stem': hidden, 'elapsed_hours': elapsed, 'void_branches': void},
        'chief': {'zhi_fu': STARS[origin], 'zhi_shi': DOORS[_host(origin)], 'origin_palace': origin,
                  'zhi_fu_palace': target, 'zhi_fu_raw_palace': target_raw,
                  'zhi_shi_palace': door_target, 'zhi_shi_raw_palace': door_raw},
        'horse': {'basis': horse_basis, 'basis_branch': basis, 'branch': horse, 'palace': BRANCH_PALACE[horse]},
        'palaces': palaces,
    }

def cast_chart(dt=None, *, use_current_time=None, timezone_name='Asia/Shanghai',
               longitude=120.0, latitude=30.0, time_mode='standard_time',
               day_boundary='midnight', horse_basis='hour', yuan_strategy='chai_bu_v1',
               center_policy='kun2', clock=None):
    if use_current_time is not None and type(use_current_time) is not bool:
        raise ValueError('use_current_time 必须是布尔值')
    if use_current_time and dt is not None:
        raise ValueError('use_current_time 与 datetime 不能同时提供')
    if use_current_time is False and dt is None:
        raise ValueError('use_current_time=false 时必须提供 datetime')
    options = {'time_mode': (time_mode, ('standard_time','true_solar_time')),
               'day_boundary': (day_boundary, ('midnight','zi_start')), 'horse_basis': (horse_basis, ('hour','day')),
               'yuan_strategy': (yuan_strategy, ('chai_bu_v1',)), 'center_policy': (center_policy, ('kun2',))}
    for key, (value, choices) in options.items():
        if value not in choices:
            raise ValueError(f'{key} 无效，可选：{", ".join(choices)}')
    for name, value, limit in [('longitude',longitude,180),('latitude',latitude,90)]:
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not isfinite(value) or abs(value) > limit:
            raise ValueError(f'{name} 必须在 {-limit} 至 {limit} 之间')
    try:
        tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError(f'无效时区：{timezone_name}') from exc
    is_now = dt is None
    captured = (clock or (lambda: datetime.now().astimezone()))() if is_now else dt
    if isinstance(captured, str):
        try:
            captured = datetime.fromisoformat(captured)
        except ValueError as exc:
            raise ValueError('datetime 应为 ISO 8601 时间，例如 2026-09-08T14:30:00+08:00') from exc
    if not isinstance(captured, datetime):
        raise ValueError('datetime 必须是日期时间字符串或 datetime 对象')
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError('datetime 必须包含时区偏移，例如 +08:00；避免夏令时歧义')
    local = captured.astimezone(tz).replace(microsecond=0)
    if not 1901 <= local.year <= 2099:
        raise ValueError('当前支持年份为 1901 至 2099')
    cal, term = calendar_data(local, longitude, time_mode, day_boundary)
    yuan, head, offset = yuan_for(cal['day_pillar'])
    dun = 'yang' if list(JU_TABLE).index(term['name']) < 12 else 'yin'
    ju = JU_TABLE[term['name']][('upper','middle','lower').index(yuan)]
    term.update(dun=dun, yuan=yuan, ju=ju, fu_head=head, days_after_fu_head=offset)
    result = arrange(ju, dun, cal['hour_pillar'], cal['day_pillar'], horse_basis)
    result.update(
        input={'datetime': local.isoformat(), 'captured_at': local.isoformat(),
               'captured_at_utc': local.astimezone(timezone.utc).isoformat(), 'use_current_time': is_now,
               'time_source': 'runtime_clock' if is_now else 'explicit',
               'device_timezone': str(captured.tzinfo) if is_now else None,
               'timezone': timezone_name, 'longitude': longitude, 'latitude': latitude,
               'time_mode': time_mode, 'day_boundary': day_boundary, 'horse_basis': horse_basis,
               'yuan_strategy': yuan_strategy, 'center_policy': center_policy},
        calendar=cal, solar_term=term, rule_version=RULE_VERSION,
        trace=[f'交节以绝对时刻为准：{term["name"]} {term["transition_time"]}',
               f'日柱 {cal["day_pillar"]} → 符头 {head} → {yuan} → {dun}遁{ju}局',
               '地盘按宫号 1…9 阳顺阴逆；星门沿外八宫整体旋转；八神阳顺阴逆',
               f'旬首 {result["xun"]["head"]} 遁 {result["xun"]["hidden_stem"]}，本宫 {result["chief"]["origin_palace"]}',
               f'值符随时干至 {result["chief"]["zhi_fu_raw_palace"]} 宫，值使计 {result["xun"]["elapsed_hours"]} 步至 {result["chief"]["zhi_shi_raw_palace"]} 宫',
               '中五一律寄坤二，天禽随天芮；真太阳时采用经度与 NOAA 均时差近似'],
    )
    return result
