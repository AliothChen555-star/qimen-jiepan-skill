# case-07 实际操作记录

输入：case-07.json。实际仅打开指定evals/fixtures/hosted.json，与已有case-07-chart.json完整JSON比较相等，文件字节哈希相同。原盘2026-01-13T23:30:00+08:00，午夜换日，未因23点改日或另起盘。已有patterns沿用，原盘完整校验通过。

实际固定本人日干丁、丁年命同为坎一天盘寄丁，景门也在坎一；同宫结构只核一次，不造中五独立天盘本人，不把地盘寄丁当过去本人。惊门震三为争议辅助，时干庚没有编成对手。保留整体背景、宫内主寄核读、回归整体，末尾才细化取象。

实际补查固定MJ-2丁庚、丙壬，读原义与文书/行人、为客不利等条件；飞宫与辛庚、飞干与丁庚的同源结构不重复计票。无已定主客不使用对应不害或不利例外。芮禽、值符星/神与九星默认旺衰分别核。

init_record函数创建草稿，人工另存final。实际reading_record.py validate退出0，valid_final_record，6角色、2结果；stdout/stderr与argv在case-07-validate.json。当前公开表达/评价定调的有限目标adverse，近期最终结果及应期undetermined，不把当前限制冒充名声已坏。

已冻结case-07-answer.md及case-07-reading.json。无真实结局、无自行评分。

本轮使用候选qimen-jiepan 0.7.0。业务来源只读候选SKILL.md、references、scripts、assets及指定的两个fixture；不读evals.json、replay-status、旧回放、审查报告、封存资料或其他代理答案。另按平台技能规则读取using-superpowers的SKILL.md，发现其明确排除已派遣子代理，不将其作为奇门业务来源。未读取现装奇门SKILL；只调用其已有私有Python解释器。

本轮公共核读范围：解盘流程、方法配置、事类方法、用神与象义、格局分析、规则卡、来源登记、取象规范、主客取法、空墓与应期、记录与复核、起盘程序；读取assets/rules.json并核相关卡，读取reading_record.py的记录字段及校验实现。实际执行均加-B。未安装依赖，未运行setup_env.py，未用Git，未对候选或现装技能目录写入，未重取当前时刻，未运行日期候选。

前代理已有原始chart/patterns全部保留。本轮原盘校验采用候选validate_chart，在冻结时刻作纯一致性复算，不读取当前时钟来另起盘。a2-frozen-validation.json保留实际解释器、每盘退出前的结构校验状态与哈希；原source-hashes-start.json未更改，本轮另保存source-hashes-a2-start.json和source-hashes-a2-end.json。原盘文件与canonical数据哈希采用不同口径并分别记录，不能相互冒充。


本轮边界补记：首末源哈希实际检出候选有5项外部变化（详见source-hashes-a2-end.json），本代理没有修改候选。变化为：references\空墓与应期.md、references\起盘程序.md、scripts\inspect_patterns.py、scripts\rule_evaluator.py、scripts\timing_candidates.py。各项回答与工具结果表示本轮实际读取和执行时的状态，不冒称整批始终为同一源哈希。
