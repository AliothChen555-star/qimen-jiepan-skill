# case-04 实际操作记录

输入：case-04.json。实际仅打开指定evals/fixtures/base.json，与已有case-04-chart.json作完整JSON数据比较，相等；原盘文件字节哈希也相同。沿用已有patterns。冻结时刻2026-10-14T13:27:13+08:00；本轮未重取现在。

实际固定日干辛巽四为本人、开门离九为工作职位的现代有限转译；无年命不补造，时干乙未借作雇主。三个月范围明确从原盘时刻至2027-01-14同钟面。“落实并开始任职”是本答采用的成功标准，不冒称用户已提供的现实事实。

实际先扫描全盘，再核本人和工作宫的主寄星干门神、月令、空墓刑迫与吉凶反义。丙辛未收录，固定补查MJ-2；旬首跌穴、悖格同源不重复计票。辛墓仅旧表partial，不作关键依据。不挪用开店/行人/合伙条文补换职期限。

init_record函数创建草稿，人工另存final。实际reading_record.py validate退出0，valid_final_record，4角色、2结果，详见case-04-validate.json。当前有限状态mixed，固定三个月结果undetermined；不是只因缺精确日期就否定期限判断，而是缺完整本事期限适用。

已冻结case-04-answer.md及case-04-reading.json。无真实结局、无自行评分。

本轮使用候选qimen-jiepan 0.7.0。业务来源只读候选SKILL.md、references、scripts、assets及指定的两个fixture；不读evals.json、replay-status、旧回放、审查报告、封存资料或其他代理答案。另按平台技能规则读取using-superpowers的SKILL.md，发现其明确排除已派遣子代理，不将其作为奇门业务来源。未读取现装奇门SKILL；只调用其已有私有Python解释器。

本轮公共核读范围：解盘流程、方法配置、事类方法、用神与象义、格局分析、规则卡、来源登记、取象规范、主客取法、空墓与应期、记录与复核、起盘程序；读取assets/rules.json并核相关卡，读取reading_record.py的记录字段及校验实现。实际执行均加-B。未安装依赖，未运行setup_env.py，未用Git，未对候选或现装技能目录写入，未重取当前时刻，未运行日期候选。

前代理已有原始chart/patterns全部保留。本轮原盘校验采用候选validate_chart，在冻结时刻作纯一致性复算，不读取当前时钟来另起盘。a2-frozen-validation.json保留实际解释器、每盘退出前的结构校验状态与哈希；原source-hashes-start.json未更改，本轮另保存source-hashes-a2-start.json和source-hashes-a2-end.json。原盘文件与canonical数据哈希采用不同口径并分别记录，不能相互冒充。


本轮边界补记：首末源哈希实际检出候选有5项外部变化（详见source-hashes-a2-end.json），本代理没有修改候选。变化为：references\空墓与应期.md、references\起盘程序.md、scripts\inspect_patterns.py、scripts\rule_evaluator.py、scripts\timing_candidates.py。各项回答与工具结果表示本轮实际读取和执行时的状态，不冒称整批始终为同一源哈希。
