# 环境证据综合报告：CEE、ROSES 与 PRISMA-EcoEvo

本文件把核心材料分工为：CEE 管 conduct 与最低报告标准，ROSES 管环境系统综述/系统地图的协议与报告透明度，PRISMA-EcoEvo 补足生态与进化 Meta 分析的定量报告，CEESAT 用可获得的 conduct/reporting/limitations 证据评价既有环境综述的 review-level reliability，MATES 评价 Meta 报告完整性。完成清单不等于方法正确；必须先按适用的 conduct 指南完成工作，再用报告或评价工具审计对应层级。

## 目录

- [1. 框架路由与权威顺序](#1-框架路由与权威顺序)
- [2. 建立版本冻结与追踪表](#2-建立版本冻结与追踪表)
- [3. 按 CEE 报告 conduct](#3-按-cee-报告-conduct)
- [4. 选择并执行 ROSES](#4-选择并执行-roses)
- [5. 执行 PRISMA-EcoEvo 定量审计](#5-执行-prisma-ecoevo-定量审计)
- [5.1 评价既有环境证据综合：CEESAT 与 MATES](#51-评价既有环境证据综合ceesat-与-mates)
- [6. 区分系统地图与系统综述的交付包](#6-区分系统地图与系统综述的交付包)
- [7. 保证流程计数与研究身份一致](#7-保证流程计数与研究身份一致)
- [8. 报告依赖、异质性和外推](#8-报告依赖异质性和外推)
- [9. 最终审计清单](#9-最终审计清单)
- [10. Living guideline 更新策略](#10-living-guideline-更新策略)
- [11. 来源登记](#11-来源登记)

## 1. 框架路由与权威顺序

| 产品/领域 | 必用主框架 | 补充框架 | 不要这样用 |
|---|---|---|---|
| 环境系统地图协议 | CEE v5.1 conduct + ROSES map protocol form | CEE map database/visualisation standards | 用 PRISMA-EcoEvo 代替地图专用表 |
| 环境系统地图报告 | CEE v5.1 + ROSES map report form/flow diagram | 按期刊要求附机器可读数据库 | 把地图空白写成无效应结论 |
| 环境系统综述协议 | CEE v5.1 conduct + ROSES review protocol form | 若计划 Meta 分析，提前映射 PRISMA-EcoEvo 10–18 | 把 ROSES 当作 protocol registration |
| 环境系统综述，无 Meta | CEE v5.1 + ROSES review report | 结构化叙述综合；选用适用的 PRISMA-EcoEvo 条目 | 用显著性投票替代综合 |
| 生态/进化系统综述 + Meta | CEE v5.1 + ROSES review report + PRISMA-EcoEvo v1.0 | PRISMA 2020/期刊要求可并列 | 只交 PRISMA 流程图而不交 ROSES 表 |
| 非环境管理的生态/进化 Meta | PRISMA-EcoEvo v1.0 | CEE conduct 作为高标准参考 | 声称 PRISMA-EcoEvo 是 conduct 或偏倚工具 |
| 评价既有环境系统综述的可信度 | CEESAT v2.2（evidence review） | 核对产品类型、协议、补充材料和问题级证据；evidence overview 使用其专用工具 | 把 CEESAT 当原始研究 RoB、证据确定性分级或总质量分 |
| 评价既有环境 Meta 的报告完整性 | MATES 2026 | PRISMA-EcoEvo/ROSES 页码映射 | 把完整报告误称为模型正确或 conduct 严谨 |

权威冲突时按以下规则：

1. 先满足目标期刊/机构的强制要求，但不得降低协议已承诺的标准。
2. 对环境证据综合，以当前 CEE living guidance 决定 conduct。
3. ROSES 负责“是否完整报告”，不证明研究按标准实施，也不替代风险偏倚评价。
4. PRISMA-EcoEvo 专门补强效应量、模型、非独立性、异质性、软件、开放数据和 Meta 结果；其完整清单主要面向系统综述/Meta 分析，不是系统地图清单。[PRISMA 官方 EcoEvo 页](https://www.prisma-statement.org/ecoevo)

## 2. 建立版本冻结与追踪表

在项目初始化时建立 `guidance_manifest`，每行至少包含：

```text
guideline_id, title, organization_or_authors, official_url,
displayed_version, publication_or_release_date, accessed_date,
local_copy_or_archive, file_hash, scope_used, checked_at_milestone,
change_summary, adoption_decision, rationale
```

冻结规则：

- 访问日期统一按实际访问记录；本模块核验日期为 `2026-08-03`。
- 保存 ROSES 实际填写的四类表之一及流程图模板，不只保存主页链接。
- 保存 PRISMA-EcoEvo 清单版本和解释论文 DOI；不要把交互式 App 的即时结果当作唯一记录。
- 对 CEE 保存显示版本、章节 URL 和必要的稳定快照/哈希；living 网页可能增量更新。
- 在稿件中声明实际遵循的冻结版本，不笼统写“遵循最新指南”。

## 3. 按 CEE 报告 conduct

CEE v5.1 同时给出 conduct 与 reporting standards；报告必须让第三方看出实际做了什么，而不是只写“遵循 CEE”。[CEE living guidelines](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/index.html)；[CEE standards table](https://environmentalevidence.org/standards-table/)

### 3.1 规划与协议

- 引用独立、事先公开的协议；给出注册平台、永久标识、首次公开日期和当时所处阶段。
- 报告问题和 PECO/PICO/其他框架、目标系统、主要/次要问题、目标 estimand 与利益相关方参与。
- 提供概念模型或因果链，说明干预/暴露如何影响结局。
- 单列 protocol deviations：原计划、实际方法、时间点、理由、是否接触结果、影响及是否对全部记录重做。

### 3.2 检索

- 对每个数据库报告名称、平台/供应商、覆盖时段、检索字段、完整检索式、限制和检索日期。
- 分开报告同行评议文献、灰色文献、组织网站、搜索引擎、引文追踪、手工检索、专家征集和其他来源。
- 报告独立“已知相关文献”测试集的建立方式、捕获结果及由此产生的检索修订。
- 说明语言、日期、文献类型、地域和可获得性限制，并评估其偏倚后果；不能以“灰色文献质量低”未经评价地排除全部灰色文献。
- 报告搜索更新的日期、范围、是否沿用原策略和去重方法。

### 3.3 筛选与研究身份

- 给出各阶段精确纳排标准、决策树/软件、筛选者数量、独立性、试筛样本、分歧解决方式和一致性检查。
- 提供全文排除列表及逐条理由、无法取得全文列表、资格不明列表和最终纳入研究列表。
- 区分 records/reports/articles 与 underlying studies；说明如何识别同一研究的多篇报告和重叠数据。
- 说明任何机器学习/自动化的训练资料、阈值、人工复核范围和漏检验证；自动化不承担最终资格判断。

### 3.4 编码、提取与有效性评价

- 附最终编码/提取表及数据字典；报告试提取、双人核验比例、分歧解决和作者联系。
- 系统地图只编码元数据；系统综述另提取结果、效应量和方差。不要在地图中悄然进行未规划的效应综合。
- 报告内部有效性与外部有效性的工具、信号问题、评审人数、支持证据和判定理由；不要用一个数值总分掩盖不同偏倚域。
- 说明评价结果如何改变纳入、分层、敏感性分析、权重或结论；只附风险偏倚图而不进入综合不够。

### 3.5 综合、限制与含义

- 在协议和报告中说明为什么选择 Meta、地图或结构化叙述综合；PECO/estimand 不兼容时明确拒绝合并。
- 报告所有统计方法、权重、方差估计、依赖处理、异质性、调节变量、敏感性和缺失结果偏倚分析，使第三方能复算。
- 不做 Meta 时，按研究设计、偏倚风险、PECO 和结果不确定性组织叙述；不得以“多少篇显著”为效应证据。
- 单列 evidence-base limitations 与 review-process limitations。
- 对政策/实践客观陈述适用条件和不确定性；避免把依赖资源和价值判断的内容写成证据直接支持的建议。

## 4. 选择并执行 ROSES

ROSES 官网提供四个不同表：systematic review protocol、systematic review report、systematic map protocol、systematic map report，另有 review/map 流程图。当前官网标示版本为 **ROSES 1.0, November 2017**。[ROSES forms](https://www.roses-reporting.com/forms)

### 4.1 开始前

1. 按产品选择唯一主表；不要把 review 与 map 表混填。
2. 下载当时官网表，记录 DOI/文件名、版本、下载日期和哈希。
3. 协议阶段逐项映射到计划章节；对“不适用”给出理由，不留空让读者猜。
4. 建立 `ROSES_item -> manuscript_section -> supplement_file -> evidence_owner -> status` 跟踪表。

### 4.2 实施中

- 将 ROSES 作为过程记录提示，而不是完稿后补勾选；每完成一个阶段就更新证据位置。
- 维护流程计数、全文排除、无法获得全文、研究合并、编码、提取、有效性评价和综合资格的可追踪日志。
- 协议与报告之间保留项目级 diff；任何方法变化都进入 deviations，而不是只更新最终文本。
- 需要调整流程图时保留 ROSES 的最低阶段粒度：检索、筛选、编码/元数据提取、结果数据提取、有效性评价、综合。[ROSES flow diagram](https://www.roses-reporting.com/flow-diagram)

### 4.3 投稿前

- 填写 report form，给每项实际页码、段落、表或补充文件定位。
- 附完成的 ROSES 表和对应流程图；表、图与正文数字必须由同一份机器可读 ledger 生成。
- 确认协议表承诺与报告表陈述一致；不一致处必须能在 deviations 中找到。
- 不宣称“ROSES compliant”来代替方法质量结论；准确写“按冻结版本完成并附清单”。

## 5. 执行 PRISMA-EcoEvo 定量审计

PRISMA-EcoEvo v1.0 包含 27 个主项，适用于生态与进化生物学的系统综述和 Meta 分析；它补充而不替代详细 conduct 指南。[O'Dea et al. 2021](https://doi.org/10.1111/brv.12721)；[官方清单](https://www.prisma-statement.org/ecoevo)

按以下分组审计，保留原清单编号：

| 项目 | 必须显式报告 |
|---|---|
| 1–3：识别、目的、注册 | 标题/摘要中的产品类型、范围与主结果；既有综述；问题与预设 moderators；实验/观察来源；注册和偏离 |
| 4–6：资格、查找、选择 | 设计/分类群/数据可得性标准及理由；搜索类型与信息源；完整策略和覆盖日期；筛选人员与流程 |
| 7–8：数据收集与数据项 | 数据来自正文/表/图/外部库何处；数字化与构造 moderator；缺失/歧义处理；提取者和复核数；真正复制单位及简化假设 |
| 9：个体研究质量 | 评价哪些域，以及如何进入分析或敏感性结果 |
| 10：效应量 | 每种效应量和采样方差的定义、公式来源、方向、转换和分布假设 |
| 11：缺失数据 | 缺失 SD、样本量、moderator 等的处理与理由；插补不确定性 |
| 12–14：模型、软件、非独立性 | 模型类型及选择理由；随机效应与采样 VCV；平台、包、函数、非默认参数和版本；空间、时间、系统发育、共享对照、多结局等依赖及处理理由 |
| 15：Meta 回归与模型选择 | 每个 moderator 的先验理由；参数数相对独立 studies 的可支持性；交互、共线性和完整模型选择路径 |
| 16–18：偏倚、敏感性、事后分析与开放材料 | 发表、时滞、分类群和其他缺失结果偏倚；替代效应量/权重/模型/子集；明确 post hoc；共享元数据、原始提取、分析数据和代码 |
| 19–20：选择结果与资料构成 | 各阶段流程数字和全文排除理由；每个分析/亚组同时报告 studies 与 effects 数；分类群、地域、设计、风险偏倚和 moderator 支持 |
| 21–24：定量结果 | 平均效应及区间；所有方差分量、`tau²/I²` 等异质性指标；全部 moderator 系数及区间、交互、R²/模型选择；偏倚和稳健性结果 |
| 25–27：解释与责任 | 效应大小、精度、异质性、生物/实践意义、与旧综述比较、普适性边界；作者贡献、资助、利益冲突；纳入研究的可识别参考文献 |

优先检查生态 Meta 最常漏报的三处：

1. **Item 8.4 与 14**：复制单位和所有非独立来源必须写清，不能只说“用了多层模型”。
2. **Items 20–24**：每个模型给 studies 与 effects 数、层级方差、完整 moderator 结果和敏感性，不只报显著项。
3. **Item 25**：用分类群、地理、尺度和时间证据缺口限制 generality，不以“随机效应模型”自动获得普适性。

### 5.1 评价既有环境证据综合：CEESAT 与 MATES

必须区分作者侧报告审计与读者侧既有证据综合评价。

**CEESAT v2.2** 用于评价已经完成的 environmental evidence review；evidence overview 必须改用官网列出的 overview 工具。评价单位是明确的 review question 或 hypothesis；一篇综述包含多个问题时分别评价。可检查正文及其直接链接的协议和补充材料，但不得用另一篇论文对方法的声称替代目标综述自身应提供的证据。CEESAT 根据可获得报告形成判断，因此“未报告”不等于“确定未实施”。Gold/Green/Amber/Red 反映不同判断域，不得求和、平均或压成单一质量分。它不是原始研究风险偏倚工具、报告清单或证据确定性框架。[CEESAT v2.2](https://environmentalevidence.org/wp-content/uploads/2026/06/CEESAT-Reviews-Version-2.2-updated-170526.pdf)；[官方版本页](https://environmentalevidence.org/ceeder/about-ceesat/)

**MATES** 是环境 Meta 分析的 14 项报告完整性评价工具。默认按官方实现评价论文中出现的第一个 Meta 分析；若研究问题要求评价另一个模型，必须在阅读其报告完整性前预先定义客观选择规则，冻结 `model_id` 并记录偏离。不得在同一论文的多个模型之间选择性拼接最完整的报告。MATES 结果只描述报告可见性，不证明效应量计算、依赖处理、模型设定、实际 conduct 或因果解释正确。[Morrison et al. 2026](https://doi.org/10.1016/j.envint.2025.109935)；[公开仓库](https://github.com/KyleMorrison99/MATES)；[Shiny 应用](https://kylemorrisonisshiny99.shinyapps.io/MATES_shiny/)

二次评价至少保存：

```text
review_id, question_id, model_id, documents_examined,
tool_name, tool_version, item_id, judgment, support_locator,
overall_result, assessor, assessed_at,
product_type, target_selection_rule, target_selection_deviation,
not_reported_does_not_prove_not_done, aggregation_forbidden, notes
```

CEESAT 和 MATES 均不得替代 CEE conduct、ROSES、PRISMA-EcoEvo、原始研究风险偏倚评价或证据体确定性评价；不得把它们与这些层级相加为一个“总质量分”。

从 `assets/review_level_appraisal_template.csv` 建立机器可读 ledger，并运行：

```bash
python scripts/validate_review_appraisal.py review_appraisal.csv
```

校验器只检查工具—产品—问题/模型目标、MATES 选择规则、版本和禁止聚合等契约，不替代人工题项判断。

## 6. 区分系统地图与系统综述的交付包

| 产物 | 系统地图 | 系统综述/Meta |
|---|---|---|
| 公开协议及偏离日志 | 必须 | 必须 |
| 完整检索策略与检索日志 | 必须 | 必须 |
| ROSES 专用表与流程图 | map 版本 | review 版本 |
| 全文排除/无法获取/资格不明列表 | 必须 | 必须 |
| report—study 关系表 | 必须 | 必须 |
| 数据 | 研究级编码数据库与数据字典 | 编码数据库 + 原始提取 + effect-level 分析数据 |
| 个体研究有效性 | 可选；若做须预设并报告 | 必须，并说明如何进入综合 |
| 综合 | 证据数量、分布、簇、空白和可视化 | 效应/关联综合、异质性、敏感性、外推 |
| 定量 Meta 报告 | 不适用 | 按 PRISMA-EcoEvo 10–24 |
| 开放材料 | 地图数据库、生成图表代码 | 数据、公式、VCV/树/空间对象、分析代码、软件版本 |

地图报告必须提供可下载的完整编码数据库和至少一种恰当的地图/热图/替代可视化；空白单元格表示“在检索范围内未找到合格证据”，不是“干预无效”。

## 7. 保证流程计数与研究身份一致

建立单一来源 ledger，以稳定 ID 生成流程图和所有计数：

```text
record_id -> report_id -> study_id -> site/experiment_id -> effect_id
```

至少输出以下不同数字：

- 从数据库/网站/其他方法识别的 records 数；
- 去重后的 reports 数；
- 标题摘要筛选、全文获取、全文排除、无法获取与资格不明数；
- 最终纳入 reports 和 underlying studies 数；
- 进入编码、结果提取、有效性评价、每个综合/Meta 模型的 studies 与 effects 数。

执行一致性断言：

- 每个全文排除 report 恰有一个主排除理由；多重理由可保留为辅助字段。
- 一个 study 可关联多个 reports，但同一数据不得重复贡献独立效应。
- 每个模型的 effect IDs 必须能回到 study、提取出处和资格决定。
- 流程图、摘要、正文、表格、ROSES 和 PRISMA-EcoEvo 清单中的数字必须从同一 ledger 生成。
- 更新检索产生的新 records 单独记录来源与日期，再并入总流程。

## 8. 报告依赖、异质性和外推

### 8.1 Methods 必须写出

- 独立性单位和层级：study、site、experiment、plot、species/taxon、outcome、time。
- 采样协方差来源：共享对照、配对、重复测量、多结局；`V` 的构造公式、已知/假定相关值和敏感性范围。
- 随机效应结构、空间/时间相关函数、系统发育树/相关矩阵、非系统发育 species 项。
- 异质性估计量、区间方法、小样本校正、prediction interval 的目标分布。
- moderator 的因果/生态依据、编码、尺度、缺失、共线性、交互和参数限制。
- 主分析与替代模型：多层、VCV、cluster-robust、替代树/空间结构、聚合或不加权敏感性。

### 8.2 Results 必须写出

- 每个模型的 studies、independent clusters 和 effects 数；不要只报总行数。
- 平均效应和 CI/credible interval、反变换后的生态单位或百分比及其解释。
- study/site/species/phylogeny/effect 等层级方差分量、总/分层 `I²` 与不确定性。
- prediction interval 及其目标范围；研究很少或方差不可识别时明确不报告或谨慎解释。
- 全部预设 moderator 系数与区间，包括不显著结果；报告残余异质性和解释度。
- 影响诊断、leave-one-cluster-out、相关假设、效应量、偏倚风险和外推支持的敏感性结果。

### 8.3 Discussion 必须划边界

- 用 PECO、地理、分类群、空间 grain/extent、随访时间、剂量和研究设计逐项说明 applicability/transportability。
- 区分实验室 efficacy 与野外 effectiveness，短期响应与长期持续性，观察关联与因果效应。
- 对证据不足写“未能确定”，不要写成“无效”；对平均接近零但 prediction interval 很宽，说明可能存在相反情境效应。
- 说明 taxonomic、geographic、publication、time-lag 和 availability biases 如何影响普适性。

## 9. 最终审计清单

### 9.1 文件与版本

- [ ] `guidance_manifest` 含 CEE、ROSES、PRISMA-EcoEvo、CEESAT/MATES（若适用）的版本、URL、2026-08-03 或项目实际访问日期、归档与哈希。
- [ ] 附正确的 ROSES protocol/report、review/map 表和流程图。
- [ ] 生态/进化 Meta 附 PRISMA-EcoEvo v1.0 页码映射。
- [ ] 报告所有期刊附加要求，但没有以其替代 CEE conduct。

### 9.2 可追踪性

- [ ] 协议、注册、所有偏离与搜索更新可定位。
- [ ] 完整检索式、全文排除、无法获取和资格不明记录可下载。
- [ ] report—study—effect 身份和流程计数一致。
- [ ] 每个效应可追到原始数值、页/表/图、公式、方向和核验者。
- [ ] 风险偏倚/外部有效性有逐域依据，并说明如何进入综合。

### 9.3 定量完整性

- [ ] 复制单位、伪重复、共享对照、空间、时间、分类群和系统发育依赖均有处置。
- [ ] 报告 effect-size/variance 公式、模型、软件包/函数/版本和非默认参数。
- [ ] 同时报 studies 与 effects；异质性不止一个 Q 或 `I²`。
- [ ] moderator 完整报告，post hoc 明示，未用显著性选择叙事。
- [ ] 提供 sensitivity、prediction/applicability 与停止合并理由。

### 9.4 开放与解释

- [ ] 共享机器可读元数据、提取数据、分析数据、代码、数据字典和许可；不能共享时说明原因与可访问路径。
- [ ] 报告资金、角色、利益冲突和利益相关方参与。
- [ ] 区分无证据与无效应、平均效应与效应分布、统计显著与生物/管理意义。
- [ ] 明示空间、时间、分类群、系统发育和设计的外推边界。

## 10. Living guideline 更新策略

### 10.1 CEE

CEE v5.1 公开为 living guidelines：major 表示核心方法/结构重大修订，minor 表示增加或澄清，patch 表示小修正；更新通过开放 GitHub 历史追踪，稳定版本可打标签归档。[CEE versioning](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/index.html#versioning)

执行：

1. 在立项、协议锁定、末次检索、分析锁定、投稿和大修六个里程碑检查官方主页、相关章节与变更历史。
2. 记录旧/新版本差异及其对资格、提取、有效性和分析的影响。
3. conduct 变化需要协议修订，并把新规则一致应用到全部研究；只影响措辞/链接的 patch 可在不改变方法时更新引用。
4. 保留原冻结版本；最终稿声明实施版本与投稿前最新核验版本。

### 10.2 ROSES

ROSES 官网说明：小型术语/结构更新可即时发布并进入 Current Version Update Record；重大内容变化需同行评议并发表新版本；CEE/Environmental Evidence 允许使用综述启动时可用的版本。[ROSES updates](https://www.roses-reporting.com/updates-and-extensions)

执行：

- 启动时下载表并冻结；投稿前检查主页显示版本和 update record。
- 小更新若只影响定位或术语，可更新表并记录；若改变应报告内容，补充报告但不伪装为原协议承诺。
- 大版本发布后做影响评估；已完成项目可继续报告冻结版本，同时说明未迁移的理由。

### 10.3 PRISMA-EcoEvo

截至 2026-08-03，PRISMA 官方页仍列 2021 年 v1.0；解释论文说明可通过 OSF 项目反馈并在未来更新。[PRISMA-EcoEvo 官方页](https://www.prisma-statement.org/ecoevo)；[OSF 更新入口](https://doi.org/10.17605/OSF.IO/GB5VX)

执行：

- 启动与投稿前检查 PRISMA 官方 EcoEvo 页、OSF 项目和解释论文勘误。
- 保存实际使用的 PDF/Word/Excel 清单版本；交互式 ShinyApp 只作辅助核查。
- 若新版本改变条目，保存 v1.0 与新版的映射和迁移决定，不覆盖已完成清单。

## 11. 来源登记

以下来源均于 **2026-08-03** 访问。

| 来源（URL） | 机构/作者 | 适用范围 | 当前状态/更新策略 |
|---|---|---|---|
| [CEE Guidelines and Standards v5.1](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/index.html) | Collaboration for Environmental Evidence；Guidance and Standards Team | 环境系统综述/地图全流程 conduct 与 reporting | Living；按里程碑检查版本、提交和标签 |
| [CEE Summary of Standards](https://environmentalevidence.org/standards-table/) | CEE | SR/SM 最低标准及 conduct/reporting 区分 | Living 网页；与 v5.1 章节交叉核验 |
| [CEE Chapter 2](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/Chapter_2.html) | CEE | PECO、开放/闭合问题、地图/综述路由 | Living 章节；问题或路由改变时复核 |
| [CEE Chapter 6](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/Chapter_6.html) | CEE | 编码、结果提取、双人核验与补充数据 | Living 章节；提取表冻结前复核 |
| [CEE Chapter 7](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/Chapter_7.html) | CEE | 内部/外部有效性、applicability/transportability | Living 章节；偏倚工具和外推计划冻结前复核 |
| [CEE Chapter 8](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/Chapter_8.html) | CEE | Meta/叙述综合、独立性、异质性和 effect modifiers | Living 章节；分析锁定前复核 |
| [CEE Chapter 9](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/Chapter_9.html) | CEE | 解释、限制、政策含义和补充文件 | Living 章节；投稿前复核 |
| [ROSES homepage](https://www.roses-reporting.com/) | ROSES initiative；Haddaway, Macura, Whaley & Pullin | 环境证据综合报告标准 | 官网显示 v1.0, November 2017；投稿前查显示版本 |
| [ROSES forms](https://www.roses-reporting.com/forms) | ROSES initiative | 四类协议/报告表及流程图入口 | 下载实际表并存 DOI/哈希 |
| [ROSES updates and extensions](https://www.roses-reporting.com/updates-and-extensions) | ROSES initiative / CEE | 小更新记录、重大版本与扩展机制 | 每个里程碑查 Current Version Update Record |
| [ROSES development paper](https://doi.org/10.1186/s13750-018-0121-7) | Haddaway, Macura, Whaley & Pullin (2018) | ROSES 的目的、pro forma 与 flow diagram | 静态原始论文；当前模板以官网为准 |
| [PRISMA-EcoEvo official page](https://www.prisma-statement.org/ecoevo) | PRISMA Executive | 生态/进化 SR 与 Meta 报告入口、清单和解释论文 | 截至访问日为 2021 v1.0；投稿前复核 |
| [PRISMA-EcoEvo paper](https://doi.org/10.1111/brv.12721) | O'Dea et al. (2021) | 27 项清单的解释、实例与适用范围 | 静态 v1.0 解释论文；检查勘误/新版 |
| [PRISMA-EcoEvo update/feedback OSF](https://doi.org/10.17605/OSF.IO/GB5VX) | O'Dea et al. / PRISMA-EcoEvo community | 反馈与未来更新入口 | Living project；保存访问时版本与下载清单 |
| [Quantitative evidence synthesis guide](https://doi.org/10.1186/s13750-023-00301-6) | Nakagawa et al., Environmental Evidence (2023) | 环境 Meta 定量方法和 PRISMA-EcoEvo 20–24 报告补充 | 静态方法论文；分析/报告前查后续证据 |
| [CEESAT v2.2](https://environmentalevidence.org/wp-content/uploads/2026/06/CEESAT-Reviews-Version-2.2-updated-170526.pdf)；[official page](https://environmentalevidence.org/ceeder/about-ceesat/) | Collaboration for Environmental Evidence | 对既有 environmental evidence review 进行问题级严谨性、透明度与局限评价 | Updated 17 May 2026；overview 用专用工具；使用前查官网，不复制整表、不聚合颜色判断 |
| [MATES paper](https://doi.org/10.1016/j.envint.2025.109935) | Morrison et al. (2026) | 环境 Meta 分析报告完整性评价 | 静态论文；默认首个 Meta 分析，替代目标须预设规则；仓库、Shiny 应用和题项许可分别核对 |

不得长篇复制官方清单。项目交付应附官方表原件或链接，本文件只提供执行路由、交叉映射和审计逻辑。
