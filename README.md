# 奇门遁甲起盘与解盘 Skill

`qimen-jiepan` 是面向 Codex 及兼容 Agent Skill 环境的中文奇门遁甲技能，包含拆补法时家转盘程序、格局核验工具和带依据的解盘流程。可以按当前时间、指定时间或用户提供的盘面分析求职、合作、风评、人际等问题。

**当前技能版本：0.3.0。** 本版将解盘改为：

**全盘分析 → 取用神 → 用神宫位关系 → 宫内四盘与格局细析 → 合并分析 → 最终结论。**

每一步都说明“盘面字段或组合 → 采用的规则与取法 → 本步判断”。结论重点给出奇门大势、关键条件与可能取象，取消固定免责声明、机械反证配额和反复现实误差提醒。

## 六步解盘如何工作

| 步骤 | 分析内容 | 本步输出 |
| --- | --- | --- |
| 1. 全盘分析 | 扫描外八宫与中宫寄宫，查看月令气势、值符值使、星/门/奇仪各自的反伏吟，以及格局、空亡和马星分布 | 动静、顺阻、显隐等共同背景及依据，暂不指定人物用神 |
| 2. 取用神 | 按问句确定本人、对方、事项及必要辅助用神，声明主辅、盘层与落宫 | 为什么这样取用；不因某宫吉凶临时改换用神 |
| 3. 宫位关系 | 比较用神宫的有向生克、旺衰、同宫、比和和对宫关系 | 谁支持谁、谁向谁付出、谁约束谁，以及关系能发挥的力度 |
| 4. 宫内四盘细析 | 每个不重复的用神宫分析天盘、地盘、人盘、神盘及天地干叠加，核验刑墓空马、门迫与复合格局 | 先分别说明各层作用，再合并为该宫的结论 |
| 5. 合并分析 | 将全盘背景、宫位关系和各宫结论结合，解释一致与冲突 | 区分气势、意向、行动和兑现能力；不按吉凶数量计票 |
| 6. 最终结论 | 回答所问的主要走势、关键条件、可能取象；需要且有依据时再给应期 | 每条结论可追溯到前面的证据 |

四盘在本技能中的分工：

- **天盘：**九星、天盘三奇六仪，观察外在走势和呈现状态。
- **地盘：**九宫卦象、五行、地盘三奇六仪及寄干，观察基底和承接条件。
- **人盘：**八门，观察行动通道及其开放、收束或受阻方式。
- **神盘：**八神，观察助力与阻力的表现方式。

“天干加地干”有方向：乙加辛与辛加乙分别分析。多干宫区分主干与寄干；同宫多个用神共用一份宫内证据，再分别映射其角色，不重复计证。具体执行要求见 [解盘流程](qimen-jiepan-skill/references/解盘流程.md)。

## 格局分析与核验

本版新增 [`inspect_patterns.py`](qimen-jiepan-skill/scripts/inspect_patterns.py)，读取已保存的内置盘面 JSON，生成格局的成立条件与分层派生依据。它不重新起盘、不选用神、不自动给问事结论。

| 范围 | 核验或分析方式 |
| --- | --- |
| 整体反伏吟 | 星盘、门盘、奇仪盘分别核验；局部同干不冒充全盘伏吟 |
| 天地干组合 | 处理九干构成的 81 种有向组合，核对五行生克、同干、五合和双方状态；重点格名另列条件 |
| 门与宫 | 门克宫为门迫，宫克门为门受制；得生、泄气、比和分别记录 |
| 刑与墓 | 天盘六仪逐仪击刑，标明是否为本旬遁仪；天盘入墓与地盘墓位分别记录 |
| 命名相加格 | 青龙返首、飞鸟跌穴、青龙逃走、白虎猖狂、朱雀投江、腾蛇夭矫及庚格等 |
| 复合格局 | 按声明条件核验九遁、三奇得使、玉女守门和三诈 |
| 时间与修正 | 五不遇时、旬空、驿马、值符值使关系及寄宫信息 |

格局的几何条件成立后，还要结合月令、事类、宫位和其他三盘判断其发挥。例如，三奇得使可与青龙逃走并见；岗位宫有承接格，也可能同时开门受制。解盘须解释这些条件如何共同作用。

采用口径及古籍出处见 [格局分析](qimen-jiepan-skill/references/格局分析.md)。其中九星使用《奇门遁甲统宗》的专门旺衰公式，与门、干、宫的一般五行月令法区分；九遁默认按已列明的《遁甲演义》条件。工具只支持完整的 `chai_bu_v1.0.0`、`kun2` 内置盘面；其他盘式按用户明确规则人工核验。

## 起盘能力与规则

起盘程序支持当前时间或带时区偏移的 ISO 8601 时间，输出文本盘或完整 JSON。结果包含四柱、节气、阴阳遁、三元、局数、旬首、旬空、值符值使、马星，以及九宫的天干、地干、星、门、神和寄宫信息。

| 版本或规则 | 当前采用值 |
| --- | --- |
| 技能指令版本 | `0.3.0` |
| 格局核验版本 | `qimen_patterns_v1.0.0` |
| 排盘规则版本 | `chai_bu_v1.0.0`，拆补法时家转盘 |
| Python 开发包版本 | `0.1.0`，与技能版本独立 |
| 默认时间 | `Asia/Shanghai` 标准时，也支持指定时区和真太阳时 |
| 中宫 | 中五寄坤二，天禽随天芮；中宫展示天干不作为独立天盘落点 |
| 马星 | CLI 默认按时支；Python 起盘接口也支持按日支 |
| 起盘年份 | 1901—2099 年 |

排盘算法与格局核验分开维护：`qimen_cli.py` 产生原始盘面，`inspect_patterns.py` 从该盘面派生核验结果。本版保留现有排盘规则。

## 安装与更新

需要 Python 3.10 或更高版本。首次初始化需能访问 Python 包索引，依赖见 [requirements.txt](qimen-jiepan-skill/requirements.txt)。初始化只在技能目录内创建私有 `.venv` 并安装依赖。

先取得仓库：

```bash
git clone https://github.com/AliothChen555-star/qimen-jiepan-skill.git
cd qimen-jiepan-skill
```

### 安装为个人 Skill

仓库根目录中的 **`qimen-jiepan-skill/` 子目录**才是可安装技能。复制到个人技能目录时命名为 `qimen-jiepan`，安装后的入口应为 `<技能目录>/qimen-jiepan/SKILL.md`。

下面示例用于首次安装；已有同名目录时，请按下一节合并更新。

Windows PowerShell，在仓库根目录运行：

```powershell
$skillBase = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skillRoot = Join-Path $skillBase 'skills'
$skillPath = Join-Path $skillRoot 'qimen-jiepan'
if (Test-Path -LiteralPath $skillPath) { throw '已有 qimen-jiepan，请按更新章节合并。' }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
Copy-Item -LiteralPath '.\qimen-jiepan-skill' -Destination $skillPath -Recurse
python (Join-Path $skillPath 'scripts\setup_env.py')
```

macOS 或 Linux，在仓库根目录运行：

```bash
skill_path="${CODEX_HOME:-$HOME/.codex}/skills/qimen-jiepan"
if [ -e "$skill_path" ]; then
  echo '已有 qimen-jiepan，请按更新章节合并。'
else
  mkdir -p "$(dirname "$skill_path")"
  cp -R ./qimen-jiepan-skill "$skill_path"
  python3 "$skill_path/scripts/setup_env.py"
fi
```

也可直接读取仓库内的 `qimen-jiepan-skill/SKILL.md`，临时使用相邻脚本。首次调用 `qimen_cli.py` 时会自动初始化私有环境。安装后让宿主重新加载技能列表，例如开启新会话。

### 更新已有安装

先检查并备份仓库及安装目录中的个人修改，再合并新版 `SKILL.md`、`references/`、`scripts/`、`evals/` 和依赖清单，保留已有私有环境。合并完成后运行该技能的 `scripts/setup_env.py`。

本版需一起更新 `references/格局分析.md`、`scripts/inspect_patterns.py` 和 `evals/test_patterns.py`，仅替换 `SKILL.md` 会遗漏格局依据与核验工具。不要把其他名称相近的技能自动删除或当成同一版本。

首次使用可让助手报告实际加载的 `SKILL.md` 路径。有 Git 的副本可用 `git remote -v` 和 `git rev-parse HEAD` 核对来源；复制安装则核对文件与声明版本。故障处理见 [起盘程序](qimen-jiepan-skill/references/起盘程序.md)。

## 命令行使用

以下命令从仓库内的技能目录运行：

```bash
cd qimen-jiepan-skill
```

当前时间起盘：

```bash
python scripts/qimen_cli.py chart --now --format json
```

指定时间起盘：

```bash
python scripts/qimen_cli.py chart --datetime 2026-10-14T14:30:00+08:00 --timezone Asia/Shanghai --format json
```

指定经度，按真太阳时起盘：

```bash
python scripts/qimen_cli.py chart --datetime 2026-10-14T14:30:00+08:00 --timezone Asia/Shanghai --longitude 116.4074 --latitude 39.9042 --time-mode true_solar_time --format json
```

| CLI 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--now` | 使用程序实际运行时刻 | 不启用 |
| `--datetime` | 带时区偏移的 ISO 8601 时间 | 无 |
| `--timezone` | IANA 时区名称 | `Asia/Shanghai` |
| `--longitude` | 经度，用于真太阳时校正 | `120` |
| `--latitude` | 纬度，记录在输入参数中 | `30` |
| `--time-mode` | `standard_time` 或 `true_solar_time` | `standard_time` |
| `--format` | `text` 或 `json` | `text` |

`--now` 和 `--datetime` 二选一。标准时不需要提供城市；默认经纬度不是用户定位。真太阳时应提供用户认可的经度。同一问事保存第一次成功起盘的 JSON，补充年命或追问解法继续沿用该盘。

### 保存原盘并核验格局

输出保存在仓库外。Windows PowerShell 示例兼容 UTF-8 BOM：

```powershell
$chartPath = Join-Path $env:TEMP 'qimen-chart.json'
$patternsPath = Join-Path $env:TEMP 'qimen-patterns.json'
$chartResult = python scripts/qimen_cli.py chart --datetime 2026-10-14T14:30:00+08:00 --format json
if ($LASTEXITCODE -ne 0) { throw '起盘失败，不能继续核验。' }
$chartResult | Set-Content -LiteralPath $chartPath -Encoding utf8
python scripts/inspect_patterns.py $chartPath --output $patternsPath
```

macOS 或 Linux 示例：

```bash
python3 scripts/qimen_cli.py chart --datetime 2026-10-14T14:30:00+08:00 --format json > /tmp/qimen-chart.json
python3 scripts/inspect_patterns.py /tmp/qimen-chart.json --output /tmp/qimen-patterns.json
```

格局工具使用标准库和本技能规则常量，不需要额外安装排盘库。它保留主干/寄干、上下盘方向、成立条件与所用口径，供助手继续四盘分析和整合。

## 在对话中使用

完整分析：

```text
用 qimen-jiepan，按当前时间起盘，分析未来三个月换工作是否顺利。
按全盘、取用神、宫位关系、宫内四盘与格局、合并、最终结论的顺序讲依据，
重点给大势和可能取象。
```

风评与年命：

```text
按当前时间看近期整体风评，我的年命是丁。取法由你根据问题选择，
说明日干与年命的主辅，以及人物宫和景门宫怎样共同影响结论。
```

仅起盘：

```text
只按 2026-10-14T14:30:00+08:00 起盘，使用标准北京时间，展示完整盘面，不解盘。
```

已有盘面也可直接提供，不必重起。年命不是排盘必填项；同宫角色分别声明，但宫内分析只做一次。简版仍保留六步及依据，教学版展开格局的成立条件。现状问题不强定应期，未来事件只有相关用神和触发机制有依据时才给日期窗口。

## 验证与维护

[`evals/evals.json`](qimen-jiepan-skill/evals/evals.json) 包含八个合成行为场景，覆盖当前时间与年命、仅起盘、来源冲突、新六步流程、门迫与反伏吟、格局并存、同宫寄干及不同规则口径。

[`evals/test_patterns.py`](qimen-jiepan-skill/evals/test_patterns.py) 提供 17 项确定性测试，覆盖阴阳遁各九局与六十甲子时的 1,080 种排盘组合、81 种天地干组合、有向生克、分层反伏吟、寄干、刑墓、门迫与受制、复合格局条件及不完整数据处理。

从技能目录初始化并运行测试：

```bash
python scripts/setup_env.py
```

Windows PowerShell：

```powershell
& .\.venv\Scripts\python.exe .\evals\test_patterns.py
```

macOS 或 Linux：

```bash
.venv/bin/python evals/test_patterns.py
```

这些检查验证排盘结构、格局规则和指令遵循；行为场景需要实际回放评估，不因文件存在而视为已全部通过。运行记录、个人问事和盘面 JSON 保存在仓库外。

## 项目结构

```text
.
├─ README.md
├─ CHANGELOG.md
├─ LICENSE
├─ qimen-jiepan-skill/          # 可安装技能，安装时命名为 qimen-jiepan
│  ├─ SKILL.md
│  ├─ requirements.txt
│  ├─ references/
│  │  ├─ 解盘流程.md
│  │  ├─ 用神与象义.md
│  │  ├─ 格局分析.md
│  │  ├─ 规则边界.md
│  │  └─ 起盘程序.md
│  ├─ scripts/
│  │  ├─ qimen_cli.py          # 起盘入口及私有环境初始化
│  │  ├─ setup_env.py
│  │  ├─ inspect_patterns.py  # 读取原盘，核验格局
│  │  └─ qimen/               # 技能内独立分发的排盘模块
│  └─ evals/
│     ├─ evals.json
│     └─ test_patterns.py
├─ src/qimen/                 # 排盘算法的开发源码
├─ docs/                      # 研究资料与历史设计文档
└─ pyproject.toml
```

修改核心排盘算法时，应同步维护 `src/qimen/` 与技能内 `scripts/qimen/`。当前解盘要求以 `SKILL.md` 及其引用资料为准，`docs/` 中的历史设计用于追溯。

## 规则范围与许可证

技能明确区分盘面事实、传统取法与问事取象。未提供或未核验的相关字段只说明影响范围，不编造格局；工具没有统一覆盖五假、三奇升殿、天三门地四户等其他门派术语，也不自动计算应期。

涉及具体高风险行动时保留必要的一句边界说明，普通解盘不追加常规风险提示段落。不同门派的中宫、旺衰、墓刑和九遁口径须先声明，不能在同盘混用。详细规则见 [规则边界](qimen-jiepan-skill/references/规则边界.md)。

本项目采用 [MIT License](LICENSE)，使用、修改与分发时保留原始版权及许可声明。
