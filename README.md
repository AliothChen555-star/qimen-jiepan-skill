# 奇门遁甲起盘与解盘 Skill

当前技能版本：**0.7.0**。包含拆补法时家转盘程序、冻结盘严格核验、带来源及完整条件的规则卡、分事取用和解盘记录工具。它不声明已经验证真实预测准确率。

## 本版改变

执行顺序为：定题与结果 → 校盘定法 → 固定角色 → 全盘扫描 → 核核心宫 → 按事类比较 → 条件与反证 → 分项结论 → 必要取象及应期 → 留档。全盘第一遍只列背景及待核条件，不强制提前给顺逆。

规则资料维护在 [rules.json](qimen-jiepan-skill/assets/rules.json)，包含69张卡、22条有向干对选录及5个方法入口。几何匹配、传统解释、有利取用、事件适用和主客例外分别核验；关键未知不作成立。没有补全的干格按固定来源查，不用五行关系编克应。

首批文本方法区分合伙助益、贸易资本收益和开店经营。现代合同期限、证券方向和工作压力持续天数没有自动换算公式。现状、期限结果、精确应期分别回答，原义有凶不抹去，有吉及例外也不遗漏。

## 使用

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
| [解盘流程](qimen-jiepan-skill/references/解盘流程.md) | 从定题到分项判断和反证复核 |
| [方法配置](qimen-jiepan-skill/references/方法配置.md)、[事类方法](qimen-jiepan-skill/references/事类方法.md) | 固定盘法、主辅角色和分类适用边界 |
| [规则卡](qimen-jiepan-skill/references/规则卡.md)、[来源登记](qimen-jiepan-skill/references/来源登记.md) | 原文位置、条件、异说和未核范围 |
| [取象规范](qimen-jiepan-skill/references/取象规范.md) | 区分传统义、现代类比与现实事实 |
| [空墓与应期](qimen-jiepan-skill/references/空墓与应期.md) | 期限与精确应期、候选工具边界 |
| [记录与复核](qimen-jiepan-skill/references/记录与复核.md) | 原盘哈希、角色、正反依据和期限一致性 |
| [金融解盘](qimen-jiepan-skill/references/金融解盘.md) | 传统解释、事实核验与实验预测分开 |
| [评估方法](qimen-jiepan-skill/references/评估方法.md) | 资料、程序、行为与真实效验分层 |

完整内置盘校验检查布局耦合、原始时刻、历法和方法的一致性；不相容盘或截图可作有限人工解读，不能强行改成内置盘。合成排布测试使用明确的结构接口，生产命令不提供降级开关。

日期候选工具支持独立搜索起点、日历日与24小时两种时长，以及历史时区缺失/重复钟面。输出UTC端点、并集时长和覆盖比例；候选不是应验日，覆盖比例不是命中率。

## 验证

```text
<技能私有Python> -B -m unittest discover -s qimen-jiepan-skill/evals -p "test_*.py" -v
```

现有测试和新增反例检查结构、输入、时间、条件三态及记录一致性。行为执行状态单列在 [replay-status.json](qimen-jiepan-skill/evals/replay-status.json)。程序通过不等于独立历法签核，也不证明真实预测能力。

技能指令版本、排盘规则 `chai_bu_v1.0.0`、盘面模式 `qimen_chart_v1.1` 与Python开发包版本分别维护。源码包 `src/qimen` 与技能内排盘模块同步。版本改动见[更新记录](CHANGELOG.md)。
