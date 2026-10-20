"""Explicit-time command-line adapter; never installs software."""
import argparse
import json
import sys
from .chart import cast_chart


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(prog='qimen')
    sub = parser.add_subparsers(dest='cmd', required=True)
    chart = sub.add_parser('chart')
    time = chart.add_mutually_exclusive_group(required=True)
    time.add_argument('--datetime', help='ISO 8601 时间，必须含偏移')
    time.add_argument('--now', action='store_true', help='显式读取当前时钟')
    chart.add_argument('--format', choices=['text', 'json'], default='text')
    chart.add_argument('--timezone', default='Asia/Shanghai')
    chart.add_argument('--longitude', type=float, default=120)
    chart.add_argument('--latitude', type=float, default=30)
    chart.add_argument('--time-mode', choices=['standard_time', 'true_solar_time'], default='standard_time')
    chart.add_argument('--day-boundary', choices=['midnight', 'zi_start'], default='midnight')
    chart.add_argument('--horse-basis', choices=['hour', 'day'], default='hour')
    args = parser.parse_args(argv)
    try:
        result = cast_chart(args.datetime, use_current_time=args.now,
                            timezone_name=args.timezone, longitude=args.longitude,
                            latitude=args.latitude, time_mode=args.time_mode,
                            day_boundary=args.day_boundary, horse_basis=args.horse_basis)
    except ValueError as exc:
        parser.error(str(exc))
    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    cal, term, chief = result['calendar'], result['solar_term'], result['chief']
    print(f"时间 {cal['solar_datetime']}  {cal['year_pillar']} {cal['month_pillar']} {cal['day_pillar']} {cal['hour_pillar']}")
    dun = {'yang': '阳', 'yin': '阴'}[term['dun']]
    yuan = {'upper': '上', 'middle': '中', 'lower': '下'}[term['yuan']]
    print(f"{dun}遁 {yuan}元 {term['ju']}局  节气:{term['name']}  值符宫:{chief['zhi_fu_palace']}")
    xun, horse = result['xun'], result['horse']
    print(f"旬首:{xun['head']}（遁{xun['hidden_stem']}）  值符:{chief['zhi_fu']}（{chief['zhi_fu_palace']}宫）  值使:{chief['zhi_shi']}（{chief['zhi_shi_palace']}宫）")
    print(f"旬空:{'、'.join(xun['void_branches'])}  马星:{horse['branch']}（{horse['palace']}宫，按{'时支' if horse['basis'] == 'hour' else '日支'}）")
    for palace in result['palaces']:
        details = ' '.join(palace[key] for key in ('heaven_stem', 'star', 'door', 'spirit') if palace[key])
        marks = ([f"空亡:{'、'.join(palace['void_branches'])}"] if palace['void'] else [])
        if palace['horse']:
            marks.append('马星')
        print(f"{palace['number']}宫{palace['name']} 地:{palace['earth_stem']} 天:{details}" + (f" {' '.join(marks)}" if marks else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
