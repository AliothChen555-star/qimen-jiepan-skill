import argparse, json, sys
from datetime import datetime
from .chart import cast_chart

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser(prog="qimen"); sub=p.add_subparsers(dest="cmd",required=True); c=sub.add_parser("chart"); c.add_argument("--datetime"); c.add_argument("--now",action="store_true"); c.add_argument("--format",choices=["text","json"],default="text"); c.add_argument("--timezone",default="Asia/Shanghai"); c.add_argument("--longitude",type=float,default=120); c.add_argument("--latitude",type=float,default=30); c.add_argument("--time-mode",default="standard_time")
    a=p.parse_args();
    if a.datetime and a.now: p.error("--datetime 与 --now 冲突")
    dt=datetime.fromisoformat(a.datetime) if a.datetime else None
    result=cast_chart(dt,use_current_time=True if a.now else (False if dt else None),timezone_name=a.timezone,longitude=a.longitude,latitude=a.latitude,time_mode=a.time_mode)
    if a.format=="json": print(json.dumps(result,ensure_ascii=False,indent=2)); return
    print(f"时间 {result['calendar']['solar_datetime']}  {result['calendar']['year_pillar']} {result['calendar']['month_pillar']} {result['calendar']['day_pillar']} {result['calendar']['hour_pillar']}")
    dun = {'yang':'阳','yin':'阴'}.get(result['solar_term']['dun'], result['solar_term']['dun'])
    yuan = {'upper':'上','middle':'中','lower':'下'}.get(result['solar_term']['yuan'], result['solar_term']['yuan'])
    print(f"{dun}遁 {yuan}元 {result['solar_term']['ju']}局  节气:{result['solar_term']['name']}  值符宫:{result['chief']['zhi_fu_palace']}")
    xun = result['xun']; chief = result['chief']
    print(f"旬首:{xun['head']}（遁{ xun['hidden_stem'] }）  值符:{chief['zhi_fu']}（{chief['zhi_fu_palace']}宫）  值使:{chief['zhi_shi']}（{chief['zhi_shi_palace']}宫）")
    horse = result['horse']
    print(f"旬空:{'、'.join(xun['void_branches'])}  马星:{horse['branch']}（{horse['palace']}宫，按{horse['basis']=='hour' and '时支' or '日支'}）")
    for x in result['palaces']:
        parts = [x.get('heaven_stem',''), x.get('star',''), x.get('door',''), x.get('spirit','')]
        suffix = ' '.join(v for v in parts if v)
        marks = []
        if x.get('void'): marks.append('空亡:' + '、'.join(x.get('void_branches', [])))
        if x.get('horse'): marks.append('马星')
        print(f"{x['number']}宫{x['name']} 地:{x['earth_stem']}" + (f" 天:{suffix}" if suffix else '') + (f" {' '.join(marks)}" if marks else ''))

if __name__ == "__main__":
    main()
