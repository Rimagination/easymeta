# 医学与环境证据综合：偏倚风险、评价框架与证据确定性

> 用途：供另一个 Codex 对医学、公共卫生、生态与环境研究进行结果层面的偏倚评价，选择或设计适用的环境 critical-appraisal 方法，并对证据体进行 GRADE 或专门确定性评价。
>
> 资料核验日：2026-08-02。本文不复制工具原文；执行时必须同时打开所选工具的当前模板、详细指南和适用变体。

## 目录

- [一、边界与总流程](#一边界与总流程)
- [环境研究的 critical appraisal：FEAT](#环境研究的-critical-appraisalfeat)
- [二、偏倚工具路由](#二偏倚工具路由)
- [三、RCT：RoB 2](#三rctrob-2)
- [四、非随机干预：ROBINS-I](#四非随机干预robins-i)
- [五、暴露及其他专门设计](#五暴露及其他专门设计)
- [六、偏倚结果如何进入综合](#六偏倚结果如何进入综合)
- [七、GRADE 证据确定性](#七grade-证据确定性)
- [八、专门问题的确定性路由](#八专门问题的确定性路由)
- [九、不可自动化的判断与人工复核](#九不可自动化的判断与人工复核)
- [十、最小记录模板](#十最小记录模板)
- [十一、来源与更新](#十一来源与更新)

## 一、边界与总流程

**就近依据：** [Cochrane Ch.7](https://training.cochrane.org/handbook/current/chapter-07)、[Ch.8](https://training.cochrane.org/handbook/current/chapter-08)、[Ch.14](https://training.cochrane.org/handbook/current/chapter-14)、[Ch.25](https://training.cochrane.org/handbook/current/chapter-25)。

### 1.1 必须区分的三个层级

- **偏倚风险（risk of bias）：** 某项研究的某个结果是否因设计、实施、分析或报告过程而系统性偏离目标效应。
- **证据确定性（certainty of evidence）：** 针对一个结局、比较、目标人群和时间窗，跨研究的真实效应落在目标范围或决策阈值一侧的可信程度。
- **报告完整性：** PRISMA 等规范评价报告是否透明；不能替代前两者。

不得把研究层面的“质量”、报告字数、期刊影响因子、是否同行评议或总分当作偏倚风险。不得把单项研究的 RoB 等级直接称为 GRADE 确定性。

### 1.2 标准工作流

1. 锁定问题、estimand、主要结局、时间点、比较和综合组。
2. 按设计及研究意图选择**一个适用工具及版本**；下载当前详细指南和模板。
3. 对每个待用结果建立 `result_id = study × contrast × outcome × timepoint × analysis`。
4. 在看结果方向前定制工具：RoB 2 选择 assignment/adherence；ROBINS-I 写目标试验、混杂域和并发干预；专门工具写 synthesis question/适用性标准。
5. 两名经过训练的评价者独立阅读全部相关资料：论文、方案、注册、统计分析计划、补充材料、勘误和必要的监管资料。
6. 先记录支持信息，再回答 signaling questions，再做域判断、方向判断（能判断时）和总体判断。不得从总体印象倒推答案。
7. 使用工具算法生成**建议判断**；人工最终确认。偏离算法时记录具体理由，不得静默覆盖。
8. 将偏倚判断用于预设的主分析/敏感性分析和 GRADE risk-of-bias 域；不计算总分、不按分数加权。
9. 保存分歧、裁决者、日期、工具版本和引用位置；更新研究报告或工具版本变化时重新评估。

## 环境研究的 critical appraisal：FEAT

对比较性定量环境研究选择或设计 critical-appraisal 方法时，先用 FEAT 检查方法是否适配，不把 FEAT 当作另一份固定风险偏倚量表。[Frampton et al. 2022](https://environmentalevidencejournal.biomedcentral.com/articles/10.1186/s13750-022-00264-0)

- **Focused**：预先声明要评价的 validity construct，将内部有效性、外部有效性、报告完整性和研究伦理分开。
- **Extensive**：按全部合格研究设计枚举相关偏倚机制，不能只覆盖随机实验常见域。
- **Applied**：预先说明评价结果将如何进入纳入决策、分层、敏感性分析、证据解释或外推。
- **Transparent**：保存题项、支持证据、判断理由、评价者分歧、裁决和工具版本。

采用近似适用的既有工具时，先建立“研究设计—偏倚机制—工具域”覆盖映射。只有在许可允许、领域与方法专家复核并完成试评后方可修改；修改版记录变更、依据和新版本标识，不得继续声称为未经修改的官方工具。没有适用工具时可建立项目专用工具，但必须记录理论依据、专家审阅、试评结果和预定综合用途。

最小选型记录：

```yaml
environmental_appraisal_plan:
  validity_construct: ""
  eligible_designs: []
  bias_mechanism_map: ""
  selected_tool_and_version: ""
  feat_focused: ""
  feat_extensive: ""
  planned_synthesis_use: ""
  transparency_records: ""
  modifications: []
  modification_license_basis: ""
  expert_review: ""
  pilot_result: ""
```

CEESAT 和 MATES 属于证据综合层或报告层评价，其结果不得写入单项研究风险偏倚字段，不得自动触发 GRADE 或其他证据确定性升降级，也不得与 FEAT/RoB 判断相加为总分。

## 二、偏倚工具路由

**就近依据：** [RoB 2 current](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2)、[ROBINS-I official](https://www.riskofbias.info/welcome/home)、[ROBINS-E](https://www.riskofbias.info/welcome/robins-e-tool)、[JBI current tools](https://jbi.global/critical-appraisal-tools)、[Cochrane Prognosis tools](https://methods.cochrane.org/prognosis/tools)。

| 研究问题/设计 | 默认工具 | 适用单位与关键限制 |
|---|---|---|
| 个体平行组 RCT | RoB 2（22 Aug 2019 current） | 对具体结果；先选“分配效应”或“遵循干预效应” |
| 整群 RCT | RoB 2 cluster-randomized variant | 除一般域外，重点评价个体识别/招募时序及聚类分析 |
| 交叉 RCT | RoB 2 crossover variant | 重点评价时期效应、残留效应、配对数据和退出 |
| 非随机干预效果，有比较组 | ROBINS-I 2016 正式版为默认 | 对具体因果结果；须定义目标试验、estimand、混杂和并发干预 |
| 非随机环境、职业、行为或其他暴露 | ROBINS-E（24 Mar 2024） | 暴露效应，不属于 ROBINS-I 的干预范围；当前完整工具主要针对 follow-up studies |
| 诊断准确性 | QUADAS-3 current | 对 synthesis question 下的具体准确性估计评价 RoB 与适用性；2026 年已取代 QUADAS-2 为当前推荐 |
| 预后因子 | QUIPS | 按 Cochrane Prognosis 当前指导；需预设因子、结局、时距和调整要求 |
| 诊断/预后预测模型（回归或 AI） | PROBAST+AI current | 区分开发、验证、更新和适用性；不能用普通队列表替代 |
| 总体预后 | Cochrane Prognosis 当前指导所建议的定制工具 | 官方 FAQ 指出没有单一专用工具；可按指导定制 QUIPS/PROBAST，但须公开修改，不得自称原工具 |
| 患病率/发病率 | JBI current prevalence tool / PERSyst guidance | 关注抽样框、代表性、病例定义、测量、应答与分母；病例对照不能估患病率 |
| 病因/风险但不在 ROBINS-E 设计范围 | JBI 当前相应设计工具及病因风险章节 | 选队列、病例对照、分析性横断面等当前工具；说明为何 ROBINS-E 不适用 |
| 测量属性 | COSMIN Risk of Bias tools | 按信度、效度、反应度等测量属性分别评价 |
| 定性、经济、文本证据 | JBI 对应当前工具或预先选定的专门框架 | 不得套 RoB 2/ROBINS-I，也不生成虚假的统一数值分数 |

若研究设计不在工具适用范围，必须停下并请求方法学专家选择/定制工具；不得仅因“最接近”而套用。

## 三、RCT：RoB 2

**就近依据：** [RoB 2 official current version and guidance](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2)、[Cochrane Handbook Ch.8](https://training.cochrane.org/handbook/current/chapter-08)、[Ch.23 design variants](https://training.cochrane.org/handbook/current/chapter-23)。

### 3.1 评价前必须固定

- 目标结果及其测量方式和时间点。
- 比较的两个干预及目标 estimand。
- **分配效应（effect of assignment）**还是**遵循干预效应（effect of adhering）**。前者通常优先使用完整 ITT 结果；后者要求处理偏离、依从和相应混杂，不能用朴素 per-protocol 冒充。
- 试验变体：个体平行组、整群或交叉；使用对应版本，不能混用题目或算法。
- 所有可用的方案/注册/SAP 版本及其日期，以便判断结果选择。

### 3.2 五个标准域

| 域 | 要问的核心问题 | 常见红旗 |
|---|---|---|
| 1. 随机化过程 | 序列是否随机、分配是否隐藏、基线差异是否提示随机化问题 | 可预测分配、实施者可见序列、与机会不符的关键基线失衡 |
| 2. 偏离预期干预 | 依据所选 estimand，知晓分组后发生的偏离是否不平衡并被适当分析 | 交叉/污染、额外干预、排除已随机者、朴素 as-treated/per-protocol |
| 3. 结局数据缺失 | 缺失比例、原因及其与真实结局/分组的关系是否足以改变结果 | 组间失访不平衡、因疗效或伤害退出、只做 complete case 且假设不可信 |
| 4. 结局测量 | 方法是否适当，评定者是否知晓分组，知晓是否可能影响测量 | 主观结局未盲、各组测量不同、工具无效或判定流程不对称 |
| 5. 报告结果选择 | 是否从多个量表、定义、时间点、模型或分析中按结果选择 | 注册/SAP 晚于揭盲、方案仅写宽泛结局、报告与预设不符且无解释 |

不同结局和时间点的域 3–5 往往不同，禁止给整篇论文一个永久 RoB 标签。盲法不是单独总域；它通过偏离干预和结局测量等具体机制影响判断。

### 3.3 总体判断

- `Low risk`：所有域均为低风险。
- `Some concerns`：至少一个域有些担忧，且没有高风险域。
- `High risk`：至少一个域高风险，或多个“有些担忧”共同实质降低对结果的信心。

方向只能在有机制依据时填写（趋向无效、远离无效、偏向某组、不可预测）。不知道时填不可预测，禁止猜测。

### 3.4 非标准随机设计

- **整群 RCT：** 使用 cluster 变体；核对随机后招募/同意导致的识别偏倚、基线簇差异、簇丢失、ICC/聚类校正以及分析层级。
- **交叉 RCT：** 使用 crossover 变体；核对疾病稳定性、洗脱期、残留和时期效应、序列、仅首周期结果与配对分析。
- **多臂/析因：** RoB 仍对具体比较和结果评价；统计上避免共享对照重复计权，并检查交互或析因假设。

## 四、非随机干预：ROBINS-I

**就近依据：** [ROBINS-I 2016 official](https://www.riskofbias.info/welcome/home/original-2016-version-of-robins-i)、[ROBINS-I V2 draft page](https://www.riskofbias.info/welcome/robins-i-v2)、[Cochrane Handbook Ch.25](https://training.cochrane.org/handbook/current/chapter-25)。

### 4.1 默认版本政策

截至 2026-08-02，官网将 ROBINS-I V2（20 Nov 2025）明确标为**草案且可能修改**。因此：

- 常规项目默认使用 ROBINS-I 2016 正式版，并在方案、表格和报告中写明版本。
- 只有方案预先指定、团队接受培训、资助方/期刊允许且全体研究统一应用时，才可试用 V2 草案；必须显著标注 draft 状态和发布日期。
- 不得把 2016 的七域、V2 的域顺序/算法或旧表格拼成“混合版”。工具更新后，评估是否需要双评或重评，而不是只改版本标签。

### 4.2 先模拟目标试验

在回答任何 signaling question 前填写：

- 资格标准与目标总体。
- 比较的干预策略、剂量/持续时间和对照。
- 时间零点：资格判定、干预分配/开始和随访开始应对齐。
- 目标效应：分配/启动策略的效应，或遵循策略的效应。
- 随访期、结局、分析尺度。
- 预先认定的关键混杂域、可靠测量指标和重要并发干预。
- 可能的 immortal time、选择进入、暴露错分和检测差异。

无法定义可理解的目标试验，通常表示该结果不适合用 ROBINS-I 作干预因果解释，应停下重新表述问题。

### 4.3 2016 正式版七域

| 时间位置 | 域 | 操作关注点 |
|---|---|---|
| 干预前 | 混杂 | 关键预后因素是否同时影响干预选择；测量、建模和调整是否充分；有无时变混杂 |
| 干预前 | 研究参与者选择 | 纳入/排除是否依赖干预与结局相关因素；时间零点是否错位；是否有幸存者/immortal time 机制 |
| 干预时 | 干预分类 | 分类是否清晰、准确、在不知晓结局时确定；误分是否差异性 |
| 干预后 | 偏离预期干预 | 与 estimand 相关的交叉、依从、并发干预及分析是否适当 |
| 干预后 | 缺失数据 | 参与者、变量或结局缺失的数量、原因与处理是否可能偏倚结果 |
| 干预后 | 结局测量 | 测量有效性、分组知情、检测强度和判定是否在组间可比 |
| 干预后 | 报告结果选择 | 是否从多个结局、时间点、调整集、模型或亚组中按结果选择 |

### 4.4 调整估计的选择

- 主提取应最接近预设 estimand 和混杂域，而不是变量最多、CI 最窄或效果最显著的模型。
- 记录模型中的全部变量及测量时间；区分混杂、暴露后变量、中介、碰撞变量和纯精度变量。
- 倾向评分、加权、匹配、工具变量或 target trial emulation 不是“自动低偏倚”标签；分别核对可交换性、positivity、模型设定、平衡、时间对齐和缺失。
- 未调整估计可作描述/敏感性分析，但不能与调整后估计混成一个主效应而不说明目标差异。

### 4.5 总体判断

- `Low`：所有域低；含义是该结果在各域可与设计良好的随机试验相比，NRSI 中很少达到。
- `Moderate`：至少一个域中等，且无严重/极严重域。
- `Serious`：至少一个域严重，且无极严重域。
- `Critical`：至少一个域极严重；该结果问题过大，不能提供有用的因果证据。
- `No information`：关键域资料不足，不能作有依据的判断；不能把它自动当低或中等。

遵循正式算法和指南处理组合判断。`Critical` 结果按 Cochrane 指导不进入任何效果综合；仍应透明列出研究、原因和判断。若方向不确定，不得根据观察到的效果猜方向。

## 五、暴露及其他专门设计

**就近依据：** [ROBINS-E official](https://www.riskofbias.info/welcome/robins-e-tool)、[QUADAS-3 official](https://www.bristol.ac.uk/population-health-sciences/projects/quadas/quadas-3/)、[Cochrane Prognosis tools](https://methods.cochrane.org/prognosis/tools)、[JBI current tools](https://jbi.global/critical-appraisal-tools)。

### 5.1 暴露研究：ROBINS-E

- 环境、职业、营养、行为等“暴露效应”使用 ROBINS-E，而非 ROBINS-I；先定义每项结果所估计的因果效应。
- 当前 24 Mar 2024 完整版主要适用于非随机 follow-up studies。病例对照、横断面或其他设计超出明确范围时，使用 JBI 当前相应工具或经专家认可的方法，并说明选择。
- 重点人工判断包括暴露时间窗/测量误差、时变暴露、混杂、参与者选择、暴露后的选择、结局检测和报告选择。
- ROBINS-E 给出域风险、可能方向及风险是否足以威胁“是否存在重要效应”的结论；这些判断不能由回归调整变量个数自动生成。

### 5.2 诊断准确性：QUADAS-3

- 2026 年 2 月发布的 QUADAS-3 是当前推荐版本；使用官网最新文件（核验日为 v1.2），不再默认 QUADAS-2。
- 先定义每个 synthesis question 和理想准确性试验，再画流程并识别要评价的**具体准确性估计**；RoB 与适用性在估计层面评价。
- 人工核对参与者谱、index test 与阈值、target condition/reference standard、流程与时序、部分/差异验证以及不可判定结果。
- 准确性偏倚判断不能替代双变量/HSROC 模型，也不能回答检测策略是否改善患者结局。

### 5.3 预后、预测模型和患病率

- 预后因子用 QUIPS；总体预后按 Cochrane Prognosis 当前 FAQ 定制工具；预测模型使用 PROBAST+AI 当前版。三类问题不可互换。
- 预测模型分别评价参与者、预测变量、结局和分析等问题，并区分开发、外部验证、更新和影响研究；样本量、过拟合、缺失、校准及验证方式必须由模型专家复核。
- 患病率/发病率用 JBI 当前工具及 PERSyst 方法，不能只评价“统计分析是否合适”；代表性、抽样框、应答、病例定义、分母和设计效应决定可推广性。

## 六、偏倚结果如何进入综合

**就近依据：** [Cochrane Handbook Ch.7](https://training.cochrane.org/handbook/current/chapter-07)、[Ch.14](https://training.cochrane.org/handbook/current/chapter-14)、[Ch.25](https://training.cochrane.org/handbook/current/chapter-25)。

### 6.1 禁止做法

- 不把域答案相加成总分，不设置任意“≥7 分为高质量”。
- 不按质量分数修改 Meta 权重；逆方差权重只表达统计精度，不表达可信度。
- 不因研究“高偏倚”就静默删除，也不因纳入全部研究就忽略偏倚。
- 不用漏斗图、Egger 检验或期刊等级替代研究内偏倚评价。

### 6.2 推荐用法

1. 方案预设主分析如何处理偏倚。RCT 可纳入全部合格研究并以低风险/排除高风险作敏感性分析，或在有理由时限制主分析；必须说明选择。
2. ROBINS-I `Critical` 结果不进入效果综合。`Serious` 结果是否进入主 Meta 取决于预设策略、问题稀缺性和方向，但应至少做剔除敏感性分析并在 GRADE 中反映。
3. 若偏倚域对应不同效应方向或 estimand，优先分层而非平均。
4. GRADE 的 risk-of-bias 判断看各研究对该结局效应估计的贡献、偏倚严重度和敏感性分析，而不是数研究篇数。
5. 报告“全部合格研究”和预设的低偏倚/关键域敏感性结果；若结论改变，解释是哪一域、哪些研究驱动。

## 七、GRADE 证据确定性

**就近依据：** [GRADE Book](https://book.gradepro.org/)、[Principles for assessing certainty of interventions](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions)、[Decision thresholds](https://book.gradepro.org/guideline/decision-thresholds)、[Cochrane Handbook Ch.14](https://training.cochrane.org/handbook/current/chapter-14)。

### 7.1 评价单位与准备

GRADE 单位是：`population × comparison × outcome × time horizon × estimand` 的证据体。每个重要结局单独评级；同一综述不同结局可以有不同确定性。

开始前必须：

- 预先选出最多约七个 critical/important 结局用于 Summary of Findings（SoF），即使无数据也保留行。
- 给每个结局定义绝对效应、基线风险来源和无/微小、小、中、大效应或其他决策阈值。
- 选择 GRADE 指南/Book 章节版本与情境化方式并记录。GRADE Book 在持续更新，阈值导向的新章节应优先于过时的纯“是否跨无效线”习惯。
- 由两人独立评级并共识；所有降级、升级和不降级的重要理由写脚注。

### 7.2 起始确定性

| 证据体 | 通常起点 | 规则 |
|---|---|---|
| 干预 RCT | High | 再按五域降级 |
| 未使用 ROBINS-I 评价的干预观察性研究 | Low | 可按适用升级域升级；不得因“大样本”直接升高 |
| 使用 ROBINS-I 的 NRSI 干预证据 | 可从 High 开始 | ROBINS-I 已以目标随机试验为参照；随后按域降级。必须预先声明此路线，避免同时以观察性设计先降两级又因同一偏倚重复降级 |
| 暴露或预后因子证据 | 依当前专门 GRADE 指导，可从适合该问题的起点开始 | 观察性设计本身通常是正确设计；只在明确采用相应 GRADE 指南时执行，不能从干预规则自行类推 |
| 诊断准确性、总体预后、预测模型、患病率 | 使用对应专门 GRADE/方法指导 | 不得把干预 RCT 起点评级机械套用；指导仍发展中的领域要明确“不评级”或方法不确定性 |

无合格研究是“无证据”，不是“极低确定性”。极低确定性表示存在证据但对目标估计几乎没有信心。

### 7.3 五个降级域

#### A. Risk of bias

- 汇总该结局各结果的 RoB，考虑研究权重、效应方向和剔除高偏倚研究后的变化。
- 关键结果由高/严重偏倚研究主导、或偏倚足以跨越决策阈值时降级。
- 不能因个别小研究高偏倚而自动降级整个证据体；也不能因多数研究低偏倚而忽略一个权重很大的高偏倚研究。

#### B. Inconsistency

- 比较点估计方向和大小、CI 重叠、`tau²`、预测区间、亚组与预设机制；`I²` 只是一个输入。
- 判断不一致是否使真实效应可能落入不同决策范围，而非只看异质性检验是否显著。
- 可解释且预设的亚组差异可分层评级；无法解释且影响决策时降级。
- 单项研究填“未发现不一致/无法跨研究判断”的透明说明，不以“研究数少”在本域和 imprecision 域重复降级。

#### C. Indirectness

- 逐项检查人群、干预/暴露、比较、结局、时间窗、场景和 estimand 是否直接回答目标问题。
- 替代结局、不同剂量/实施方式、不同疾病阶段、间接比较或过时诊疗背景均可能降级。
- 适用性问题与研究内偏倚概念不同；若同一事实确实影响两个域，说明不同机制，避免重复计数。

#### D. Imprecision

- 以绝对效应和预设决策阈值判断 CI 是否跨越无/微小、小、中、大获益或伤害范围。
- 同时考虑 optimal information size（OIS）、事件数和模型/异质性造成的不确定性；不要以“研究少”本身作为理由。
- 不能只看 CI 是否跨无效线，也不能用“不显著”等同“无效”。当 CI 同时允许重要获益与重要伤害，通常需严重降级。
- 若宽 CI 主要源于研究间异质性，决定在 inconsistency、imprecision 或两者降级时写明理由，避免对同一不确定性重复降级。

#### E. Publication/dissemination bias

- 比较注册、方案、监管资料、会议摘要和发表结果；考虑资助、研究规模、延迟发表及结果缺失的方向。
- 漏斗图/小样本效应检验在研究少时通常能力不足，且不对称有多种原因。软件检验不能自动给“有/无发表偏倚”。
- 未发现不对称不是无偏倚证明；未系统检索未发表/注册资料时不能轻率判“无担忧”。

### 7.4 升级域

主要用于非随机证据，并在确认不是偏倚造成后考虑：

- **大效应：** Cochrane 给出的传统粗略参照包括相对效应 >2 或 >5，但必须结合基线风险、精度、残余混杂、选择和发表偏倚；阈值不是自动按钮。
- **剂量反应梯度：** 暴露/剂量层次预设、测量可信、趋势模型合适，且非线性和混杂不能更好解释。
- **所有合理残余混杂会削弱已观察效应，或在无效时制造相反方向效应：** 必须明确写出机制和方向。

同一特征不能同时用于“没有降级”和升级。若仍有严重偏倚、间接性或发表偏倚疑虑，升级通常不可信。

### 7.5 终级与表达

- `High`：对真实效应位于目标范围/阈值一侧有高度信心。
- `Moderate`：有中等信心，真实效应可能有一定差异。
- `Low`：信心有限，真实效应可能明显不同。
- `Very low`：信心很低，真实效应很可能明显不同。

SoF 至少包含结局及时间窗、研究/参与者数、相对效应、基于明确基线风险的绝对效应、最终确定性和简明脚注。结论措辞同时反映**效应大小**与**确定性**；不得仅按 P 值写“有效/无效”。

### 7.6 多证据流

- RCT 与 NRSI 回答同一干预结局时，分别评级并比较其直接性、偏倚和精度；不要把两个确定性等级平均。
- NRSI 可补充 RCT 不充分的罕见/长期伤害或目标人群，但该结果的人群差异须在 indirectness 中处理。
- 若两条证据流估计不同 estimand，必须各自呈现；不能因数值接近就合并。
- 不进行 Meta 仍可 GRADE，只要存在结构化的证据体和可解释的效应估计；“叙述综合”不是免评理由。

## 八、专门问题的确定性路由

**就近依据：** [GRADE Book topic index](https://book.gradepro.org/)、[Cochrane DTA GRADE resources](https://training.cochrane.org/online-learning/cochrane-methodology/grade-approach/jce-series)、[Cochrane Prognosis tools](https://methods.cochrane.org/prognosis/tools)、[PERSyst](https://persyst.group/)。

| 问题 | 路由与禁忌 |
|---|---|
| 诊断准确性 | 使用 GRADE test accuracy 专门指导，通常分别考虑敏感度/特异度及其下游真阳性、假阳性、真阴性、假阴性后果；不能只给 DOR 一个确定性等级 |
| 检测策略改善患者结局 | 作为干预问题对患者重要结局 GRADE；准确性证据可作为间接链条，但不能替代结局证据 |
| 总体预后 | 使用预后事件率的专门 GRADE 指导，统一起始点和时距；竞争风险和失访会影响 RoB/精度 |
| 预后因子 | 使用预后因子 GRADE 指导，对调整后关联及绝对风险分层评价；关联不自动等于可干预因果效应 |
| 预测模型 | 按 Cochrane Prognosis/GRADE 当前可用概念指导；校准与区分度分别处理。若正式指导尚不完整，明确“不作标准 GRADE”而非自行发明分数 |
| 暴露/环境健康 | 使用适用的 GRADE 暴露/环境健康指导，结合 ROBINS-E；观察性研究是典型设计，不自动因非随机而判低 |
| 患病率/发病率 | PERSyst 的 GRADE prevalence 工作仍在发展；应透明评价 RoB、间接性、不一致、精度和 dissemination bias，但不能声称使用不存在/未定稿的正式扩展 |
| 定性证据 | 若采用 JBI，使用 ConQual；它与 GRADE 效果确定性不是同一体系 |
| 测量属性 | 使用 COSMIN 的证据质量/推荐流程；不要套干预 GRADE |

## 九、不可自动化的判断与人工复核

**就近依据：** [GRADE Book certainty principles](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions)、[Cochrane Ch.14](https://training.cochrane.org/handbook/current/chapter-14)、所选偏倚工具的官方详细指南。

### 9.1 必须由人最终裁决

- 工具是否适用、选哪个版本/变体，以及结果/estimand 的边界。
- RoB 2 的 assignment 与 adherence；ROBINS-I 的目标试验、关键混杂、并发干预和偏倚方向。
- signaling question 中“可能”“足以”“重要”等依赖临床与因果背景的判断。
- 结局测量是否可受知晓干预影响，缺失机制是否可信，分析是否真正对应目标效应。
- 研究间差异是否构成不一致或应拆分问题；代理结局和目标人群差异是否构成间接性。
- 决策阈值/MID、基线风险和 OIS 假设；CI 跨阈值的临床含义。
- 发表/传播偏倚的可能性、升级是否合理、是否发生跨域重复降级。
- 最终确定性、结论措辞，以及证据是否足以支持临床/政策建议。

### 9.2 Codex 可协助但不得独立决定

- 抽取方案、注册、SAP 与论文之间的差异，并生成待核验引用位置。
- 按工具算法计算建议域判断，标记答案冲突或缺字段。
- 计算研究对 Meta 的权重、剔除敏感性、绝对效应、OIS 和 CI 跨阈值情况。
- 生成 Evidence Profile/SoF 草稿和脚注候选。

所有机器建议必须由两名评价者或一名评价者加独立方法学复核确认。任何算法无法处理、资料矛盾或需主题知识的项目应标记 `HUMAN_REVIEW_REQUIRED`，不得默认取较乐观等级。

## 十、最小记录模板

### 10.1 单项结果偏倚记录

```yaml
study_id:
result_id:
question_type:
design_features:
tool_and_version:
tool_variant:
estimand:
target_trial:        # ROBINS-I/ROBINS-E 时填写
confounding_domains: # 适用时填写
sources_reviewed: []
domain_support: {}
signalling_answers: {}
algorithm_proposal: {}
final_domain_judgements: {}
direction_of_bias: {}
overall_judgement:
deviation_from_algorithm_and_reason:
reviewer_1:
reviewer_2:
consensus_or_adjudication:
assessment_date:
```

### 10.2 结局证据确定性记录

```yaml
population_comparison_outcome_time_estimand:
grade_guidance_version:
decision_thresholds_and_sources:
baseline_risk_and_source:
starting_certainty_and_route:
risk_of_bias:        # judgement, levels, rationale
inconsistency:
indirectness:
imprecision:
publication_bias:
upgrading_domains:
double_counting_check:
final_certainty:
relative_effect:
absolute_effect:
plain_language_conclusion:
reviewers_and_consensus:
assessment_date:
```

脚注应具体说明“哪些研究、什么问题、如何影响阈值判断”，避免只写“因偏倚降一级”。

## 十一、来源与更新

以下均为本文件规则的主要来源；执行时应打开当前工具，不依赖本文复刻 signaling questions。

| 来源/机构 | 适用范围与本文件用途 | URL | 版本/状态（核验时） | 访问日期 | 更新提醒 |
|---|---|---|---|---|---|
| Cochrane Handbook，Cochrane | 偏倚概念、RoB 2、ROBINS-I、偏倚进入综合、GRADE | [Ch.7](https://training.cochrane.org/handbook/current/chapter-07)、[Ch.8](https://training.cochrane.org/handbook/current/chapter-08)、[Ch.14](https://training.cochrane.org/handbook/current/chapter-14)、[Ch.25](https://training.cochrane.org/handbook/current/chapter-25) | Handbook 主版 6.5 (2024)；Ch.14 在线标注 last updated May 2025 | 2026-08-02 | 每次评价前核对章节更新时间，尤其 Ch.14 与 GRADE Book 的差异 |
| RoB 2 Development Group / riskofbias.info | RCT 偏倚；平行、整群、交叉变体与正式模板 | [RoB 2 首页](https://www.riskofbias.info/welcome/rob-2-0-tool)、[current version](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2) | 个体平行组 current 22 Aug 2019；cluster/crossover revised 18 Mar 2021 | 2026-08-02 | 新项目下载最新版指南/模板；官网提示 Excel 部分文字略旧，不能只依赖宏表 |
| ROBINS-I Development Group / riskofbias.info | 非随机干预研究偏倚 | [2016 正式版](https://www.riskofbias.info/welcome/home/original-2016-version-of-robins-i)、[V2 页面](https://www.riskofbias.info/welcome/robins-i-v2) | 2016 final；V2 20 Nov 2025 仍为 draft、可能修改 | 2026-08-02 | 每次项目核对 V2 是否转正式；转正式后制定迁移与重评策略，禁止静默混版 |
| ROBINS-E Development Group / riskofbias.info | 非随机暴露效应偏倚 | [ROBINS-E](https://www.riskofbias.info/welcome/robins-e-tool) | Version 24 Mar 2024，full version for follow-up studies | 2026-08-02 | 确认设计适用范围及版本；病例对照/横断面另选工具 |
| GRADE Working Group | 确定性定义、阈值、五域、升级和呈现 | [GRADE Book](https://book.gradepro.org/)、[About](https://book.gradepro.org/about)、[Principles for certainty of interventions](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions)、[Decision thresholds](https://book.gradepro.org/guideline/decision-thresholds) | 官方 Book 持续补章，计划 2026 年底完全替代旧 Handbook；章节各有 last modified | 2026-08-02 | 每次 GRADE 前记录目标章节修改日期；新旧指导冲突时优先当前官方 Book 并说明 |
| Cochrane GRADEing Methods Group / Cochrane | Cochrane 中 SoF、按结局评级、五域和双人评价 | [Handbook Ch.14](https://training.cochrane.org/handbook/current/chapter-14)、[GRADE resource](https://training.cochrane.org/resource/grade-handbook) | Ch.14 online last updated May 2025；GRADE resource 指向逐步更新的 Book | 2026-08-02 | 与 GRADE Book 同步复核，不把旧 Handbook 当唯一最新来源 |
| QUADAS Steering Group / University of Bristol | 诊断准确性研究 RoB 与适用性 | [QUADAS-3 official](https://www.bristol.ac.uk/population-health-sciences/projects/quadas/quadas-3/)；[Cochrane 2026 introduction](https://www.cochrane.org/events/introducing-quadas-3-tool) | QUADAS-3 published Feb 2026；官网 latest v1.2（核验日） | 2026-08-02 | 每个 DTA 项目下载 latest version；若 Cochrane DTA Handbook 尚写旧工具，以 QUADAS 官网当前版为准并说明 |
| Cochrane Prognosis Methods Group | 总体预后、预后因子、预测模型的 RoB 与 GRADE 路由 | [Tools](https://methods.cochrane.org/prognosis/tools)、[FAQ](https://methods.cochrane.org/prognosis/faq) | 在线持续更新；列有 QUIPS、PROBAST+AI 及预后 GRADE 资源 | 2026-08-02 | 每次预后项目复核；FAQ/handbook drafts 更新后调整本文件 |
| JBI | 不同观察设计、患病率及其他证据类型的当前 appraisal tools | [JBI Critical Appraisal Tools](https://jbi.global/critical-appraisal-tools)、[JBI Manual 2024](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true) | 工具套件持续修订；队列 2025、分析性横断面及 DTA 页面 2026 已更新 | 2026-08-02 | 必须从 current tools 页面下载，不复制 2024 Manual 附录旧表 |
| PRISMA Executive | 报告规范边界及 DTA 等扩展 | [PRISMA 2020](https://www.prisma-statement.org/prisma-2020)、[Extensions](https://www.prisma-statement.org/extensions)、[PRISMA-DTA](https://www.prisma-statement.org/dta) | PRISMA 2020；扩展持续更新，prevalence extension 在核验日仍列为 under development | 2026-08-02 | 报告前核对正式状态；不得将清单完成度转成 RoB/GRADE 分数 |
| Frampton et al. / Collaboration for Environmental Evidence | 环境研究 critical-appraisal 方法的 Focused、Extensive、Applied、Transparent 选型与设计框架 | [FEAT paper](https://doi.org/10.1186/s13750-022-00264-0) | 2022 静态开放论文；FEAT 是框架而非固定题项量表 | 2026-08-02 | 新工具或修改工具时复核；复制图表/题项前核对论文许可 |

### 更新触发器

出现以下任一情况时，先更新本文件：ROBINS-I V2 转为正式版或再次修订；RoB 2 任一变体更新；ROBINS-E 扩展到新设计；QUADAS-3 更新；PROBAST+AI/QUIPS/JBI appraisal tools 更新；GRADE Book 新章替代旧 Handbook 或修改起点/阈值/域判断；Cochrane Handbook Ch.7/8/14/25 更新；PRISMA 专门扩展正式发布。
