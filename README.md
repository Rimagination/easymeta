<p align="center">
  <img src="./assets/easymeta-hero-handdrawn-white.png" alt="EasyMeta" width="920">
</p>
<p align="center">
  <a href="#一分钟开始"><img alt="Input: studies and data" src="https://img.shields.io/badge/INPUT-STUDIES_%2B_DATA-25A9E0?style=for-the-badge&amp;labelColor=555555"></a>
  <a href="#结果长什么样"><img alt="Output: auditable synthesis" src="https://img.shields.io/badge/OUTPUT-AUDITABLE_SYNTHESIS-39A96B?style=for-the-badge&amp;labelColor=555555"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/LICENSE-MIT-FF6699?style=for-the-badge&amp;labelColor=555555"></a>
</p>

# EasyMeta

EasyMeta 是一个面向医学、公共卫生、生态学、环境科学和生物多样性研究的系统综述与 Meta 分析 skill。它会先冻结研究问题、estimand、纳入标准、效应量和依赖结构，再决定应该合并、转入专项模型、改做叙述综合，还是停止分析。

项目强调“让 Meta 分析更易执行，但不降低方法标准”。每个关键判断都尽量保留来源、假设、版本、偏离和验证记录；同一研究内的多个效应、共享对照、重复时间点、空间或系统发育相关性不会被默认为相互独立。结果适合用于协议设计、数据提取、统计分析、方法审计和论文报告，但仍需要领域专家作出最终判断。

## 一分钟开始

### 使用 Agent

先把仓库安装为 skill：

```text
请帮我安装这个 skill：
https://github.com/Rimagination/easymeta
```

然后提供研究问题、协议、论文或待分析数据：

```text
请用 EasyMeta 为这个研究问题设计系统综述和 Meta 分析方案。
先冻结问题、estimand、纳入标准、效应量和依赖结构；不满足合并条件时请明确停止。
```

已有提取表时，可以直接要求审计：

```text
请用 EasyMeta 检查这份提取表的研究—报告映射、效应量方向、抽样单位、
依赖结构和分析尺度，然后给出可执行的 R 分析与敏感性分析方案。
```

植物生态或生物多样性项目建议明确结局类型、空间尺度和数据层级：

```text
请用 EasyMeta 审计这个植物多样性 Meta 分析。
区分 alpha/beta/gamma/composition、分类/系统发育/功能维度、Hill q、
grain、extent、sampling unit，以及 observed/estimated diversity。
```

## 结果长什么样

EasyMeta 的结果不只有森林图。一个完整任务应保留同一条证据链：研究问题与协议 → 综合路由 → 研究—报告映射 → 原始提取 → 分析效应 → 模型与稳健性 → 评价与报告 → 字段级 lineage。

一次任务通常会从以下文件中选择最小必要集合；实际文件名可由项目定义：

| 文件或产物 | 用途 |
| --- | --- |
| `pending-route.json` | 保存任务领域/阶段、数据层级、专项触发器、匹配的资料规则、必读本地文件、必查 source ID 和 plan SHA-256；此时 `runner_allowed=false` |
| `reference-receipt.json` | 逐项记录实际读取的本地文件哈希与章节、对应决策、官方来源版本、访问日期、里程碑检查和采用决定 |
| `route.json` | 回执通过后保存最终综合路线与 `runner_allowed`；专项路线或不合并路线即使资料门通过也不会被普通 runner 放行 |
| `study-report-map.csv` | 区分研究与报告，记录多篇报告、样本重叠和无法消解的身份问题 |
| `raw-extraction.csv` | 保存逐字段原始提取值、页码或表图位置、单位、方向和提取者 |
| `analysis-effects.csv` | 保存经审计的 `yi`、`vi`、分析尺度、转换公式和独立抽样簇 |
| `V.csv` 与模型规格 | 显式记录抽样协方差、随机效应结构、稳健聚类变量及假设情景 |
| 模型结果与敏感性分析 | 保存合并效应、异质性、预测区间、影响诊断和逐独立簇删除结果 |
| appraisal 与 certainty 表 | 分开保存研究偏倚、证据确定性、综述可靠性和报告完整性判断 |
| `field-lineage.csv` | 把分析字段追溯到输入、脚本、版本、转换和 SHA-256 记录 |

仓库提供对应的 CSV、JSON 和 YAML 模板。模板是工作起点，不是自动生成科学判断的表单。

## 能做什么，什么时候停止

| 路线 | 当前范围 |
| --- | --- |
| 可直接执行 | 连续、二分类、比例结局的效应量计算；声明独立抽样簇后的共同效应、随机效应和多层 Meta 分析；预先指定的 Meta 回归、抽样 `V`、逐簇删除及有条件的 CR2/CRVE |
| 需要严格输入合同 | 配对/交叉、变化值、BACI、共享对照和群集调整后效应；每研究单阈值的诊断准确性；两阶段、过原点的线性剂量—反应；共同效应一致性网络；已验证系统发育相关矩阵 |
| 先路由或专项审计 | 群落矩阵、组成变化、多维生物多样性、尺度依赖、变异性、多功能性、析因交互、恢复轨迹、复杂时空相关和二阶综合；空间与时间结构目前只验证矩阵，不拟合模型 |
| 应当停止 | estimand 不明确、结局不可比、必要方差无法恢复、依赖无法识别，或当前实现不能支持所需模型 |

“需要严格输入合同”不表示 EasyMeta 已覆盖这些领域的全部模型。诊断路线不覆盖多阈值、SROC 或 AUC；网络路线不覆盖随机效应、不一致性、传递性或排序。专项路线没有可靠自动计算器时会停止并说明缺少什么，而不会把问题强行转换成普通 `yi/vi` 分析。

EasyMeta 还会主动拒绝以下做法：

- 不把同一研究的多个效应量假设为独立，也不把共享对照复制成额外信息。
- 不合并一个只叫作 “biodiversity” 的含糊结局。
- 不根据异质性检验的 P 值选择共同/固定效应或随机效应模型。
- 不用漏斗图、Egger 检验、trim-and-fill 或单一选择模型给出二元发表偏倚结论。
- 不把风险偏倚、证据确定性、综述可靠性和报告完整性相加为“质量总分”。
- 不因为 Nature、Science 或其他高影响力期刊使用了某个模型，就把它变成通用默认设置。
- 不替代纳入排除、数据提取、偏倚评价、临床解释或生态解释中的人工复核。
- 不提供个人医疗诊断或治疗建议。

## 它如何工作

1. **定义问题**：明确产品类型、PICO/PECO、estimand、结局、尺度、时间范围和决策语境。
2. **路由资料**：由 `task.domain`、`task.stage`、decision points、数据层级、依赖来源和专项触发器匹配 `reference_routes.json`，生成最小必读文件与 source ID 集合。
3. **验证阅读记录**：用 plan 哈希绑定回执，核对本地文件字节、章节定位、决策映射和 living guidance 的当次里程碑检查；未通过时普通 runner 保持关闭。
4. **建立证据集**：设计检索与筛选，关联研究和报告，完成双人提取、裁决与完整性检查。
5. **构造效应量**：统一方向、单位和分析尺度，记录转换、独立抽样簇、抽样协方差 `V` 和真实效应结构。
6. **分析与诊断**：路由适用模型，报告异质性、预测目标、影响点、缺失证据和敏感性分析。
7. **评价与报告**：分层记录风险偏倚、证据确定性、综述可靠性、报告完整性、来源版本和字段 lineage。

### 资料怎样抵达正确决策点

EasyMeta 不把书籍全文塞进 `SKILL.md`，也不要求每次读取全部资料。第一次运行路由器时，它按机器可读规则取并集并去重：普通医学分析只得到医学、效应量和 R 实现资料；诊断任务额外得到 Cochrane DTA、QUADAS-3 与专项模型资料；原始群落矩阵转向生态、生物多样性、Hill 数和尺度资料；共享对照则转向复杂设计、抽样协方差与依赖推断。回归测试同时断言无关医学或生态资料不会混入这些集合。

```powershell
# 1. 完成模板；task.as_of_date 写实际核验日期
python easymeta/scripts/route_synthesis.py plan.json --output pending-route.json

# 2. 按 pending-route.json 的最小集合阅读并填写回执
python easymeta/scripts/validate_reference_receipt.py pending-route.json reference-receipt.json

# 3. 同一 plan + 合格回执才可能放行普通 runner
python easymeta/scripts/route_synthesis.py plan.json `
  --reference-receipt reference-receipt.json --output route.json

# 普通 runner 本身也要求这份 passed route，不能只靠提示词放行
Rscript easymeta/scripts/run_meta_analysis.R --route-contract route.json ...
```

这个 gate 能证明的是：回执绑定了哪份 plan、哪些本地文件字节、哪些章节和哪些来源版本，并且 living source 在声明的日期/阶段被检查。它不能证明人或模型真正理解了资料，也不能自动证明官网内容确为最新；这些仍需人工复核，必要时联网核验。

仓库中的 Python 校验器和 R 分析器可以本地运行。通过 Agent 处理论文全文或未公开数据时，数据是否离开本机取决于所用 Agent、模型和连接器配置；请先确认版权、隐私、伦理与机构政策。

## 开发者使用

```powershell
git clone https://github.com/Rimagination/easymeta.git
cd easymeta
python easymeta/tests/run_contract_tests.py
```

完整测试还需要 R、[`metafor`](https://wviechtb.github.io/metafor/)、[`clubSandwich`](https://jepusto.github.io/clubSandwich/) 和用于核验 route contract 的 [`jsonlite`](https://cran.r-project.org/package=jsonlite)。如果 `Rscript` 不在 `PATH`，设置 `R_SCRIPT`；如果 R 包位于自定义库，设置 `META_TEST_R_LIBRARY`：

```powershell
$env:R_SCRIPT = 'path\to\Rscript.exe'
$env:META_TEST_R_LIBRARY = 'path\to\R-library'
python easymeta/tests/run_all_tests.py
```

当前版本覆盖 P0-1 至 P0-6，并保留 31 个 P1 端到端案例；P0-6 额外测试医学诊断、原始群落矩阵、共享对照、错误哈希、过期 living guidance 和路径穿越。本次验证环境使用 R 4.5.3、`metafor 5.0.1`、`clubSandwich 0.7.0` 和 `jsonlite 2.0.0`。这些测试证明代码和数据合同按预期工作，不构成对任意真实研究的科学有效性认证。

项目结构：

```text
easymeta/
├── SKILL.md                 # 核心路由、硬规则与执行流程
├── agents/openai.yaml       # Codex 展示与默认提示
├── assets/                  # 分析计划、资料路由/回执、提取表和机器可读合同
├── references/              # 医学、生态、模型、报告和来源方法库
├── scripts/                 # Python 校验器与 R 分析器
└── tests/                   # 合同、P0 与 P1 端到端测试
```

## 项目文档

- [`easymeta/SKILL.md`](easymeta/SKILL.md)：完整路由、硬规则和执行流程
- [`evidence-synthesis-core.md`](easymeta/references/evidence-synthesis-core.md)：系统综述共同基础
- [`medical-review.md`](easymeta/references/medical-review.md)：医学与公共卫生路线
- [`ecology-review.md`](easymeta/references/ecology-review.md)：生态、环境和系统地图路线
- [`effect-size-and-models.md`](easymeta/references/effect-size-and-models.md)：效应量、依赖、异质性和模型
- [`plant-biodiversity-specialist-routes.md`](easymeta/references/plant-biodiversity-specialist-routes.md)：植物与生物多样性专项路线
- [`source-registry.md`](easymeta/references/source-registry.md)：核心来源的版本、适用范围、许可和更新治理
- [`reference_routes.json`](easymeta/assets/reference_routes.json)：任务字段到最小必读文件、source ID 与 living-source 标记的机器路由
- [`reference_receipt_template.json`](easymeta/assets/reference_receipt_template.json)：绑定 plan、章节、决策与来源核验记录的 P0-6 回执模板

## 许可

代码与原创文档采用 [MIT License](LICENSE) 发布。第三方标准、论文、书籍和工具名称仍归各自权利人所有；EasyMeta 只保留必要的方法转述、字段设计和测试，不重新发布受版权保护的完整手册、清单、评价工具、图表或章节。

## 参考资料与方法依据

EasyMeta 不是把某一本书或某一篇论文改写成提示词，而是把不同层级的资料分别用于综述实施、报告、统计建模、评价和边界测试。以下列出直接影响当前设计的主要来源；核心来源的版本、访问日期、许可、替代关系和复查频率见 [`source-registry.md`](easymeta/references/source-registry.md)，GRADE、RoB 2、ROBINS 和 QUADAS 等专题来源还登记在 [`bias-and-certainty.md`](easymeta/references/bias-and-certainty.md)，其他细化依据位于相应专题文档末尾。

### 系统综述实施与报告

- [Cochrane Handbook for Systematic Reviews of Interventions, v6.5 (2024)](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current)：健康干预综述的范围、检索、提取、效应量、综合、偏倚和解释。
- [JBI Manual for Evidence Synthesis](https://synthesismanual.jbi.global/)（在线版与 2024 edition）：多类型健康证据综合、协议、双人评价与提取。
- [Cochrane Handbook for Systematic Reviews of Diagnostic Test Accuracy, v2.0 (2023)](https://www.cochrane.org/authors/handbooks-and-manuals/handbook-systematic-reviews-diagnostic-test-accuracy)：诊断准确性综述的问题、数据、偏倚和综合方法。
- [CEE Guidelines and Standards for Evidence Synthesis in Environmental Management, v5.1](https://environmentalevidence.org/information-for-authors/guidelines-for-authors/)：环境系统综述与系统地图的实施标准；网页更新按 living guidance 管理。
- [PRISMA 2020](https://www.prisma-statement.org/prisma-2020) 与 [PRISMA-S](https://www.prisma-statement.org/prisma-search)：系统综述及检索过程的透明报告。
- [ROSES 1.0](https://www.roses-reporting.com/) 与 [PRISMA-EcoEvo](https://www.prisma-statement.org/ecoevo)：环境、生态与进化证据综合的报告要求。

### Meta 分析、依赖与 R 实现

- Borenstein, Hedges, Higgins & Rothstein, [*Introduction to Meta-Analysis*, 2nd ed.](https://www.wiley-vch.de/en/areas-interest/mathematics-statistics/statistics-16st/biostatistics-16st3/introduction-to-meta-analysis-978-1-119-55835-4)：通用效应量、异质性、模型和常见误用。
- Koricheva, Gurevitch & Mengersen (eds.), [*Handbook of Meta-analysis in Ecology and Evolution*](https://academic.oup.com/princeton-scholarship-online/book/27898)：生态与进化 Meta 分析的方法基础。
- Gurevitch et al. (2018), [*Meta-analysis and the science of research synthesis*](https://www.nature.com/articles/nature25753)：跨学科研究综合的原则与局限。
- Nakagawa et al. (2023), [*Quantitative evidence synthesis: a practical guide on meta-analysis, meta-regression, and publication bias*](https://doi.org/10.1186/s13750-023-00301-6)：生态 Meta 的多层、多变量、依赖和高级综合。
- Hedges, Gurevitch & Curtis (1999), [response ratio 方法](https://doi.org/10.1890/0012-9658%281999%29080%5B1150%3ATMAORR%5D2.0.CO%3B2)，以及 Lajeunesse 关于[相关与多组 response ratio](https://doi.org/10.1890/11-0423.1)和[小样本偏倚校正](https://doi.org/10.1890/14-2402.1)的研究：生态效应量及其抽样方差。
- Pustejovsky & Tipton (2022), [correlated and hierarchical effects with CRVE](https://doi.org/10.1007/s11121-021-01246-3)：CR2、小样本自由度和相关—层级效应工作模型。
- Nakagawa et al. (2022), [publication-bias methods for ecology and evolution](https://doi.org/10.1111/2041-210X.13724)：高异质性和非独立证据中的小研究效应与敏感性分析。
- Williams et al. (2025), [dependent effect sizes simulation study](https://doi.org/10.1111/2041-210X.70156)，以及 Yang et al. (2025), [pluralistic heterogeneity reporting](https://doi.org/10.1111/2041-210X.70155)：依赖结构、方差分量和多视角异质性报告。
- [`metafor` 官方文档](https://wviechtb.github.io/metafor/) 与 Harrer et al., [*Doing Meta-Analysis with R*](https://doing-meta.guide/)：R 实现与可复现示例；软件默认值不作为方法选择依据。

### 植物生态、生物多样性与恢复

- Koricheva & Gurevitch (2014), [*Uses and misuses of meta-analysis in plant ecology*](https://doi.org/10.1111/1365-2745.12224)：植物生态中的检索、独立性、效应量与敏感性问题。
- Spake & Doncaster (2017), [forest biodiversity Meta-analysis challenges](https://www.sciencedirect.com/science/article/pii/S0378112717303778)：森林参照、伪重复、物种密度、尺度与权重。
- Spake et al. (2021), [scale dependence of biodiversity responses](https://doi.org/10.1111/ele.13641)：grain、extent、采样单元、丰富度和采样完整度。
- Chao et al. (2021), [Hill-number diversity framework](https://doi.org/10.1111/2041-210X.13682)：分类、系统发育与功能多样性的 Hill 数和 coverage standardization。
- Cinar et al. (2022), [phylogenetic multilevel meta-analysis](https://doi.org/10.1111/2041-210X.13760)：系统发育相关与非系统发育物种方差的区分。
- Duncan & Kefford (2021), [scale-dependent interactions](https://doi.org/10.1111/2041-210X.13714)：多胁迫和析因设计中的交互 estimand。
- Byrnes, Roger & Bagchi (2023), [Hill-number multifunctionality](https://doi.org/10.1111/oik.09402)：生态系统多功能性的候选构造及其敏感性边界。
- Gann et al. (2026), [*International principles and standards for ecological restoration*, 3rd ed.](https://doi.org/10.1111/rec.70441)：参考模型、恢复目标和过程语境。

### 偏倚、确定性、综述评价与 AI

- [RoB 2](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2)、[ROBINS-I / ROBINS-E](https://www.riskofbias.info/welcome/home)、[QUADAS-3](https://www.bristol.ac.uk/population-health-sciences/projects/quadas/quadas-3/) 与 [JBI Critical Appraisal Tools](https://jbi.global/critical-appraisal-tools)：按研究设计选择结果层面的偏倚评价工具。
- [GRADE Book](https://book.gradepro.org/) 与 [Cochrane Handbook Chapter 14](https://training.cochrane.org/handbook/current/chapter-14)：按关键结局评价证据确定性，而不是生成研究质量总分。
- [CEESAT](https://environmentalevidence.org/ceeder/about-ceesat/)、[MATES](https://doi.org/10.1016/j.envint.2025.109935) 与 [FEAT](https://doi.org/10.1186/s13750-022-00264-0)：分别用于环境综述可靠性、Meta 分析报告完整性和 critical-appraisal 方法设计；三者不能互换。
- [Cochrane、Campbell、JBI 与 CEE 的 AI 使用立场声明（2025）](https://doi.org/10.1186/s13750-025-00374-5)及 [CEE AI reporting guidance](https://environmentalevidence.org/artificial-intelligence-reporting-guidance/)：人类责任、验证、提示词、参数、错误、隐私与协议偏离记录。

### 应用压力测试论文

[`plant-biodiversity-benchmark-casebook.md`](easymeta/references/plant-biodiversity-benchmark-casebook.md) 收录 19 篇植物生态与生物多样性代表性研究，用于检验 EasyMeta 能否重建真实高影响研究中的 estimand、尺度、依赖结构和解释边界。casebook 是方法路由与边界测试，不等同于逐篇下载数据、重跑模型或复现论文结果，也不构成通用方法规范。

其中已进入核心来源登记的三篇 Nature 压力测试论文是：

- Chen et al. (2025), [plant diversity effects on productivity](https://www.nature.com/articles/s41586-024-08407-8)
- Keck et al. (2025), [global human impact on biodiversity](https://www.nature.com/articles/s41586-025-08752-2)
- Shaw et al. (2025), [global genetic diversity loss](https://www.nature.com/articles/s41586-024-08458-x)

对这些论文，EasyMeta 分开记录“原论文实际采用的方法”和“按当前资料进行的方法审计”，不会因为发表期刊或影响力而继承其默认设置。
