<div align="center">
  <img src="./assets/easymeta-hero-handdrawn-white.png" alt="EasyMeta hand-drawn meta-analysis workflow hero" width="1200" />

  <h1>EasyMeta</h1>

  <a href="./easymeta/SKILL.md"><img alt="Skill: EasyMeta" src="https://img.shields.io/badge/SKILL-EasyMeta-2563EB?style=flat-square" /></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0F766E?style=flat-square" /></a>
  <img alt="Tests: P0 5/5, P1 31/31" src="https://img.shields.io/badge/tests-P0%205%2F5%20%7C%20P1%2031%2F31-16A34A?style=flat-square" />

  **让 Meta 分析更易执行，但不降低方法标准。**

  面向医学、公共卫生、生态学、环境科学与生物多样性研究的可审计 Meta 分析 Skill。
</div>

## EasyMeta 做什么

EasyMeta 把系统综述与 Meta 分析组织成一条可复核的科学工作流：从问题与 estimand、检索和筛选、数据提取与效应量，到依赖结构、异质性、偏倚、确定性评价、R 分析和报告。它不以“成功跑出一个合并值”为目标；证据不可比、协方差不明或模型能力不足时，会明确停止、改走专项路线或建议不合并。

- 医学路线：干预、诊断、患病率、预后、病因和伤害结局。
- 生态路线：植物生态、生物多样性、群落组成、恢复、多功能性及系统发育结构。
- 统计路线：共同效应、随机效应、多层/多变量模型、CR2、Meta 回归和专科模型。
- 审计路线：研究—报告映射、双人提取核对、风险偏倚、证据确定性、来源版本和字段级 lineage。
- 可复现执行：Python 校验器、R 命令行分析器、CSV/JSON/YAML 合同和端到端回归测试。

## 核心原则

EasyMeta 会主动拦截一些“软件能运行、方法却不成立”的分析：

- 不把同一研究的多个效应量假设为独立。
- 不合并一个仅叫作“biodiversity”的含糊结局。
- 不混淆抽样协方差 `V`、真实效应随机结构和稳健系数推断。
- 不根据异质性检验的 P 值选择固定效应或随机效应模型。
- 不用漏斗图、Egger 检验或单一选择模型给出二元“发表偏倚存在/不存在”结论。
- 不把高影响力论文中的模型当作通用默认设置。
- 不把风险偏倚、证据确定性、综述可靠性和报告完整性压成一个质量总分。

## 快速安装

克隆仓库后，把 `easymeta/` 子目录复制到 Codex 的 Skill 目录。

PowerShell：

```powershell
gh repo clone Rimagination/easymeta "$HOME\easymeta"
Copy-Item -LiteralPath "$HOME\easymeta\easymeta" `
  -Destination "$HOME\.codex\skills\easymeta" -Recurse
```

Bash：

```bash
git clone https://github.com/Rimagination/easymeta.git ~/easymeta
cp -R ~/easymeta/easymeta ~/.codex/skills/easymeta
```

重启 Codex 后，直接调用：

```text
Use $easymeta to design a preregistered meta-analysis protocol for this question.

用 $easymeta 检查这些效应量能否合并，并为重复结局建立依赖结构。

用 $easymeta 审计这篇植物多样性 Meta 分析的 estimand、空间尺度和统计模型。
```

## 工作结构

```text
easymeta/
├── SKILL.md                 # 核心路由、硬规则与执行流程
├── agents/openai.yaml       # Codex 展示与默认提示
├── assets/                  # 分析计划、提取表和机器可读合同
├── references/              # 医学、生态、模型、报告和来源方法库
├── scripts/                 # Python 校验器与 R 分析器
└── tests/                   # 合同、P0 与 P1 端到端测试
```

普通 `yi/vi` 分析只有在路由器批准并声明独立抽样簇后才能运行。群落组成、多维生物多样性、复杂恢复轨迹等问题会进入专项路线；当前没有可靠自动计算器的路线会停止并说明需要什么，而不会伪装成已实现。

## 运行测试

基础合同测试只需要 Python 3.10+：

```bash
python easymeta/tests/run_contract_tests.py
```

完整测试还需要 R、`metafor` 和 `clubSandwich`。若 `Rscript` 不在 `PATH`，设置 `R_SCRIPT`；若 R 包安装在自定义库，设置 `META_TEST_R_LIBRARY`：

```powershell
$env:R_SCRIPT = 'path\to\Rscript.exe'
$env:META_TEST_R_LIBRARY = 'path\to\R-library'
python easymeta/tests/run_all_tests.py
```

当前版本通过 P0-1 至 P0-5 全部测试及 31 个 P1 端到端案例；发布前验证环境使用 R 4.5.3、`metafor 5.0.1` 和 `clubSandwich 2.0.0`。

## 方法来源与边界

EasyMeta 蒸馏 Cochrane、PRISMA、JBI、GRADE、CEE、ROSES、PRISMA-EcoEvo、MATES、CEESAT、`metafor` 官方资料及医学与生态学方法研究。来源、版本、访问日期和替代状态记录在 [source-registry.md](./easymeta/references/source-registry.md)。项目只保留方法规则、字段和测试，不复制受版权保护的完整手册或专有检查表。

EasyMeta 是研究工作流工具，不提供个人医疗诊断或治疗建议。纳入排除、数据提取、风险偏倚、生态解释和所有 AI 生成内容仍需具备相应专业能力的人类复核。

## 许可

代码与原创文档采用 [MIT License](./LICENSE) 发布。第三方标准、论文和工具名称仍归各自权利人所有；引用与使用应遵守原始来源的许可和条款。
