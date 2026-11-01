# 奇门遁甲起盘与解盘 Skill

当前技能版本：**0.9.0**。包含拆补法时家转盘、冻结盘核验、传统规则卡、分事解盘与金融日／周／月预测。本版加入前置使用规则，并按六步流程整合全盘、取用、宫内、宫间、综合应期与运筹。

## 本版改变

执行顺序为：前置定题校盘 → 审局观象 → 固定主辅用神 → 宫内分析 → 宫间比较 → 综合取象与应期 → 运筹与留档。全盘可给可修正的盘势与节奏初判，最终综合须回看核心宫和事类条件；回答仍先给结论。

前置规则涵盖自然动念、问时与事件时间、异步接问、重复与补问、纠错重占及盘面时效。按实际问题承接或另立新盘，不设置通用三次额度和等待天数。专项取用新增原文定位说明，年命、十二长生、生克、庚格与宫数都标明各自适用范围。

规则资料维护在 [rules.json](qimen-jiepan-skill/assets/rules.json)，包含69张卡、22条有向干对选录及6个方法入口。几何匹配、传统解释、有利取用、事件适用和主客例外分别核验；关键未知不作成立。没有补全的干格按固定来源查，不用五行关系编克应。

首批文本方法区分合伙助益、贸易资本收益和开店经营。金融方向现按 FINANCE_FIXED_CHART_V1 的 F01—F10 规则计算；现代合同期限和工作压力持续天数仍按各自方法处理。现状、期限结果、精确应期分别回答，原义有凶不抹去，有吉及例外也不遗漏。

## 使用

金融预测先读[金融解盘](qimen-jiepan-skill/references/金融解盘.md)，再按[逐日方法](qimen-jiepan-skill/references/固定盘逐日推演.md)与[输入格式](qimen-jiepan-skill/references/金融数据与幅度.md)建立产品档案和行情快照：

```text
<技能私有Python> qimen-jiepan-skill/scripts/finance_forecast.py --chart chart.json --request request.json --output forecast.json --markdown answer.md
<技能私有Python> qimen-jiepan-skill/scripts/finance_record.py validate forecast.json --chart chart.json
```

固定同盘逐日给干支关系、方向档位与历史幅度，周按每日路径复利，月输出三段总势和转折。内置沪深港2026日历，其他市场／年份接入已核日历。板块并列保留，场外基金按净值归属日；原预测及后来结局分开保存。金融记录示例输入位于 `evals/fixtures/finance/`，均为合成产品和行情。

可安装目录是仓库内的 **qimen-jiepan-skill/** 子目录；安装到个人技能目录时命名为 **qimen-jiepan**，保留原私有环境。修改或更新前保留原版。初始化是明确的单独步骤，日常入口不再自动联网安装。

```text
python qimen-jiepan-skill/scripts/setup_env.py
<技能私有Python> qimen-jiepan-skill/scripts/qimen_cli.py chart --now --format json
<技能私有Python> qimen-jiepan-skill/scripts/qimen_cli.py chart --datetime 2026-09-14T14:30:00+08:00 --format json
<技能私有Python> qimen-jiepan-skill/scripts/inspect_patterns.py chart.json --output patterns.json
<技能私有Python> qimen-jiepan-skill/scripts/reading_record.py init --chart chart.json --question 问题 --output reading.json
<技能私有Python> qimen-jiepan-skill/scripts/reading_record.py validate reading.json --chart chart.json
```

Windows私有解释器为安装目录内的 `.venv/Scripts/python.exe`，macOS/Linux为 `.venv/bin/python`。当前/指定时间必须二选一。默认上海标准时、午夜换日、时马、坤二寄宫；新盘记录实际依赖和UTC时刻。太阳时、换日、马星和时区参数见[起盘程序](qimen-jiepan-skill/references/起盘程序.md)。

## 核验与资料

| 资料 | 用途 |
|---|---|
| [前置使用规则](qimen-jiepan-skill/references/前置使用规则.md) | 随心取时、重复问事、纠错、事变与期限 |
| [解盘流程](qimen-jiepan-skill/references/解盘流程.md) | 从定题到分项判断和反证复核 |
| [运筹与建议](qimen-jiepan-skill/references/运筹与建议.md) | 将具体判断转为行动、时间、方向与复核节点 |
| [方法配置](qimen-jiepan-skill/references/方法配置.md)、[事类方法](qimen-jiepan-skill/references/事类方法.md) | 固定盘法、主辅角色和分类适用边界 |
| [规则卡](qimen-jiepan-skill/references/规则卡.md)、[来源登记](qimen-jiepan-skill/references/来源登记.md) | 原文位置、条件、异说和未核范围 |
| [取象规范](qimen-jiepan-skill/references/取象规范.md) | 区分传统义、现代类比与现实事实 |
| [空墓与应期](qimen-jiepan-skill/references/空墓与应期.md) | 期限与精确应期、候选工具边界 |
| [记录与复核](qimen-jiepan-skill/references/记录与复核.md) | 原盘哈希、角色、正反依据和期限一致性 |
| [金融解盘](qimen-jiepan-skill/references/金融解盘.md) | 行业取用、方向强弱与金融解释 |
| [评估方法](qimen-jiepan-skill/references/评估方法.md) | 资料、程序、行为与真实效验分层 |

完整内置盘校验检查布局耦合、原始时刻、历法和方法的一致性；不相容盘或截图可作有限人工解读，不能强行改成内置盘。合成排布测试使用明确的结构接口，生产命令不提供降级开关。

日期候选工具支持独立搜索起点、日历日与24小时两种时长，以及历史时区缺失/重复钟面。输出UTC端点、并集时长和覆盖比例；候选不是应验日，覆盖比例不是命中率。

## 验证

```text
<技能私有Python> -B -m unittest discover -s qimen-jiepan-skill/evals -p "test_*.py" -v
```

现有测试检查结构、输入、时间、条件三态及记录一致性。旧版行为执行状态保留在 [replay-status.json](qimen-jiepan-skill/evals/replay-status.json)，金融基线见 [0.8.0金融验收](qimen-jiepan-skill/evals/replays/0.8.0.md)，流程更新见 [0.9.0验收](qimen-jiepan-skill/evals/replays/0.9.0.md)。金融测试覆盖流日、日历、身份排重、数据可得时点、复利与记录复算；真实结局采用独立结果文件统计。

0.9.0更新指令与参考资料，排盘和金融算法保持原有版本；金融配置及复算所用方法版本仍为0.8.0，不因技能说明版本更新而改变旧预测。

技能指令版本、排盘规则 `chai_bu_v1.0.0`、盘面模式 `qimen_chart_v1.1` 与Python开发包版本分别维护。源码包 `src/qimen` 与技能内排盘模块同步。版本改动见[更新记录](CHANGELOG.md)。
