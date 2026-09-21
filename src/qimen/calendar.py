"""历法以北京时间读取天文交节，日时干支按选定地方钟面计算。"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import sin, cos, pi
from lunar_python import Solar
from .rules import SEXAGENARY, STEMS, BRANCHES

BEIJING = timezone(timedelta(hours=8))

@lru_cache(maxsize=4096)
def _lunar(year, month, day, hour, minute, second):
    return Solar.fromYmdHms(year, month, day, hour, minute, second).getLunar()

def lunar_at(dt):
    return _lunar(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def equation_of_time(instant):
    """NOAA 谐波近似均时差，单位分钟（视太阳时减平太阳时）。"""
    utc = instant.astimezone(timezone.utc)
    days = 366 if utc.year % 4 == 0 and (utc.year % 100 != 0 or utc.year % 400 == 0) else 365
    gamma = 2*pi/days * (utc.timetuple().tm_yday - 1 + (utc.hour + utc.minute/60 - 12)/24)
    return 229.18*(0.000075 + 0.001868*cos(gamma) - 0.032077*sin(gamma) - 0.014615*cos(2*gamma) - 0.040849*sin(2*gamma))

def calendar_data(instant, longitude, time_mode, day_boundary):
    bj = instant.astimezone(BEIJING)
    astronomical = lunar_at(bj)
    term = astronomical.getPrevJieQi(False)
    upcoming = astronomical.getNextJieQi(False)
    term_time = datetime.fromisoformat(term.getSolar().toYmdHms()).replace(tzinfo=BEIJING)
    next_time = datetime.fromisoformat(upcoming.getSolar().toYmdHms()).replace(tzinfo=BEIJING)
    eot = equation_of_time(instant) if time_mode == 'true_solar_time' else 0
    offset = instant.utcoffset().total_seconds()/60
    correction = 4*longitude - offset + eot if time_mode == 'true_solar_time' else 0
    wall = instant.replace(tzinfo=None) + timedelta(minutes=correction)
    day_clock = wall + timedelta(days=1) if day_boundary == 'zi_start' and wall.hour == 23 else wall
    day = lunar_at(day_clock).getDayInGanZhi()
    hour_index = ((wall.hour + 1)//2) % 12
    hour = STEMS[(STEMS.index(day[0])*2 + hour_index) % 10] + BRANCHES[hour_index]
    return {
        'solar_datetime': instant.isoformat(), 'effective_wall_time': wall.isoformat(timespec='seconds'),
        'effective_time_kind': '地方视太阳钟面' if time_mode == 'true_solar_time' else '所选时区标准钟面',
        'lunar_date': astronomical.toString(), 'lunar_date_basis': '北京时间民用日期',
        'year_pillar': astronomical.getYearInGanZhiExact(), 'month_pillar': astronomical.getMonthInGanZhiExact(),
        'day_pillar': day, 'hour_pillar': hour, 'day_cycle_index': SEXAGENARY.index(day),
        'correction_minutes': round(correction, 6), 'equation_of_time_minutes': round(eot, 6),
    }, {
        'name': term.getName(), 'transition_time': term_time.astimezone(instant.tzinfo).isoformat(),
        'next_name': upcoming.getName(), 'next_transition_time': next_time.astimezone(instant.tzinfo).isoformat(),
        'provider': 'lunar-python 1.4.8',
    }
