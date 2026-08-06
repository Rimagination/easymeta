# 第二阶 Meta、Umbrella Review 与跨综述综合

本文件处理 `data.level=meta_level`：输入单位是既有系统综述、Meta 分析或其 pooled estimates。它不等同于普通研究级 Meta，也不授权把 review-level summary 当作相互独立的 `yi/vi`。

## 目录

1. 先选择产品
2. 建立可审计输入
3. 处理一级研究重叠
4. 对齐 estimand 与不确定性
5. 评价综述而不制造质量权重
6. 定量路线与停止规则
7. 更新与报告

## 1. 先选择产品

在协议中只选择一个主要目标：

| 产品 | 主要单位 | 适用目标 |
|---|---|---|
| Overview/umbrella review | 系统综述及其证据体 | 描述、比较和评价多个综述 |
| 第二阶定量综合 | 可交换且不确定性可审计的 review-level estimates | 估计跨 Meta 的上层分布或关系 |
| 一级研究重分析 | 去重后的 primary studies/effects | 用统一 PECO、estimand 和模型重新综合 |

如果目标是回答一个新的、精确的干预/暴露问题，而现有综述重叠严重、过时或方法不兼容，优先回到一级研究。不得为节省提取工作而选择统计上不成立的第二阶路线。

## 2. 建立可审计输入

每个综述至少记录：

```text
meta_review_id, protocol_or_registration, search_end_date, databases,
PECO_or_PICO, eligible_designs, outcome_and_timepoint, estimand,
effect_measure_and_scale, adjustment_status, model, tau2_method,
interval_method, primary_study_ids, pooled_estimate, uncertainty_type,
risk_of_bias_tool, certainty_framework, corrections_status, source_locator
```

同一综述中的多个结局、比较或模型不是新的独立综述。为每个候选 summary 分配 `meta_effect_id`，保留其 review、evidence body 和 primary-study 集合。

## 3. 处理一级研究重叠

建立 `meta_review_id × primary_study_id` citation matrix，并在 outcome/contrast/timepoint 层面细化。仅按论文 DOI 去重可能漏掉同一研究的多篇报告。

重叠带来两类问题：

- 同一一级研究被多次计权，给某些数据过大影响；
- review-level estimates 的抽样误差相关，忽略协方差会产生过窄区间。

至少报告重叠图、重叠研究的数量/权重和采用的处置。Corrected Covered Area 可作描述，但不是协方差矩阵，也不能单独修复重复计权。

优先顺序：

1. 回到一级数据去重并统一重算；
2. 按预设的最新、最全面、最相关或最低偏倚标准选择一个综述；
3. 在能构造/近似 review-level covariance 时用多变量或广义最小二乘路线；
4. 无法识别协方差时做去重、重叠分层和极端相关敏感性，并降低结论强度；
5. 重叠无法评估且会影响目标时停止定量合并。

## 4. 对齐 estimand 与不确定性

合并前逐项核对：人群/生态系统、干预/暴露、比较、结局定义、时间窗、研究设计、调整集、效应方向、分析尺度和目标总体。名称相同的“biodiversity”“mortality”或“effect size”不证明 estimand 相同。

不得把以下对象仅靠标准化强行平均：

- OR、RR、HR 与风险差；
- 调整和未调整估计；
- endpoint 和 change score；
- 不同 Hill order、grain/extent 或多样性分量；
- pooled mean、prediction interval、moderator coefficient 与异质性指标。

确认传入的是 estimate 的 SE/variance，而不是一级研究平均 SE、`tau²`、I² 或置信区间宽度。若转换 review-level estimate，使用 `meta-analysis-decision-gates.md` 的转换账本并传播协方差。

## 5. 评价综述而不制造质量权重

分别保存：

- 综述 conduct/methodological quality 或 risk of bias；
- 一级研究的 risk of bias；
- body-of-evidence certainty/confidence；
- 报告完整性。

这些对象不可互换、不可求和成单一“质量分”。禁止用任意 review quality score 乘以逆方差权重；该做法把题项选择和评分尺度伪装成统计信息。可在协议中把适用的 RoB/方法学判断用于纳入标准、分层、敏感性分析或 certainty 解释，并报告改变了什么。

## 6. 定量路线与停止规则

普通 `run_meta_analysis.R` 保持阻断。专项统计审查必须声明：

- 第二阶目标总体和 independent unit；
- review-level sampling covariance；
- 一级研究重叠处置；
- review 内多个 estimate 的依赖；
- 一级与二级异质性的解释；
- 小 review 数量下的区间和先验敏感性；
- 预测目标和可外推范围。

在以下任一情形停止自动定量合并：estimand 不可对齐、一级研究列表缺失、重叠无法评估、review-level uncertainty 来源不明、同一数据被重复计权、质量分拟作权重，或二级模型复杂度超出独立 review 数支持。

## 7. 更新与报告

旧综述加入新研究时，按 `meta-analysis-decision-gates.md` 的更新门重新执行搜索、资格、完整性、提取、偏倚评价、方法核对与报告；不要把旧 pooled estimate 与新一级研究效应直接当作两个独立输入。

最低交付物：产品选择及理由、review–study overlap matrix、estimand alignment table、纳入/优先规则、评价工具和版本、定量或不合并决定、重叠/相关敏感性、协议偏离、更新日期和结论适用边界。

主要依据：

- [Cochrane Handbook Chapter V: Overviews of Reviews](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-v)
- [JBI Manual for Evidence Synthesis](https://synthesismanual.jbi.global)
- [PRIOR statement](https://doi.org/10.1136/bmj-2022-070849)
- [Jüni et al. 1999](https://doi.org/10.1001/jama.282.11.1054)

