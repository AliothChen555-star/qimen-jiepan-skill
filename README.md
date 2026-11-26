# 奇门遁甲排盘与解盘 Skill（v1.0 基本版）

当前技能版本：**1.0.0**。采用**拆补法时家转盘奇门**，内置 Python 排盘程序与精简的基础解盘框架。

> **模型建议：建议使用 Qwen 或 Gemini。**

## 版本说明

`v1.0` 推倒重写了旧版冗杂的说明文档、繁琐留档与衍生金融规则，回归轻量化、准确可用的基本版：

- 保留稳定的拆补法时家转盘排盘核心（`chai_bu_v1.0.0` / `qimen_chart_v1.1`），不靠模型手算排盘。
- 精简为单入口指令 [SKILL.md](qimen-jiepan-skill/SKILL.md) + 1 份基础对照表 [基础速查.md](qimen-jiepan-skill/references/基础速查.md)。
- 明确五步解盘主线：审大势 → 定用神 → 查宫内状态与四害空马 → 比宫间生克 → 看应期与建议。

## 目录结构

```text
.
├── qimen-jiepan-skill/          # 可直接安装的 Skill 目录
│   ├── SKILL.md                 # 主指令（v1.0 基本版）
│   ├── references/
│   │   └── 基础速查.md          # 九宫五行、门迫、星神、击刑、入墓、五不遇时、常用克应
│   ├── requirements.txt         # 排盘依赖（lunar-python、tzdata）
│   └── scripts/
│       ├── setup_env.py         # 在 Skill 目录内初始化私有 .venv
│       ├── qimen_cli.py         # 排盘 CLI 入口
│       └── qimen/               # 排盘核心模块
├── src/qimen/                   # 与 Skill 内同步的 Python 源码包
├── pyproject.toml
├── CHANGELOG.md
└── LICENSE
```

## 安装与使用

1. 将仓库中的 `qimen-jiepan-skill/` 目录复制到你的 Agent 技能目录（通常命名为 `qimen-jiepan`，例如 `~/.codex/skills/qimen-jiepan` 或 `~/.gemini/skills/qimen-jiepan`）。
2. 初始化 Skill 私有虚拟环境（不会修改系统 Python）：
   ```bash
   python qimen-jiepan-skill/scripts/setup_env.py
   ```
3. 命令行排盘示例：
   ```bash
   # 按当前时间起盘（JSON 输出）
   python qimen-jiepan-skill/scripts/qimen_cli.py chart --now --format json

   # 按指定时间起盘（文本输出，须包含时区偏移）
   python qimen-jiepan-skill/scripts/qimen_cli.py chart --datetime 2026-11-26T22:00:00+08:00 --format text
   ```

可选参数：`--timezone`、`--longitude`、`--latitude`、`--time-mode true_solar_time`、`--day-boundary zi_start`、`--horse-basis day`。

## 默认规则

- **排盘**：拆补法时家转盘（`chai_bu_v1.0.0`），中五寄坤二，天禽随天芮。
- **时间**：默认 `Asia/Shanghai` 标准时、午夜换日、时支马星；支持显式切换近似真太阳时、子初换日与日支马星。

历史变更见 [CHANGELOG.md](CHANGELOG.md)。
