# 植物生态与生物多样性 Meta 分析专项路由

本文件把植物生态、群落生态、生物多样性、恢复生态和多胁迫实验中不能直接交给普通 `yi/vi` runner 的问题转成可审计分析契约。它不是某篇论文方法的复刻，也不保证列出的专项模型已经在本技能中实现。

## 目录

- [1. 先判定产品和数据层级](#1-先判定产品和数据层级)
- [2. 所有专项路线的共同契约](#2-所有专项路线的共同契约)
- [3. 原始群落矩阵与多样性分解](#3-原始群落矩阵与多样性分解)
- [4. 多维 β 多样性与多变量综合](#4-多维-β-多样性与多变量综合)
- [5. 变异性 Meta 分析](#5-变异性-meta-分析)
- [6. 析因实验与交互效应](#6-析因实验与交互效应)
- [7. 生态系统多功能性](#7-生态系统多功能性)
- [8. 纵向抗性、恢复力和稳定性](#8-纵向抗性恢复力和稳定性)
- [9. 派生恢复债与恢复程度](#9-派生恢复债与恢复程度)
- [10. 第二阶与 cross-meta 综合](#10-第二阶与-cross-meta-综合)
- [11. 共享对照、多个结局和多个分类群](#11-共享对照多个结局和多个分类群)
- [12. 缺失证据和小研究效应](#12-缺失证据和小研究效应)
- [13. 停止规则与最低交付物](#13-停止规则与最低交付物)
- [14. 方法来源](#14-方法来源)

## 1. 先判定产品和数据层级

按顺序回答：

1. 输入是论文级效应、处理臂/析因单元汇总、样地时间序列、原始物种×样点矩阵，还是既有 Meta 分析的结果？
2. 目标是平均水平、变异性、α/β/γ 多样性、物种周转、交互效应、多功能性、抗性、恢复力、恢复债，还是跨 Meta 分析比较？
3. 独立信息单位是研究、实验、地点、区组、样地、时间序列、物种，还是既有 Meta 分析？
4. 哪些对象共享对照、样地、年份、物种、研究、数据集或纳入论文？
5. 需要从原始数据先生成 estimand，还是已有含可审计方差的目标效应？

选择路由：

| 情形 | route-schema 触发器 | 普通 runner |
|---|---|---|
| 原始物种×样点/样方矩阵，需先生成多样性指标 | `data.level=raw_community_matrix` 且 `raw_community_matrix=true` | 阻断 |
| 已有 Bray–Curtis/Jaccard/turnover/nestedness/homogeneity/composition shift | `community_composition` | 阻断；先验证距离、配对和协方差契约 |
| 分类、功能、系统发育多样性需联合建模 | `multidimensional_biodiversity` | 阻断 |
| 比较 SD、CV 或稳定性而非均值 | `variability_effect` | 阻断 |
| 两个或更多实验因子的交互为目标 | `factorial_interaction` | 阻断 |
| 一个系统有多个生态功能，需定义多功能性 | `ecosystem_multifunctionality` | 阻断 |
| 样地/实验跨年份重复，目标是轨迹、抗性或恢复力 | `one_stage_longitudinal` | 阻断 |
| 恢复债、恢复程度等需多步派生且假设主导 | `derived_recovery_stability` | 阻断 |
| 输入单位是既有 Meta 分析或跨 Meta 的总结 | `data.level=meta_level` 且 `second_order_meta=true` | 阻断 |
| 已定义的多个效应只因共享对照而相关 | `data.effect_structure=dependent` | 仅在显式 `V`、独立簇和模型层级均合格时允许 |

`Dainese et al. 2019` 一类整合多地点原始数据并拟合路径/层级模型的研究，不因样本量大就自动成为传统 Meta 分析；按原始数据综合路由处理。`Isbell et al. 2015` 一类跨实验纵向模型也不能压成每年独立 `yi/vi`。

## 2. 所有专项路线的共同契约

在分析前冻结并版本化：

- 从 `assets/biodiversity_contract_template.json` 建立每个 outcome/estimand 契约，运行 `scripts/validate_biodiversity_contract.py`；验证失败或 route JSON 未登记 `ecology_contract_path` 时停止；

- `target_estimand`：自然语言、数学定义、方向、单位和解释边界；
- `independent_unit`、`assignment_unit`、`observation_unit`、`subsample_unit`；
- 原始数据到分析对象的转换代码、随机种子和丢弃记录；
- 零值、缺失、未观测物种、分类学解析、离群值和检测限政策；
- 采样 effort、grain、extent、持续时间和空间/时间支持；
- 采样误差协方差 `V` 与真实效应随机结构的分工；
- schema 字段 `sampling_covariance_status`，只允许 `not_needed_verified`、`provided_validated`、`derived_exact`、`derived_delta_method`、`assumed_sensitivity` 或 `unavailable`；依赖效应若为 `unavailable` 必须停止；
- 假设集合 `assumption_set_id`，包括未知相关系数、标准化、阈值、树、距离和参考状态；
- 主分析和至少一个结构敏感性分析；
- 人工确认记录：生态意义、方向、可交换性和外推范围。

不执行以下捷径：

- 不把每个物种、年份、功能、距离对或 β 多样性配对当作独立研究；
- 不以“研究随机效应”代替缺失的采样协方差；
- 不按显著性挑选一个时间点、一个阈值、一个 Hill 数或一个多样性维度；
- 不把样方数、叶片数、土芯数或距离对数当作处理复制数；
- 不把原论文模型视为默认正确；先检查它是否回答本综述的 estimand。

### 2.1 生物多样性结局身份硬门

禁止使用未展开的 `outcome=biodiversity`。每个结局必须在专项契约中同时声明 `diversity_component × diversity_dimension × measure_family × input_data_type`，再声明是否观测/估计、Hill `q`、grain、extent 和采样完整度。

| 目标 | 必须区分 | 不得直接混合 |
|---|---|---|
| 局地 α | richness、evenness、Shannon entropy、Hill effective diversity；TD/PD/FD；abundance/incidence | 原始 Shannon 与 `exp(H)`；不同 q；不同 grain |
| 区域 γ | 规定 extent 内总/估计有效多样性 | species density 与 total richness；不同 extent 或 sampling units |
| β/组成 | dissimilarity、turnover、nestedness、homogeneity、composition shift | α 丰富度变化；不同距离定义；距离对数当样本量 |
| 遗传多样性 | 指标、标记、时间单位、种群和变化 estimand | 不同指标的方向/尺度未桥接；年份与世代混用 |
| 多功能性 | 平均功能、阈值曲线、Hill-number/effective multifunctionality、多变量函数 | 函数数目当独立样本量；一个指数代表所有构念 |
| 恢复 | resistance、initial response、return rate、distance、completeness、persistence | restored-vs-degraded、restored-vs-reference、change-from-baseline |

最少必填字段为 `grain_area`、`spatial_extent`、`n_sampling_units`、`observed_or_estimated`、`sampling_effort_definition` 和 coverage/standardization 决定。物种密度是在固定 grain/effort 下每单位面积观察到的丰富度，总丰富度是规定 extent 的累积或估计量；二者不是同一 estimand。[Spake et al. 2021](https://doi.org/10.1111/ele.13641)

Hill 数只在构念一致时统一 q=0/1/2 下的分类、系统发育或功能 α 多样性。若把 Shannon entropy 转为有效物种数，记录对数底并使用相应指数变换；不要把此转换套给 β/组成距离或普通 Meta 效应量。采样 effort 不等时优先按 coverage 而非样本量机械稀释，并使用论文的 corrigendum 后版本。[Chao et al. 2021](https://doi.org/10.1111/2041-210X.13682)

## 3. 原始群落矩阵与多样性分解

### 3.1 输入契约

最低输入包括：

- 稳定的 `study_id/site_id/plot_id/time_id/treatment_id`；
- 物种或分类单元列、丰度或出现数据及其数据类型；
- 采样面积、样本数、观测 effort、覆盖度或稀释所需信息；
- 处理分配、对照、空间坐标、时间和嵌套层级；
- 分类学名称原值、接受名称、解析来源和版本；
- 功能性状或系统发育树及匹配失败记录（若适用）。

矩阵必须区分：结构性零、真实缺失、未采样和未知。合并数据前检查采样方法、物种检测、分类分辨率和 effort 是否可比。

### 3.2 estimand 契约

分别定义：

- `alpha`：一个样点/样地或规定 grain 内的有效物种数；
- `gamma`：规定 extent 内合并群落的有效物种数；
- `beta`：在明确分解关系或距离定义下的群落差异；
- Hill 数阶数 `q`：例如 `q=0` 强调丰富度，`q=1` 对常见种平衡，`q=2` 更强调优势种；
- β 多样性是总体差异、turnover、nestedness，还是相对于对照的变化。

若采用 Hill 乘法分解，冻结 `D_beta^q = D_gamma^q / D_alpha^q`，因此处理效应满足 `lnRR_beta = lnRR_gamma - lnRR_alpha`。α、β、γ 由同一矩阵生成且具有确定性关系，不得作为三个独立结局联合拟合；优先联合估计 α 与 γ 后派生 β，或为六个 `component × q` 模型预注册清晰的分开解释。

不要把不同 grain/extent 下的 α、γ 或 β 当成同一结局。`Gonçalves-Souza et al. 2025` 展示了用原始群落数据同时研究 α、β、γ 和 Hill 数的高价值路线，但其空间配对和碎片化定义不能无条件复制到其他生态系统。[论文](https://www.nature.com/articles/s41586-025-08688-7)；[代码](https://github.com/thiago-goncalves-souza/ms-biodiversity-loss-fragmented-landscapes)；[归档](https://doi.org/10.5281/zenodo.14885581)

### 3.3 标准化与依赖

- effort 不等时优先使用基于样本完整度/覆盖度的标准化或有明确目标的稀释/外推；保存完整曲线或目标覆盖度，不只保存最终数值。覆盖度只校正“采得是否完整”，不能消除 grain 与 extent 所代表的真实生态尺度。
- α 比较冻结共同 grain；γ 比较平衡样方数、总采样面积和 extent；β 必须由同一 grain、extent 和 effort 支持下的 α 与 γ 派生。无法统一时停止对应分量，而不是静默更换 estimand。
- 同一群落贡献的多个距离对高度相关；使用站点/研究层级、置换、阻断 bootstrap 或专门的距离矩阵模型，不按距离对数计算自由度。
- 同一矩阵生成多个 `q`、多个分量或多个空间尺度时，将它们视为重复测量/多结局。若用 bootstrap，同一次重抽样同时计算全部分量和 q，以得到研究内完整协方差；重抽独立景观/区组在先，内部样方在后。
- 稀有物种、未识别分类单元和零丰度政策必须做敏感性分析。

## 4. 多维 β 多样性与多变量综合

分类、功能和系统发育 β 多样性不是可互换的三个标签。为每一维冻结：

- 距离或相异度定义及是否具有 turnover/nestedness 分解；
- 性状选择、变换、缺失值处理、距离和降维方法；
- 系统发育树来源、分支长度、修枝和多树不确定性；
- 共同样点、共同对照和共同物种数据造成的跨维协方差；
- 目标是分别估计、比较维度，还是估计联合响应。

若多个维度共享样点、对照或原始矩阵，优先使用多变量/多层模型、显式采样 `V` 或按独立研究聚类的小样本稳健方差；分别拟合后比较置信区间不是正式的维度差异检验。`Li et al. 2025` 可作为多维 β 多样性、共享对照、嵌套结构和稳健推断的压力测试，而非固定模板。[论文](https://www.nature.com/articles/s41467-025-66574-2)；[代码](https://doi.org/10.6084/m9.figshare.30304906)

## 5. 变异性 Meta 分析

### 5.1 选择效应

- `lnVR` 比较 SD 的比例，回答绝对离散程度是否改变；
- `lnCVR` 比较 CV 的比例，回答相对于均值的离散程度是否改变；
- 以方差、稳定性倒数或时序变异为目标时另行定义，不能与组内个体 SD 的 `lnVR` 混为一谈。

先确定方向：正值究竟表示“更不稳定”还是“更稳定”。若展示稳定性，可反号，但同时保留原始 `lnVR/lnCVR`、转换规则和自然尺度解释。

### 5.2 最低输入与警戒线

最低需要每组 `mean, SD, n`、独立单位定义和组间关系。执行以下规则：

- `lnCVR` 要求比率尺度和有意义且远离 0 的均值；均值可为负、跨零或人为中心化时停止；
- 小样本偏倚校正和采样方差必须来自已声明的方法/软件版本，不能只计算 `log(SD_T/SD_C)` 后沿用均值效应方差；
- 处理影响均值时，同时报告 `lnRR` 与 `lnCVR`，避免把均值变化引起的 CV 变化误称为离散度机制；
- 配对、重复测量、共享对照和多个结局必须进入协方差；
- 做替代效应、校正方式、极端 CV 和均值接近 0 的敏感性分析。

`Atkinson et al. 2022` 同时综合恢复对生物多样性水平和变异性的影响，是检验 `lnRR + lnCVR` 双估计量路线的首选开放基准。[论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9320827/)；[数据与代码](https://doi.org/10.17605/OSF.IO/4AUCP)

## 6. 析因实验与交互效应

### 6.1 先定义无交互尺度

对两个二元因子 A、B 的四个单元 `Y00, Y10, Y01, Y11`：

- 加法交互：`(Y11 - Y10) - (Y01 - Y00)`；
- 正值比率尺度上的乘法交互：`log(Y11/Y10) - log(Y01/Y00)`。

两者检验不同的无交互假设。不得看到结局后选择产生“协同”的尺度；应由机制、单位和决策问题预先决定。三个以上因子、连续胁迫或非线性响应需要更一般的对比矩阵/层级模型。

加法与乘法交互会因尺度而改变，非线性主效应、测量变换和未控制混杂也可产生表观交互。契约必须保存 `interaction_scale`、四单元顺序、对比系数、完整单元协方差和非线性/混杂检查；“A 显著而 B 不显著”或“联合处理显著”均不是交互检验。[Duncan & Kefford 2021](https://doi.org/10.1111/2041-210X.13714)（使用前检查 corrigendum）

### 6.2 方差与提取契约

- 提取所有析因单元的均值、SD/SE、独立 `n`、区组/样地和重复测量关系；
- 用对比向量与完整单元协方差计算交互方差；独立单元仅是特例；
- 多个交互共享同一对照或单元时构造跨效应 `V`；
- 区分“联合处理相对对照”的总效应和正式交互效应；前者不能证明协同/拮抗；
- 同时报告单因子效应、联合效应和交互，避免只有交互符号而无生态量级。

`Hong et al. 2022` 的生物多样性×全球变化资料适合作为“相关效应之差”路线和来源完整性反例；其 `ΔNBE` 必须按论文定义和协方差传播，不能因同属析因设计就自动套用四个原始单元的加法公式。Figshare v1 只有图表结果数据、没有核心效应/方差和代码，因此只能做结果表身份核对或现代重建，不能声称论文模型复现。[论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9300022/)；[数据](https://doi.org/10.6084/m9.figshare.16947451.v1)

## 7. 生态系统多功能性

多功能性不是原始观测变量。先建立函数注册表：函数名称、生态方向、单位、测量时间、标准化方式、是否为服务/过程、函数间相关及缺失模式。

至少区分：

- 平均法：将方向统一并标准化的多个函数取平均；
- 单阈值法：超过某个阈值的函数数；
- 多阈值法：在预设阈值范围内考察效应曲线；
- 多变量联合模型：保留各函数及其协方差，不先压成一个指数。

执行以下规则：

- 不以全数据最大值随意标准化而不检查极端值和跨研究可比性；
- 预先冻结“高值更好/低值更好”、阈值范围和函数权重；
- 阈值扫描是一条相关结果曲线，不是数十个独立检验；报告全曲线和同时/重采样不确定性；
- 函数集合不同会改变 estimand；报告共同函数集、研究特异函数集及敏感性分析；
- 不用函数数目代替独立研究数。

Hill-number multifunctionality 是补充路线：把“有多少函数”“函数是否平衡”和“平均功能水平”分开，并对 q、函数集合、方向、标准化、参照和权重做敏感性。它是候选构念而非唯一共识；主报告仍并列个体函数、多变量或阈值路线，不能因一个有效多功能性指数方便就删除其他生态解释。[Byrnes, Roger & Bagchi 2023](https://doi.org/10.1111/oik.09402)

`Lefcheck et al. 2015` 是平均标准化、多阈值和函数集合敏感性的经典基准。[论文、数据与补充脚本](https://www.nature.com/articles/ncomms7936)

## 8. 纵向抗性、恢复力和稳定性

先画时间轴并冻结事件/处理前基线、冲击期、恢复期和目标时间窗。区分：

- resistance：冲击发生时相对基线或对照的变化；
- resilience/recovery rate：冲击后返回参考状态的速度或轨迹；
- recovery extent：在规定时间点达到参考状态的程度；
- temporal stability：时间序列均值相对于时间波动的量，不能与组内个体 CV 混用。

最低契约：样地/实验稳定 ID、年份、观测间隔、处理、事件定义、基线、失访、协议变化和时间相关结构。优先拟合研究内轨迹、分段/非线性模型或一阶段层级模型；若先提取斜率/抗性指标，保留其协方差。不得把每年作为独立研究或凭经验固定 AR(1) 参数而不做替代结构敏感性分析。

`Isbell et al. 2015` 是跨实验重复年份、抗性/恢复力和时间自相关的路由边界基准。[论文](https://www.nature.com/articles/nature15374)；`Vellend et al. 2013` 是长期植物群落变化率综合的补充基准。[论文与 Dataset S1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3845118/)

恢复生态项目另行冻结 reference model、restorative continuum 位置和目标属性；比较对象至少分为 `restored vs degraded`、`restored vs reference` 与 `change from baseline`。Gann et al. (2026) 的第三版原则用于定义目标和实践语境，不把 five-star framework 转成连续效应量、研究质量分或 certainty 分数。[Gann et al. 2026](https://doi.org/10.1111/rec.70441)

## 9. 派生恢复债与恢复程度

恢复债、相对参考状态、恢复百分比等量通常由处理、受损和参考状态多步派生。建立逐效应假设账本：

```text
effect_id, estimand_formula, numerator_source, denominator_source,
reference_state_definition, time_since_action, zero_policy,
missing_variance_route, covariance_terms, assumption_set_id,
biological_interpretation, reviewer, verification_status
```

若参考状态接近零、方向不一致、恢复值越界或方差需要未知相关，停止自动计算并人工裁决。不同参考生态系统、年代或空间尺度不能只因单位相同而合并。非线性恢复模型必须报告观测时间支持，不能把短期曲线外推为完全恢复时间。

`Moreno-Mateos et al. 2017` 用于压力测试参考状态、时间、非线性恢复债、零值和缺失方差假设。[论文](https://www.nature.com/articles/ncomms14163)；[数据](https://doi.org/10.5061/dryad.t5c97)

## 10. 第二阶与 cross-meta 综合

先读取通用 `second-order-meta.md`。本节只补充生态与生物多样性中的 estimand/尺度问题，不把该路线限制为植物生态。

当输入是多个既有 Meta 分析、不同生态功能的 Meta 结果或一组互相重叠的综合时：

1. 建立 `meta_review_id -> dataset_id -> primary_study_id -> outcome/contrast` 重叠图；
2. 对齐每个 Meta 的 PECO、estimand、效应方向、纳入窗口、模型和偏倚处理；
3. 区分 umbrella review 的叙述比较、对 Meta 结果的第二阶定量综合，以及回到原始研究重算；
4. 既有 Meta 的 pooled estimate 不是天然独立，重叠研究会产生未知协方差；
5. 优先回到一级效应数据统一重算；不能重算时，做去重、重叠分层和极端相关敏感性分析；
6. 不以每个 Meta 中的效应行数作为第二阶权重，不把不同 estimand 通过标准化后强行平均。

`Hooper et al. 2012` 与 `Cardinale et al. 2006` 可检验跨功能/多 estimand 综合和丰富度曲线，不应被简化成一张普通森林图。[Hooper](https://www.nature.com/articles/nature11118)；[Cardinale](https://www.nature.com/articles/nature05202)

## 11. 共享对照、多个结局和多个分类群

共享对照是采样误差依赖，不只是“同一研究”随机效应。执行：

1. 为每个处理—对照效应分配唯一 `effect_id`，为同一独立实验分配 `dependency_cluster`；
2. 从共享臂的均值、SD、`n` 和效应量公式推导非对角协方差，或声明并扫描相关参数；
3. 运行 `build_sampling_v.R` 生成带来源和假设清单的 `V`；
4. 用 `run_meta_analysis.R --model multilevel --v-matrix ... --independent-cluster-col ...` 仅拟合其已支持的模型；
5. 以合并处理臂、每研究选择一个预设对比、替代相关、cluster-robust 推断做敏感性分析；
6. 多维结局、跨分类群和可识别性不足时转 `multidimensional_biodiversity` 专项路由。

`Cheng et al. 2024` 是共享单作对照、差分生物多样性效应和多层 `V` 的首个 red-green 基准。[论文](https://www.nature.com/articles/s41467-024-48876-z)；[数据与代码](https://doi.org/10.6084/m9.figshare.24953433)。`Mori et al. 2020` 补充检验凋落物混合处理和多个分解结局的依赖。[论文](https://www.nature.com/articles/s41467-020-18296-w)

## 12. 缺失证据和小研究效应

生态 Meta 常有高异质性、多层依赖、非精度加权和调节变量不平衡。执行以下顺序：

1. 先画研究/报告/效应层级和纳入机制；
2. 检查效应 SE 是否与采样面积、持续时间、处理强度、结局或分类群混杂；
3. 在主模型结构下查看残差与条件漏斗图，而不是只画原始效应漏斗图；
4. 只在独立研究簇和自由度足够时运行适用的回归/选择模型；
5. 用替代权重、模型、效应量、缺失机制和高偏倚风险排除做灵敏度分析；
6. 报告“与某种小研究效应一致/不一致”，不输出“存在/不存在发表偏倚”的二元裁决。

遵循 [Nakagawa et al. 2022](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.13724) 对生态与进化 Meta 中异质性和非独立性的警告。

## 13. 停止规则与最低交付物

遇到以下情况停止自动建模：estimand 未冻结、独立单位不明、原始矩阵 effort 不可比、参考状态无定义、CV 均值跨零、析因单元缺失、纵向相关无法识别、共享对照无法映射、既有 Meta 重叠无法评估，或模型复杂度超出独立簇支持。

最低交付物：

1. 路由 JSON 与阻断理由；
2. 数据层级图和独立单位声明；
3. estimand 数学定义与方向；
4. 原始数据→分析对象的可执行转换及完整日志；
5. `V`、随机结构和假设集合；
6. 主模型、结构敏感性、失败模型和降级路径；
7. 生态适用范围、尺度支持与不可外推区；
8. 与 `plant-biodiversity-benchmark-casebook.md` 中最接近基准的能力对照；
9. 对应机器场景 ID、`test_type`、通过/拒绝 oracle 和 `source_replication_status`；合成 conceptual benchmark 不得写成论文复现。

## 14. 方法来源

- [CEE Guidelines and Standards v5.1](https://collaborationenvironmentalevidence.github.io/CEE_guidelines/index.html)：环境证据综合 conduct 主规范。
- [Nakagawa et al. 2023, Quantitative evidence synthesis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11378872/)；[R tutorial](https://itchyshin.github.io/Meta-analysis_tutorial/)：多层、多变量、依赖、尺度和高级综合的开放指南。
- [Koricheva & Gurevitch 2014](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/1365-2745.12224)：植物生态 Meta 的常见误用和质量门。
- [Spake & Doncaster 2017](https://www.sciencedirect.com/science/article/pii/S0378112717303778)；[作者版](https://eprints.soton.ac.uk/411631/2/1_s2.0_S0378112717303778_main.pdf)：森林生物多样性中的伪重复、参照林分、尺度和权重问题。
- [Gurevitch et al. 2018](https://www.nature.com/articles/nature25753)：研究综合的总体原理与边界。
- [Handbook of Meta-analysis in Ecology and Evolution](https://academic.oup.com/princeton-scholarship-online/book/27898)：理论背景；受版权保护，只做概念和章节级蒸馏。
