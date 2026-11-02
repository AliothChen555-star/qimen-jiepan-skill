# 奇门遁甲起盘与解盘 Skill

当前技能版本：**0.10.0**。包含拆补法时家转盘、冻结盘核验、传统规则卡、分事解盘与金融日／周／月预测。本版新增金融综合解盘、基金主题拆解、行情核验及预测发布流程，保留六步分析与旧金融基线。

## 本版改变

新金融分析采用 FINANCE_MULTI_ROLE_V2_CANDIDATE 0.1.0：固定景门、值符、戊、生门、开门、值使与时干的不同用途，保存支持、反证和冲突裁决。AI、有色、发电、电力设备、红利低波等主题分别分析；未知权重不编造。该综合框架尚未校准价格预测能力，程序检查通过不表示预测更准。

行情层保存日线、分时和第三方原始响应，核代码、名称、日期、报价时刻及价格精度。预测层区分证据、待填草稿、实际发布和后来结局；方向未明不等于窄幅，ETF价格不代替基金净值或账户收益。

执行顺序为：前置定题校盘 → 审局观象 → 固定主辅用神 → 宫内分析 → 宫间比较 → 综合取象与应期 → 运筹与留档。全盘可给可修正的盘势与节奏初判，最终综合须回看核心宫和事类条件；回答仍先给结论。

前置规则涵盖自然动念、问时与事件时间、异步接问、重复与补问、纠错重占及盘面时效。按实际问题承接或另立新盘，不设置通用三次额度和等待天数。专项取用新增原文定位说明，年命、十二长生、生克、庚格与宫数都标明各自适用范围。

规则资料维护在 [rules.json](qimen-jiepan-skill/assets/rules.json)，包含69张卡、22条有向干对选录及6个方法入口。几何匹配、传统解释、有利取用、事件适用和主客例外分别核验；关键未知不作成立。没有补全的干格按固定来源查，不用五行关系编克应。

首批文本方法区分合伙助益、贸易资本收益和开店经营。旧 FINANCE_FIXED_CHART_V1 的 F01—F10保留原样计算与独立对照，新综合判断另存；现代合同期限和工作压力持续天数仍按各自方法处理。现状、期限结果、精确应期分别回答，原义有凶不抹去，有吉及例外也不遗漏。

## 使用

金融预测先读[金融解盘](qimen-jiepan-skill/references/金融解盘.md)，新分析按[金融综合解盘](qimen-jiepan-skill/references/金融综合解盘.md)建立产品主题、证据与综合记录：

```text
<技能私有Python> qimen-jiepan-skill/scripts/finance_forecast.py --mode multi_role --chart chart.json --request request.json --output context.json --draft draft.json --markdown evidence.md
# 完成draft.json中的逐日方向、支持、反证、裁决与条件后发布
<技能私有Python> qimen-jiepan-skill/scripts/finance_record.py publish --draft draft.json --output forecast-v2.json --markdown answer.md
<技能私有Python> qimen-jiepan-skill/scripts/finance_record.py validate forecast-v2.json --chart chart.json
```

固定同盘逐日列干支、遁仪、宫位与实际支级作用，再由解盘者完成综合判断；程序不把空草稿当预测。内置沪深港2026日历，其他市场／年份接入已核日历；场外基金按净值归属日及采价窗口分类。原预测、修订、结局与订单分别保存。CLI不带mode时保持旧版兼容，旧[逐日方法](qimen-jiepan-skill/references/固定盘逐日推演.md)和[历史幅度](qimen-jiepan-skill/references/金融数据与幅度.md)不覆盖新综合结论。示例产品与测试行情均为合成数据。

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
| [金融解盘](qimen-jiepan-skill/references/金融解盘.md)、[金融综合解盘](qimen-jiepan-skill/references/金融综合解盘.md) | 方法选择、产品主题、显式综合、行情与14:30纠偏 |
| [评估方法](qimen-jiepan-skill/references/评估方法.md) | 资料、程序、行为与真实效验分层 |

完整内置盘校验检查布局耦合、原始时刻、历法和方法的一致性；不相容盘或截图可作有限人工解读，不能强行改成内置盘。合成排布测试使用明确的结构接口，生产命令不提供降级开关。

日期候选工具支持独立搜索起点、日历日与24小时两种时长，以及历史时区缺失/重复钟面。输出UTC端点、并集时长和覆盖比例；候选不是应验日，覆盖比例不是命中率。

## 验证

```text
<技能私有Python> -B -m unittest discover -s qimen-jiepan-skill/evals -p "test_*.py" -v
```

本版183项程序检查通过：原159项保留，新增24项覆盖主题与未知权重、甲柱遁仪及五行分层、支级空亡、证据复算、草稿/发布时序、开发样本和代理排除、覆盖率/形态分评、报价精度与分时高低价。旧版行为状态见 [replay-status.json](qimen-jiepan-skill/evals/replay-status.json)，基线见 [0.8.0金融验收](qimen-jiepan-skill/evals/replays/0.8.0.md)，前次流程见 [0.9.0验收](qimen-jiepan-skill/evals/replays/0.9.0.md)，本版范围见 [0.10.0复核](qimen-jiepan-skill/evals/replays/0.10.0.md)。真实前瞻结局另行统计，合成检查与独立执行试用不构成预测命中率。

0.10.0新增综合分析方法0.1.0；旧金融方法及复算版本仍为0.8.0，排盘核心与Python开发包版本保持原样。新方法的显式综合与旧基线独立留档，不改变历史预测。

技能指令版本、排盘规则 `chai_bu_v1.0.0`、盘面模式 `qimen_chart_v1.1` 与Python开发包版本分别维护。源码包 `src/qimen` 与技能内排盘模块同步。版本改动见[更新记录](CHANGELOG.md)。
