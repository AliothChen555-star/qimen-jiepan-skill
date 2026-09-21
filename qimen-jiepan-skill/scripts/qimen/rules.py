"""转盘拆补规则数据，与时间及展示层无关。"""
STEMS = '甲乙丙丁戊己庚辛壬癸'
BRANCHES = '子丑寅卯辰巳午未申酉戌亥'
SEXAGENARY = tuple(STEMS[i % 10] + BRANCHES[i % 12] for i in range(60))
GAN_SEQUENCE = '戊己庚辛壬癸丁丙乙'
RING = (1, 8, 3, 4, 9, 2, 7, 6)
GRID = (4, 9, 2, 3, 5, 7, 8, 1, 6)
STARS = dict(enumerate(('天蓬','天芮','天冲','天辅','天禽','天心','天柱','天任','天英'), 1))
DOORS = dict(zip(RING, ('休门','生门','伤门','杜门','景门','死门','惊门','开门')))
SPIRITS = ('值符','腾蛇','太阴','六合','白虎','玄武','九地','九天')
PALACES = dict(enumerate((('坎','北','水'),('坤','西南','土'),('震','东','木'),('巽','东南','木'),('中','中央','土'),('乾','西北','金'),('兑','西','金'),('艮','东北','土'),('离','南','火')), 1))
BRANCH_PALACE = dict(zip(BRANCHES, (1,8,8,3,4,4,9,2,2,7,6,6)))
JU_TABLE = dict(zip(
    ('冬至','小寒','大寒','立春','雨水','惊蛰','春分','清明','谷雨','立夏','小满','芒种','夏至','小暑','大暑','立秋','处暑','白露','秋分','寒露','霜降','立冬','小雪','大雪'),
    ((1,7,4),(2,8,5),(3,9,6),(8,5,2),(9,6,3),(1,7,4),(3,9,6),(4,1,7),(5,2,8),(4,1,7),(5,2,8),(6,3,9),(9,3,6),(8,2,5),(7,1,4),(2,5,8),(1,4,7),(9,3,6),(7,1,4),(6,9,3),(5,8,2),(6,9,3),(5,8,2),(4,7,1))))
RULE_VERSION = 'chai_bu_v1.0.0'

def rule_description():
    return {
        'version': RULE_VERSION, 'method': '拆补法时家转盘奇门',
        'yuan_strategy': 'chai_bu_v1', 'center_policy': 'kun2',
        'center_description': '中五寄坤二；天禽随天芮；中宫地盘干随天禽转动',
        'day_boundary_options': ['midnight', 'zi_start'],
        'horse_basis_options': ['hour', 'day'],
        'solar_term_boundary': '绝对时刻交节；等于交节时刻即用新节气',
        'year_month_boundary': '年柱立春、月柱十二节；均按绝对时刻',
        'ju_table': JU_TABLE, 'calendar_provider': 'lunar-python 1.4.8',
        'validation_status': '已做算法与边界自动校验；尚无独立人工签核的完整逐宫案例',
    }
