#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1)

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Strict ecological/evolutionary structured meta-analysis runner\n\n",
  "Usage:\n",
  "  Rscript run_ecoevo_meta_analysis.R --spec FILE\n\n",
  "P1-3 v1 supports only a frozen phylogenetic correlation matrix through\n",
  "metafor::rma.mv(R=..., Rscale='none'). Spatial and temporal specifications\n",
  "stop explicitly after schema recognition; they are validation-only in v1.\n\n",
  "The JSON specification is based on assets/ecoevo_model_spec_template.json.\n",
  "A successful run writes exactly coefficients.csv, variance_components.csv,\n",
  "analysis_manifest.json, and model.rds. The runner never repairs a matrix,\n",
  "uses nearPD, drops rows, installs packages, or simplifies a failed model.\n"
)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0L || "--help" %in% args) {
  cat(help_text)
  quit(save = "no", status = 0L, runLast = FALSE)
}
if (length(args) != 2L || args[[1L]] != "--spec") {
  abort("Expected exactly '--spec FILE'. Use --help.")
}

spec_path <- normalizePath(args[[2L]], winslash = "/", mustWork = FALSE)
if (!file.exists(spec_path)) abort(sprintf("Specification file does not exist: %s", spec_path))
if (dir.exists(spec_path)) abort("--spec must point to a JSON file, not a directory.")

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  abort(paste0(
    "Required package 'jsonlite' is not installed in the active project library. ",
    "The runner did not install anything. Current .libPaths(): ",
    paste(.libPaths(), collapse = "; ")
  ))
}
if (!requireNamespace("metafor", quietly = TRUE)) {
  abort(paste0(
    "Required package 'metafor' is not installed in the active project library. ",
    "The runner did not install anything. Current .libPaths(): ",
    paste(.libPaths(), collapse = "; ")
  ))
}

spec <- tryCatch(
  jsonlite::fromJSON(spec_path, simplifyVector = TRUE),
  error = function(e) abort(sprintf("Could not parse JSON specification: %s", conditionMessage(e)))
)
if (!is.list(spec) || is.null(names(spec))) abort("Specification root must be a JSON object.")

assert_exact_names <- function(object, expected, label) {
  actual <- names(object)
  if (is.null(actual) || any(!nzchar(actual)) || anyDuplicated(actual)) {
    abort(sprintf("%s must be an object with unique non-empty keys.", label))
  }
  missing <- setdiff(expected, actual)
  extra <- setdiff(actual, expected)
  if (length(missing) || length(extra)) {
    details <- c(
      if (length(missing)) paste0("missing=", paste(missing, collapse = ",")),
      if (length(extra)) paste0("unexpected=", paste(extra, collapse = ","))
    )
    abort(sprintf("%s keys do not match schema (%s).", label, paste(details, collapse = "; ")))
  }
}

scalar_character <- function(value, label, choices = NULL) {
  if (!is.character(value) || length(value) != 1L || is.na(value) || !nzchar(value)) {
    abort(sprintf("%s must be one non-empty string.", label))
  }
  if (!identical(value, trimws(value))) abort(sprintf("%s cannot have leading or trailing whitespace.", label))
  if (!is.null(choices) && !(value %in% choices)) {
    abort(sprintf("%s must be one of: %s.", label, paste(choices, collapse = ", ")))
  }
  value
}

scalar_logical <- function(value, label) {
  if (!is.logical(value) || length(value) != 1L || is.na(value)) {
    abort(sprintf("%s must be one JSON boolean.", label))
  }
  value
}

scalar_number <- function(value, label, lower = -Inf, upper = Inf,
                          lower_open = FALSE, upper_open = FALSE) {
  if (!is.numeric(value) || length(value) != 1L || is.na(value) || !is.finite(value)) {
    abort(sprintf("%s must be one finite JSON number.", label))
  }
  lower_bad <- if (lower_open) value <= lower else value < lower
  upper_bad <- if (upper_open) value >= upper else value > upper
  if (lower_bad || upper_bad) abort(sprintf("%s is outside the allowed range.", label))
  as.numeric(value)
}

top_level_keys <- c(
  "schema_version", "structure_type", "input_csv", "output_dir", "analysis_scale",
  "columns", "phylogeny", "sampling_v_matrix", "moderators", "method", "test",
  "dfs", "level", "model_role", "species_iid_exception_reason",
  "random_effects", "hessian_policy",
  "variance_boundary_tolerance", "overwrite"
)
assert_exact_names(spec, top_level_keys, "Specification")

schema_version <- scalar_character(spec$schema_version, "schema_version", "1.1.0")
structure_type <- scalar_character(
  spec$structure_type, "structure_type", c("phylogenetic", "spatial", "temporal")
)
if (structure_type %in% c("spatial", "temporal")) {
  abort(sprintf(
    paste0(
      "P1-3 v1 recognizes structure_type='%s' but does not fit it. ",
      "Use validate_structure_matrix.py for strict matrix validation and stop for a ",
      "specialist model review; no model or output was produced."
    ),
    structure_type
  ))
}

input_value <- scalar_character(spec$input_csv, "input_csv")
output_value <- scalar_character(spec$output_dir, "output_dir")
analysis_scale <- scalar_character(
  spec$analysis_scale,
  "analysis_scale",
  c(
    "identity", "log", "fisher-z", "logit", "arcsine",
    "arcsine_difference", "sqrt", "sqrt_difference", "analysis"
  )
)

if (!is.list(spec$columns)) abort("columns must be a JSON object.")
column_keys <- c("effect_id", "study_id", "species_id", "yi", "vi")
assert_exact_names(spec$columns, column_keys, "columns")
columns <- lapply(column_keys, function(key) scalar_character(spec$columns[[key]], paste0("columns.", key)))
names(columns) <- column_keys
if (anyDuplicated(unlist(columns, use.names = FALSE))) {
  abort("columns.effect_id, study_id, species_id, yi, and vi must map to distinct columns.")
}

if (!is.list(spec$phylogeny)) abort("phylogeny must be a JSON object for structure_type='phylogenetic'.")
phylogeny_keys <- c("correlation_matrix", "source", "version", "branch_length_method", "pruning_rule")
assert_exact_names(spec$phylogeny, phylogeny_keys, "phylogeny")
phylogeny <- lapply(
  phylogeny_keys,
  function(key) scalar_character(spec$phylogeny[[key]], paste0("phylogeny.", key))
)
names(phylogeny) <- phylogeny_keys
provenance_values <- unlist(phylogeny[c("source", "version", "branch_length_method", "pruning_rule")])
if (any(startsWith(provenance_values, "REPLACE_"))) {
  abort("Replace every phylogeny provenance placeholder before fitting the model.")
}

sampling_v_value <- spec$sampling_v_matrix
if (!is.null(sampling_v_value)) {
  sampling_v_value <- scalar_character(sampling_v_value, "sampling_v_matrix")
}
moderator_text <- scalar_character(spec$moderators, "moderators")
method <- scalar_character(toupper(spec$method), "method", c("REML", "ML"))
test_method <- scalar_character(tolower(spec$test), "test", c("z", "t"))
dfs_method <- scalar_character(tolower(spec$dfs), "dfs", c("residual", "contain"))
if (test_method == "z" && dfs_method != "residual") {
  abort("dfs must be 'residual' when test='z'; contain degrees of freedom are only used with test='t'.")
}
level <- scalar_number(spec$level, "level", lower = 0, upper = 100, lower_open = TRUE, upper_open = TRUE)
model_role <- scalar_character(spec$model_role, "model_role", c("primary", "sensitivity"))
species_iid_exception_reason <- spec$species_iid_exception_reason
if (!is.null(species_iid_exception_reason)) {
  species_iid_exception_reason <- scalar_character(
    species_iid_exception_reason,
    "species_iid_exception_reason",
    c("nonidentifiable", "prespecified_sensitivity")
  )
}

if (!is.list(spec$random_effects)) abort("random_effects must be a JSON object.")
random_keys <- c("study", "phylogenetic_species", "species_iid", "effect")
assert_exact_names(spec$random_effects, random_keys, "random_effects")
random_effects <- lapply(
  random_keys,
  function(key) scalar_logical(spec$random_effects[[key]], paste0("random_effects.", key))
)
names(random_effects) <- random_keys
if (!isTRUE(random_effects$phylogenetic_species)) {
  abort("P1-3 v1 requires random_effects.phylogenetic_species=true; otherwise use the ordinary runner.")
}
if (!isTRUE(random_effects$species_iid)) {
  if (is.null(species_iid_exception_reason)) {
    abort(paste0(
      "Disabling random_effects.species_iid requires species_iid_exception_reason. ",
      "Do not remove non-phylogenetic species variance by significance or convergence."
    ))
  }
  if (model_role == "primary" && species_iid_exception_reason != "nonidentifiable") {
    abort("A primary model may disable species_iid only for a documented nonidentifiability reason.")
  }
} else if (!is.null(species_iid_exception_reason)) {
  abort("species_iid_exception_reason must be null when random_effects.species_iid=true.")
}
hessian_policy <- scalar_character(
  spec$hessian_policy, "hessian_policy", "require_positive_definite"
)
variance_boundary_tolerance <- scalar_number(
  spec$variance_boundary_tolerance,
  "variance_boundary_tolerance",
  lower = 0,
  upper = 0.01,
  lower_open = TRUE
)
overwrite <- scalar_logical(spec$overwrite, "overwrite")

spec_dir <- dirname(spec_path)
resolve_spec_path <- function(value) {
  is_absolute <- grepl("^(?:[A-Za-z]:[/\\\\]|[/\\\\]{2}|/)", value, perl = TRUE)
  candidate <- if (is_absolute) value else file.path(spec_dir, value)
  normalizePath(candidate, winslash = "/", mustWork = FALSE)
}

input_path <- resolve_spec_path(input_value)
output_dir <- resolve_spec_path(output_value)
phylogeny_path <- resolve_spec_path(phylogeny$correlation_matrix)
sampling_v_path <- if (is.null(sampling_v_value)) NULL else resolve_spec_path(sampling_v_value)

if (!file.exists(input_path) || dir.exists(input_path)) abort(sprintf("input_csv does not exist as a file: %s", input_path))
if (!file.exists(phylogeny_path) || dir.exists(phylogeny_path)) {
  abort(sprintf("phylogeny.correlation_matrix does not exist as a file: %s", phylogeny_path))
}
if (!is.null(sampling_v_path) && (!file.exists(sampling_v_path) || dir.exists(sampling_v_path))) {
  abort(sprintf("sampling_v_matrix does not exist as a file: %s", sampling_v_path))
}
if (file.exists(output_dir) && !dir.exists(output_dir)) abort("output_dir points to a file.")
if (normalizePath(input_path, winslash = "/", mustWork = TRUE) == normalizePath(phylogeny_path, winslash = "/", mustWork = TRUE)) {
  abort("input_csv and phylogenetic correlation matrix must be different files.")
}

dat <- tryCatch(
  read.csv(input_path, check.names = FALSE, fileEncoding = "UTF-8", na.strings = c("", "NA")),
  error = function(e) abort(sprintf("Could not read UTF-8 input CSV: %s", conditionMessage(e)))
)
if (nrow(dat) < 2L) abort("Input must contain at least two effect rows.")
if (anyDuplicated(names(dat)) || any(!nzchar(names(dat)))) abort("Input column names must be unique and non-empty.")
required_columns <- unique(c(unlist(columns, use.names = FALSE), "analysis_scale"))
missing_columns <- setdiff(required_columns, names(dat))
if (length(missing_columns)) {
  abort(sprintf("Input is missing required column(s): %s.", paste(missing_columns, collapse = ", ")))
}
if ("data_stage" %in% names(dat)) {
  stages <- trimws(as.character(dat$data_stage))
  if (any(is.na(stages) | stages != "analysis_effect")) {
    abort("Every data_stage value must be 'analysis_effect'.")
  }
}
input_scales <- trimws(tolower(as.character(dat$analysis_scale)))
if (any(is.na(input_scales) | input_scales == "") || any(input_scales != analysis_scale)) {
  abort(sprintf("Every input analysis_scale must equal specification analysis_scale '%s'.", analysis_scale))
}

reserved_columns <- c("study_re_id", "phylo_id", "species_iid_id", "effect_re_id", "yi_internal", "vi_internal")
collisions <- intersect(reserved_columns, names(dat))
if (length(collisions)) {
  abort(sprintf("Input uses runner-reserved column(s): %s.", paste(collisions, collapse = ", ")))
}

strict_id_column <- function(data, column_name, label, unique_required = FALSE) {
  raw <- as.character(data[[column_name]])
  cleaned <- trimws(raw)
  bad <- is.na(raw) | cleaned == ""
  if (any(bad)) abort(sprintf("%s has missing/blank values at row(s): %s.", label, paste(which(bad), collapse = ", ")))
  whitespace <- raw != cleaned
  if (any(whitespace)) abort(sprintf("%s has leading/trailing whitespace at row(s): %s.", label, paste(which(whitespace), collapse = ", ")))
  if (unique_required && anyDuplicated(cleaned)) abort(sprintf("%s values must be unique.", label))
  cleaned
}

strict_numeric_column <- function(data, column_name, label) {
  raw <- data[[column_name]]
  text <- trimws(as.character(raw))
  missing <- is.na(raw) | text == ""
  value <- suppressWarnings(as.numeric(text))
  bad <- missing | is.na(value) | !is.finite(value)
  if (any(bad)) abort(sprintf("%s must be finite numeric at row(s): %s.", label, paste(which(bad), collapse = ", ")))
  value
}

effect_ids <- strict_id_column(dat, columns$effect_id, "effect_id", unique_required = TRUE)
study_ids <- strict_id_column(dat, columns$study_id, "study_id")
species_ids <- strict_id_column(dat, columns$species_id, "species_id")
yi <- strict_numeric_column(dat, columns$yi, "yi")
vi <- strict_numeric_column(dat, columns$vi, "vi")
if (any(vi <= 0)) abort("Every vi must be > 0.")
if (length(unique(study_ids)) < 2L) abort("At least two independent study IDs are required.")
species_order <- unique(species_ids)
if (length(species_order) < 3L) abort("At least three distinct species IDs are required for a phylogenetic model.")

mods_formula <- tryCatch(
  as.formula(moderator_text, env = environment()),
  error = function(e) abort(sprintf("Invalid moderators formula: %s", conditionMessage(e)))
)
if (length(mods_formula) != 2L) abort("moderators must be a one-sided formula beginning with '~'.")
formula_variables <- all.vars(mods_formula)
term_labels <- attr(stats::terms(mods_formula), "term.labels")
if ("." %in% formula_variables || "." %in% term_labels) abort("moderators cannot use '.'; list columns explicitly.")
missing_formula_columns <- setdiff(formula_variables, names(dat))
if (length(missing_formula_columns)) {
  abort(sprintf("moderators refers to missing column(s): %s.", paste(missing_formula_columns, collapse = ", ")))
}
moderator_matrix <- tryCatch(
  model.matrix(mods_formula, data = dat),
  error = function(e) abort(sprintf("Could not construct moderator model matrix: %s", conditionMessage(e)))
)
if (nrow(moderator_matrix) != nrow(dat) || any(!is.finite(moderator_matrix))) {
  abort("Moderator model matrix contains missing/non-finite values or silently dropped rows.")
}
if (qr(moderator_matrix)$rank < ncol(moderator_matrix)) abort("Moderator model matrix is rank deficient.")
independent_cluster_count <- length(unique(study_ids))
if (independent_cluster_count <= ncol(moderator_matrix)) {
  abort(sprintf(
    "There are %d independent studies for %d fixed-effect coefficients; residual cluster degrees of freedom are not positive.",
    independent_cluster_count, ncol(moderator_matrix)
  ))
}

read_labeled_matrix <- function(path, expected_ids, matrix_type, expected_vi = NULL, tolerance = 1e-8) {
  raw <- tryCatch(
    read.csv(path, check.names = FALSE, fileEncoding = "UTF-8", na.strings = c("", "NA")),
    error = function(e) abort(sprintf("Could not read %s matrix CSV: %s", matrix_type, conditionMessage(e)))
  )
  if (ncol(raw) < 3L || nrow(raw) < 2L) abort(sprintf("%s matrix needs an ID column and at least two matrix columns.", matrix_type))
  if (anyDuplicated(names(raw)) || any(!nzchar(names(raw)))) abort(sprintf("%s matrix column names must be unique and non-empty.", matrix_type))
  row_ids <- as.character(raw[[1L]])
  column_ids <- names(raw)[-1L]
  if (any(is.na(row_ids) | row_ids == "") || anyDuplicated(row_ids)) abort(sprintf("%s matrix row IDs must be unique and non-empty.", matrix_type))
  if (any(row_ids != trimws(row_ids)) || any(column_ids != trimws(column_ids))) abort(sprintf("%s matrix IDs cannot have leading/trailing whitespace.", matrix_type))
  if (nrow(raw) != length(column_ids)) abort(sprintf("%s matrix must be square.", matrix_type))
  if (!setequal(row_ids, column_ids)) abort(sprintf("%s matrix row IDs and column IDs must be exactly the same set.", matrix_type))
  if (!setequal(row_ids, expected_ids) || length(row_ids) != length(expected_ids)) {
    missing_ids <- setdiff(expected_ids, row_ids)
    extra_ids <- setdiff(row_ids, expected_ids)
    abort(sprintf(
      "%s matrix IDs do not match data IDs (missing=%s; extra=%s).",
      matrix_type,
      if (length(missing_ids)) paste(missing_ids, collapse = ",") else "none",
      if (length(extra_ids)) paste(extra_ids, collapse = ",") else "none"
    ))
  }
  numeric_columns <- lapply(seq_along(column_ids), function(index) {
    text <- trimws(as.character(raw[[index + 1L]]))
    value <- suppressWarnings(as.numeric(text))
    if (any(is.na(value) | !is.finite(value))) {
      abort(sprintf("%s matrix column '%s' contains missing/non-finite/non-numeric values.", matrix_type, column_ids[[index]]))
    }
    value
  })
  matrix_value <- do.call(cbind, numeric_columns)
  rownames(matrix_value) <- row_ids
  colnames(matrix_value) <- column_ids
  matrix_value <- matrix_value[expected_ids, expected_ids, drop = FALSE]
  scale_value <- max(1, max(abs(matrix_value)))
  numeric_tolerance <- tolerance * scale_value
  symmetry_error <- max(abs(matrix_value - t(matrix_value)))
  if (symmetry_error > numeric_tolerance) abort(sprintf("%s matrix is not symmetric within tolerance.", matrix_type))
  eigenvalues <- eigen((matrix_value + t(matrix_value)) / 2, symmetric = TRUE, only.values = TRUE)$values
  minimum_eigenvalue <- min(eigenvalues)

  if (matrix_type == "phylogenetic correlation") {
    diagonal_error <- max(abs(diag(matrix_value) - 1))
    if (diagonal_error > tolerance) abort("Phylogenetic correlation matrix diagonal must equal 1.")
    if (min(matrix_value) < -1 - tolerance || max(matrix_value) > 1 + tolerance) {
      abort("Phylogenetic correlation matrix entries must lie in [-1, 1].")
    }
    if (minimum_eigenvalue <= numeric_tolerance) {
      abort(sprintf(
        "Phylogenetic correlation matrix is not strictly positive definite (minimum eigenvalue %.12g). No nearPD repair was attempted.",
        minimum_eigenvalue
      ))
    }
  } else if (matrix_type == "sampling V") {
    if (minimum_eigenvalue < -numeric_tolerance) {
      abort(sprintf("Sampling V is not positive semidefinite (minimum eigenvalue %.12g).", minimum_eigenvalue))
    }
    if (any(diag(matrix_value) <= 0)) abort("Sampling V diagonal must be > 0.")
    diagonal_tolerance <- tolerance * pmax(1, abs(expected_vi))
    mismatched <- abs(diag(matrix_value) - expected_vi) > diagonal_tolerance
    if (any(mismatched)) {
      abort(sprintf("Sampling V diagonal does not match vi for effect ID(s): %s.", paste(expected_ids[mismatched], collapse = ", ")))
    }
  }
  list(
    matrix = matrix_value,
    diagnostics = list(
      source_row_order = row_ids,
      source_column_order = column_ids,
      mapped_order = expected_ids,
      symmetry_max_error = symmetry_error,
      minimum_eigenvalue = minimum_eigenvalue,
      tolerance = tolerance,
      repair_applied = FALSE,
      near_pd_applied = FALSE
    )
  )
}

matrix_tolerance <- 1e-8
phylo_result <- read_labeled_matrix(
  phylogeny_path, species_order, "phylogenetic correlation", tolerance = matrix_tolerance
)
A <- phylo_result$matrix

if (is.null(sampling_v_path)) {
  V <- vi
  sampling_v_result <- NULL
} else {
  sampling_v_result <- read_labeled_matrix(
    sampling_v_path, effect_ids, "sampling V", expected_vi = vi, tolerance = matrix_tolerance
  )
  V <- sampling_v_result$matrix
}

same_partition <- function(first, second) {
  if (length(first) != length(second)) return(FALSE)
  first_to_second <- vapply(split(second, first), function(values) length(unique(values)) == 1L, logical(1))
  second_to_first <- vapply(split(first, second), function(values) length(unique(values)) == 1L, logical(1))
  all(first_to_second) && all(second_to_first)
}

species_study_confounded <- same_partition(species_ids, study_ids)
study_effect_confounded <- same_partition(study_ids, effect_ids)
species_effect_confounded <- same_partition(species_ids, effect_ids)

if (species_study_confounded && isTRUE(random_effects$study) && isTRUE(random_effects$species_iid)) {
  abort(paste0(
    "species_id and study_id define the same partition. Study IID and species IID variance ",
    "components are then exactly confounded; remove one component in the frozen specification."
  ))
}
if (study_effect_confounded && isTRUE(random_effects$study) && isTRUE(random_effects$effect)) {
  abort("study_id and effect_id define the same partition, so study and effect IID variances are not separately identifiable.")
}
if (species_effect_confounded && isTRUE(random_effects$species_iid) && isTRUE(random_effects$effect)) {
  abort("species_id and effect_id define the same partition, so species IID and effect IID variances are not separately identifiable.")
}

dat$yi_internal <- yi
dat$vi_internal <- vi
dat$study_re_id <- study_ids
dat$phylo_id <- species_ids
dat$species_iid_id <- species_ids
dat$effect_re_id <- effect_ids

random_terms <- list()
component_roles <- character()
if (isTRUE(random_effects$study)) {
  random_terms <- c(random_terms, list(~ 1 | study_re_id))
  component_roles <- c(component_roles, "study")
}
random_terms <- c(random_terms, list(~ 1 | phylo_id))
component_roles <- c(component_roles, "phylogenetic_species")
if (isTRUE(random_effects$species_iid)) {
  random_terms <- c(random_terms, list(~ 1 | species_iid_id))
  component_roles <- c(component_roles, "species_iid")
}
if (isTRUE(random_effects$effect)) {
  random_terms <- c(random_terms, list(~ 1 | effect_re_id))
  component_roles <- c(component_roles, "effect")
}

R_list <- list(phylo_id = A)
captured_warnings <- character()
fit <- withCallingHandlers(
  tryCatch(
    metafor::rma.mv(
      yi = yi_internal,
      V = V,
      mods = mods_formula,
      random = random_terms,
      R = R_list,
      Rscale = "none",
      data = dat,
      method = method,
      test = test_method,
      dfs = dfs_method,
      level = level,
      cvvc = "varcor",
      control = list(nearpd = FALSE)
    ),
    error = function(e) abort(sprintf("rma.mv failed without model simplification: %s", conditionMessage(e)))
  ),
  warning = function(w) {
    captured_warnings <<- c(captured_warnings, conditionMessage(w))
    invokeRestart("muffleWarning")
  }
)
if (length(captured_warnings)) {
  abort(sprintf("rma.mv emitted warning(s); strict runner stopped: %s", paste(unique(captured_warnings), collapse = " | ")))
}
if (!inherits(fit, "rma.mv")) abort("rma.mv did not return an rma.mv model object.")
if (is.null(fit$opt.res) || is.null(fit$opt.res$convergence) || fit$opt.res$convergence != 0L) {
  abort("Optimizer did not report convergence code 0.")
}
if (length(fit$sigma2) != length(component_roles) || any(!is.finite(fit$sigma2))) {
  abort("Variance-component output is incomplete or non-finite.")
}
boundary <- fit$sigma2 <= variance_boundary_tolerance
if (any(boundary)) {
  abort(sprintf(
    "Variance component(s) at/below boundary tolerance %.12g: %s. The runner did not delete or fix components.",
    variance_boundary_tolerance,
    paste(component_roles[boundary], collapse = ", ")
  ))
}

hessian <- fit$hessian
if (!is.matrix(hessian) || nrow(hessian) != length(component_roles) || ncol(hessian) != length(component_roles) || any(!is.finite(hessian))) {
  abort("Variance-component Hessian is unavailable, incomplete, or non-finite.")
}
hessian_symmetry_error <- max(abs(hessian - t(hessian)))
hessian_scale <- max(1, max(abs(hessian)))
hessian_tolerance <- 1e-8 * hessian_scale
if (hessian_symmetry_error > hessian_tolerance) abort("Variance-component Hessian is not symmetric within tolerance.")
hessian_eigenvalues <- eigen((hessian + t(hessian)) / 2, symmetric = TRUE, only.values = TRUE)$values
hessian_minimum_eigenvalue <- min(hessian_eigenvalues)
if (hessian_minimum_eigenvalue <= hessian_tolerance) {
  abort(sprintf(
    "Variance-component Hessian is not strictly positive definite (minimum eigenvalue %.12g); parameters are not sufficiently identified.",
    hessian_minimum_eigenvalue
  ))
}
if (!is.matrix(fit$vvc) || any(!is.finite(fit$vvc))) abort("Variance-component covariance matrix could not be obtained from the Hessian.")

coefficient_terms <- rownames(fit$b)
if (is.null(coefficient_terms)) coefficient_terms <- paste0("coefficient_", seq_along(fit$se))
coefficient_df <- if (test_method == "t") as.numeric(fit$ddf) else rep(NA_real_, length(fit$se))
coefficients <- data.frame(
  term = coefficient_terms,
  estimate = as.numeric(fit$b),
  se = as.numeric(fit$se),
  statistic_type = if (test_method == "t") "t" else "z",
  statistic = as.numeric(fit$zval),
  df = coefficient_df,
  p_value = as.numeric(fit$pval),
  ci_lb = as.numeric(fit$ci.lb),
  ci_ub = as.numeric(fit$ci.ub),
  analysis_scale = analysis_scale,
  stringsAsFactors = FALSE
)
if (any(!is.finite(coefficients$estimate)) || any(!is.finite(coefficients$se)) ||
    any(!is.finite(coefficients$statistic)) || any(!is.finite(coefficients$p_value)) ||
    any(!is.finite(coefficients$ci_lb)) || any(!is.finite(coefficients$ci_ub))) {
  abort("Coefficient output contains non-finite values.")
}
if (test_method == "t" && any(!is.finite(coefficients$df) | coefficients$df <= 0)) {
  abort("Coefficient degrees of freedom are non-finite or non-positive.")
}

variance_se <- sqrt(diag(fit$vvc))
variance_component_correlation <- stats::cov2cor(fit$vvc)
variance_component_max_abs_correlation <- if (nrow(variance_component_correlation) > 1L) {
  max(abs(variance_component_correlation[row(variance_component_correlation) != col(variance_component_correlation)]))
} else {
  0
}
variance_components <- data.frame(
  component = component_roles,
  grouping_term = unname(fit$s.names),
  estimate = as.numeric(fit$sigma2),
  se_from_hessian = as.numeric(variance_se),
  boundary_tolerance = variance_boundary_tolerance,
  on_boundary = FALSE,
  covariance_structure = ifelse(component_roles == "phylogenetic_species", "R:phylogenetic_correlation", "IID"),
  stringsAsFactors = FALSE
)
if (any(!is.finite(variance_components$se_from_hessian))) abort("Variance-component standard errors are non-finite.")

owned_names <- c("coefficients.csv", "variance_components.csv", "analysis_manifest.json", "model.rds")
owned_paths <- file.path(output_dir, owned_names)
if (!overwrite && any(file.exists(owned_paths))) {
  abort(sprintf(
    "Output file(s) already exist and overwrite=false: %s.",
    paste(basename(owned_paths[file.exists(owned_paths)]), collapse = ", ")
  ))
}
if (!dir.exists(output_dir)) {
  created <- dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  if (!created || !dir.exists(output_dir)) abort(sprintf("Could not create output_dir: %s", output_dir))
}

file_md5 <- function(path) unname(as.character(tools::md5sum(path)))
manifest <- list(
  schema_version = "1.1.0",
  status = "success",
  structure_type = structure_type,
  generated_at_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
  specification = list(path = spec_path, md5 = file_md5(spec_path)),
  input = list(path = input_path, md5 = file_md5(input_path)),
  phylogeny = list(
    correlation_matrix_path = phylogeny_path,
    correlation_matrix_md5 = file_md5(phylogeny_path),
    source = phylogeny$source,
    version = phylogeny$version,
    branch_length_method = phylogeny$branch_length_method,
    pruning_rule = phylogeny$pruning_rule,
    validation = phylo_result$diagnostics
  ),
  sampling_covariance = if (is.null(sampling_v_path)) {
    list(type = "diagonal_vi", path = NULL, validation = NULL)
  } else {
    list(
      type = "full_sampling_v",
      path = sampling_v_path,
      md5 = file_md5(sampling_v_path),
      validation = sampling_v_result$diagnostics
    )
  },
  data_counts = list(
    effects = nrow(dat),
    independent_studies = independent_cluster_count,
    species = length(species_order),
    fixed_effect_coefficients = ncol(moderator_matrix)
  ),
  model = list(
    engine = "metafor::rma.mv",
    method = method,
    test = test_method,
    dfs = dfs_method,
    level = level,
    moderators = moderator_text,
    analysis_scale = analysis_scale,
    model_role = model_role,
    species_iid_exception_reason = species_iid_exception_reason,
    random_effects = random_effects,
    Rscale = "none",
    nearpd = FALSE,
    cvvc = "varcor",
    optimizer_convergence_code = fit$opt.res$convergence,
    optimizer_message = fit$opt.res$message,
    captured_warnings = unique(captured_warnings)
  ),
  identifiability = list(
    species_study_same_partition = species_study_confounded,
    study_effect_same_partition = study_effect_confounded,
    species_effect_same_partition = species_effect_confounded,
    variance_boundary_tolerance = variance_boundary_tolerance,
    hessian_policy = hessian_policy,
    hessian_symmetry_max_error = hessian_symmetry_error,
    hessian_minimum_eigenvalue = hessian_minimum_eigenvalue,
    variance_component_max_abs_correlation = variance_component_max_abs_correlation,
    variance_component_correlation_note = "Large absolute correlations indicate that variance components may be difficult to separate even when the Hessian passes."
  ),
  software = list(
    R = R.version.string,
    metafor = as.character(utils::packageVersion("metafor")),
    jsonlite = as.character(utils::packageVersion("jsonlite"))
  ),
  outputs = as.list(setNames(owned_paths, owned_names)),
  repair_applied = FALSE,
  near_pd_applied = FALSE
)

temporary_paths <- setNames(
  vapply(owned_names, function(name) tempfile(pattern = paste0(".", name, "."), tmpdir = output_dir), character(1)),
  owned_names
)
cleanup_temporaries <- function() {
  existing <- temporary_paths[file.exists(temporary_paths)]
  if (length(existing)) unlink(existing, force = TRUE)
}
on.exit(cleanup_temporaries(), add = TRUE)

tryCatch(
  write.csv(coefficients, temporary_paths[["coefficients.csv"]], row.names = FALSE, fileEncoding = "UTF-8", na = ""),
  error = function(e) abort(sprintf("Could not stage coefficients.csv: %s", conditionMessage(e)))
)
tryCatch(
  write.csv(variance_components, temporary_paths[["variance_components.csv"]], row.names = FALSE, fileEncoding = "UTF-8", na = ""),
  error = function(e) abort(sprintf("Could not stage variance_components.csv: %s", conditionMessage(e)))
)
model_bundle <- list(
  model = fit,
  specification = spec,
  input_data = dat,
  phylogenetic_correlation = A,
  sampling_V = if (is.matrix(V)) V else NULL,
  analysis_scale = analysis_scale,
  component_roles = component_roles
)
tryCatch(
  saveRDS(model_bundle, temporary_paths[["model.rds"]]),
  error = function(e) abort(sprintf("Could not stage model.rds: %s", conditionMessage(e)))
)
tryCatch(
  jsonlite::write_json(
    manifest,
    temporary_paths[["analysis_manifest.json"]],
    pretty = TRUE,
    auto_unbox = TRUE,
    null = "null",
    na = "null",
    digits = NA
  ),
  error = function(e) abort(sprintf("Could not stage analysis_manifest.json: %s", conditionMessage(e)))
)

for (name in owned_names) {
  target <- file.path(output_dir, name)
  if (file.exists(target)) {
    if (!overwrite) abort(sprintf("Output appeared during commit and overwrite=false: %s", target))
    if (!file.remove(target)) abort(sprintf("Could not replace existing output: %s", target))
  }
  if (!file.rename(temporary_paths[[name]], target)) abort(sprintf("Could not commit output: %s", target))
}

cat(sprintf(
  "OK: fitted phylogenetic rma.mv model with %d effects, %d studies, and %d species; outputs: %s\n",
  nrow(dat), independent_cluster_count, length(species_order), output_dir
))
