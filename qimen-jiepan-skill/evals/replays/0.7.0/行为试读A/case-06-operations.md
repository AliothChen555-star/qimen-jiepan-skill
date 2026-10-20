# case-06 实际操作记录

输入：case-06.json，局部理论核验。只用乙辛、艮八、休门、甲午旬等已给字段；没有编造实际值符星或神、月令、完整局盘。未起盘、未full validation。

实际核QI_ENVOY的乙辛本旬值符星同临附条件，GEOM_乙辛原义和MJ-P主客例外边界，以及DUN_HU所选乙辛休艮虎遁。甲午不等于已知值符星同宫；神盘值符不能替代。休艮为受制非门迫。

乙己按固定MJ-2实际补查，所见写入雾；即使另表名入墓也与实际乙落坤墓位分开，不在坤则该落宫墓结构不成立。ZZG-4已核乙坤子集不扩张全干墓表。正文另据YY-2得使与九遁段、ZG-4青龙逃走/迫制核读，URLs在a2-source-notes.md。

已冻结case-06-answer.md。只有局部规则核验，不造完整前瞻reading记录，无真实结局、无自行评分。

本轮使用候选qimen-jiepan 0.7.0。业务来源只读候选SKILL.md、references、scripts、assets及指定的两个fixture；不读evals.json、replay-status、旧回放、审查报告、封存资料或其他代理答案。另按平台技能规则读取using-superpowers的SKILL.md，发现其明确排除已派遣子代理，不将其作为奇门业务来源。未读取现装奇门SKILL；只调用其已有私有Python解释器。

本轮公共核读范围：解盘流程、方法配置、事类方法、用神与象义、格局分析、规则卡、来源登记、取象规范、主客取法、空墓与应期、记录与复核、起盘程序；读取assets/rules.json并核相关卡，读取reading_record.py的记录字段及校验实现。实际执行均加-B。未安装依赖，未运行setup_env.py，未用Git，未对候选或现装技能目录写入，未重取当前时刻，未运行日期候选。

前代理已有原始chart/patterns全部保留。本轮原盘校验采用候选validate_chart，在冻结时刻作纯一致性复算，不读取当前时钟来另起盘。a2-frozen-validation.json保留实际解释器、每盘退出前的结构校验状态与哈希；原source-hashes-start.json未更改，本轮另保存source-hashes-a2-start.json和source-hashes-a2-end.json。原盘文件与canonical数据哈希采用不同口径并分别记录，不能相互冒充。


本轮边界补记：首末源哈希实际检出候选有5项外部变化（详见source-hashes-a2-end.json），本代理没有修改候选。变化为：references\空墓与应期.md、references\起盘程序.md、scripts\inspect_patterns.py、scripts\rule_evaluator.py、scripts\timing_candidates.py。各项回答与工具结果表示本轮实际读取和执行时的状态，不冒称整批始终为同一源哈希。
