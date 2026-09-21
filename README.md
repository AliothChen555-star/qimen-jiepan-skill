# 奇门遁甲解盘 Skill

这是一个面向 Codex 及兼容 Agent Skill 运行环境的中文奇门遁甲工具，包含拆补法时家转盘的起盘程序、规则说明和结构化解盘流程。

项目不仅提供命令行排盘程序，还通过 `SKILL.md` 约束智能体在解盘前核对盘式、时间与用神，在结论中同时列出支持依据、反向依据和不确定因素，避免脱离盘面直接下判断。

> 本项目用于传统文化研究与辅助分析，不应替代医疗、法律、投资、安全等领域的专业意见和现实证据。

## 主要能力

- 按当前时间或指定的 ISO 8601 时间起盘。
- 支持时区、经纬度、标准时与真太阳时参数。
- 生成文本盘面或完整 JSON，便于智能体继续分析。
- 输出年、月、日、时四柱，阴阳遁、三元、局数、旬首、旬空、值符、值使和马星。
- 给出九宫的地盘干、天盘干、九星、八门、八神等信息。
- 采用“规则核对 → 声明用神 → 宫位分析 → 正反证据 → 趋势与应期 → 风险提示”的解盘流程。
- 对尚未计算或核验的规则明确标注边界，不把缺失信息当作既定结论。

## 当前规则

当前规则版本为 `chai_bu_v1.0.0`：

- 拆补法时家转盘；
- 中宫地盘干寄坤二；
- 中宫保留天盘天干，九星、八门、八神留空；
- 天禽随天芮；
- 马星默认按时支计算，也支持按日支；
- 起盘年份范围为 1901—2099 年。

不同门派在置闰、换日、中宫寄宫、用神和象义优先级上可能存在差异。使用本 Skill 时，应以盘面中的规则版本及参数为准，不混用其他规则体系。

## 环境要求

- Python 3.10 或更高版本；
- 首次初始化时可连接 Python 包索引；
- 依赖见 [`qimen-jiepan-skill/requirements.txt`](qimen-jiepan-skill/requirements.txt)。

初始化脚本会在 Skill 目录内部创建私有 `.venv`，不会向系统 Python 环境安装依赖。

## 安装为 Codex Skill

先克隆仓库：

```bash
git clone https://github.com/AliothChen555-star/qimen-jiepan-skill.git
cd qimen-jiepan-skill
```

将仓库中的 `qimen-jiepan-skill` 目录复制到个人 Skill 目录，并命名为 `qimen-jiepan`。安装后的关键文件应位于：

```text
<Codex Skill 目录>/qimen-jiepan/SKILL.md
```

Windows PowerShell 示例：

```powershell
Copy-Item -Recurse .\qimen-jiepan-skill "$env:USERPROFILE\.codex\skills\qimen-jiepan"
python "$env:USERPROFILE\.codex\skills\qimen-jiepan\scripts\setup_env.py"
```

macOS 或 Linux 示例：

```bash
cp -R ./qimen-jiepan-skill "$HOME/.codex/skills/qimen-jiepan"
python3 "$HOME/.codex/skills/qimen-jiepan/scripts/setup_env.py"
```

也可以不提前初始化环境。首次调用 `scripts/qimen_cli.py` 时，它会自动创建私有环境并安装依赖。

## 单独使用起盘程序

进入 Skill 目录后，可直接调用统一入口。

按当前时间起盘并输出 JSON：

```bash
python scripts/qimen_cli.py chart --now --format json
```

按指定时间起盘：

```bash
python scripts/qimen_cli.py chart \
  --datetime 2026-09-14T14:30:00+08:00 \
  --timezone Asia/Shanghai \
  --format json
```

按真太阳时起盘：

```bash
python scripts/qimen_cli.py chart \
  --datetime 2026-09-14T14:30:00+08:00 \
  --timezone Asia/Shanghai \
  --longitude 116.4074 \
  --latitude 39.9042 \
  --time-mode true_solar_time \
  --format json
```

常用参数：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--now` | 使用运行时的当前时间 | 不启用 |
| `--datetime` | 带时区偏移的 ISO 8601 时间 | 无 |
| `--timezone` | IANA 时区名称 | `Asia/Shanghai` |
| `--longitude` | 经度，真太阳时计算会使用 | `120` |
| `--latitude` | 纬度，并记录到输出参数中 | `30` |
| `--time-mode` | `standard_time` 或 `true_solar_time` | `standard_time` |
| `--format` | `text` 或 `json` | `text` |

`--now` 与 `--datetime` 不能同时使用。显式时间必须包含时区偏移，例如 `+08:00`，以避免夏令时和本地时间歧义。

## 在对话中使用

安装后，可以直接向智能体提出包含时间、地点、事项和期限的问题，例如：

```text
请按 2026-09-14 14:30（北京时间）起一个拆补法时家转盘，
分析未来一个月内这次求职是否有进展，并说明用神、正反依据和应期窗口。
```

如果只要求起盘，Skill 应只输出盘面；如果同时提出具体问题，才继续执行解盘流程。问题信息不足时，智能体应先明确假设或询问关键条件。

## 项目结构

```text
.
├─ qimen-jiepan-skill/       # 可直接安装的完整 Skill
│  ├─ SKILL.md               # 触发条件、工作流程与输出规范
│  ├─ requirements.txt       # Skill 私有环境依赖
│  ├─ references/            # 规则边界、用神象义与解盘流程
│  └─ scripts/               # 独立起盘程序与环境初始化脚本
├─ src/qimen/                # 起盘程序的开发源码
├─ docs/                     # 研究资料、规则说明与任务文档
├─ pyproject.toml            # Python 项目配置
└─ README.md
```

## 已知边界

- 当前自动起盘结果未完整计算入墓、击刑、门迫、伏吟和反吟；未核验时不得声称已经判定。
- 经纬度和真太阳时换算属于时间校正参数，不代表自动处理所有地方时、历史时区和门派差异。
- 解盘输出是基于既定规则与用神假设的趋势分析，不保证事件结果。
- `src/qimen/` 与 Skill 内的 `scripts/qimen/` 分别用于开发和独立分发，修改核心算法时应保持两处同步。

## 开源许可证

本项目采用 [MIT License](LICENSE)。你可以自由使用、复制、修改和分发本项目，但需保留原始版权及许可声明。
