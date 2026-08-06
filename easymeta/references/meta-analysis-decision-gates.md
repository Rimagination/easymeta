# Meta 分析关键决策门与错误说法审计

本文件是决策路由，不是统计教材。先定位当前问题命中的门，再读取路由返回的领域资料。任何一门未通过，都不能用森林图、软件输出或期刊等级替代缺失的设计判断。

## 目录

1. 证据综合前置门
2. 少研究与信息量门
3. 效应量转换与自定义估计门
4. 二阶综合与更新门
5. 方法说法审计表
6. 最低输出与主要依据

## 1. 证据综合前置门

当产品是 protocol、systematic review、systematic map、scoping review、rapid review 或 umbrella review 时，本门在所有阶段持续有效，不只在 planning 阶段有效。

进入定量合成前，至少冻结并核验：

- PICO/PECO 或其他适用问题框架、目标 estimand、结局身份、方向、时间窗和适用范围；
- 带日期的协议、注册或时间戳，以及结果知情后的偏离日志；
- 可复现检索、更新日期、去重、双人或有依据的核验式筛选；
- `record -> report -> study -> effect` 映射、重复样本和多报告处理；
- 双人提取/核验、来源定位、风险偏倚和确定性/可信度路线；
- 合并资格、独立抽样簇、依赖结构和不合并方案。

若只有一张现成数据表而上述对象未知，只能把任务标为“给定数据的 quantitative reanalysis/audit”。不得将它包装成完整系统综述，也不得暗示搜索、筛选或偏倚控制已经完成。详细实施读取 `evidence-synthesis-core.md` 及领域 reference。

## 2. 少研究与信息量门

### 2.1 先数什么

用独立抽样簇计数，不用效应行、物种、时间点、处理对比、样方或距离对计数。把 `data.independent_cluster_count` 写入 route plan；分析阶段未知时停止普通 runner 交接。

### 2.2 不存在“k=4 才能做 Meta”的通用下限

- 两项可比研究在数学上可以合并，但这不等于异质性、可推广性或缺失证据可以可靠判断。
- `k=2–3` 时 `tau²`、I²、Knapp–Hartung 区间和预测区间通常极不稳定；`k=4` 不是突然变可靠的分界。
- 研究少不是自动选择共同效应模型的理由；共同效应与随机效应取决于目标总体和可交换性，也不能由 Q 检验 P 值决定。
- REML 只决定 `tau²` 的一种估计方式，不会自动解决少研究推断。并列有依据的区间/异质性敏感性，必要时使用可辩护先验的 Bayesian 模型，并降低结论强度。
- 预测区间在少研究时可能虚假地宽或窄。即使计算，也必须同时说明其分布假设和信息不足。

### 2.3 小研究效应不是发表偏倚诊断

- 独立研究/簇少于 10 时，通常不运行漏斗图不对称检验；达到 10 也只是适用性检查起点，还要有足够精度范围、合理效应量参数化和可用自由度。
- 漏斗不对称可由异质性、设计质量、真实效应修饰、效应量与 SE 的机械相关或偶然性造成。
- Egger、trim-and-fill、fail-safe N、P-curve 或单一选择模型均不能输出“发表偏倚存在/不存在”或“结果可靠”的二元结论。

详细模型规则读取 `effect-size-and-models.md`；医学项目核对 Cochrane Chapters 10 和 13，生态项目同时读取 Nakagawa et al. 2022 与当前 CEE synthesis guidance。

## 3. 效应量转换与自定义估计门

先把转换声明为 `unit_conversion`、`ratio_log_transform`、`correlation_bridge`、`response_ratio_to_smd` 或 `other`。凡来源或目标是 Pearson `r`、Spearman rho、Kendall tau、偏相关、phi 或其他相关性指标，均使用 `correlation_bridge`；`other` 仅用于前四类都不适用的已命名转换，不能作为不确定时的默认项。通用门只加载通用效应量资料；只有生态/环境领域的 `response_ratio_to_smd` 才加载 Lajeunesse (2026)，软件文档只在实现或软件审计时加载。

每个转换建立 assumption ledger：

```text
conversion_id, source_estimand, target_estimand, source_scale, target_scale,
exact_or_approximate, formula_or_code, required_parameters,
variance_or_covariance_propagation, assumption_set_id,
sensitivity_analysis, source_locator, reviewer, human_verified
```

执行规则：

1. 先问转换后是否仍回答同一科学问题。单位统一不等于 estimand 相同。
2. 区分恒等变换、已知参数下的精确转换、依赖分布/基线风险/方差关系的近似转换和经验桥接。
3. 同时传播抽样方差与跨效应协方差。若 `yi*=a*yi`，一致的单位缩放要求 `vi*=a²*vi`，非对角协方差也按对应乘数缩放。
4. Spearman、Kendall、R²、偏相关与 Pearson `r` 不是无条件可互换；转换需要分布、样本设计、其他相关结构或近似公式，并可能改变 estimand。
5. `lnRR/RR` 与 Hedges' d/g 的互换不是通用恒等式。只在完整公式的适用条件、方差传播、离群/边界规则和验证均满足时使用；把一个固定常数乘除所有生态 `lnRR` 不是默认路线。
6. 自定义效应量不因名称不在软件菜单中就“不适合 metafor”。只要估计量及其合法的 `V` 已定义，`rma.mv(yi, V, ...)` 可处理一般估计。软件可接受不等于 estimand 合理。
7. 给模型增加 observation-level 随机效应描述额外真实效应变异；它不会生成共享样本导致的采样协方差，也不会把对角 `vi` 变成正确的非对角 `V`。

任何关键假设未知、转换后方向或解释改变、方差无法传播，或转换只为“把更多研究塞进一个模型”时，停止转换并分层报告或不合并。

## 4. 二阶综合与更新门

### 4.1 以既有 Meta 为输入

设置 `data.level=meta_level` 和 `specialist_triggers.second_order_meta=true`，阻断普通 runner，并读取 `second-order-meta.md`。

先区分：

- umbrella/overview 的结构化比较；
- 对既有 pooled estimates 的二阶定量模型；
- 回到一级研究或效应量统一重算。

既有 Meta 的 pooled estimates 不是天然独立。一级研究重叠会重复计权并造成协方差；不同 PECO、效应尺度、调整策略、时间窗和模型也会破坏可交换性。不得把 review-level “质量总分”乘到逆方差权重上。

### 4.2 更新旧综述

“把新论文追加到旧 CSV 再重跑”不构成合格更新。至少重新检查：

- 问题、资格标准和方法是否仍适用；
- 从旧检索截止日起的系统检索、持续中/待分类研究和灰色文献；
- 旧、新研究的更正、撤稿、版本、重复报告和样本重叠；
- 新研究的筛选、提取和偏倚评价，以及旧研究是否需按新工具重评；
- 效应量定义、软件默认、统计方法和确定性框架是否变化；
- 所有改动、重复查看数据和结论变化的报告。

新增研究数量本身不保证“最终得到确定结论”。更新仍可能受偏倚、异质性、间接性、依赖、选择性报告和重复检验影响。

## 5. 方法说法审计表

先声明审计对象：`conduct`、`reporting`、`effect_model`、`software`、`appraisal` 或 `citation`。一个教程可命中多个对象；例如“遵循 ROSES 且 Egger 证明无偏倚”同时命中 `reporting` 和 `effect_model`。不允许只写笼统的 `audit` 后用统计资料替代报告/实施规范。

| 说法 | 审计结论 | 必须改写为 |
|---|---|---|
| “至少 4 篇才能做 Meta” | 错误的通用阈值 | 报告独立簇数、可合并性和少研究下各估计的不稳定性 |
| “4 篇也可做 Egger，未显著说明无发表偏倚” | 高风险错误 | 少于 10 通常不检验；任何不对称检验都只涉及小研究效应 |
| “REML 已解决少研究问题” | 错误 | REML 只是 `tau²` 候选估计量；还需小样本区间、敏感性和谨慎解释 |
| “I² 很低，研究一致” | 信息不足时错误 | 同时报 I² 不确定性、`tau²`、效应方向和临床/生态异质性 |
| “自定义效应量只能改用 nlme” | 错误 | 先定义估计与 `V`；`metafor::rma.mv` 可接收一般估计 |
| “加 obsID 就解决非独立性” | 错误 | 分开处理 sampling `V`、真实效应随机结构和 robust coefficient inference |
| “统一换成 Pearson r/d 后即可合并” | 通常不成立 | 为每个转换记录 estimand、公式、假设、方差传播与敏感性 |
| “二阶 Meta 按质量分加权” | 不安全 | 用设计适当的 RoB/方法学评价做排除、分层或敏感性；权重不使用任意总分 |
| “追加新研究即可更新并逐渐获得确定性” | 不完整 | 重新执行更新搜索、资格、完整性、评价、方法和报告流程 |
| “漏斗、fail-safe N、trim-and-fill 都通过，因此结果可靠” | 错误 | 分别报告方法适用性、假设和局限，不给二元可靠性裁决 |
| “Nature/Science 已采用，所以方法正确” | 错误 | 期刊和引用量不是方法验证；重建 estimand、设计、依赖与假设 |

审计还要核对引用是否真的支持所述数据、对象和公式。题名、期刊、卷页、DOI、研究对象或结果表与正文不一致时，先回原文和更正页，不把引文数量当作佐证。

## 6. 最低输出与主要依据

每次命中本文件至少输出：命中的门、已知信息、缺失信息、停止/继续决定、需读 reference、需核对的 living source、允许的最强结论和人工确认点。

主要依据：

- [Cochrane Handbook Chapter 10](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10)
- [Cochrane Handbook Chapter 13](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-13)
- [Cochrane Handbook Chapter IV: Updating a review](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-iv)
- [Cochrane Handbook Chapter V: Overviews of Reviews](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-v)
- [`metafor::rma.mv` official reference](https://wviechtb.github.io/metafor/reference/rma.mv.html)
- [Jüni et al. 1999, hazards of quality scores](https://doi.org/10.1001/jama.282.11.1054)
- [Lajeunesse 2026, response-ratio conversions](https://doi.org/10.1111/ele.70335)
