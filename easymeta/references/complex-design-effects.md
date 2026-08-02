# 复杂研究设计效应量：P1-1 执行契约

## 目录

1. 适用范围与边界
2. 共同输入、输出与版本
3. 配对连续结局
4. 交叉试验连续结局
5. 两组变化值与 BACI 加法对比
6. 已报告的群集校正估计
7. 相关假设治理
8. 硬性拒绝条件
9. 命令与验证
10. 主要依据

## 1. 适用范围与边界

使用 `scripts/calculate_complex_effects.R` 把完整 `raw_extraction` CSV 转换为现有分析阶段校验器可接受的 `analysis_effect` CSV。脚本仅实现五个边界清晰的逐行路线：

- `paired_continuous_md`：同一受试者或匹配单元的两条件连续结局 MD；
- `crossover_continuous_md`：已确认可采用配对对比且 carryover 已清除的连续结局 MD；
- `two_group_change_md`：两个独立组的变化值之差；
- `baci_additive_md`：简单加法 BACI 对比；
- `cluster_adjusted_generic`：原报告已经按群集设计校正的估计及其不确定性。

本工具不计算 SMD，不处理二分类配对/交叉数据，不从个体数据拟合模型，不校正 period/sequence effect，不分析 cluster-crossover，也不处理具有多地点、多时间、嵌套采样或时空协方差的 replicated BACI。遇到这些问题应停止并使用设计专用模型。

“能够代入公式”不等于设计适用。每行都必须给出 `design_applicable=yes` 和非空 `design_applicability_basis`；否则脚本拒绝。

## 2. 共同输入、输出与版本

从 `assets/complex_effect_input_template.csv` 复制完整表头。示例行仅用于解释字段，真实项目必须替换所有数值和来源。

版本分三层：

- 原始提取 schema：`schema_version=1.0.0`、`data_stage=raw_extraction`；
- P1-1 扩展契约：`complex_effect_contract_version=1.1.0`；
- 计算器：`calculator_version=1.1.0`；
- 输出仍使用现有 `analysis_effect` schema `1.0.0`，以兼容 `validate_extraction.py --stage analysis`。

每行必须保留现有 raw 契约的身份、出处、提取者、核验者、日期和状态字段。脚本把所有原始字段复制到输出，并新增：

- `complex_effect_route`、`calculation_method`；
- `design_formula`、`sd_derivation`、`effect_orientation`；
- `correlations_used`、`assumption_audit`；
- `uncertainty_route`、`cluster_adjustment_audit`；
- `effective_sample_size_audit`；
- `yi`、`vi`、`sei`、`measure`、`analysis_scale`、`display_transform`。

一个输出文件只能有一个 `analysis_scale`。MD 路线产生 `identity`；群集通用路线可产生显式声明的现有分析尺度。若输入将产生混合尺度，脚本在写出前拒绝，必须拆分文件。

## 3. 配对连续结局

固定方向为：

\[
MD=\bar X_{condition\ 1}-\bar X_{condition\ 2}.
\]

设置：

- `complex_design=paired_continuous_md`；
- `effect_measure=MD`；
- `reported_value_scale=identity`；
- `target_analysis_scale=identity`；
- `contrast_definition=condition_1_minus_condition_2`；
- `carryover_cleared=not_applicable`。

### 3.1 已报告差值及差值 SD

设置 `paired_input_pathway=direct_difference`，提供 `n_pairs`、`mean_difference`、`sd_difference`。计算：

\[
y_i=\bar D,\qquad v_i=\frac{SD_D^2}{n_{pairs}}.
\]

同时设置 `paired_correlation_status=not_used`，并将条件均值、条件 SD、相关、`assumption_set_id` 和 `correlation_source` 留空。`n_pairs` 是实际进入配对分析的完整配对数；不能用最初入组数替代。

### 3.2 由两条件 SD 与相关推导差值 SD

设置 `paired_input_pathway=derived_from_conditions`，提供 `n_pairs`、两条件均值和 SD，以及 `paired_correlation`：

\[
\bar D=\bar X_1-\bar X_2,
\]

\[
SD_D=\sqrt{SD_1^2+SD_2^2-2rSD_1SD_2},
\qquad
v_i=\frac{SD_D^2}{n_{pairs}}.
\]

`paired_correlation_status` 只能是 `reported` 或 `assumed`。两条数值路径互斥；脚本拒绝把已报告差值字段和条件字段混在同一行。

## 4. 交叉试验连续结局

数值路径与配对 MD 相同，但设置 `complex_design=crossover_continuous_md`。此外必须：

- `carryover_cleared=yes`；
- `carryover_assessment_source` 指向 carryover、washout、period/sequence 处理的原文或分析说明；
- `design_applicability_basis` 解释为何该配对对比可估计计划中的处理效应。

`carryover_cleared=no`、`unclear` 或空值均阻断计算。脚本不会把“存在 washout”自动等同于 carryover 已清除，也不会自行校正 period 或 sequence effect。若结局不可逆、效应持续到下一阶段、报告只给出不适当的平行组汇总，或为 cluster-crossover，停止并使用专门分析。

## 5. 两组变化值与 BACI 加法对比

两条路线都固定：

- `change_definition=post_minus_pre`；
- `contrast_definition=intervention_minus_comparator`；
- `group_independence=yes`，并提供 `independence_basis`；
- `effect_measure=MD`，输入和目标尺度均为 `identity`。

计算：

\[
y_i=(\bar X_{I,post}-\bar X_{I,pre})-
    (\bar X_{C,post}-\bar X_{C,pre}),
\]

\[
v_i=\frac{SD_{\Delta I}^2}{n_I}+
    \frac{SD_{\Delta C}^2}{n_C}.
\]

这里 `I/C` 在 `two_group_change_md` 中表示干预/对照，在 `baci_additive_md` 中表示 impact/control。正值始终表示 intervention 或 impact 的 post-minus-pre 变化更大。

每组分别选择 SD 路径：

- `reported_change_sd`：提供该组 `sd_change_*`，相关状态设为 `not_used`；
- `derived_pre_post`：提供该组 pre SD、post SD、pre-post 相关，差值 SD 为

\[
SD_\Delta=\sqrt{SD_{pre}^2+SD_{post}^2-2rSD_{pre}SD_{post}}.
\]

两个组可以选择不同 SD 路径，但任一 `derived_pre_post` 都必须有显式相关及来源。

这个 BACI 路线只表示单个独立 impact 组与单个独立 control 组的加法均值对比。传统单地点 BACI 的伪重复、时间交互和缺乏独立对照不会被公式修复；多地点、多时点或层级 BACI 应进入混合、时空或专门生态模型，而不是把所有观测压成一个虚假独立 MD。

## 6. 已报告的群集校正估计

设置：

- `complex_design=cluster_adjusted_generic`；
- `contrast_definition=reported_adjusted_effect`；
- `cluster_adjusted_estimate=yes`；
- `cluster_adjustment_method` 与 `cluster_adjustment_source` 非空；
- `effect_estimate` 为原报告的设计调整估计；
- `uncertainty_type` 明确为 `se`、`vi` 或 `ci`。

不确定性路径严格互斥：

- `se`：只提供标准字段 `se`，计算 `vi=se^2`；
- `vi`：只提供标准字段 `variance`；
- `ci`：提供 `ci_lower`、`ci_upper`、比例形式 `ci_level`（如 `0.95`）、`ci_distribution=normal|t`；t 区间还必须提供 `ci_df`。

`reported_value_scale` 规定报告值所在尺度：

- 已经位于分析尺度：直接填 `identity`、`log`、`fisher-z`、`logit` 等，并令 `target_analysis_scale` 完全相同；
- 原尺度比值及完整 CI：填 `natural_ratio`，目标必须为 `log`；
- 原尺度相关及完整 CI：填 `natural_correlation`，目标必须为 `fisher-z`。

自然尺度比值或相关的 SE/vi 不会被当成 log/Fisher-z 尺度不确定性；这些情况被拒绝。CI 路线仅适用于与正态或 t 型对称区间兼容的 SE 重建。默认拒绝分析尺度上明显不对称的区间；只有核实区间构造并记录理由后，才可显式使用 `--allow-asymmetric-ci yes`。

`n_total` 和可选的 `effective_sample_size` 只作为原始审计信息保留，绝不进入 `yi` 或 `vi`。因此，仅有有效样本量、设计效应或 ICC，而没有已经报告的调整估计及 SE/vi/CI，不能运行此路线。需要从原始群集汇总数据做近似校正时，应另建经统计负责人批准的专用实现，不能冒充“已报告调整估计”。

## 7. 相关假设治理

相关状态使用：

- `not_used`：该路径不使用相关；相关数值必须为空；
- `reported`：相关来自本研究或可核验分析；必须提供 `correlation_source`；
- `assumed`：相关为借用、插补或情景值；必须同时提供 `assumption_set_id` 和 `correlation_source`。

`correlation_source` 应说明相关来自哪一报告、表格、作者回复、外部数据集或预设推理。一个 BACI 行内有两个相关时，在同一字段中分别写明 intervention/impact 与 comparator/control 的来源。

每个假定相关必须预先建立多个合理情景，例如 `rho=0.3/0.5/0.7`，为每个情景使用不同 `assumption_set_id` 生成独立分析文件，并比较权重、合并效应和结论。不要根据哪一个相关产生显著结果来选择主分析。

## 8. 硬性拒绝条件

任一情况都会停止且不写分析文件：

- 原始提取字段或 1.1.0 扩展字段不完整；
- `design_applicable` 不是 `yes`，或缺少适用性依据；
- 非 crossover 行声明 carryover 状态，或 crossover 未明确清除 carryover；
- 输入路径混用、未使用字段仍有值、方向定义不匹配；
- 样本量不是整数或小于 2，SD、SE、vi 或推导方差非正；
- 使用相关却未说明状态/来源，或假定相关没有 `assumption_set_id`；
- 两组变化/BACI 的组并非独立，或 change 方向不是 post-minus-pre；
- 群集估计未明确为已调整、无调整方法/来源、仅有有效样本量；
- 自然比值/相关只给 SE/vi，CI 不完整，或 CI 与估计/尺度矛盾；
- `effect_measure` 与目标分析尺度不兼容；
- 同一输出会混合多个 `analysis_scale`。

## 9. 命令与验证

PowerShell：

```powershell
$skill = Resolve-Path './easymeta'
$Rscript = if ($env:R_SCRIPT) { $env:R_SCRIPT } else { 'Rscript' }
$output = Join-Path ([IO.Path]::GetTempPath()) 'complex-analysis-effects.csv'

& $Rscript "$skill\scripts\calculate_complex_effects.R" `
  --input "$skill\assets\complex_effect_input_template.csv" `
  --output $output `
  --overwrite yes

python "$skill\scripts\validate_extraction.py" `
  $output `
  --stage analysis --allow-warnings
```

脚本同时生成同名 `.manifest.txt`。运行后检查 `calculation_method`、`design_formula`、`sd_derivation`、`correlations_used`、`assumption_audit`、`uncertainty_route` 和原文定位，不要只检查 `yi/vi`。

## 10. 主要依据

- Cochrane Handbook version 6.5, Chapter 6, *Choosing effect measures and computing estimates of effect*：变化值 SD、pre-post 相关、通用逆方差及尺度方向。https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
- Cochrane Handbook version 6.5, Chapter 23, *Including variants on randomized trials*：配对/交叉分析、carryover、群集试验及已正确调整估计的通用逆方差合并。https://training.cochrane.org/handbook/current/chapter-23
- `metafor` 官方 `escalc()` 参考：效应量与抽样方差的输入语义。https://wviechtb.github.io/metafor/reference/escalc.html
- Morris SB. 2008. *Estimating Effect Sizes From Pretest-Posttest-Control Group Designs*. Organizational Research Methods 11:364–386. https://doi.org/10.1177/1094428106291059
- Underwood AJ. 1994. *On Beyond BACI: Sampling Designs that Might Reliably Detect Environmental Disturbances*. Ecological Applications 4:3–15. https://doi.org/10.2307/1942110

上述在线资料核对日期：2026-08-02。当前脚本采取比 Cochrane 的某些近似群集校正选项更窄的政策：P1-1 的 `cluster_adjusted_generic` 只接收原报告已经调整的估计及不确定性，不实施仅基于有效样本量的近似重建。
