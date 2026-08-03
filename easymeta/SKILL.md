---
name: easymeta
description: 设计、执行、审计和报告医学、公共卫生、自然科学、生态学与环境科学中的系统综述、系统地图和 Meta 分析。Use when Codex needs to formulate PICO/PECO questions, draft or audit protocols and searches, design extraction tables, select or convert effect sizes, analyze dependent or heterogeneous evidence with fixed/common-effect, random-effects, multilevel, multivariate, robust-variance, GLMM, meta-regression or Bayesian methods, handle plant or biodiversity evidence involving community matrices, diversity partitioning, variability, factorial interactions, multifunctionality or longitudinal recovery, assess risk of bias and certainty, generate reproducible R workflows, or report results using PRISMA, PRISMA-EcoEvo, ROSES, Cochrane, JBI, CEE or GRADE guidance.
---

# EasyMeta

## Mission

Conduct evidence synthesis as an auditable scientific workflow. Select methods from the question, estimand, study design, outcome, and dependence structure; do not select methods merely because software exposes them.

Treat statistical pooling as optional. Recommend structured narrative synthesis or a systematic map when quantitative pooling would answer an incoherent question.

## Non-negotiable rules

- Separate evidence synthesis from individual medical diagnosis or treatment advice.
- Preserve provenance from every extracted value to publication, table, figure, page, arm, outcome, and time point.
- Never invent missing data, silently impute values, reverse outcome direction without recording it, or convert an effect without documenting the formula and assumptions.
- Never assume multiple effects from one study are independent.
- Never pool an outcome named only “biodiversity”. Freeze component, dimension, measure family, data type, Hill order where applicable, grain, extent, sampling units, observed/estimated status, and completeness/coverage first.
- Separate sampling-error covariance `V`, true-effect random/correlation structure, and coefficient-level robust inference. None of these three layers substitutes for another.
- Never treat the analysis used by a high-impact benchmark paper as a universal default; reconstruct its question, estimand, sampling unit, dependence, and assumptions before borrowing any method.
- Never mix reported natural-scale estimates with analysis-scale standard errors or variances. Keep raw extraction and analysis effects as separate versioned data stages.
- Never run the ordinary `yi/vi` model runner until the synthesis router permits it, the P0-6 reference gate has passed, and an independent sampling-cluster field is declared.
- Never choose common/fixed-effect versus random-effects models from a heterogeneity-test P value alone.
- Never return a binary “publication bias present/absent” verdict from funnel, Egger, trim-and-fill, fail-safe, P-curve, or one selection model.
- Distinguish reporting guidance from conduct guidance and risk-of-bias tools from certainty-of-evidence frameworks.
- Distinguish association, intervention effect, prediction, and causal effect. Do not upgrade observational associations into causal claims.
- Report uncertainty, limitations, protocol deviations, exclusions, and failed analyses even when they weaken the narrative.
- Require human verification for eligibility decisions, extracted values, risk-of-bias judgments, clinical/ecological interpretation, and all AI-generated outputs used in a review.
- Use current official guidance when standards, software defaults, or package behavior may have changed. Record the source version and access date.
- Never treat `read=true`, a file hash, or a completed receipt as proof that a person or model understood a source. The receipt is an auditable attestation; consequential interpretation still requires human verification.

## Route the task

1. Identify the requested product: protocol, systematic review, systematic map, scoping review, rapid review, umbrella review, quantitative re-analysis, audit, or manuscript report.
2. Identify the domain and question frame:
   - Use PICO or a justified variant for interventions and clinical questions.
   - Use PECO/PICO and an explicit causal or conceptual model for environmental and ecological questions.
3. Identify eligible study designs, outcome families, effect estimands, unit of analysis, spatial/temporal scale, and intended decision context.
4. Identify the data level: use `aggregate` for report-level effects or arm/cell summaries, `ipd` for individual/unit-level raw data, `raw_community_matrix` for species-by-sample matrices, and `meta_level` for existing Meta-analysis summaries. Then identify multiple outcomes/time points, clustered studies, phylogenetic data, or spatially/temporally correlated data.
5. State whether the request concerns planning, execution, interpretation, reporting, or independent audit.
6. Copy `assets/synthesis_route_template.json`, complete the task, data, and trigger fields, set `task.as_of_date` to the actual guidance-check date, and run `python scripts/route_synthesis.py <plan.json> --output <pending-route.json>`. The first pass deterministically returns `required_references`, `required_source_ids`, matched rules, and a plan SHA-256; it keeps `runner_allowed=false` while the receipt is pending.
7. Read only the routed local references and open the current official pages for every routed source ID. Copy `assets/reference_receipt_template.json`; record exact local-file SHA-256 values, section locators that occur in those files, decision mappings, source versions, access dates, milestone checks, update summaries, and the accountable reviewer/agent run.
8. Run `python scripts/validate_reference_receipt.py <pending-route.json> <receipt.json>`. Resolve every failure; do not substitute a free-text claim of reading.
9. Re-run `python scripts/route_synthesis.py <plan.json> --reference-receipt <receipt.json> --output <route.json>`. Require `reference_gate.status=passed` before any analysis handoff. Use the ordinary runner only when `runner_allowed=true`; when `route=specialist_route`, keep the ordinary runner blocked and follow `required_handoff` plus the specialist input contract. A `no_pooling` route never becomes executable.

`assets/reference_routes.json` is the authoritative machine-readable routing table. The following list is its human-readable mirror; never use it to bypass or broaden the routed minimum set:

- Always read `references/evidence-synthesis-core.md` before planning a full review.
- Read `references/medical-review.md` for medicine, public health, diagnostics, prognosis, prevalence, etiology, harms, or clinical interventions.
- Read `references/ecology-review.md` for ecology, evolution, conservation, environmental management, biodiversity, exposure-response, or systematic maps.
- Read `references/effect-size-and-models.md` before calculating, transforming, pooling, or interpreting effect sizes.
- Read `references/bias-and-certainty.md` before selecting appraisal tools or rating a body of evidence.
- Read `references/environmental-reporting.md` for CEE, ROSES, or PRISMA-EcoEvo outputs.
- Read `references/data-and-reproducibility.md` before building extraction data or using AI in screening, extraction, appraisal, synthesis, or reporting.
- Read `references/r-metafor-workflows.md` before producing R code.
- Read `references/complex-design-effects.md` before reconstructing paired, crossover, change-score, BACI, or cluster-adjusted effects.
- Read `references/specialist-medical-models.md` before running diagnostic, dose-response, or network models.
- Read `references/ecoevo-structured-models.md` before using phylogenetic, spatial, or temporal correlation structures.
- Read `references/plant-biodiversity-specialist-routes.md` for plant ecology, biodiversity, restoration, community composition, ecosystem multifunctionality, variability, factorial global-change experiments, longitudinal resistance/recovery, or second-order synthesis.
- Read `references/plant-biodiversity-benchmark-casebook.md` when designing or auditing a method against the collected Nature, Science-family, Ecology Letters, PNAS, and forest-ecology benchmark studies.
- Read `references/quality-control-contracts.md` before reconciling duplicate extraction, linking reports to studies, or validating appraisal records.
- Read `references/source-registry.md` when checking authority, licensing, versioning, or update frequency of source guidance.

If the machine table and this prose disagree, stop, treat the table or documentation as a defect, and reconcile both with a tested change. Do not silently choose whichever route is more convenient.

## Execute the workflow

### 1. Freeze the question and protocol

- Define the target population/system, intervention or exposure, comparator, outcomes, eligible designs, settings, time horizon, geography, and language/publication constraints.
- Define the estimand and the grouping logic for synthesis before inspecting result direction or significance.
- Specify search, deduplication, screening, extraction, critical appraisal, synthesis, sensitivity analyses, subgroup/meta-regression hypotheses, and reporting plan.
- Register or time-stamp the protocol where appropriate. Log every later deviation with its reason and likely impact.

### 2. Search and select evidence

- Translate concepts into database-specific searches; retain complete reproducible strategies, dates, platforms, limits, and deduplication rules.
- Use at least two reviewers or a justified verification design for consequential screening decisions.
- Link multiple reports of one underlying study before extraction.
- Start from `assets/study_report_map_template.csv` and run `python scripts/validate_study_map.py <map.csv>`; unresolved sample overlap or one report mapped to multiple studies without a documented split blocks synthesis.
- Keep a study-level exclusion log with explicit reasons.
- Create a paper/data/code ledger from `assets/publication_integrity_template.csv`. Before synthesis, run `python scripts/validate_integrity.py <ledger.csv>` and stop on unchecked objects or unresolved non-clear statuses.

### 3. Build auditable extraction data

- Start raw extraction from `assets/extraction_template.csv` and planning from `assets/analysis_plan_template.yaml`; adapt them before extraction rather than deleting provenance fields.
- Keep `data_stage=raw_extraction` separate from `data_stage=analysis_effect`. Do not require a reported study to supply a ready-to-pool effect, SE, variance, or CI when the raw design statistics are sufficient to calculate them later.
- Represent one candidate effect per row and keep distinct `study_id`, `report_id`, `effect_id`, and `dependency_cluster`/independent-cluster identifiers.
- Record sample sizes, events or summary statistics, effect direction, units, outcome definition, follow-up, hierarchy, cluster/paired structure, and extraction provenance.
- Run `python scripts/validate_extraction.py <raw.csv> --stage raw`. Resolve errors; review every warning explicitly.
- Preserve two independent extraction files for consequential fields. Run `python scripts/reconcile_extractions.py <reviewer1.csv> <reviewer2.csv> --output <differences.csv>` and require an adjudication ledger for every substantive difference; never let the script choose a reviewer automatically.

### 4. Select and compute effect sizes

- Match the measure to the outcome, estimand, design, and interpretability. Preserve natural units when clinically or ecologically meaningful.
- Record every sign reversal, scale harmonization, continuity correction, back-transformation, and variance reconstruction.
- Avoid mixing adjusted and unadjusted effects, endpoint and change scores, conditional and marginal effects, or incompatible reference categories without a prespecified rationale.
- Use `scripts/calculate_effect_sizes.R` only after verifying its input contract and assumptions.
- Use `scripts/calculate_complex_effects.R` for paired/crossover continuous results, two-group change/BACI contrasts, or already design-adjusted cluster estimates. Require explicit correlation sources and assumption-set IDs; do not manufacture a cluster-adjusted effect from an effective sample size alone.
- Validate its output with `python scripts/validate_extraction.py <effects.csv> --stage analysis`. Require one declared `analysis_scale` per analysis file and require `vi ~= sei^2` on that scale.

### 5. Model dependence and heterogeneity

- Define the target of inference before selecting common/fixed-effect, random-effects, multilevel, multivariate, robust-variance, GLMM, dose-response, network, or Bayesian methods.
- Require `--independent-cluster-col` for `scripts/run_meta_analysis.R`. Count information, small-study method eligibility, moderator support, and leave-one-out analyses by independent clusters rather than effect rows.
- Model study, comparison, outcome, time, site, species, taxon, phylogeny, and spatial/temporal dependence where they affect sampling covariance or true-effect structure.
- When sampling covariance is explicit or can be defensibly approximated, use `scripts/build_sampling_v.R` to construct an audited `V` under stated `rho`/`phi` scenarios; never guess design fields or shared-group weights.
- Report the heterogeneity estimator, interval method, variance components, uncertainty in heterogeneity, and prediction intervals where defensible.
- Treat subgroup analysis and meta-regression as observational comparisons. Limit complexity when the number and distribution of studies do not support the planned moderators.
- Use `scripts/run_meta_analysis.R --route-contract <route.json> ...` as a conservative baseline, then extend it only with documented justification. The runner independently rejects a missing contract, a specialist/no-pooling route, `runner_allowed=false`, a non-passed reference gate, gate issues, or an invalid plan hash.
- Keep the ordinary runner blocked for specialist routes. Use `scripts/run_diagnostic_meta.R` only for one threshold per study with study-level 2x2 data; use `scripts/run_dose_response.R` only for a prespecified two-stage linear trend with an explicit sampling covariance matrix; use `scripts/run_network_meta.R` only for a connected contrast network under a consistency model, without treating ranking or inconsistency as solved.
- Keep the ordinary runner blocked when the estimand must first be generated from a raw community matrix, community-composition distance, multidimensional biodiversity object, variability contrast, factorial interaction, multifunctionality construction, longitudinal resistance/recovery process, derived recovery-debt/stability quantity, or second-order/cross-meta evidence base. Set the matching schema 1.2 trigger; for biodiversity/ecology triggers, validate `assets/biodiversity_contract_template.json` with `scripts/validate_biodiversity_contract.py` and record its path before routing. Do not convert such inputs to generic `yi/vi` merely to make the baseline runner accept them.
- Shared controls alone do not require a new specialist route when the target effects are already defined: declare dependent effects, construct and audit the sampling `V`, identify independent clusters, and use a defensible multilevel/multivariate model or robust sensitivity analysis. Escalate multidimensional outcomes or unidentified covariance rather than duplicating the control as independent information.
- For ecological structured dependence, validate every matrix with `scripts/validate_structure_matrix.py`. Use `scripts/run_ecoevo_meta_analysis.R` only for its implemented phylogenetic-correlation contract. Spatial and temporal matrices are validation-only in P1: stop after validation and obtain a specialist model instead of claiming a fitted result. Do not repair matrices silently, infer IDs by position, or fit separable phylogenetic/study/species components when the data cannot identify them.

### 6. Diagnose robustness and bias

- Examine influential cases, residuals, leave-one-study/cluster-out results, alternative estimators, effect definitions, dependence assumptions, and justified exclusion scenarios.
- Do not treat funnel plots, asymmetry tests, trim-and-fill, or one selection model as definitive evidence for or against publication bias.
- Apply design-appropriate risk-of-bias tools at the result level where required; quote supporting evidence and preserve reviewer judgments separately.
- For environmental reviews, keep four judgments separate: study-level validity, body-of-evidence confidence, review-level reliability appraisal based on available evidence about conduct/reporting/limitations (for example CEESAT), and reporting completeness (for example ROSES, PRISMA-EcoEvo, or MATES). Never convert one into another or sum them into a single quality score; “not reported” does not prove “not done”.
- Rate certainty or confidence at the body-of-evidence level only with an applicable framework and explicit reasons.
- Start from `assets/risk_of_bias_template.csv` and `assets/certainty_template.csv`, then run `python scripts/validate_appraisal.py risk-of-bias <rob.csv>` and `python scripts/validate_appraisal.py certainty <certainty.csv>`. Keep original reviewer judgments and adjudication; never compute a quality score or let a validator make the final RoB/GRADE/CEE judgment.

### 7. Interpret and report

- Report absolute as well as relative effects when meaningful, and connect statistical results to clinical, biological, ecological, spatial, and temporal relevance.
- Separate pooled mean effects from the distribution of effects and from predictions for new settings.
- Explain why studies were or were not pooled, what populations/systems the result applies to, and where extrapolation fails.
- Use PRISMA and relevant extensions for health reviews; use CEE conduct standards plus ROSES and/or PRISMA-EcoEvo for environmental and ecology reviews.
- Supply data dictionaries, extraction sheets, code, software/package versions, prompts or automation settings, and a source/version manifest when sharing is legally and ethically permitted.
- Create field-level lineage from `assets/field_lineage_template.csv` with `python scripts/build_lineage_manifest.py ...`; require SHA-256 records for frozen inputs, scripts, and structured outputs.

## AI and source governance

- Treat AI as an assisted process, never as an accountable reviewer.
- Record the tool, developer, version/date, task, parameters, exact prompt when material, input scope, validation sample, human agreement, errors, corrections, limitations, privacy controls, and protocol deviations.
- Do not upload confidential, copyrighted, identifiable, or restricted full texts to external services without authorization.
- Paraphrase and distill authoritative sources. Do not reproduce paywalled books, long passages, proprietary tables, or copyrighted checklists beyond their licenses.
- Cite official sources near each methodological rule and record retrieval dates for living guidance.

## Required deliverable

Return the smallest complete package appropriate to the request:

1. question, scope, estimand, and assumptions;
2. protocol or analysis-plan decisions and deviations;
3. study/effect data schema with provenance;
4. synthesis route, P0-6 reference receipt, pooling decision, effect-size and model rationale;
5. executable code and validation output when analysis is requested;
6. primary, heterogeneity, robustness, and bias results;
7. certainty/confidence assessment where applicable;
8. limitations, applicability, and non-pooling rationale;
9. reporting checklist mapping, publication-integrity disposition, and reproducibility/lineage record;
10. authoritative source list with versions, access dates, milestone checks, and update/adoption decisions.

Resolve `Rscript` from `R_SCRIPT` or the system `PATH`, and record the R and package versions used for every analysis.
