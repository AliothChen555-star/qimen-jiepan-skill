# case-13 操作记录

输入：X:\Daily\奇门\skill重写验收_2026-10-19\行为试读输入\case-13.json。这是虚构演练，未提供实际结局。

候选技能：X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\SKILL.md，metadata version 0.7.0。

实际读取范围：

- 本题输入 JSON；新版 SKILL.md。
- 本组共用参考读取：X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\解盘流程.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\方法配置.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\事类方法.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\用神与象义.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\格局分析.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\规则卡.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\来源登记.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\主客取法.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\空墓与应期.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\取象规范.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\起盘程序.md、X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\references\金融解盘.md。
- assets/rules.json 通过 JSON 解析读取；针对本题相关卡和字段作选择显示。
- 读取 scripts/inspect_patterns.py、timing_candidates.py、rule_evaluator.py；部分合并读取输出被工具截断，后续对相关参数、局部卡、盘面与派生字段作了定向读取。
- references/scripts/assets 下全部文件还以 SHA256 原始字节方式读取摘要，哈希读取不等于逐文件语义核读。
- 启动时读取 C:\Users\Euell\.agents\skills\using-superpowers\SKILL.md；其 SUBAGENT-STOP 要求子代理跳过，未用于本题断法。

本题核读用途：空墓与应期、方法配置、STEM_TOMB_LEGACY：区分辰巳旬空与天辛沿用墓位，列支级候选及来源未知范围，不选日期。

指定 fixture：X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\evals\fixtures\base.json。完整原始字节复制至 X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-chart.json，未转换或修改输入。

实际工具调用：

```text
C:\Users\Euell\.codex\skills\qimen-jiepan\.venv\Scripts\python.exe -B X:\Daily\奇门\qimen-jiepan-rewrite-20261019\qimen-jiepan-skill\scripts\inspect_patterns.py X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-chart.json --output X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-patterns.json
```

退出码 0；输出声明 validation_scope=full。校验按冻结时刻作内部纯计算比对，没有请求当前时钟、联网、安装或生成替换盘。输出不是独立古历校核或预测有效性证明。

工具与边界记录：

- 使用 exec_command 完成只读读取、原始字节复制、已有脚本执行、答案及本记录写入；未使用 web 或外部来源。
- 没有读取 evals.json、replay-status、旧回放、审查报告、封存稿、其他代理答案或预期标准。
- 未重起盘、未安装依赖、未修改候选技能或现装技能、未运行 Git、未作真实结局核验。
- 读盘工具的隐式导入读取属于候选 scripts 及现有解释器依赖，-B 禁止写入字节码；没有调用 setup_env.py。

产物：

- X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-answer.md
- X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-operations.md
- X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-chart.json
- X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-patterns.json

本组原始字节哈希记录：X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\source-hashes-case09-17-start.json。原 source-hashes-start.json 未被本子代理打开或覆盖，已告知主代理统一追加本轮条目。

未执行部分：本题范围以外的整盘事件预测、精确结果或真实应验检验均未执行；没有据此计算准确率。

末尾哈希复核：首次“所有源均未变化”断言退出码 1；随后定向复核发现 inspect_patterns.py、rule_evaluator.py、timing_candidates.py 三个候选脚本末尾摘要不同，本子代理没有发出对技能目录的写入。七份 fixture 副本仍与指定源逐字节一致；case-15 两套九星配置的普通门干宫月令字段一致。变化明细及复核过程保存在 X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\source-hashes-case09-17-end.json。本组没有逐次调用前的脚本哈希，不能据现有记录保证每次执行都对应起始脚本摘要；未回滚源、未重跑覆盖派生数据。

后续核验：收到主代理要求后，重新读取当前 references/空墓与应期.md 与 references/事类方法.md；未补得本题适用的统一空亡作用或求职阶段应期原文，另存 X:\Daily\奇门\skill重写验收_2026-10-19\行为试读B\case-13-revision.md 明确范围。原 answer、chart、patterns、timing 均未覆盖；未重起盘、未重算、未修改技能。
