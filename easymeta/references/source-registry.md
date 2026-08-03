# 方法来源登记与治理

**登记快照日期：2026-08-03。** 本登记用于确定“什么要求来自哪里、何时复查、可以怎样蒸馏”，不是官方文件的替代品。开始新协议、重大方法变更和投稿前都应回到官方原文确认当前版本。

## 1. 来源类型与优先级

| 类型 | 用途 | 权威边界 |
|---|---|---|
| `规范` | 报告清单、最低实施/报告标准、立场或政策 | 约束“必须披露/达到什么”；报告规范不能单独证明实施质量 |
| `教材/方法手册` | 解释如何设计、实施和解释证据综合 | 为方法选择提供默认路径；须结合问题、设计和更新版本 |
| `评价工具/框架` | 评价研究、综述 conduct 或报告完整性 | 必须固定评价对象；不同层级不能互换或相加为总分 |
| `软件文档` | 说明命令、参数、默认值、版本行为和文件格式 | 证明软件做了什么，不证明该方法对当前问题合适 |

冲突时按以下顺序处理：适用的法律/伦理/监管要求 > 明确适用的最低实施标准与投稿硬要求 > 已注册协议 > 方法手册 > 软件默认值。若协议与更高层要求冲突，保留原协议并通过修订或偏离日志解释改变及影响，不回写历史；一般性新建议则先做影响评估，不因“更新”自动改写进行中的项目。

## 2. 核心登记

### 2.1 规范

| ID | 官方来源与版本 | 本技能采用的范围 | 更新信号与复查频率 | 版权/蒸馏状态 |
|---|---|---|---|---|
| `CEE-STD-5.1` | [CEE Guidelines and Standards for Evidence Synthesis in Environmental Management, v5.1](https://environmentalevidence.org/information-for-authors/guidelines-for-authors/)；[Summary of Standards](https://environmentalevidence.org/standards-table/) | 环境证据的问题、协议、检索、筛选、提取、评价、合成和报告最低要求 | CEE 是持续更新网页；每个新协议、投稿前和每季度查 [Updates and Corrections](https://environmentalevidence.org/information-for-authors/updates-and-corrections/) | CEE 网页版权；仅保留短标题、条款编号和实质性转述，不复制整表/整章 |
| `CEE-SYNTHESIS-LIVING` | [CEE Section 8: Data synthesis](https://environmentalevidence.org/information-for-authors/8-data-synthesis/)；2026-01-27 更新 8.2.2 | 定量/叙述综合、依赖、异质性、调节变量和缺失证据 | 每次分析计划与投稿前查更新页；把固定研究数阈值和网页措辞作为需情境化判断的最低提示，不覆盖独立簇、参数数、杠杆和有效自由度 | 只蒸馏原则；若网页示例、术语或错误与统计原理/后续方法证据冲突，记录差异并采用有依据的保守规则 |
| `CEE-PUBBIAS-LIVING` | [CEE Section 8.2.2 and update record](https://environmentalevidence.org/information-for-authors/updates-and-corrections/)；section last updated 2026-01-27 | 环境证据中的 missing evidence 与 small-study-effect 报告更新 | 每次缺失证据计划、分析锁定和投稿前记录 section URL、更新时间、当前/前一快照哈希、change summary、impact class、adoption decision 和 protocol deviation ID | 不照搬固定研究数或二元偏倚结论；与 Nakagawa 2022 的依赖感知方法共同蒸馏 |
| `CEE-AI-LIVING` | [CEE Artificial Intelligence Reporting Guidance](https://environmentalevidence.org/artificial-intelligence-reporting-guidance/)；2025-12-14 加入 CEE 3.2，官方称 living document | 逐 AI 系统记录身份、用途、参数、协议偏离、验证、人机一致性、限制/纠错、提示词、代码、伦理隐私、资金与冲突 | 每次计划或实际使用 AI 前、报告冻结前和每季度复查；保存访问日期与页面快照/哈希（许可范围内） | 逐点蒸馏为自有字段；不复制官方整段模板。精确提示词要求不授权再分发提示中嵌入的受限原文 |
| `AI-POSITION-2025` | [Position statement on AI use across Cochrane, Campbell, JBI and CEE (2025)](https://doi.org/10.1186/s13750-025-00374-5) | 人类最终责任、方法严谨性、判断性 AI 的透明报告 | 每年及上述组织发布替代立场时复查 | 开放论文仍以概括和短引为主；保留 DOI 与版本 |
| `PRISMA-2020` | [PRISMA 2020 statement、清单与扩展清单](https://www.prisma-statement.org/prisma-2020)；[流程图](https://www.prisma-statement.org/prisma-2020-flow-diagram) | 健康及一般系统综述的完整报告、流程计数和公开材料 | 每个报告启动与投稿前检查官网；至少每年复查扩展与勘误 | 官方清单/流程图标明 CC BY 4.0；复用时署名并指明是否改编。本技能只蒸馏，不冒充官方清单 |
| `PRISMA-S-2021` | [PRISMA-S: literature-search reporting extension](https://www.prisma-statement.org/prisma-search) | 数据库/平台、逐字策略、日期、限制、补充检索与同行评审的报告 | 每次检索计划和投稿前；至少每年检查 FAQ/更新 | 引用官方页面和 DOI；不复制完整 16 项清单 |
| `PRISMA-DTA-LIVING` | [PRISMA-DTA official extension page](https://www.prisma-statement.org/dta) | 诊断准确性系统综述的报告扩展与当前正式材料定位 | 每个 DTA 报告冻结与投稿前检查扩展页、勘误和替代状态 | 报告规范，不替代 Cochrane DTA conduct 手册或 QUADAS-3；只保存版本、定位和自有映射 |
| `ROSES` | [ROSES reporting standards](https://www.roses-reporting.com/)；[forms](https://www.roses-reporting.com/forms) | 环境系统综述和系统地图的报告与流程图 | 环境项目协议和投稿前检查；每年复查 | 官方 forms 页面标示表单为 CC BY 4.0；复用时署名并标注改编，不把整个网站默认视为同一许可 |
| `PRISMA-ECOEVO-1.0` | [PRISMA-EcoEvo official page](https://www.prisma-statement.org/ecoevo)；[O'Dea et al. 2021](https://doi.org/10.1111/brv.12721)；[OSF updates](https://doi.org/10.17605/OSF.IO/GB5VX) | 生态与进化系统综述和 Meta 分析的 27 项报告扩展 | 截至 2026-08-03 为 v1.0；投稿前检查官方页、OSF 与勘误 | 报告规范，不是 conduct、偏倚或 certainty 工具；保存实际清单版本和页码映射 |

### 2.2 教材/方法手册

| ID | 官方来源与版本 | 本技能采用的范围 | 更新信号与复查频率 | 版权/蒸馏状态 |
|---|---|---|---|---|
| `COCHRANE-HB-6.5` | [Cochrane Handbook for Systematic Reviews of Interventions, v6.5 (2024)](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current)；重点 [Chapter 4](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04)、[Chapter 5](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05)、[Chapter 10](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10) | 检索/双人筛选、研究与报告区分、双人结局提取、效应量、依赖与荟萃分析 | `current` 页面可能换版；每个健康项目启动、模型定稿和投稿前检查，至少每年一次 | Cochrane 版权；记录章节和更新时间，转述方法，不复制长表、图或整章 |
| `COCHRANE-DTA-HB-2.0` | [Cochrane Handbook for Systematic Reviews of Diagnostic Test Accuracy, v2.0 (2023)](https://www.cochrane.org/authors/handbooks-and-manuals/handbook-systematic-reviews-diagnostic-test-accuracy) | DTA 问题、2×2 数据、阈值、双变量/HSROC 综合与解释边界 | 每个 DTA 项目启动、分析锁定和投稿前核对版本；偏倚工具另查 QUADAS 当前页 | Cochrane 版权；仅蒸馏方法和章节导航，不复制整章或工具 |
| `JBI-MANUAL-2024` | [JBI Manual for Evidence Synthesis 在线版](https://synthesismanual.jbi.global)；[2024 edition 公告](https://jbi.global/news/article/jbi-updates-methodological-guidance-0)；[2024 PDF](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true) | 多类型健康证据综合；协议、两人独立评价/提取、争议解决、缺失与转换计划 | 在线章节可能先于 PDF 更新；每个项目选型与投稿前、每 6 个月检查在线手册和 “What’s New” | JBI 版权；只提炼流程，表格/评价工具从官方获取，不在技能中重印 |
| `CEE-METHODS-5.1` | [CEE online methods sections](https://environmentalevidence.org/information-for-authors/guidelines-for-authors/) | 环境证据的检索测试集、灰色文献、筛选、数据编码、有效性评价、定量/叙述合成 | 与 `CEE-STD-5.1` 同步；章节页显示更新时立即复核相关模块 | 按页保存标题、URL、版本/更新时间和自有摘要；不镜像全文 |
| `INTRO-META-2E` | [Borenstein, Hedges, Higgins & Rothstein, *Introduction to Meta-Analysis*, 2nd ed.](https://www.wiley-vch.de/en/areas-interest/mathematics-statistics/statistics-16st/biostatistics-16st3/introduction-to-meta-analysis-978-1-119-55835-4) | 通用效应量、异质性、模型选择、常见错误和发表偏倚的概念解释 | 新版或勘误发布时复查；不以本书替代领域规范 | 商业教材；仅保存书目信息、章节定位和自有摘要，不复制章节或习题 |
| `ECO-META-HB-2013` | [Koricheva, Gurevitch & Mengersen (eds.), *Handbook of Meta-analysis in Ecology and Evolution*](https://academic.oup.com/princeton-scholarship-online/book/27898) | 生态与进化问题构建、效应量、依赖、频率学派与贝叶斯方法、领域实例 | 新版或领域共识变化时复查；统计建议需与当前 CEE/软件文档交叉核对 | 商业教材；仅蒸馏方法原则和章节导航，不再分发受限正文 |
| `NAKAGAWA-QES-2023` | [Nakagawa et al., *Quantitative evidence synthesis*](https://pmc.ncbi.nlm.nih.gov/articles/PMC11378872/)；[R tutorial](https://itchyshin.github.io/Meta-analysis_tutorial/) | 环境 Meta 的多层/多变量模型、依赖、异质性、尺度、空间/系统发育和高级综合 | 静态 CC BY 4.0 方法论文；教程、代码和软件依赖另行冻结 | 可在署名和标明改编条件下蒸馏；本技能使用自有表述和验证代码 |
| `PLANT-MISUSE-2014` | [Koricheva & Gurevitch, *Uses and misuses of meta-analysis in plant ecology*](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/1365-2745.12224) | 植物生态检索、依赖、效应量、敏感性与报告质量门 | 静态综述；方法建议与当前 CEE/软件文档交叉核对 | 链接并转述结论，不复制受版权保护的图表或长段 |
| `FOREST-BIODIV-2017` | [Spake & Doncaster, forest biodiversity meta-analysis challenges](https://www.sciencedirect.com/science/article/pii/S0378112717303778)；[author manuscript](https://eprints.soton.ac.uk/411631/2/1_s2.0_S0378112717303778_main.pdf) | 森林参照、伪重复、丰富度/物种密度、尺度、SMD 与权重问题 | 静态方法综述；森林项目立项和分析冻结前复核 | 优先使用作者版阅读；只蒸馏方法原则 |
| `ECO-PUBBIAS-2022` | [Nakagawa et al., publication-bias methods](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.13724) | 高异质性和非独立生态 Meta 的小研究效应、残差漏斗和敏感性 | 静态开放方法论文；检查后续模拟与勘误 | 不把任何单一检验蒸馏为二元裁决器 |
| `DEPENDENT-ES-2025` | [Williams et al., dependent effect sizes simulation study](https://doi.org/10.1111/2041-210X.70156) | 多层模型、采样 VCV、CRVE 与 study × species/phylogeny 交叉依赖的比较 | 静态模拟研究；仅在其研究数、物种数、效应数、相关结构和分布假设范围内解释 | 蒸馏为三层依赖契约和 CRVE 边界，不把模拟优胜方法升级为所有数据的唯一默认 |
| `PHYLO-MLMA-2022` | [Cinar et al., phylogenetic multilevel meta-analysis](https://doi.org/10.1111/2041-210X.13760) | 同时区分系统发育相关和非系统发育 species 方差 | 静态方法/模拟论文；使用前检查勘误和软件实现 | 默认候选同时含 phylogeny 与 species IID；只因不可识别、设计理由或预设敏感性简化，不按显著性删项 |
| `CHE-CRVE-2022` | [Pustejovsky & Tipton, correlated and hierarchical effects with CRVE](https://doi.org/10.1007/s11121-021-01246-3) | 相关—层级效应工作模型、CR2 和小样本自由度 | 静态方法论文；每次实现核对软件版本和校正类型 | CRVE 保护系数推断，不修复错误效应、错误簇、错误均值模型或不可解释方差分量 |
| `HETEROGENEITY-2025` | [Yang et al., pluralistic heterogeneity reporting](https://doi.org/10.1111/2041-210X.70155) | 平均抽样方差、各层方差分量、总/分层 I²、原尺度异质性与 prediction interval | 静态方法论文；检查后续实现和勘误 | 不以单一 I² 或通用阈值代表异质性；均值接近零时慎用 CV/M 等均值缩放量 |
| `BIODIV-SCALE-2021` | [Spake et al., scale dependence of biodiversity responses](https://doi.org/10.1111/ele.13641) | grain、extent、采样单元数、物种密度/总丰富度和采样完整度 | 静态方法/实证研究；尺度结论仅用于其适用结局 | 蒸馏为必填尺度字段和不可合并门；其 lnRR/渐近丰富度表现不作为所有生物多样性结局默认 |
| `HILL-DIVERSITY-2021` | [Chao et al., Hill-number diversity framework](https://doi.org/10.1111/2041-210X.13682) | q=0/1/2 下分类、系统发育、功能 α 多样性和 coverage standardization | 静态方法论文；使用校正版并检查勘误 | Shannon 转有效种数只在构念一致时使用；不把 α 公式套给 β/组成变化或任意 Meta 效应 |
| `MULTIFUNCTION-2023` | [Byrnes, Roger & Bagchi, Hill-number multifunctionality](https://doi.org/10.1111/oik.09402) | 将函数数目、平衡性和平均功能拆分的多功能性候选度量 | 静态方法论文；属于提议性框架，需与其他度量并列敏感性 | 不把单一多功能性指数当共识金标准；保留每个函数的方向、单位、标准化、参照和权重 |
| `INTERACTION-2021` | [Duncan & Kefford, scale-dependent interactions](https://doi.org/10.1111/2041-210X.13714) | 多胁迫/析因实验的加法与乘法交互、非线性和混杂 | 静态方法论文；使用前检查其 corrigendum | 蒸馏为四单元对比和效应尺度预注册；禁止以显著性差异代替交互检验 |
| `RESTORATION-2026` | [Gann et al., International principles and standards for ecological restoration, third edition](https://doi.org/10.1111/rec.70441) | 参考模型、restorative continuum、恢复目标与过程维度 | 2026 静态标准论文；后续勘误/新版发布时复核 | 五星框架用于实践目标/进展语境，不作为连续效应量、研究质量分或 certainty 总分 |
| `SYNTHESIS-NATURE-2018` | [Gurevitch et al., *Meta-analysis and the science of research synthesis*](https://www.nature.com/articles/nature25753) | 研究综合的总体原理、局限和跨学科边界 | 静态综述；与领域指南共同使用 | 只保存书目信息与自有摘要 |
| `CEE-TRAINING` | [CEE systematic review and map training](https://systematicreviewmethods.github.io/) | 可直接访问的协议、检索、筛选和环境证据综合教学 | 课程可更新；每次使用记录访问日 | 标示 CC BY-NC-ND 4.0；可学习和链接，不把内容改编为技能资产 |
| `MAEDR` | [Meta-analysis of Ecological Data in R](https://bookdown.org/robcrystalornelas/meta-analysis_of_ecological_data/) | 生态数据 Meta 的开放 R 学习材料和实现提示 | 在线 bookdown；代码运行前核对包版本 | 教学辅助而非权威规范；许可证逐页核对，不以其覆盖正式指南 |
| `DOING-META-R-2021` | [Harrer, Cuijpers, Furukawa & Ebert, *Doing Meta-Analysis with R*](https://doing-meta.guide/) | 可直接访问的 R 入门与进阶实例，包括异质性、Meta 回归、多层和贝叶斯方法 | 使用代码前检查在线版、仓库和所用包版本 | 可访问不等于任意转载；保留作者引用，优先链接并重写为本技能的保守工作流 |
| `META-WITH-R-2015` | [Schwarzer, Carpenter & Rücker, *Meta-Analysis with R*](https://link.springer.com/book/10.1007/978-3-319-21416-0) | `meta`/相关方法、二分类结局、异质性、缺失数据、诊断与网络 Meta 分析 | 新版、勘误或配套包大版本变化时复查 | 商业教材；仅记录书目、方法定位和自行验证的实现差异 |

### 2.3 评价工具与评价框架

| ID | 官方来源与版本 | 本技能采用的范围 | 更新信号与复查频率 | 版权/蒸馏状态 |
|---|---|---|---|---|
| `CEESAT-2.2` | [CEESAT v2.2, updated 17 May 2026](https://environmentalevidence.org/wp-content/uploads/2026/06/CEESAT-Reviews-Version-2.2-updated-170526.pdf)；[official version page](https://environmentalevidence.org/ceeder/about-ceesat/) | 对既有 environmental evidence review 进行 question/hypothesis 级严谨性、透明度和局限评价；evidence overview 使用另一个工具 | CEE 发布新版或每年复查；每次评价记录目标问题、产品类型和检查材料 | 不复制题项；“未报告”不证明“未实施”；Gold/Green/Amber/Red 不求和、不平均为质量分 |
| `CEESAT-2.1-SUPERSEDED` | [CEESAT v2.1, updated 21 Aug 2025](https://environmentalevidence.org/wp-content/uploads/2025/08/CEESAT2-Reviews-Version-2.1-updated-210825.pdf) | 仅用于复现按 v2.1 完成的历史评价 | 已由 `CEESAT-2.2` 取代；不得用于新评价；历史项目保留原工具和迁移决定 | 历史版本登记，不复制题项，不静默覆盖旧评价 |
| `MATES-2026` | [Morrison et al. 2026](https://doi.org/10.1016/j.envint.2025.109935)；[repository](https://github.com/KyleMorrison99/MATES)；[Shiny app](https://kylemorrisonisshiny99.shinyapps.io/MATES_shiny/) | 环境 Meta 分析的 14 项报告完整性评价 | 论文、仓库和应用分别记录版本；默认评价论文中的第一个 Meta 分析；若改评其他模型，须预先定义客观选择规则并记录偏离 | 不评价 actual conduct、RoB、模型正确性或 certainty；复制题项前核实许可 |
| `FEAT-2022` | [Frampton et al. 2022](https://doi.org/10.1186/s13750-022-00264-0) | 用 Focused、Extensive、Applied、Transparent 原则选择或设计环境研究 critical-appraisal 方法 | 新建/修改评价工具时复核；静态开放论文 | 框架而非固定量表；不生成质量总分；复用图表/题项前核对具体许可 |
| `ROB2-LIVING` | [RoB 2 current-version page](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2) | 随机试验结果层面的偏倚评价及平行、整群、交叉变体路由 | 每个项目从 current page 获取对应变体并记录发布日期；不得只依赖旧 Excel 宏表 | 工具版权归开发组；不重印 signaling questions 或模板，只记录版本和判断依据 |
| `ROBINS-I-LIVING` | [ROBINS-I official pages](https://www.riskofbias.info/welcome/home) | 非随机干预研究的结果层面偏倚评价 | 每个项目确认 2016 正式版与 V2 状态；draft 不得静默替代正式版 | 不重印工具；不同版本的评价不得无记录混用 |
| `ROBINS-E-2024` | [ROBINS-E official page](https://www.riskofbias.info/welcome/robins-e-tool)；version 24 March 2024 | 非随机暴露效应研究偏倚，限工具声明的设计范围 | 每个暴露综述启动与评价前检查版本和设计适用性 | 不复制工具题项；病例对照、横断面等超出范围时另行路由 |
| `QUADAS-3-LIVING` | [QUADAS-3 official page](https://www.bristol.ac.uk/population-health-sciences/projects/quadas/quadas-3/) | 诊断准确性研究的 RoB 与适用性 | 每个 DTA 项目下载并记录官网 current version；若 DTA 手册仍指向旧工具，明确采用当前工具的理由 | 不重印完整题项；保留版本、支持原文定位和人工判断 |
| `GRADE-BOOK-LIVING` | [GRADE Book](https://book.gradepro.org/) | 关键结局层面的证据确定性、阈值、降级/升级与表达 | 每次 GRADE 前记录目标章节 last modified；新 Book 与旧 handbook 冲突时登记采用决定 | 只蒸馏原则，不复制整章或官方表格；GRADE 不生成研究质量总分 |
| `JBI-APPRAISAL-LIVING` | [JBI Critical Appraisal Tools](https://jbi.global/critical-appraisal-tools) | JBI 覆盖的观察性、患病率及其他设计评价工具路由 | 每个项目从 current tools 页面选择并记录工具版本，不用 2024 手册附录替代更新版 | 工具从官方获取；本技能不重印清单或自动作出最终判断 |

### 2.4 应用压力测试来源

这些论文用于检验路由、estimand、依赖和解释边界，不用于规定默认方法；“原论文做了什么”与“现代审计认为应做什么”必须分栏保存。

| ID | 应用来源 | 本技能压力测试 | 不可继承的默认 |
|---|---|---|---|
| `BENCH-NATURE-PLANT-2025` | [Chen et al., plant diversity effects on productivity](https://www.nature.com/articles/s41586-024-08407-8) | NBE、complementarity/selection、实验/时间/功能依赖和机制语言 | 不把分解项当独立效应，不因 Nature 发表而跳过方差与依赖审计 |
| `BENCH-NATURE-BIODIV-2025` | [Keck et al., global human impact on biodiversity](https://www.nature.com/articles/s41586-025-08752-2) | local diversity、homogeneity、composition shift 三个 estimand；空间距离对依赖；非加权与发表偏倚路线 | 不把未加权模型、平均每研究效应数或 fail-safe/P-curve 直接复制成通用规则 |
| `BENCH-NATURE-GENETIC-2025` | [Shaw et al., global genetic diversity loss](https://www.nature.com/articles/s41586-024-08458-x) | 时间单位、遗传指标/标记桥接、paper/species 多层依赖、极端值和观察性保护措施解释 | 不把高影响个案删除、弱信息先验或“未检出偏倚”当普遍安全证明 |

### 2.5 软件文档

| ID | 官方来源 | 本技能采用的范围 | 更新信号与复查频率 | 版权/蒸馏状态 |
|---|---|---|---|---|
| `PYTHON-CSV` | [Python Standard Library: csv](https://docs.python.org/3/library/csv.html) | `validate_extraction.py` 的 UTF-8 CSV 读取和字典行解析 | 修改校验器或升级 Python 次版本时；项目记录实际 `python --version` | PSF 官方文档；实现只依赖公开 API，不复制文档示例 |
| `PYTHON-ARGPARSE` | [Python Standard Library: argparse](https://docs.python.org/3/library/argparse.html) | 命令行帮助、参数和用法错误处理 | 与 Python 运行时同步；修改 CLI 时复查 | 同上 |
| `METAFOR-DOCS` | [metafor official documentation](https://wviechtb.github.io/metafor/) | R 中效应量计算、常规/多层模型、诊断和软件调用的候选实现 | 每次分析冻结前记录安装版本并查 NEWS/帮助页；升级包后重跑测试 | 软件文档只证明接口和默认值；方法合理性仍由手册、协议和统计审查决定 |
| `CLUBSANDWICH-DOCS` | [clubSandwich official documentation](https://jepusto.github.io/clubSandwich/) | CR2/cluster-robust coefficient inference and small-sample degrees of freedom used with fitted Meta models | 每次 CR2 分析冻结前记录安装版本并查 NEWS/reference；升级包后重跑测试 | 软件文档只证明接口、校正和输出行为；不能修复错误效应量、错误聚类或错误均值模型 |

软件条目是可选实现来源，不构成对单一软件的强制。项目若使用 RevMan、JBI SUMARI、CADIMA、其他 R/Python 包或 AI 平台，应按同一字段新增项目级登记：工具、开发者、版本、URL、访问日期、用途、默认值、许可证、更新信号和归档方式。

### 2.6 P0-6 机器路由关系

`assets/reference_routes.json` 是本登记的可执行子集：它只引用本页已登记的 `source_id`，并按产品、领域、阶段、决策点、数据层级、依赖来源和专项触发器选择最小必要集合。新增或改名 `source_id` 时，必须同时更新登记、机器路由和回归测试；机器路由中出现未登记 ID 或不存在的本地 reference 文件会使合同测试失败。

`reference_receipt.json` 绑定 canonical plan SHA-256，并要求本地文件 SHA-256、实际章节定位、决策映射、版本、访问日、里程碑和采用决定。哈希只能证明字节一致，回执只能证明留下了声明；两者都不能证明阅读者理解正确，也不能代替对 living official page 的人工或联网核验。

## 3. 更新巡检程序

1. 在协议立项、正式分析冻结和投稿前读取本登记。
2. 打开每个适用来源的官方版本页、更新/勘误页或 NEWS；不以搜索摘要代替原文。
3. 记录 `checked_at`、检查人、观察到的版本/更新时间、旧版本、差异及影响。
4. 将差异分类为：仅编辑、报告要求变化、实施要求变化、软件行为变化或法律/许可变化。
5. 对会改变纳入、数据或模型的更新，先做影响评估；已注册项目通过偏离/修订处理，不偷偷改协议。
6. 更新模板或脚本时增加模式版本，并对既有示例和边界案例重新测试。

建议项目级登记字段：

```text
source_id, source_type, title, owner, url, doi, version_used,
published_or_updated, accessed_at, applicable_stage, authority,
check_frequency, update_signal, license_or_copyright, distilled_claims,
verbatim_quote_location, reviewer, supersedes, impact_notes
```

## 4. 版权与蒸馏原则

1. **优先一手、最少必要。** 保存官方 URL、DOI、版本、章节定位和自己的方法摘要；搜索结果和二手教程只用于发现，不作为最终依据。
2. **转述要求，不复制作品。** 不把整章、完整清单、整表、图、评价工具或官方模板搬入技能。短引仅在原词不可替代时使用，并紧邻署名与定位。
3. **许可证逐项核对。** “可在线访问”不等于“可再分发”。CC BY 材料复用时署名、链接许可证并标注改编；无明确许可按版权所有处理。
4. **派生物不得冒充官方。** 本技能的 CSV、YAML、字段映射和中文摘要均标为工作模板，不使用“官方中文版/官方表格”等表述。
5. **版本可追溯。** 不用裸粘贴取代引用；保存访问日期和适用版本。网页滚动更新时，在许可允许的范围保存哈希或机构归档定位。
6. **受限输入不随提示词公开。** CEE 要求提供精确提示词；若提示包含全文、个人数据或机密材料，公开可复现包提供提示结构、引用、内容哈希和受控访问路径，完整内容仅在授权环境保存。
7. **软件默认值不是方法依据。** 软件文档可引用参数行为，但模型选择、偏倚处理和解释必须追溯到协议及方法来源。

## 5. 来源纳入检查

新增来源前确认：

- 是否为发布组织、作者/开发者或正式标准维护者的一手页面？
- 类型是规范、教材/方法手册还是软件文档？它能支持哪一类主张？
- 是否有版本、更新时间、勘误或替代关系？多久复查一次？
- 当前项目为何适用，和已有来源是否冲突？
- 可以公开哪些元数据、摘要、短引、表单或代码？署名和许可证要求是什么？
- 若网页消失或软件升级，审计者能否知道当时实际使用了什么？
