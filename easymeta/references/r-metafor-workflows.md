# R / `metafor` 可审计工作流

## 目录

1. 原则与依赖
2. CSV 输入契约
3. 计算效应量
4. 拟合模型
5. 高级 `metafor` 工作流
6. 输出文件
7. 结果前的最低校验
8. 主要官方资料

## 1. 原则与依赖

三个 R 脚本是保守型命令行工具：

- `calculate_effect_sizes.R`：把明确列映射的汇总数据转换为 `yi`、`vi` 和 `sei`；
- `build_sampling_v.R`：按显式 `vcalc()` 设计字段和 `rho`/`phi` 情景生成抽样协方差矩阵；
- `run_meta_analysis.R`：读取已在正确分析尺度上的 `yi/vi`，拟合共同效应、随机效应或多层/多变量模型。

P1 specialist 工具保持独立入口：`calculate_complex_effects.R` 处理显式复杂设计效应；`run_diagnostic_meta.R`、`run_dose_response.R`、`run_network_meta.R` 处理边界明确的医学专科模型；`run_ecoevo_meta_analysis.R` 只处理已验证的系统发育相关矩阵。空间和时间结构在 P1 仅验证并停止。不得把 specialist 失败静默降级为本文件的普通 runner。

脚本不会安装包、猜测列名、猜测效应尺度、自动选择模型、自动连续性校正或静默删除缺失行。三个 R 脚本只依赖 base R 和 `metafor`；CR2 额外依赖 `clubSandwich`。若包缺失，会给出可执行的安装提示，但不会自行安装。

从仓库根目录用 PowerShell 调用 R；若 `Rscript` 不在 `PATH`，先设置 `R_SCRIPT`：

```powershell
$skill = Resolve-Path './easymeta'
$Rscript = if ($env:R_SCRIPT) { $env:R_SCRIPT } else { 'Rscript' }
& $Rscript (Join-Path $skill 'scripts/calculate_effect_sizes.R') --help
& $Rscript (Join-Path $skill 'scripts/run_meta_analysis.R') --help
```

先在项目自己的 R 库中准备依赖；不要在技能目录安装包：

```r
install.packages("metafor")
# 仅在明确需要 CR2 时：
install.packages("clubSandwich")
```

## 2. CSV 输入契约

- 文件必须是 UTF-8 CSV；首行为唯一列名。
- 数值列只允许数值或空值；字符值不会被静默转成 `NA`。
- `vi` 是抽样方差且必须 `>0`，不是 SE。
- 传入 `run_meta_analysis.R` 的 `yi` 必须来自通过校验的 `analysis_effect` 文件；CLI `--analysis-scale` 必须与文件中的 `analysis_scale` 每行一致。
- runner 支持 `identity`, `log`, `fisher-z`, `logit`, `arcsine`, `arcsine_difference`, `sqrt`, `sqrt_difference`, `analysis`。差值型或未指定语义的 `analysis` 尺度不伪造原尺度解释。
- 每次运行必须用 `--independent-cluster-col` 指定独立研究/抽样单元。不得用 effect ID 人为增加独立簇数。
- 默认缺失值策略是 `fail`。只有显式 `--na-action omit` 才删除模型所需字段缺失的行，并生成 `excluded_rows.csv`。
- 默认不覆盖已有输出。要覆盖脚本自己的已知输出文件，显式使用 `--overwrite yes`。

## 3. 计算效应量

完整参数以 `--help` 为准。列名通过 `--*-col` 显式映射。

```powershell
$calc = Join-Path $skill 'scripts/calculate_effect_sizes.R'
```

### 3.1 二分类：log RR

无零格时：

```powershell
& $Rscript $calc `
  --input 'binary.csv' --output 'effects_rr.csv' --measure RR `
  --ai-col event_treat --bi-col nonevent_treat `
  --ci-col event_control --di-col nonevent_control
```

存在零格时必须明确校正规则；下例仅对含零格的研究四格均加 0.5，并明确保留双零研究。若产生不可计算值，脚本会停止：

```powershell
& $Rscript $calc `
  --input 'binary.csv' --output 'effects_rr.csv' --measure RR `
  --ai-col event_treat --bi-col nonevent_treat `
  --ci-col event_control --di-col nonevent_control `
  --zero-policy only0 --add 0.5 --drop-double-zero no
```

连续性校正不是默认推荐。稀有事件的主分析通常应回到原四格表，比较 `rma.mh()`、条件满足时的 `rma.peto()` 和适当 `rma.glmm()`。

### 3.2 连续结局：Hedges' g

```powershell
& $Rscript $calc `
  --input 'continuous.csv' --output 'effects_smd.csv' --measure SMD `
  --m1i-col mean_treat --sd1i-col sd_treat --n1i-col n_treat `
  --m2i-col mean_control --sd2i-col sd_control --n2i-col n_control `
  --bias-correction yes --vtype LS
```

`SMD` 的正值表示第一组均值更高。若量表方向不同，先按方案统一方向。`--bias-correction yes` 对应 Hedges' g；`no` 只有在明确需要未校正 d 时使用。

### 3.3 相关系数：Fisher z

```powershell
& $Rscript $calc `
  --input 'correlations.csv' --output 'effects_zcor.csv' --measure ZCOR `
  --ri-col r --ni-col n
```

同一研究多个相关系数的 `yi/vi` 仍然相关；本脚本不会猜协方差。后续按设计使用 `rcalc()`/`vcalc()` 构造 `V`。

### 3.4 已报告 OR 与 95% Wald CI

```powershell
& $Rscript $calc `
  --input 'adjusted_or.csv' --output 'effects_or.csv' --measure GEN `
  --yi-col odds_ratio --uncertainty ci `
  --ci-lb-col lower --ci-ub-col upper `
  --input-scale ratio --ci-level 95 --ci-distribution normal
```

输出 `yi=log(OR)`。若原报告使用 t 区间，必须提供自由度：

```powershell
& $Rscript $calc `
  --input 'estimates.csv' --output 'effects_md.csv' --measure GEN `
  --yi-col estimate --uncertainty ci `
  --ci-lb-col lower --ci-ub-col upper `
  --input-scale analysis --ci-level 95 --ci-distribution t --df-col df
```

若已有 `vi` 或 SE，输入必须已经在分析尺度：

```powershell
& $Rscript $calc `
  --input 'generic.csv' --output 'effects.csv' --measure GEN `
  --yi-col log_hr --uncertainty se --se-col se_log_hr `
  --input-scale analysis
```

脚本会写主 CSV、同名 `.manifest.txt`，以及在显式 `--na-action omit` 时写同名 `.excluded.csv`。

## 4. 拟合模型

设置路径示例：

```powershell
$fit = Join-Path $skill 'scripts/run_meta_analysis.R'
```

### 4.1 共同效应

```powershell
& $Rscript $fit `
  --input 'effects_md.csv' --output-dir 'meta_common' `
  --model common --yi-col yi --vi-col vi `
  --independent-cluster-col study_id `
  --analysis-scale identity --prediction no
```

共同效应使用 `rma.uni(method="EE", test="z")`。不要因为 Q 检验不显著就自动选择它。

### 4.2 随机效应与预测区间

```powershell
& $Rscript $fit `
  --input 'effects_rr.csv' --output-dir 'meta_random' `
  --model random --yi-col yi --vi-col vi `
  --independent-cluster-col study_id `
  --analysis-scale log --tau-method REML --test knha `
  --prediction yes --level 95 `
  --sensitivity-tau 'REML,PM,DL' `
  --sensitivity-test 'knha,z' --leave-one-out yes
```

`analysis-scale=log` 只控制展示列的 `exp()` 反变换，不改变拟合输入。输出同时保留分析尺度和展示尺度。预测区间由 `metafor::predict()` 计算；研究很少时必须按方法文档谨慎解释。

### 4.3 Meta 回归

```powershell
& $Rscript $fit `
  --input 'effects.csv' --output-dir 'meta_regression' `
  --model random --yi-col yi --vi-col vi `
  --independent-cluster-col study_id `
  --analysis-scale identity --tau-method REML --test knha `
  --moderators '~ scale(mean_age) + habitat' `
  --prediction no
```

公式必须以 `~` 开头；脚本禁止 `.` 通配符并检查公式涉及的列。`scale()`、交互项等仍需研究者解释。含调节变量的预测必须对应明确的新协变量值；通用 CLI 不猜测这些值，因此建议读取保存的 bundle，并在审核过的 R 代码中调用 `predict(bundle$base_model, newmods=...)`。

### 4.4 多层模型（对角抽样方差）

```powershell
& $Rscript $fit `
  --input 'effects_multi.csv' --output-dir 'meta_multilevel' `
  --model multilevel --yi-col yi --vi-col vi `
  --independent-cluster-col study_id `
  --analysis-scale fisher-z `
  --random '~ 1 | study_id/effect_id' `
  --mv-method REML --test t --dfs residual `
  --prediction yes `
  --prediction-target 'new study and new effect' `
  --prediction-components 'study,effect'
```

把 `V=vi` 传给 `rma.mv()` 只表达对角抽样方差；嵌套随机效应表达真实效应层级，不代表同一被试或共享对照导致的抽样误差相关。多层 `--prediction yes` 必须同时声明目标和纳入的方差分量；CLI 只把二者记录为审计语义，不替研究者判断 `predict()` 的数学目标是否与生态问题一致。

### 4.5 构造抽样协方差矩阵

先把设计字段和相关假设写进独立 CSV，再调用保守包装器；完整参数以 `--help` 为准：

```powershell
$buildV = Join-Path $skill 'scripts/build_sampling_v.R'
& $Rscript $buildV `
  --input 'effects_multi.csv' --output-v 'V.csv' `
  --vi-col vi --id-col effect_id --cluster-col study_id `
  --obs-col outcome_id --rho 0.6 --scenario-label rho_0.6
```

`rho`/`phi` 是工作假设时，按预设范围分别生成矩阵和 manifest 并重跑模型。共享组、权重、time/type/obs 等字段必须对应真实设计；工具不会猜测。若设计不能由 `vcalc()` 契约表达，停止并编写经审计的专用构造代码。

### 4.6 使用完整抽样协方差矩阵

`V.csv` 的第一列是效应 ID，后续列名也是同一组效应 ID：

```csv
effect_id,e1,e2,e3
e1,0.040,0.012,0
e2,0.012,0.050,0
e3,0,0,0.030
```

```powershell
& $Rscript $fit `
  --input 'effects_multi.csv' --output-dir 'meta_mv' `
  --model multilevel --yi-col yi --vi-col vi --id-col effect_id `
  --independent-cluster-col study_id `
  --analysis-scale identity --v-matrix 'V.csv' `
  --random '~ 1 | study_id/effect_id' `
  --mv-method REML --test t --dfs residual --prediction no
```

脚本验证 ID 一一对应、矩阵对称、对角线与 `vi` 一致且矩阵半正定；不会重猜顺序或修复矩阵。

### 4.7 Cluster-robust 推断

CR1 不需要附加包：

```powershell
& $Rscript $fit `
  --input 'effects_multi.csv' --output-dir 'meta_cr1' `
  --model multilevel --yi-col yi --vi-col vi `
  --independent-cluster-col study_id `
  --analysis-scale identity --random '~ 1 | study_id/effect_id' `
  --mv-method REML --test t --dfs residual --prediction no `
  --robust-cluster study_id --robust-method CR1 `
  --dependence-topology nested
```

CR2 需要已安装 `clubSandwich`：

```powershell
# 将上一命令的 robust method 改为：
--robust-cluster study_id --robust-method CR2 --dependence-topology nested
```

`CR0` 不做小样本校正，通常只用于方法比较。聚类变量应代表独立抽样单元；不能为了增加“聚类数”而改用效应量 ID。任何 CRVE 都必须声明 `independent|nested|one_way|crossed|mixed|unknown` 拓扑；单向 CRVE 对 `crossed`、`mixed` 或 `unknown` 直接停止。robust-cluster 与 independent-cluster 两列若不同，必须在所有行定义完全相同的分区。

## 5. 高级 `metafor` 工作流

### 5.1 稀有事件：保留原始四格表

```r
library(metafor)

# 固定效应 Mantel-Haenszel OR；零值策略必须按方案指定
mh <- rma.mh(measure = "OR", ai = ai, bi = bi, ci = ci, di = di,
             data = dat, add = 0, to = "none", drop00 = TRUE)

# Peto 仅在事件很少、效应接近 1、组间大致平衡时作为候选
peto <- rma.peto(ai = ai, bi = bi, ci = ci, di = di,
                 data = dat, drop00 = TRUE)

# GLMM 的模型/积分方法需结合数据和版本核对
glmm <- rma.glmm(measure = "OR", ai = ai, bi = bi, ci = ci, di = di,
                 data = dat, model = "UM.RS", method = "ML")
```

### 5.2 依赖效应量：`V` + 多层模型 + RVE

```r
library(metafor)

# rho 是工作假设，不能伪装成已知值；对多个 rho 重跑
V <- vcalc(vi = vi, cluster = study_id, obs = effect_id,
           rho = 0.6, data = dat)

fit <- rma.mv(yi, V,
              mods = ~ moderator,
              random = ~ 1 | study_id/effect_id,
              data = dat, method = "REML", test = "t")

# CR1
robust(fit, cluster = study_id, adjust = TRUE)

# CR2，需要 clubSandwich
robust(fit, cluster = study_id, clubSandwich = TRUE)
```

若不同效应量共享对照、时间点或物种，`vcalc()` 参数必须按真实设计设置；上例不是通用模板。对相关系数优先检查 `rcalc()`。

### 5.3 预测与反变换

```r
fit <- rma.uni(yi, vi, data = dat, method = "REML", test = "knha")
pred_log <- predict(fit)
pred_ratio <- predict(fit, transf = exp)
```

`predict()` 的 CI 是平均效应/拟合均值不确定性，PI 是真实效应分布范围。对于 `rma.mv()` 中多个异质性分量或 `~ inner | outer` 结构，必须明确 `tau2.levels`/`gamma2.levels` 或目标方差层级。

### 5.4 小研究效应与缺失证据

```r
# 仅在效应量适配、通常 k >= 10 且精度有足够跨度时
regtest(fit)
ranktest(fit)

# 仅作为模型化敏感性分析
tf <- trimfill(fit)
```

脚本用 `--small-study-test egger|rank` 和 `--trimfill yes` 暴露这些分析，并在独立簇少于 10 时拒绝执行。任何结果都只能描述漏斗图不对称/小研究效应，不能单独证明发表偏倚。

## 6. 输出文件

`run_meta_analysis.R` 在输出目录中写入：

- `analysis_manifest.txt`：参数、公式、版本、警告和反变换说明；
- `data_used.csv`，以及显式缺失值删除时的 `excluded_rows.csv`；
- `coefficients.csv`：系数、SE、检验统计量、P 值、CI 和展示尺度边界；
- `heterogeneity.csv`：`tau^2`/`sigma^2`、I²、Q 等可用指标；
- `predictions.csv`：仅在 `--prediction yes` 时；多层模型同时保存 `prediction_target` 和 `prediction_components`；
- `sensitivity_models.csv`、`leave_one_cluster_out.csv`、`influence.txt`、`small_study_test.txt`、`trimfill.txt`：仅在请求相应分析时；簇级删一按 `independent_cluster_col` 重拟合 common、random 或 multilevel，multilevel 同步对子集 `V` 取行列并保留 random/robust 设置；任何删簇后的不收敛或系数结构变化都会明确失败；
- `model.rds` 与 `session_info.txt`：复核和复现。

`--overwrite yes` 只替换或清除上述脚本自有文件名，不触碰输出目录中的其他文件；这样可避免上一次运行遗留的可选结果被误当成新结果。

## 7. 结果前的最低校验

```r
stopifnot(all(is.finite(dat$yi)))
stopifnot(all(is.finite(dat$vi)), all(dat$vi > 0))
stopifnot(!anyDuplicated(dat$effect_id))  # 使用 V 时
summary(dat[c("yi", "vi")])
table(dat$study_id)
```

随后至少检查：原始数据方向、森林图、标准化残差、Cook 距离/DFBETAS、方差分量 profile、不同 `tau^2`/CI 方法、依赖相关假设，以及高风险偏倚/重复队列的限制分析。模型成功收敛不等于模型适当。

## 8. 主要官方资料

- `metafor` 参考索引：https://wviechtb.github.io/metafor/reference/
- `metafor` 复杂依赖推荐流程：https://wviechtb.github.io/metafor/reference/misc-recs.html
- `meta` CRAN 手册：https://cran.r-project.org/web/packages/meta/meta.pdf
- Cochrane Handbook Chapter 10：https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
- *Doing Meta-Analysis in R*：https://doing-meta.guide/
