# case-08 实际操作记录

输入：case-08.json，三项纯规则查询。未取具体盘，未造完整record或运行排盘。

实际读FIVE_NOT_MEET要求原时干克原日干且同性阴阳；核甲阳辛阴不同性。读DRAGON_CHIEF/DRAGON_WU并实际核MJ-P庚值符限制，甲申遁庚的旬首几何与戊丙简法分别解释。方法配置、来源登记固定普通月令、统宗九星法、演义正文法三表，不按结果择表。实际YY-2和MJ-P原文网页已经打开，未凭记忆宣称全文核实。

已冻结case-08-answer.md。局部理论题不造前瞻reading记录；未对具体盘解事，无真实结局、无自行评分。

本轮使用候选qimen-jiepan 0.7.0。业务来源只读候选SKILL.md、references、scripts、assets及指定的两个fixture；不读evals.json、replay-status、旧回放、审查报告、封存资料或其他代理答案。另按平台技能规则读取using-superpowers的SKILL.md，发现其明确排除已派遣子代理，不将其作为奇门业务来源。未读取现装奇门SKILL；只调用其已有私有Python解释器。

本轮公共核读范围：解盘流程、方法配置、事类方法、用神与象义、格局分析、规则卡、来源登记、取象规范、主客取法、空墓与应期、记录与复核、起盘程序；读取assets/rules.json并核相关卡，读取reading_record.py的记录字段及校验实现。实际执行均加-B。未安装依赖，未运行setup_env.py，未用Git，未对候选或现装技能目录写入，未重取当前时刻，未运行日期候选。

前代理已有原始chart/patterns全部保留。本轮原盘校验采用候选validate_chart，在冻结时刻作纯一致性复算，不读取当前时钟来另起盘。a2-frozen-validation.json保留实际解释器、每盘退出前的结构校验状态与哈希；原source-hashes-start.json未更改，本轮另保存source-hashes-a2-start.json和source-hashes-a2-end.json。原盘文件与canonical数据哈希采用不同口径并分别记录，不能相互冒充。


本轮边界补记：首末源哈希实际检出候选有5项外部变化（详见source-hashes-a2-end.json），本代理没有修改候选。变化为：references\空墓与应期.md、references\起盘程序.md、scripts\inspect_patterns.py、scripts\rule_evaluator.py、scripts\timing_candidates.py。各项回答与工具结果表示本轮实际读取和执行时的状态，不冒称整批始终为同一源哈希。
