# Specialist medical Meta-analysis runners

## Contents

1. Shared execution contract
2. Single-threshold diagnostic accuracy
3. Two-stage linear dose-response
4. Contrast-based network consistency model
5. Interpretation boundaries

## 1. Shared execution contract

Use these runners only after the synthesis router identifies a specialist medical problem. Do not send their inputs to the ordinary `yi/vi` runner.

All three scripts:

- require explicit named CLI options and reject positional, unknown, duplicate, or valueless options;
- read and write UTF-8 CSV, never install packages, and depend only on the R distribution plus `metafor >= 5.0.1`;
- require the output parent to exist;
- refuse an existing output directory unless `--overwrite yes` is explicit;
- replace only a directory containing the exact script-owned flat output set, refusing unknown files and subdirectories;
- stage the complete output set in a sibling directory and commit it by directory rename;
- emit `analysis_manifest.txt`, MD5 records, `session_info.txt`, and `model.rds`;
- stop on malformed data, incompatible covariance, non-identifiability, or severe convergence warnings rather than silently simplifying the model.

An explicit full sampling covariance matrix uses this CSV shape:

```csv
effect_id,E1,E2
E1,0.04,0.01
E2,0.01,0.05
```

Require unique row and column IDs, exact ID-set matching, finite values, symmetry, positive definiteness, and zero cross-study covariance. Reorder by IDs, never by row position.

## 2. Single-threshold diagnostic accuracy

The runner marks random-effect variances at or below `1e-8` as boundary estimates. When either variance is on that boundary, treat the estimated sensitivity–specificity random-effect correlation as weakly identified and do not interpret it substantively; the manifest records this condition even if the fixed summary means remain estimable.

Start from `assets/diagnostic_meta_template.csv`. Require exactly one row and one 2x2 table per `study_id` with:

```text
study_id, threshold_id, tp, fp, fn, tn
```

Run either:

```powershell
Rscript scripts/run_diagnostic_meta.R --input diagnostic.csv --output-dir diagnostic-out --zero-strategy reject
```

or, after prespecifying a correction:

```powershell
Rscript scripts/run_diagnostic_meta.R --input diagnostic.csv --output-dir diagnostic-out --zero-strategy continuity --continuity-correction 0.5
```

`continuity` adds the constant to all four cells only for a study containing at least one zero. The manifest records the strategy, constant, and number of corrected studies. Never choose the strategy after comparing which result is more favorable.

The runner calculates logit sensitivity and specificity with sampling variances `1/tp + 1/fn` and `1/tn + 1/fp`, then fits:

```r
rma.mv(yi, V, mods = outcome - 1,
       random = ~ outcome | study_id, struct = "UN",
       method = "REML", test = "t", dfs = "contain")
```

Require at least four independent studies. Reject repeated `study_id` rows, including multiple thresholds from one study. Outputs are `summary_measures.csv`, `random_effects.csv`, long analysis effects, data used, model, session information, and manifest.

Do not report SROC, AUC, likelihood ratios, diagnostic odds ratios, threshold curves, or multi-threshold inference from this runner. Different thresholds across studies remain an unresolved source of threshold heterogeneity.

## 3. Two-stage linear dose-response

Start from `assets/dose_response_template.csv`. Require:

```text
effect_id, study, dose_difference, yi
```

Also require a complete `V` covering every effect. Each study must provide at least two distinct non-zero dose differences against its reference dose. Reject reference rows, missing covariance, non-positive-definite blocks, cross-study covariance, and ill-conditioned study blocks.

Run:

```powershell
Rscript scripts/run_dose_response.R --input dose.csv --v-matrix dose-V.csv --output-dir dose-out
```

For study `s`, fit the through-origin GLS slope:

```text
b_s = (x_s' V_s^-1 x_s)^-1 x_s' V_s^-1 y_s
Var(b_s) = (x_s' V_s^-1 x_s)^-1
```

Pool at least three study slopes with `rma.uni(method="REML", test="knha")`. Report study slopes, the pooled slope and prediction interval, and model-based heterogeneity. Interpret the estimate as change in `yi` per one supplied `dose_difference` unit.

This runner does not fit an intercept, splines, fractional polynomials, nonlinear trends, absolute risks, or extrapolations outside observed doses. If linearity through the reference origin is scientifically implausible, use a different specialist workflow.

## 4. Contrast-based network consistency model

Start from `assets/network_meta_template.csv`. Require:

```text
effect_id, study, treatment_a, treatment_b, yi, vi
```

Define `yi` as treatment B minus treatment A on one common analysis scale. Supply the reference treatment explicitly:

```powershell
Rscript scripts/run_network_meta.R --input network.csv --output-dir network-out --reference-treatment A
```

Two-arm studies contribute exactly one contrast. A multi-arm study with `m` treatments contributes a connected independent set of `m-1` contrasts and requires a complete `V`:

```powershell
Rscript scripts/run_network_meta.R --input network.csv --v-matrix network-V.csv --output-dir network-out --reference-treatment A
```

Reject disconnected networks, repeated within-study contrasts, rank-deficient designs, absent residual degrees of freedom, and multi-arm data without full covariance. Verify that `diag(V)` equals input `vi`.

The runner builds consistency design rows `d_B - d_A` relative to the declared reference and fits a common-effect generalized least-squares model with `rma.mv`; heterogeneity variance is fixed at zero. It outputs reference-based basic parameters, every unordered pairwise contrast in the direction `treatment_b - treatment_a`, and a global residual `QE` statistic.

Do not calculate treatment ranks, rank probabilities, SUCRA, P-scores, or “best treatment” claims. Do not describe `QE` as an inconsistency test or claim that consistency has been demonstrated. This first implementation does not provide random-effects NMA, design-by-treatment interaction, node splitting, transitivity assessment, or component/network meta-regression.

## 5. Interpretation boundaries

- Keep all effects on one declared analysis scale and back-transform only with an explicitly justified mapping.
- Treat zero-cell corrections, dose units, reference choices, covariance construction, and contrast orientation as protocol decisions.
- Preserve multi-report and multi-outcome dependence outside these narrow contracts; do not squeeze unsupported dependence into the runners.
- Human reviewers must verify 2x2 counts, dose definitions, treatment identities, effect direction, covariance matrices, model applicability, and clinical interpretation.
