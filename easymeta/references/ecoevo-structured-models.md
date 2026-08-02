# 生态与进化结构化 Meta 模型

## 适用边界

P1-3 首版 runner 只拟合“已冻结系统发育相关矩阵”的聚合数据多层 Meta 模型：

```r
rma.mv(
  yi, V,
  random = list(
    ~ 1 | study_re_id,
    ~ 1 | phylo_id,
    ~ 1 | species_iid_id,
    ~ 1 | effect_re_id
  ),
  R = list(phylo_id = A),
  Rscale = "none",
  control = list(nearpd = FALSE)
)
```

默认候选同时包含系统发育 species 相关项和非系统发育 species IID 项：前者表示共同进化历史，后者表示物种层面但不由树解释的相似性。只在设计上不可识别、明确的科学理由或预注册敏感性规格下关闭 IID 分量；不得按 P 值、边界估计或结论方向事后删项。不要为了获得收敛而自动删除随机项、固定参数、改变矩阵或使用 `nearPD()`。[Cinar et al. 2022](https://doi.org/10.1111/2041-210X.13760)

空间和时间结构在首版中是“可验证、不可拟合”：

- 距离矩阵可用 `validate_structure_matrix.py --type distance` 检查；
- `run_ecoevo_meta_analysis.R` 收到 `structure_type=spatial` 或 `temporal` 时必须明确停止；
- 不得把成功的矩阵验证写成成功的空间/时间模型分析。

## 数据与矩阵契约

效应表至少包含：

```text
effect_id,study_id,species_id,yi,vi,analysis_scale
```

- `effect_id` 必须唯一；`study_id` 表示独立抽样簇。
- `yi` 必须有限，`vi` 必须有限且大于零。
- 不允许模型字段缺失或静默删行。
- 调节变量公式必须显式列出字段；禁止 `.`，设计矩阵必须满秩，独立研究数必须大于固定效应系数数。

矩阵 CSV 的第一列是行 ID，后续列名是列 ID。例如：

```csv
id,sp1,sp2
sp1,1,0.4
sp2,0.4,1
```

所有矩阵都必须满足：

- 行 ID、列 ID 非空且唯一，二者集合相同；
- 与效应表所用 ID 集合精确一致；按 ID 映射，不按文件位置猜顺序；
- 数值有限、方阵、对称；不修改源矩阵。

三类矩阵的附加条件：

- `correlation`：对角线为 1，元素位于 `[-1,1]`，严格正定；
- `distance`：对角线为 0、非负、满足三角不等式，必须声明单位和计算方法；默认还要求双中心 Gram 矩阵半正定，即距离可欧氏嵌入；
- `sampling_v`：半正定、对角线大于零，且按 effect ID 与效应表 `vi` 一致。

在模型图中把两类矩阵分开：sampling `V` 表示效应估计误差的协方差；phylogenetic `A` 只约束真实效应的系统发育随机项。不得把 `A` 乘以 `vi` 冒充 sampling `V`，也不得因加入 `A` 就省略共享样本、多结局或重复测量的抽样协方差。

验证示例：

```powershell
$skill = Resolve-Path './easymeta'
$validate = Join-Path $skill 'scripts/validate_structure_matrix.py'
python $validate `
  'phylogenetic_correlation.csv' --type correlation `
  --data 'analysis_effects.csv' --id-col species_id `
  --report 'phylogenetic_correlation.validation.json'
```

```powershell
python $validate `
  'sampling_V.csv' --type sampling_v `
  --data 'analysis_effects.csv' --id-col effect_id --vi-col vi
```

```powershell
python $validate `
  'site_distance.csv' --type distance `
  --data 'analysis_effects.csv' --id-col site_id `
  --distance-unit km --distance-method 'great-circle WGS84'
```

## 运行系统发育模型

复制并完成 `assets/ecoevo_model_spec_template.json`。矩阵路径相对于 spec 文件解析；树/矩阵来源、版本、分支长度方法和修枝规则不得保留占位符。

```powershell
$Rscript = if ($env:R_SCRIPT) { $env:R_SCRIPT } else { 'Rscript' }
$runEcoEvo = Join-Path $skill 'scripts/run_ecoevo_meta_analysis.R'
& $Rscript $runEcoEvo `
  --spec 'ecoevo_model_spec.json'
```

成功时只写：

- `coefficients.csv`
- `variance_components.csv`
- `analysis_manifest.json`
- `model.rds`

runner 使用 `rma.mv(R=list(phylo_id=A), Rscale="none")`，请求方差分量 Hessian，并强制 `nearpd=FALSE`。若优化不收敛、出现模型警告、方差分量落在预设边界、Hessian 不完整/非有限/非正定，立即停止且不自动简化。清单还记录方差分量估计相关矩阵中最大的非对角绝对相关；即使 Hessian 通过，相关接近 1 仍提示多个方差来源难以分离，必须降级解释并用预设敏感性模型核查。

若另行对系数使用按 study 的 CR2/CRVE，它只改变系数推断，不能替代 `study + phylogeny + species_iid + effect` 的真实效应结构。尤其在 `study × species/phylogeny` 交叉依赖中，单向 study 聚类不能被宣称为另一维的保险；无可辩护的多层结构或多向依赖方案时停止并交给 specialist。[Williams et al. 2025](https://doi.org/10.1111/2041-210X.70156)；[Pustejovsky & Tipton 2022](https://doi.org/10.1007/s11121-021-01246-3)

## 混杂与不可识别

在拟合前比较随机效应分区：

- species 与 study 完全一一对应且同时拟合 study IID 与 species IID 时拒绝；
- 每研究仅一个 effect 且同时拟合 study IID 与 effect IID 时拒绝；
- 每物种仅一个 effect 且同时拟合 species IID 与 effect IID 时拒绝。

系统发育分量使用 `A`，species IID 分量使用单位相关结构；二者含义不同。即使数值上能够拟合，也必须由研究者证明树版本、分类名解析、修枝规则、采样层级和独立簇定义正确。

拟合前还要冻结 `prediction_target`。例如“目标总体中的新 study、新 species”需考虑 study、phylogeny/species 和 effect 方差；“同一已知 species 的新 effect”所需分量不同。首版 runner 不自动生成结构化 prediction interval；未实现目标特异预测时，只报告均值及方差分量，不用普通 `predict()` 冒充所有生态目标的预测。

## 必须另行完成的敏感性分析

首版 runner 只执行一个冻结模型，不批量搜索规格。研究者应在方案中分别预设并运行：仅 species IID、系统发育加 species IID、替代树/矩阵，以及按独立研究簇删除的分析。主分析一般保留 phylogeny + species IID；仅 species IID 是结构敏感性，不是看到系统发育方差“不显著”后的替换。方差与相关参数还应检查 profile；profile 平坦或边界结果不得解释为已识别的结构效应。

Williams et al. (2025) 的比较只在其模拟域内支持优先多层模型/VCV：研究与物种数量、每研究效应数、恒定非负相关和近似正态抽样误差均有限定。对于更少研究、负值或变化相关、严重错估 sampling variance、重尾/零膨胀或复杂时空多向聚类，结论必须降级为未经该模拟验证，并增加定制模拟或 specialist review。
