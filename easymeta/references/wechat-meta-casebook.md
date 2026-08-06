# 公众号 Meta 素材蒸馏：生态 Meta 案例与方法触发器

本文件是对一批中文公众号 Meta 分析素材的二次蒸馏结果。它是案例索引和方法审计补充，不是权威统计教材；任何进入正式分析的规则，都必须回到原论文、补充材料、数据、代码和当前官方文档核验。

## 何时读取

- 用户要求把中文公众号、课程讲义或论文解读整理成 Meta 方法知识库。
- 用户要求审计“顶刊案例”“高级模型”“二阶 Meta”“Meta+机器学习/SEM”等宣传性方法说法。
- 生态、环境、植物或生物多样性 Meta 分析需要从具体案例反推依赖结构、效应量或组合模型。

读取本文件后，仍需按 `reference_routes.json` 读取相应的核心、效应量、依赖结构、生态和二阶 Meta 参考资料。公众号文章只能作为候选来源和线索，不能作为统计规则的一手依据。

## 先分离四类素材

| 素材类型 | 可用于什么 | 不可直接用于什么 |
|---|---|---|
| 一手论文/出版社页面 | 核对研究问题、设计、估计量、模型和结果 | 不因期刊级别自动接受方法 |
| 数据/代码/补充材料 | 重建输入、依赖结构和实现细节 | 不因代码可运行就认定估计量正确 |
| 公众号方法解读 | 发现概念、案例和常见误区 | 不直接作为公式、默认值或因果证据 |
| 培训/宣传/“顶刊”评价 | 发现热门主题和教学需求 | 不计作方法创新或质量证据 |

对每个素材保留 `source_role`、`primary_source`、`source_status`、`claim_status` 和 `human_verified`。标题中的“教科书”“最可复现”“标准做法”“已解决”一律当作待审计主张。

## 蒸馏后的方法契约

### 1. 观察单位、研究单位和依赖结构必须分开

公众号材料反复指出：同一篇原始论文、物种、地点、时间序列、处理—对照组合或多个结局可能产生多行效应。可复用的规则是：

- 每行保留 `study_id`、`report_id`、`effect_id`、`dependency_cluster` 和 `independent_cluster_id`；
- 同时记录 `assignment_unit`、`observation_unit` 和 `subsample_unit`；用于判断处理分配、观测和子样本是否被错误地当成重复；
- 用独立抽样簇而不是 effect rows、物种数、时间点或距离对数判断信息量；
- 给每个效应保留唯一的观测标识，如 `obsID`，但不要声称加入 observation-level 随机效应就自动修复了所有依赖；
- 先判断关系是嵌套、交叉还是混合。物种与地点通常是交叉结构，不能机械写成 `species/site`；
- 将采样误差协方差 `V`、真实效应随机结构和系数层稳健推断分别建模。

真实处理/实验重复不足时，后续加入 study、site 或 observation 随机效应不能创造缺失的复制；它只能表达已存在的层级或额外变异。

### 2. 共享对照和多处理设计必须构造采样协方差

同一实验多个处理共用一个对照时，多个 RR、SMD 或其他效应天然相关。可复用流程是：

1. 记录共享组、处理组、比较、时间点和真实独立单位。
2. 按效应量定义推导非对角采样协方差，或明确记录相关系数/敏感性假设。
3. 将 `V` 与多层/多变量模型或聚类稳健推断配套使用。
4. 把“把对照样本复制到每一行”“增加随机效应”“随意缩放 vi”作为高风险捷径审计。

只增加 study 或 observation 的随机效应，不能生成共享样本所导致的非对角 `V`。缺少协方差且无法做合理敏感性分析时，应分层、聚合或停止定量合并。

### 3. 系统发育模型是依赖结构触发的专项路线

涉及多个物种、宿主—寄生者组合或分类群比较时，系统发育相关矩阵可以进入 Meta 模型；同一模型中还可能需要区分系统发育相关、物种独立随机效应、研究层随机效应和 observation-level 方差。

- 先定义目标 estimand、物种/组合的独立单位和树的不确定性；
- 验证矩阵的名称、顺序、正定性和来源，不按行号静默配对；
- 用交叉结构表达 study、species、site 等关系；
- 不把 PGLMM/PGLS Meta 当成所有生态 Meta 的默认模型，也不以“顶刊采用”替代可识别性检查。

### 4. 效应量转换必须保持 estimand 和不确定性

RR 与 d/g、相关系数与 Fisher z、比例、SMD、lnRR 等转换不是“为了多合并几篇文章”的格式转换。每次转换至少保存：

`source_estimand, target_estimand, formula, exact_or_approximate, required_parameters, variance_or_covariance_propagation, assumption_set_id, sensitivity_analysis, human_verified`。

对生态 response ratio 与 SMD 的桥接，优先读取效应量专项资料和对应原始论文；不得用固定常数把所有 lnRR 机械换成 d。若转换改变研究问题、需要未知分布假设或无法传播协方差，就分层报告或停止转换。

### 5. 二阶 Meta 先处理重叠，再谈模型

当输入是既有 Meta 分析时：

- 使用 `data.level=meta_level` 和二阶 Meta 专项路线；
- 建立 review × primary-study 的重叠矩阵，按结局、比较和时间窗细化；
- 对齐 PECO、estimand、效应尺度、调整状态、时间窗和不确定性来源；
- 区分 overview/umbrella、二阶定量综合和回到一级研究重算；
- 不把不同 Meta 的 pooled estimates 当作天然独立，也不把任意综述质量分直接乘进逆方差权重；
- 缺少一级研究清单、review-level 协方差或可比 estimand 时，停止自动定量合并。

“把质量指数直接作为 vi”是语义错误：质量指标越高通常代表应更受信任，但方差越大代表精度越低。任何 quality-effects 方法都必须回到其明确公式和权重定义，不能把 quality score、`vi`、`tau²`、I² 或区间宽度互换。

### 6. 只有均值、SD 和 n 的研究不是自动获得因果效应

均值、SD 和 n 可以在适当问题下构造均值型估计及其抽样方差，但这回答的是明确的均值/水平 estimand，不自动等于处理效应、暴露效应或可比较的干预效应。必须先核对：

- 参考状态、处理分配和比较条件是否存在；
- 单位、测量方法、时间窗、空间尺度和样本来源是否可比；
- SD 是个体变异、组间不确定性还是时间/地点变异；
- 是否需要把均值效应、变异性效应或关联效应分开。

“只要有均值和 SD 就几乎都能做 Meta”是过度外推。没有共同 estimand 时应做结构化叙述或系统地图。

### 7. Meta、机器学习和 SEM 是组合分析，不是单一模型

常见组合是：先用 Meta 得到研究级效应，再用 Meta 回归或机器学习解释/预测空间或环境异质性，最后用 SEM 表达候选路径。必须分别标记：

- Meta 的合并 estimand；
- Meta 回归的研究间关联；
- 机器学习的预测目标和外推范围；
- SEM 的路径假设、混杂、时间顺序和因果解释条件。

不能因为一个案例同时出现 Meta、随机森林和 SEM，就把所有输出称为因果机制或“高级 Meta”。

### 8. 模型选择、发表偏倚和复现要防止宣传性简化

- `dredge`、stepAIC、模型平均等只能在明确候选模型、研究层调节变量、有效自由度和多重比较策略下使用；不要把模型选择结果称为普遍“教科书”。
- 固定/共同效应与随机效应不能由异质性检验 P 值单独决定；预测区间、τ²、I² 和 Q 各回答不同问题。
- 漏斗图、Egger、trim-and-fill、fail-safe N 或单一选择模型不能给出“发表偏倚存在/不存在”的二元结论，依赖效应和效应量机械相关时尤其要谨慎。
- PRISMA/ROSES 等主要是报告和可追溯性框架，不等于检索、筛选、提取和偏倚控制已经正确。
- 数据、代码可得性是复现入口，不是方法正确性的证明；保留版本、许可、哈希、运行环境和未复现状态。

## 代表性案例索引

以下案例用于触发阅读路线，不替代原论文核验。

| 案例节点 | 主要方法问题 | 读取/审计重点 |
|---|---|---|
| [RR 与 d/g 转换，Ecology Letters](https://doi.org/10.1111/ele.70335) | response ratio、SMD/Hedges g 的桥接 | estimand、近似条件、方差传播和边界规则 |
| [Ecological meta-analyses often produce unwarranted results](https://doi.org/10.1002/ecy.70269) | 多效应、研究内聚类、伪重复 | 独立簇、obsID、真实随机结构和 VCV 的分工 |
| [New horizons for comparative studies and meta-analyses](https://doi.org/10.1016/j.tree.2023.12.004) | 系统发育混合模型、比较性 Meta | 物种依赖、矩阵验证、PGLMM 适用边界 |
| [Quantitative evidence synthesis for environmental sciences](https://doi.org/10.1186/s13750-023-00301-6) | 均值型效应、Meta 回归、发表偏倚 | 均值 estimand 与干预效应的区分 |
| [追加式 Meta 案例，Annual Review of Entomology](https://doi.org/10.1146/annurev-ento-041720-075234) | 在已有 Meta 基础上更新/累积 | 重新检索、研究重叠、方法版本与更新协议 |
| [Meta + 机器学习，Environmental Science & Technology](https://doi.org/10.1021/acs.est.5c12883) | Meta 与机器学习结合 | 预测目标、空间尺度上推和外部有效性 |
| [Meta + 随机森林 + SEM 的生态案例](https://www.nature.com/articles/s41467-026-72626-y) | 合并效应、预测和路径模型串联 | 关联、预测、因果路径的分层解释 |

## 从公众号材料中采纳与拒绝的内容

公众号条目不再以“某某方法”作为唯一索引。先给文章标注它试图解决的问题，再记录涉及的方法。一个条目可以有多个问题模式，但每个模式都要说明对应的 estimand 和证据关系。

| 问题模式 | 文章材料中常见的提问 | 应提取的核心信息 | 不能直接推出的结论 |
|---|---|---|---|
| 总体效应 | 某处理/暴露平均改变了多少结果 | 比较、结果尺度、目标人群/系统、时间窗 | 平均效应不等于所有场景的效果 |
| 效应分布 | 为什么不同研究结果不同、如何解释异质性 | 研究间调节变量、预测区间、适用范围 | 调节变量关联不自动是机制或因果 |
| 依赖证据 | 多结局、共享对照、重复测量、物种/地点是否重复计数 | 独立簇、嵌套/交叉关系、V/VCV、随机结构 | 加一个随机效应就自动修复所有依赖 |
| 二阶证据 | 多篇 Meta 的结论是否可以合并 | 一级研究重叠、estimand 对齐、综述层级和协方差 | 综述数量等于独立证据数量 |
| 机制/路径 | 结果可能通过哪些变量发生联系 | 概念模型、时间顺序、混杂、路径假设 | Meta+SEM 就证明了因果机制 |
| 预测/阈值/空间 | 在什么条件或地点可能出现什么结果 | 预测目标、验证设计、阈值不确定性、外推范围 | 预测准确就证明因果关系 |
| 不能合理合并 | 不同文章是否真的回答同一个问题 | 不可比的对象、比较、结果定义和尺度 | 有均值、SD、n 就一定可以合并 |

对当前公众号素材，建议先建立 `problem_pattern`、`estimand`、`row_unit`、`independent_unit`、`candidate_methods`、`primary_source`、`claim_status` 和 `next_best_check` 字段。只有当原论文或数据/代码核验完成后，才把“候选方法”提升为可采纳的分析建议；案例文章的作用是展示取舍，不是生成默认参数。

## 已核验的原文与数据/代码证据台账（2026-08-06）

以下记录来自原论文/出版社页面、补充材料、作者数据仓库或作者代码仓库的交叉核对。`已核验`只表示来源、方法位置和数据/代码入口已经确认，不表示该研究的全部结论已被本地重跑。

| 公众号线索/案例 | 原文事实 | 数据/代码证据 | 当前审计结论 |
|---|---|---|---|
| Peacor et al. 2025，生态 Meta 的非独立性 | 20 篇生态 Meta 中，14 篇未处理 paper-level effect；加入随机 paper effect 后仍有过量显著性，且 12/14 个修订模型的 paper effect 显著；作者明确说随机 paper effect 不是充分解决方案 | 论文数据声明指向 [Figshare 10.6084/m9.figshare.28187996](https://doi.org/10.6084/m9.figshare.28187996) | **可采纳为依赖结构警报**：必须按生成机制构造依赖，不能把 `study_id` 随机效应当作所有非独立性的替代品；公众号中 12.7% 等具体数字不复述，除非逐表定位 |
| Lajeunesse 2026，RR 与 d/g 转换 | 原论文把 lnRR/RoM 到 Hedges' d 的转换限定为方差同质、使用小样本校正、且仅适用于加性而非乘性生态过程；另讨论可构造的均值转换 | 论文数据声明给出 [Figshare 10.6084/m9.figshare.30782225](https://doi.org/10.6084/m9.figshare.30782225)，并有 Data S1 ZIP | **可采纳为转换契约案例**：不能将 lnRR 机械换成 d/g；必须记录 estimand、假设、校正和方差/协方差传播 |
| Cinar et al. 2022，系统发育多层 Meta | 模拟比较多种结构，最复杂模型同时拆分 species-level 的非系统发育与系统发育方差；模拟把抽样方差视为已知，属于理想化条件 | 论文明确给出 [OSF osf.io/ms8eq](https://osf.io/ms8eq/) 作为代码和复现材料 | **可采纳为专项路线**：核验树、物种顺序、矩阵和可识别性；作者推荐的“de facto standard”不能升级成 EasyMeta 的普遍默认值 |
| Nakagawa et al. 2023，环境科学定量证据综合指南 | 原文提供多层 Meta、Meta 回归、预测区间、small-study effect/时间滞后、缺失数据、空间/系统发育/VCV 等路线；明确指出常用 Egger/trim-and-fill/fail-safe 方法对非独立效应不合适或有限 | Springer 页面提供 [Additional file 1 调查数据](https://link.springer.com/article/10.1186/s13750-023-00301-6) 和 [Additional file 2 R tutorial](https://link.springer.com/article/10.1186/s13750-023-00301-6) | **可采纳为 QA/教学骨架**：报告完整性、RoB、确定性、发表偏倚不能合并成一个“质量分”；指南本身也不是某一数据集的数值复现 |
| Beillouin et al. 2023，SOC 二阶 Meta / MetaSynthesis | 原论文确实综合 230 个一级 Meta、超过 25,000 个一级研究和约 190,200 个配对比较；质量按 8 项标准，一级 Meta 间重叠用 `2m/(n1+n2)` 的伪相关进入 VCV，并比较含/不含质量和重叠的模型 | Nature 页面给出 [Dataverse 10.18167/DVN1/KKPLR8](https://doi.org/10.18167/DVN1/KKPLR8) 和 [MetaSynthesis GitHub](https://github.com/dbeillouin/MetaSynthesis)。代码中的 `QUALITY_DOI()` 输出 `W`，而 `Frequentist_models.R` 将其作为 `rma.mv` 的 `V` 或 `FUN_MAT_RED()` 的 `Variance` 输入 | **公众号批评部分支持、结论需降级**：代码层面确有“质量调整项/权重语义”直接送入 `V` 的高风险，且函数名/注释混用 variance/weight；但“所有新方法都错了”需要固定版本、输入数据、矩阵对角线和重跑结果才能成立，skill 只记录为 `source_reproduction_required`，不直接下全盘否定结论 |
| Beillouin et al. 2021，95 个一级 Meta 的作物多样化二阶综合 | 原文核实为 95 个 Meta、5156 个实验、超过 54,500 个配对观测、120 种作物、85 个国家；报告产量中位效应约 +14%，且强调不同多样化策略之间差异 | Wiley 页面给出公开数据平台 [Crop_diversification_2020](https://cropdiversification.shinyapps.io/Crop_diversification_2020)，并列出补充信息 | **可采纳为二阶 Meta 案例**：保留“一级 Meta/一级研究/配对观测”三层计数，不能把 95 个综述等同于 95 个独立实验 |
| Pan et al. 2026，Meta + 随机森林 + 阈值/空间上推 | 原文用 lnRR 的多层 Meta、study 与 N-rate 层级，随机森林筛选预测因子，阈值模型和 bootstrap，再做 0.25° 全球空间预测；明确有 missForest 插补与外部变量图层 | Nature 页面给出 [Figshare 10.6084/m9.figshare.30646841](https://doi.org/10.6084/m9.figshare.30646841)，同时声明主 R 代码、Source Data 和一级研究清单 | **可采纳为组合分析案例**：Meta 合并、预测/变量重要性、阈值识别和空间外推分层报告；插补、空间交叉验证、外推和因果措辞必须单独审计 |
| Wang et al. 2026，蚂蚁—土壤碳 Meta + RF + PLS-SEM | 原文为 2232 个观测、136 个研究；`reference/obs` 多层结构，共享对照用 Lajeunesse 方法构造 VCV；另接 ranger 随机森林和 PLS-SEM | Nature 页面给出 [Figshare 10.6084/m9.figshare.31827412](https://doi.org/10.6084/m9.figshare.31827412)，数据与代码同仓库，并列出 WorldClim、Aridity Index、SoilGrids 来源 | **可采纳为分层组合案例**：共享对照的 VCV 与随机效应各司其职；RF/PLS-SEM 结果不得反写成 Meta 的因果估计；代码可得不等于本地重现已完成 |
| Wang et al. 2026，塑料地膜 SOMA | 原文称二阶 Meta 综合 70 个一级 Meta、11,712 个田间实验和 110,809 个观测；方法使用 Comprehensive Meta-Analysis，代码可得性声明为“no new code” | Nature 页面给出 [Figshare 10.6084/m9.figshare.30283255](https://doi.org/10.6084/m9.figshare.30283255)，并记录 2026-04-09 更正过错误的 Figshare 链接 | **可作为案例而非默认模板**：数据入口已核实，但“无新代码”、商业软件和政策外推意味着应保留复现与外部有效性警告；公众号的“高级”评价不作为证据 |

### `QUALITY_DOI` 争议的精确处理

这是本轮核验中最需要保留上下文的案例。原论文的方法文字说“按逆方差加权，并按 Doi 等人的质量效果方法降低低质量一级 Meta 的权重”；作者代码的 `QUALITY_DOI()` 先计算 `Qv = Qi/vi`，再加上 `tauprim` 得到名为 `W` 的向量；同一仓库的 `Frequentist_models.R` 却在质量模型中以第二个位置参数把它交给 `rma.mv`（即 `V`），在质量+重叠模型中又把它交给构造伪 VCV 的 `Variance` 参数。由于 `metafor::rma.mv` 的 `V` 表示抽样方差/方差—协方差矩阵，而 `W` 在函数体中显然具有精度/权重方向，存在可检验的语义和权重方向冲突。

因此 EasyMeta 的处理是：

1. 记录代码事实和论文方法文字，不把公众号截图当作证明；
2. 先用固定版本数据重算 `QUALITY_DOI()`、对角线和 `FUN_MAT_RED()`，确认输入是否为权重、伪方差还是经过变换的方差；
3. 比较原模型、正确的 `V`/`W` 参数化、仅质量、仅重叠和不调整模型的估计、区间、模型选择与敏感性结果；
4. 在完成重跑前只能写“实现存在高风险/需复现”，不能写“该论文所有结果均错误”。

这条规则比“质量分永远不能进入模型”更精确：质量信息可以作为预先定义的调节变量、敏感性分层或经明确推导的 quality-effects 权重；但不能未经公式审计就把质量分、权重、`vi`、`tau²` 或 VCV 互换。

一个仅用于方向检查的数值 sanity check（`SCORE=(8,5,2)`、`vi=(0.02,0.10,0.50)`，按仓库函数重算）得到 `W=(52.8,8.0,1.2)`：`W` 与质量分同向、与原始 `vi` 大体反向；若把 `W` 直接当作 `V`，就会让高质量项的输入方差更大、逆方差权重更小。这个检查支持“存在严重实现风险”的判断，但不是对论文全部结果的重分析；正式结论仍需使用仓库固定版本的真实数据和冗余矩阵复现。

### 采纳为 EasyMeta 规则

- 将观测效应、独立研究和依赖簇分开计数；
- 显式区分嵌套与交叉随机结构；
- 将共享对照、重复测量、多结局和系统发育关系视为依赖结构触发器；
- 任何效应量转换都要有公式、假设、方差/协方差传播和敏感性分析；
- 二阶 Meta 必须做一级研究重叠和 estimand 对齐；
- 均值型 Meta、Meta+机器学习、Meta+SEM 都要拆分 estimand 和解释层次；
- 将 PRISMA、代码共享、顶刊案例和培训材料视为不同证据角色。

### 只作为警告，不作为默认方法

- “层级 Meta 几乎已经是所有生态 Meta 的标配”；
- “把 VCV 修成正定就解决二阶 Meta”；
- “质量分可以直接作为 vi 或普遍权重”；
- “加入 obsID 就完美解决非独立”；
- “只有均值、SD、n 就几乎都能做 Meta”；
- “Meta+机器学习/SEM 自动揭示因果机制”；
- “顶刊案例、引用量或代码可运行证明方法正确”。

## 最小审计记录

将公众号素材转成 skill 知识时，至少保存：

```text
material_id, article_title, publication_date, source_role,
primary_source, source_status, claim, claim_type,
estimand, independent_unit, dependence_sources,
effect_measure, formula_or_code_locator,
adopted_rule, rejected_claim, human_verified, reviewer, checked_at
```

对于未经原文核验的公众号主张，`human_verified=false`，只能进入候选清单或审计警告，不能进入主分析默认值。

## 强制停止或降级条件

- 独立抽样簇、处理分配单位或真实复制数未知；
- 公众号没有一手引用、来源定位或可恢复的原始数据；
- 共享对照、重复测量或多结局的协方差无法合理指定，也无法做相关假设敏感性分析；
- 转换改变 estimand、需要不可验证假设，或无法传播方差/协方差；
- 二阶 Meta 未评估一级研究重叠；
- 质量分被直接当作 `vi` 或普遍权重；
- 系统发育、空间、时间、原始群落矩阵或 Meta+ML/SEM 输入被强行送入普通 `yi/vi` runner。
