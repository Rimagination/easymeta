#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1)

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Conservative meta-analysis runner using metafor\n\n",
  "Usage:\n",
  "  Rscript run_meta_analysis.R --input FILE --output-dir DIR --model TYPE\n",
  "    --yi-col COLUMN --vi-col COLUMN --independent-cluster-col COLUMN\n",
  "    --analysis-scale SCALE --prediction yes|no [options]\n\n",
  "Required for every model:\n",
  "  --model common|random|multilevel\n",
  "  --independent-cluster-col COLUMN     independent study/sampling-unit identifier\n",
  "  --analysis-scale identity|log|fisher-z|logit|arcsine|arcsine_difference|sqrt|sqrt_difference|analysis\n",
  "  --prediction yes|no\n",
  "  --prediction-target TEXT             required with --prediction-components for multilevel prediction\n",
  "  --prediction-components CSV          non-empty variance-component labels; audit metadata only\n\n",
  "Model-specific requirements:\n",
  "  common:     uses method=EE and test=z; do not supply --tau-method or --test\n",
  "  random:     --tau-method DL|HE|HS|HSk|SJ|ML|REML|EB|PM|PMM --test z|t|knha\n",
  "  multilevel: --random '~ 1 | study/effect' --mv-method REML|ML --test z|t\n",
  "              with --test t, also supply --dfs residual|contain\n\n",
  "Dependence and robust inference:\n",
  "  --independent-cluster-col COLUMN     required; drives thresholds and cluster deletion\n",
  "  --dependence-topology independent|nested|one_way|crossed|mixed|unknown\n",
  "                                        required with --robust-cluster; crossed/mixed/unknown\n",
  "                                        are rejected for one-way CRVE\n",
  "  --id-col COLUMN --v-matrix FILE       FILE: first column row IDs, remaining headers column IDs\n",
  "  --robust-cluster COLUMN --robust-method CR0|CR1|CR2\n",
  "                                        CR2 requires installed clubSandwich\n\n",
  "Meta-regression and diagnostics:\n",
  "  --moderators '~ x + factor(group)'    one-sided formula; '.' is forbidden\n",
  "  --sensitivity-tau 'REML,PM,DL'        random univariate models only\n",
  "  --sensitivity-test 'knha,z'           random univariate models only\n",
  "  --leave-one-out yes|no                default: no; refits the unchanged model after\n",
  "                                        deleting each independent cluster; multilevel\n",
  "                                        refits subset both data and V; writes\n",
  "                                        leave_one_cluster_out.csv\n",
  "  --influence yes|no                    default: no\n",
  "  --small-study-test none|egger|rank    default: none; requires >=10 independent clusters\n",
  "  --trimfill yes|no                     default: no; exploratory; requires >=10 independent clusters\n\n",
  "Other options:\n",
  "  --study-label-col COLUMN\n",
  "  --level PERCENT                       default: 95\n",
  "  --na-action fail|omit                 default: fail; omit writes excluded_rows.csv\n",
  "  --overwrite yes|no                    default: no; yes replaces script-owned outputs only\n",
  "  --help\n\n",
  "The script never guesses scale/model/columns, installs packages, or silently drops rows.\n"
)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0L || "--help" %in% args) {
  cat(help_text)
  quit(save = "no", status = 0L, runLast = FALSE)
}

allowed_options <- c(
  "input", "output-dir", "model", "yi-col", "vi-col", "analysis-scale", "prediction",
  "prediction-target", "prediction-components", "dependence-topology",
  "tau-method", "test", "mv-method", "random", "dfs", "moderators",
  "independent-cluster-col", "id-col", "v-matrix", "robust-cluster", "robust-method", "study-label-col",
  "level", "na-action", "overwrite", "sensitivity-tau", "sensitivity-test",
  "leave-one-out", "influence", "small-study-test", "trimfill"
)

parse_cli <- function(x) {
  out <- list()
  i <- 1L
  while (i <= length(x)) {
    token <- x[[i]]
    if (!startsWith(token, "--")) abort(sprintf("Unexpected positional argument '%s'. Use --help.", token))
    key <- substring(token, 3L)
    if (!(key %in% allowed_options)) abort(sprintf("Unknown option '--%s'. Use --help.", key))
    if (!is.null(out[[key]])) abort(sprintf("Option '--%s' was supplied more than once.", key))
    if (i == length(x) || startsWith(x[[i + 1L]], "--")) abort(sprintf("Option '--%s' requires a value.", key))
    out[[key]] <- x[[i + 1L]]
    i <- i + 2L
  }
  out
}

opt <- parse_cli(args)
get_opt <- function(name, default = NULL) {
  value <- opt[[name]]
  if (is.null(value)) default else value
}
require_opt <- function(name) {
  value <- get_opt(name)
  if (is.null(value) || !nzchar(value)) abort(sprintf("Missing required option '--%s'.", name))
  value
}
parse_choice <- function(value, choices, label) {
  if (!(value %in% choices)) abort(sprintf("%s must be one of: %s.", label, paste(choices, collapse = ", ")))
  value
}
parse_yes_no <- function(value, label, default = NULL) {
  if (is.null(value)) {
    if (is.null(default)) abort(sprintf("%s must be explicitly set to yes or no.", label))
    return(default)
  }
  parse_choice(tolower(value), c("yes", "no"), label) == "yes"
}
parse_number <- function(value, label, lower = -Inf, upper = Inf, lower_open = FALSE,
                         upper_open = FALSE) {
  number <- suppressWarnings(as.numeric(value))
  if (length(number) != 1L || is.na(number) || !is.finite(number)) abort(sprintf("%s must be one finite number.", label))
  lower_bad <- if (lower_open) number <= lower else number < lower
  upper_bad <- if (upper_open) number >= upper else number > upper
  if (lower_bad || upper_bad) abort(sprintf("%s is outside the allowed range.", label))
  number
}
parse_nonempty_text <- function(value, label) {
  if (is.null(value)) return(NULL)
  cleaned <- trimws(value)
  if (!nzchar(cleaned)) abort(sprintf("%s must be non-empty when supplied.", label))
  if (grepl("[\r\n]", cleaned)) abort(sprintf("%s must be a single-line value.", label))
  cleaned
}
parse_nonempty_csv <- function(value, label) {
  cleaned <- parse_nonempty_text(value, label)
  if (is.null(cleaned)) return(NULL)
  values <- trimws(strsplit(cleaned, ",", fixed = TRUE)[[1L]])
  if (!length(values) || any(!nzchar(values))) {
    abort(sprintf("%s must be a comma-separated list of non-empty labels.", label))
  }
  if (anyDuplicated(values)) abort(sprintf("%s labels must be unique.", label))
  values
}
split_codes <- function(value, allowed, label, uppercase = FALSE) {
  codes <- trimws(strsplit(value, ",", fixed = TRUE)[[1L]])
  if (uppercase) codes <- toupper(codes) else codes <- tolower(codes)
  if (!length(codes) || any(!nzchar(codes)) || anyDuplicated(codes)) {
    abort(sprintf("%s must be a comma-separated list of unique non-empty codes.", label))
  }
  invalid <- setdiff(codes, allowed)
  if (length(invalid)) abort(sprintf("Invalid %s code(s): %s.", label, paste(invalid, collapse = ", ")))
  codes
}

input_path <- normalizePath(require_opt("input"), winslash = "/", mustWork = FALSE)
output_dir <- normalizePath(require_opt("output-dir"), winslash = "/", mustWork = FALSE)
model_type <- parse_choice(tolower(require_opt("model")), c("common", "random", "multilevel"), "--model")
yi_col <- require_opt("yi-col")
vi_col <- require_opt("vi-col")
independent_cluster_col <- require_opt("independent-cluster-col")
analysis_scale <- parse_choice(tolower(require_opt("analysis-scale")),
                               c(
                                 "identity", "log", "fisher-z", "logit", "arcsine",
                                 "arcsine_difference", "sqrt", "sqrt_difference", "analysis"
                               ), "--analysis-scale")
prediction_requested <- parse_yes_no(get_opt("prediction"), "--prediction")
prediction_target <- parse_nonempty_text(get_opt("prediction-target"), "--prediction-target")
prediction_component_values <- parse_nonempty_csv(get_opt("prediction-components"), "--prediction-components")
if (xor(is.null(prediction_target), is.null(prediction_component_values))) {
  abort("Supply --prediction-target and --prediction-components together.")
}
if (!prediction_requested && (!is.null(prediction_target) || !is.null(prediction_component_values))) {
  abort("--prediction-target and --prediction-components require --prediction yes.")
}
prediction_components <- if (is.null(prediction_component_values)) NULL else
  paste(prediction_component_values, collapse = ",")
dependence_topology <- if (is.null(get_opt("dependence-topology"))) NULL else
  parse_choice(
    tolower(parse_nonempty_text(get_opt("dependence-topology"), "--dependence-topology")),
    c("independent", "nested", "one_way", "crossed", "mixed", "unknown"),
    "--dependence-topology"
  )
level <- parse_number(get_opt("level", "95"), "--level", lower = 0, upper = 100,
                      lower_open = TRUE, upper_open = TRUE)
na_action <- parse_choice(tolower(get_opt("na-action", "fail")), c("fail", "omit"), "--na-action")
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", default = FALSE)
leave_one_out_requested <- parse_yes_no(get_opt("leave-one-out"), "--leave-one-out", default = FALSE)
influence_requested <- parse_yes_no(get_opt("influence"), "--influence", default = FALSE)
trimfill_requested <- parse_yes_no(get_opt("trimfill"), "--trimfill", default = FALSE)
small_study_test <- parse_choice(tolower(get_opt("small-study-test", "none")),
                                 c("none", "egger", "rank"), "--small-study-test")

if (!file.exists(input_path)) abort(sprintf("Input file does not exist: %s", input_path))
if (file.exists(output_dir) && !dir.exists(output_dir)) abort("--output-dir points to a file, not a directory.")
if (!dir.exists(output_dir) && !dir.exists(dirname(output_dir))) {
  abort(sprintf("Parent directory for --output-dir does not exist: %s", dirname(output_dir)))
}

tau_methods_allowed <- c("DL", "HE", "HS", "HSK", "SJ", "ML", "REML", "EB", "PM", "PMM")
if (model_type == "common") {
  if (!is.null(get_opt("tau-method")) || !is.null(get_opt("test")) || !is.null(get_opt("mv-method")) ||
      !is.null(get_opt("random")) || !is.null(get_opt("dfs"))) {
    abort("For --model common, do not supply tau/test/multilevel options; method=EE and test=z are fixed and recorded.")
  }
  if (prediction_requested) abort("A common-effect model does not have a random-effects prediction interval; use --prediction no.")
  tau_method <- "EE"
  test_method <- "z"
  mv_method <- NULL
  dfs_method <- NULL
} else if (model_type == "random") {
  tau_method <- toupper(require_opt("tau-method"))
  if (!(tau_method %in% tau_methods_allowed)) {
    abort(sprintf("--tau-method must be one of: %s.", paste(tau_methods_allowed, collapse = ", ")))
  }
  test_method <- parse_choice(tolower(require_opt("test")), c("z", "t", "knha"), "--test")
  if (!is.null(get_opt("mv-method")) || !is.null(get_opt("random")) || !is.null(get_opt("dfs"))) {
    abort("--mv-method, --random, and --dfs are only valid for --model multilevel.")
  }
  mv_method <- NULL
  dfs_method <- NULL
} else {
  if (!is.null(get_opt("tau-method"))) abort("--tau-method is only valid for --model random; use --mv-method for multilevel models.")
  mv_method <- toupper(require_opt("mv-method"))
  if (!(mv_method %in% c("REML", "ML"))) abort("--mv-method must be REML or ML.")
  test_method <- parse_choice(tolower(require_opt("test")), c("z", "t"), "--test")
  if (test_method == "t") {
    dfs_method <- parse_choice(tolower(require_opt("dfs")), c("residual", "contain"), "--dfs")
  } else {
    if (!is.null(get_opt("dfs"))) abort("--dfs is only used when --test t.")
    dfs_method <- "residual"
  }
  tau_method <- NULL
}

if (model_type == "multilevel" && prediction_requested &&
    (is.null(prediction_target) || is.null(prediction_components))) {
  abort("Multilevel models with --prediction yes require non-empty --prediction-target and --prediction-components.")
}

prediction_target_record <- if (!prediction_requested) {
  "not_requested"
} else if (is.null(prediction_target)) {
  "legacy_model_default"
} else {
  prediction_target
}
prediction_components_record <- if (!prediction_requested) {
  "not_requested"
} else if (is.null(prediction_components)) {
  "legacy_model_default"
} else {
  prediction_components
}

if (!is.null(get_opt("v-matrix")) && model_type != "multilevel") abort("--v-matrix is only valid for --model multilevel.")
if (!is.null(get_opt("id-col")) && is.null(get_opt("v-matrix"))) abort("--id-col is only needed with --v-matrix.")
if (!is.null(get_opt("v-matrix")) && is.null(get_opt("id-col"))) abort("--v-matrix requires --id-col.")

robust_cluster <- get_opt("robust-cluster")
robust_method <- get_opt("robust-method")
if (xor(is.null(robust_cluster), is.null(robust_method))) {
  abort("Supply --robust-cluster and --robust-method together.")
}
if (!is.null(robust_method)) robust_method <- parse_choice(toupper(robust_method), c("CR0", "CR1", "CR2"), "--robust-method")
if (!is.null(robust_cluster) && is.null(dependence_topology)) {
  abort("--robust-cluster requires an explicit --dependence-topology.")
}
if (!is.null(robust_cluster) && dependence_topology %in% c("crossed", "mixed", "unknown")) {
  abort(sprintf(
    "One-way CRVE is not permitted for dependence topology '%s'; obtain a model that addresses the crossed or unresolved dependence.",
    dependence_topology
  ))
}

if (!is.null(get_opt("sensitivity-tau")) && model_type != "random") {
  abort("--sensitivity-tau is only available for --model random.")
}
if (!is.null(get_opt("sensitivity-test")) && model_type != "random") {
  abort("--sensitivity-test is only available for --model random.")
}
dat <- tryCatch(
  read.csv(input_path, check.names = FALSE, fileEncoding = "UTF-8", na.strings = c("", "NA")),
  error = function(e) abort(sprintf("Could not read UTF-8 CSV '%s': %s", input_path, conditionMessage(e)))
)
if (nrow(dat) == 0L) abort("Input contains no data rows.")
if (anyDuplicated(names(dat))) abort("Input column names must be unique.")
if ("analysis_source_row" %in% names(dat)) abort("Input column 'analysis_source_row' is reserved; rename it before running.")
if (identical(yi_col, vi_col)) abort("--yi-col and --vi-col must refer to different columns.")
if (independent_cluster_col %in% c(yi_col, vi_col)) {
  abort("--independent-cluster-col must differ from --yi-col and --vi-col.")
}
dat$analysis_source_row <- seq_len(nrow(dat))

if ("analysis_scale" %in% names(dat)) {
  input_scales <- tolower(trimws(as.character(dat$analysis_scale)))
  missing_scales <- is.na(dat$analysis_scale) | input_scales == ""
  if (any(missing_scales)) {
    abort(sprintf(
      "Input analysis_scale is missing/blank at source row(s): %s.",
      paste(dat$analysis_source_row[missing_scales], collapse = ", ")
    ))
  }
  mismatched_scales <- input_scales != analysis_scale
  if (any(mismatched_scales)) {
    details <- paste0(
      dat$analysis_source_row[mismatched_scales], "=", input_scales[mismatched_scales]
    )
    abort(sprintf(
      "Input analysis_scale must match --analysis-scale '%s' at every row; mismatch(es): %s.",
      analysis_scale, paste(details, collapse = ", ")
    ))
  }
}
original_dat <- dat

numeric_column <- function(data, column_name, label) {
  if (!(column_name %in% names(data))) abort(sprintf("%s refers to missing column '%s'.", label, column_name))
  raw <- data[[column_name]]
  text_value <- trimws(as.character(raw))
  missing <- is.na(raw) | text_value == ""
  value <- suppressWarnings(as.numeric(text_value))
  bad <- !missing & is.na(value)
  if (any(bad)) {
    abort(sprintf("Column '%s' contains non-numeric values at source row(s): %s.",
                  column_name, paste(data$analysis_source_row[bad], collapse = ", ")))
  }
  value[missing] <- NA_real_
  value
}

dat[[yi_col]] <- numeric_column(dat, yi_col, "--yi-col")
dat[[vi_col]] <- numeric_column(dat, vi_col, "--vi-col")

parse_formula <- function(text, label) {
  formula <- tryCatch(as.formula(text, env = environment()),
                      error = function(e) abort(sprintf("Invalid %s formula: %s", label, conditionMessage(e))))
  if (length(formula) != 2L) abort(sprintf("%s must be a one-sided formula beginning with '~'.", label))
  variables <- all.vars(formula)
  term_labels <- attr(stats::terms(formula), "term.labels")
  if ("." %in% variables || "." %in% term_labels) abort(sprintf("%s may not use '.'; list columns explicitly.", label))
  missing_columns <- setdiff(variables, names(dat))
  if (length(missing_columns)) {
    abort(sprintf("%s refers to missing column(s): %s.", label, paste(missing_columns, collapse = ", ")))
  }
  formula
}

moderators_formula <- if (is.null(get_opt("moderators"))) NULL else parse_formula(get_opt("moderators"), "--moderators")
random_formula <- if (model_type == "multilevel") parse_formula(require_opt("random"), "--random") else NULL

required_columns <- unique(c(
  yi_col, vi_col, independent_cluster_col,
  if (!is.null(moderators_formula)) all.vars(moderators_formula),
  if (!is.null(random_formula)) all.vars(random_formula),
  robust_cluster, get_opt("study-label-col"), get_opt("id-col")
))
required_columns <- required_columns[!is.na(required_columns) & nzchar(required_columns)]
missing_columns <- setdiff(required_columns, names(dat))
if (length(missing_columns)) abort(sprintf("Required column(s) not found: %s.", paste(missing_columns, collapse = ", ")))

missing_mask <- lapply(required_columns, function(nm) {
  x <- dat[[nm]]
  is.na(x) | trimws(as.character(x)) == ""
})
names(missing_mask) <- required_columns
complete <- !Reduce(`|`, missing_mask)
excluded_rows <- NULL
if (any(!complete)) {
  if (na_action == "fail") {
    abort(sprintf("Missing model-required values at source row(s): %s. Fix them or explicitly use --na-action omit.",
                  paste(dat$analysis_source_row[!complete], collapse = ", ")))
  }
  missing_details <- vapply(which(!complete), function(i) {
    paste(required_columns[vapply(missing_mask, function(x) x[[i]], logical(1))], collapse = ";")
  }, character(1))
  excluded_rows <- dat[!complete, , drop = FALSE]
  excluded_rows$exclusion_reason <- paste0("missing_required:", missing_details)
  dat <- dat[complete, , drop = FALSE]
}
if (nrow(dat) < 2L) abort("At least two complete effect-size rows are required.")
if (any(!is.finite(dat[[yi_col]]))) abort("All included yi values must be finite.")
if (any(!is.finite(dat[[vi_col]]) | dat[[vi_col]] <= 0)) abort("All included vi values must be finite and > 0.")

dat[[independent_cluster_col]] <- trimws(as.character(dat[[independent_cluster_col]]))
independent_clusters <- unique(dat[[independent_cluster_col]])
independent_cluster_count <- length(independent_clusters)
if (independent_cluster_count < 2L) {
  abort("At least two independent clusters are required after applying the missing-value policy.")
}

same_partition <- function(first, second) {
  if (length(first) != length(second)) return(FALSE)
  first_to_second <- vapply(
    split(second, first),
    function(values) length(unique(values)) == 1L,
    logical(1)
  )
  second_to_first <- vapply(
    split(first, second),
    function(values) length(unique(values)) == 1L,
    logical(1)
  )
  all(first_to_second) && all(second_to_first)
}

robust_cluster_count <- NA_integer_
if (!is.null(robust_cluster)) {
  dat[[robust_cluster]] <- trimws(as.character(dat[[robust_cluster]]))
  if (!identical(robust_cluster, independent_cluster_col) &&
      !same_partition(dat[[robust_cluster]], dat[[independent_cluster_col]])) {
    abort(paste0(
      "--robust-cluster and --independent-cluster-col must define exactly the same partition ",
      "when they name different columns."
    ))
  }
  robust_cluster_count <- length(unique(dat[[robust_cluster]]))
}

if (analysis_scale == "arcsine" &&
    any(dat[[yi_col]] < 0 | dat[[yi_col]] > pi / 2)) {
  abort("On --analysis-scale arcsine, every included yi must be between 0 and pi/2.")
}
if (analysis_scale == "sqrt" && any(dat[[yi_col]] < 0)) {
  abort("On --analysis-scale sqrt, every included yi must be >= 0.")
}

moderator_matrix <- NULL
if (!is.null(moderators_formula)) {
  moderator_matrix <- tryCatch(
    model.matrix(moderators_formula, data = dat),
    error = function(e) abort(sprintf("Could not construct moderator model matrix: %s", conditionMessage(e)))
  )
  if (independent_cluster_count <= ncol(moderator_matrix)) {
    abort(sprintf(
      paste0(
        "Meta-regression has %d independent clusters for %d model-matrix coefficients; ",
        "independent-cluster residual degrees of freedom are not positive."
      ),
      independent_cluster_count, ncol(moderator_matrix)
    ))
  }
}

V <- dat[[vi_col]]
v_matrix_path <- NULL
if (!is.null(get_opt("v-matrix"))) {
  v_matrix_path <- normalizePath(get_opt("v-matrix"), winslash = "/", mustWork = FALSE)
  if (!file.exists(v_matrix_path)) abort(sprintf("V matrix file does not exist: %s", v_matrix_path))
  id_col <- get_opt("id-col")
  original_ids <- trimws(as.character(original_dat[[id_col]]))
  if (any(is.na(original_ids) | original_ids == "")) abort("--id-col cannot contain missing/blank IDs when --v-matrix is used.")
  if (anyDuplicated(original_ids)) abort("--id-col values must be unique when --v-matrix is used.")
  vraw <- tryCatch(
    read.csv(v_matrix_path, check.names = FALSE, fileEncoding = "UTF-8", na.strings = c("", "NA")),
    error = function(e) abort(sprintf("Could not read V matrix CSV: %s", conditionMessage(e)))
  )
  if (ncol(vraw) < 2L || nrow(vraw) == 0L) abort("V matrix CSV must have an ID column and at least one numeric column.")
  row_ids <- trimws(as.character(vraw[[1L]]))
  col_ids <- names(vraw)[-1L]
  if (any(is.na(row_ids) | row_ids == "") || anyDuplicated(row_ids) || anyDuplicated(col_ids)) {
    abort("V matrix row and column IDs must be non-empty and unique.")
  }
  if (!setequal(row_ids, col_ids) || !setequal(row_ids, original_ids)) {
    abort("V matrix row IDs, column IDs, and input --id-col values must be exactly the same set.")
  }
  numeric_cols <- lapply(seq_len(ncol(vraw) - 1L), function(j) {
    raw <- vraw[[j + 1L]]
    text_value <- trimws(as.character(raw))
    value <- suppressWarnings(as.numeric(text_value))
    if (any(is.na(value) | !is.finite(value))) abort(sprintf("V matrix column '%s' contains missing or non-numeric values.", col_ids[[j]]))
    value
  })
  V_full <- do.call(cbind, numeric_cols)
  rownames(V_full) <- row_ids
  colnames(V_full) <- col_ids
  V_full <- V_full[original_ids, original_ids, drop = FALSE]
  scale_v <- max(1, max(abs(V_full)))
  tolerance <- 1e-8 * scale_v
  if (max(abs(V_full - t(V_full))) > tolerance) abort("V matrix is not symmetric within numerical tolerance.")
  if (any(diag(V_full) <= 0)) abort("V matrix diagonal entries must be > 0.")
  min_eigen <- min(eigen((V_full + t(V_full)) / 2, symmetric = TRUE, only.values = TRUE)$values)
  if (min_eigen < -tolerance) abort(sprintf("V matrix is not positive semidefinite (minimum eigenvalue %.6g).", min_eigen))
  current_ids <- trimws(as.character(dat[[id_col]]))
  V <- V_full[current_ids, current_ids, drop = FALSE]
  diagonal_tolerance <- 1e-6 * pmax(1, abs(dat[[vi_col]]))
  mismatch <- abs(diag(V) - dat[[vi_col]]) > diagonal_tolerance
  if (any(mismatch)) {
    abort(sprintf("V diagonal does not match --vi-col at source row(s): %s.",
                  paste(dat$analysis_source_row[mismatch], collapse = ", ")))
  }
}

if (!requireNamespace("metafor", quietly = TRUE)) {
  abort(paste0(
    "Required package 'metafor' is not installed in this R library. ",
    "Install it deliberately in the project/library you intend to use, for example: ",
    "install.packages('metafor'). The script did not install anything. Current .libPaths(): ",
    paste(.libPaths(), collapse = "; ")
  ))
}
if (identical(robust_method, "CR2") && !requireNamespace("clubSandwich", quietly = TRUE)) {
  abort(paste0(
    "--robust-method CR2 requires package 'clubSandwich'. Install it deliberately with ",
    "install.packages('clubSandwich') in the intended library, then rerun. Nothing was installed."
  ))
}

study_labels <- if (is.null(get_opt("study-label-col"))) {
  paste0("row_", dat$analysis_source_row)
} else {
  as.character(dat[[get_opt("study-label-col")]])
}

captured_warnings <- character()
capture_warnings <- function(expr) {
  withCallingHandlers(
    expr,
    warning = function(w) {
      captured_warnings <<- c(captured_warnings, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )
}

fit_model <- function(tau = tau_method, test = test_method, fit_data = dat,
                      fit_V = V, fit_labels = study_labels) {
  if (model_type == "common") {
    args <- list(
      yi = fit_data[[yi_col]], vi = fit_data[[vi_col]], data = fit_data,
      slab = fit_labels, method = "EE", test = "z", level = level
    )
    if (!is.null(moderators_formula)) args$mods <- moderators_formula
    do.call(metafor::rma.uni, args)
  } else if (model_type == "random") {
    args <- list(
      yi = fit_data[[yi_col]], vi = fit_data[[vi_col]], data = fit_data,
      slab = fit_labels, method = tau, test = test, level = level
    )
    if (!is.null(moderators_formula)) args$mods <- moderators_formula
    do.call(metafor::rma.uni, args)
  } else {
    args <- list(
      yi = fit_data[[yi_col]], V = fit_V, random = random_formula, data = fit_data,
      slab = fit_labels, method = mv_method, test = test_method,
      dfs = dfs_method, level = level
    )
    if (!is.null(moderators_formula)) args$mods <- moderators_formula
    do.call(metafor::rma.mv, args)
  }
}

model <- tryCatch(
  capture_warnings(fit_model()),
  error = function(e) abort(sprintf("Model fitting failed: %s", conditionMessage(e)))
)

inference_model <- model
apply_robust_inference <- function(fitted_model, fit_data, context = "Robust inference") {
  if (is.null(robust_cluster)) return(fitted_model)
  clusters <- fit_data[[robust_cluster]]
  cluster_count <- length(unique(clusters))
  if (cluster_count <= fitted_model$p) {
    abort(sprintf("%s has %d clusters but %d model coefficients; residual degrees of freedom are not positive.",
                  context, cluster_count, fitted_model$p))
  }
  tryCatch(
    capture_warnings(metafor::robust(
      fitted_model,
      cluster = clusters,
      adjust = robust_method != "CR0",
      clubSandwich = robust_method == "CR2"
    )),
    error = function(e) abort(sprintf("%s failed: %s", context, conditionMessage(e)))
  )
}
inference_model <- apply_robust_inference(model, dat)

record_warning <- function(message) {
  captured_warnings <<- c(captured_warnings, message)
  invisible(NULL)
}

safe_exp <- function(x) {
  too_large <- is.finite(x) & x > log(.Machine$double.xmax)
  if (any(too_large)) {
    abort("Log-scale back-transformation would overflow; inspect the fitted estimate/interval on the analysis scale.")
  }
  exp(x)
}
safe_arcsine_inverse <- function(x) {
  outside <- is.finite(x) & (x < 0 | x > pi / 2)
  if (any(outside)) {
    record_warning("Arcsine display values outside [0, pi/2] were clipped to the valid inverse-transform domain before applying sin(x)^2.")
  }
  sin(pmin(pi / 2, pmax(0, x)))^2
}
safe_sqrt_inverse <- function(x) {
  below_zero <- is.finite(x) & x < 0
  if (any(below_zero)) {
    record_warning("Square-root display values below 0 were clipped to 0 before squaring to preserve a monotone valid-domain inverse.")
  }
  pmax(0, x)^2
}

display_transform <- switch(
  analysis_scale,
  identity = "identity",
  log = "exp",
  `fisher-z` = "tanh",
  logit = "plogis",
  arcsine = "sin(x)^2_with_domain_clipping",
  arcsine_difference = "identity_no_unique_marginal_inverse",
  sqrt = "x^2_with_nonnegative_domain_clipping",
  sqrt_difference = "identity_no_unique_marginal_inverse",
  analysis = "identity_unspecified_analysis_scale"
)
back_transform <- switch(
  analysis_scale,
  identity = identity,
  log = safe_exp,
  `fisher-z` = tanh,
  logit = plogis,
  arcsine = safe_arcsine_inverse,
  arcsine_difference = identity,
  sqrt = safe_sqrt_inverse,
  sqrt_difference = identity,
  analysis = identity
)
if (analysis_scale %in% c("arcsine_difference", "sqrt_difference")) {
  record_warning(paste0(
    "Scale '", analysis_scale,
    "' is a contrast on a transformed scale and has no unique marginal back-transformation without explicit reference values; display columns retain the analysis scale."
  ))
}
if (analysis_scale == "analysis") {
  record_warning("Scale 'analysis' is intentionally unspecified; display columns retain the supplied analysis scale.")
}

back_transform_coefficients <- function(values, terms) {
  identity_display_scales <- c("identity", "analysis", "arcsine_difference", "sqrt_difference")
  if (analysis_scale %in% identity_display_scales) return(back_transform(values))
  intercept <- terms %in% c("intrcpt", "(Intercept)", "intercept")
  transformed <- rep(NA_real_, length(values))
  transformed[intercept] <- back_transform(values[intercept])
  transformed
}
if (!is.null(moderators_formula) &&
    !(analysis_scale %in% c("identity", "analysis", "arcsine_difference", "sqrt_difference"))) {
  record_warning(paste0(
    "For meta-regression on scale '", analysis_scale,
    "', only intercept coefficients are back-transformed for display; non-intercept coefficients remain available on the analysis scale."
  ))
}

numeric_or_na <- function(x, n) {
  if (is.null(x) || !is.numeric(x) || !length(x)) rep(NA_real_, n) else rep_len(as.numeric(x), n)
}

coefficient_names <- function(fitted_model) {
  names_out <- rownames(fitted_model$beta)
  if (is.null(names_out)) names_out <- names(stats::coef(fitted_model))
  if (is.null(names_out)) names_out <- paste0("beta_", seq_along(as.numeric(fitted_model$beta)))
  as.character(names_out)
}

beta <- as.numeric(inference_model$beta)
n_beta <- length(beta)
coef_names <- coefficient_names(inference_model)
df_candidate <- inference_model$ddf
if (is.null(df_candidate) && is.numeric(inference_model$dfs)) df_candidate <- inference_model$dfs
coefficients <- data.frame(
  term = coef_names,
  estimate = beta,
  se = numeric_or_na(inference_model$se, n_beta),
  statistic = numeric_or_na(inference_model$zval, n_beta),
  df = numeric_or_na(df_candidate, n_beta),
  p_value = numeric_or_na(inference_model$pval, n_beta),
  ci_lower = numeric_or_na(inference_model$ci.lb, n_beta),
  ci_upper = numeric_or_na(inference_model$ci.ub, n_beta),
  inference = if (is.null(robust_method)) "model_based" else robust_method,
  stringsAsFactors = FALSE
)
coefficients$display_estimate <- back_transform_coefficients(coefficients$estimate, coefficients$term)
coefficients$display_ci_lower <- back_transform_coefficients(coefficients$ci_lower, coefficients$term)
coefficients$display_ci_upper <- back_transform_coefficients(coefficients$ci_upper, coefficients$term)
coefficients$display_note <- ifelse(
  is.na(coefficients$display_estimate) & !is.na(coefficients$estimate),
  "not_back_transformed_non_intercept_coefficient",
  display_transform
)

metric_rows <- list()
add_metrics <- function(name, values, inference_basis = "model_based") {
  if (is.null(values) || !length(values)) return(invisible(NULL))
  for (i in seq_along(values)) {
    metric_rows[[length(metric_rows) + 1L]] <<- data.frame(
      metric = if (length(values) == 1L) name else paste0(name, "_", i),
      value = as.numeric(values[[i]]),
      inference_basis = inference_basis,
      stringsAsFactors = FALSE
    )
  }
}
add_metrics("k", model$k)
add_metrics("p", model$p)
add_metrics("independent_clusters", independent_cluster_count)
add_metrics("effect_rows_per_independent_cluster", nrow(dat) / independent_cluster_count)
if (!is.null(moderator_matrix)) {
  add_metrics("meta_regression_coefficients", ncol(moderator_matrix))
  add_metrics("independent_clusters_per_meta_regression_coefficient",
              independent_cluster_count / ncol(moderator_matrix))
}
add_metrics("tau2", model$tau2)
add_metrics("sigma2", model$sigma2)
add_metrics("rho", model$rho)
add_metrics("gamma2", model$gamma2)
add_metrics("phi", model$phi)
add_metrics("I2", model$I2)
add_metrics("H2", model$H2)
add_metrics("R2", model$R2)
add_metrics("QE", model$QE)
add_metrics("QE_p", model$QEp)
add_metrics("QM", model$QM)
add_metrics("QM_p", model$QMp)
heterogeneity <- if (length(metric_rows)) {
  do.call(rbind, metric_rows)
} else {
  data.frame(metric = character(), value = numeric(), inference_basis = character())
}

predictions <- NULL
if (prediction_requested) {
  predictions_object <- tryCatch(
    capture_warnings(stats::predict(inference_model, level = level)),
    error = function(e) abort(sprintf("Prediction calculation failed: %s", conditionMessage(e)))
  )
  n_pred <- length(predictions_object$pred)
  prediction_labels <- if (n_pred == nrow(dat) && !is.null(moderators_formula)) {
    study_labels
  } else if (n_pred == 1L) {
    "summary"
  } else {
    paste0("prediction_", seq_len(n_pred))
  }
  predictions <- data.frame(
    label = prediction_labels,
    prediction_target = rep(prediction_target_record, n_pred),
    prediction_components = rep(prediction_components_record, n_pred),
    pred = as.numeric(predictions_object$pred),
    se = numeric_or_na(predictions_object$se, n_pred),
    ci_lower = numeric_or_na(predictions_object$ci.lb, n_pred),
    ci_upper = numeric_or_na(predictions_object$ci.ub, n_pred),
    pi_lower = numeric_or_na(predictions_object$pi.lb, n_pred),
    pi_upper = numeric_or_na(predictions_object$pi.ub, n_pred),
    stringsAsFactors = FALSE
  )
  predictions$display_pred <- back_transform(predictions$pred)
  predictions$display_ci_lower <- back_transform(predictions$ci_lower)
  predictions$display_ci_upper <- back_transform(predictions$ci_upper)
  predictions$display_pi_lower <- back_transform(predictions$pi_lower)
  predictions$display_pi_upper <- back_transform(predictions$pi_upper)
}

sensitivity_models <- NULL
if (!is.null(get_opt("sensitivity-tau")) || !is.null(get_opt("sensitivity-test"))) {
  tau_values <- if (is.null(get_opt("sensitivity-tau"))) tau_method else
    split_codes(get_opt("sensitivity-tau"), tau_methods_allowed, "--sensitivity-tau", uppercase = TRUE)
  test_values <- if (is.null(get_opt("sensitivity-test"))) test_method else
    split_codes(get_opt("sensitivity-test"), c("z", "t", "knha"), "--sensitivity-test")
  grid <- expand.grid(tau_method = tau_values, test = test_values, stringsAsFactors = FALSE)
  rows <- list()
  for (i in seq_len(nrow(grid))) {
    smod <- tryCatch(capture_warnings(fit_model(grid$tau_method[[i]], grid$test[[i]])), error = identity)
    if (inherits(smod, "error")) {
      rows[[length(rows) + 1L]] <- data.frame(
        tau_method = grid$tau_method[[i]], test = grid$test[[i]], term = NA_character_,
        estimate = NA_real_, se = NA_real_, ci_lower = NA_real_, ci_upper = NA_real_,
        p_value = NA_real_, tau2 = NA_real_, status = paste0("error: ", conditionMessage(smod)),
        stringsAsFactors = FALSE
      )
    } else {
      sbeta <- as.numeric(smod$beta)
      snames <- rownames(smod$beta)
      if (is.null(snames)) snames <- paste0("beta_", seq_along(sbeta))
      rows[[length(rows) + 1L]] <- data.frame(
        tau_method = grid$tau_method[[i]], test = grid$test[[i]], term = snames,
        estimate = sbeta, se = numeric_or_na(smod$se, length(sbeta)),
        ci_lower = numeric_or_na(smod$ci.lb, length(sbeta)),
        ci_upper = numeric_or_na(smod$ci.ub, length(sbeta)),
        p_value = numeric_or_na(smod$pval, length(sbeta)),
        tau2 = rep_len(as.numeric(smod$tau2), length(sbeta)), status = "ok",
        stringsAsFactors = FALSE
      )
    }
  }
  sensitivity_models <- do.call(rbind, rows)
  sensitivity_models$display_estimate <- back_transform_coefficients(
    sensitivity_models$estimate, sensitivity_models$term
  )
  sensitivity_models$display_ci_lower <- back_transform_coefficients(
    sensitivity_models$ci_lower, sensitivity_models$term
  )
  sensitivity_models$display_ci_upper <- back_transform_coefficients(
    sensitivity_models$ci_upper, sensitivity_models$term
  )
  sensitivity_models$display_note <- ifelse(
    is.na(sensitivity_models$display_estimate) & !is.na(sensitivity_models$estimate),
    "not_back_transformed_non_intercept_coefficient",
    display_transform
  )
}

leave_one_cluster_out <- NULL
if (leave_one_out_requested) {
  if (independent_cluster_count < 3L) {
    abort("--leave-one-out requires at least three independent clusters so each refit retains at least two.")
  }
  component_text <- function(x) {
    if (is.null(x) || !length(x)) return(NA_character_)
    paste(format(as.numeric(x), digits = 17L, scientific = TRUE, trim = TRUE), collapse = ";")
  }
  loo_rows <- vector("list", independent_cluster_count)
  independent_cluster_values <- dat[[independent_cluster_col]]
  for (i in seq_along(independent_clusters)) {
    omitted_cluster <- independent_clusters[[i]]
    keep <- independent_cluster_values != omitted_cluster
    loo_dat <- dat[keep, , drop = FALSE]
    loo_labels <- study_labels[keep]
    loo_V <- V
    v_subset_method <- "not_used_by_univariate_model"
    if (model_type == "multilevel") {
      if (is.matrix(V) || inherits(V, "Matrix")) {
        if (!identical(dim(V), c(nrow(dat), nrow(dat)))) {
          abort("Internal V alignment error before leave-one-cluster-out refitting.")
        }
        loo_V <- V[keep, keep, drop = FALSE]
        v_subset_method <- "row_and_column_subset"
      } else {
        if (length(V) != nrow(dat)) {
          abort("Internal diagonal-V alignment error before leave-one-cluster-out refitting.")
        }
        loo_V <- V[keep]
        v_subset_method <- "diagonal_vector_subset"
      }
      expected_dimension <- nrow(loo_dat)
      if ((is.matrix(loo_V) || inherits(loo_V, "Matrix")) &&
          !identical(dim(loo_V), c(expected_dimension, expected_dimension))) {
        abort(sprintf("Internal V subset alignment error after omitting cluster '%s'.", omitted_cluster))
      }
      if (!(is.matrix(loo_V) || inherits(loo_V, "Matrix")) && length(loo_V) != expected_dimension) {
        abort(sprintf("Internal diagonal-V subset alignment error after omitting cluster '%s'.", omitted_cluster))
      }
    }
    loo_base <- tryCatch(
      capture_warnings(fit_model(fit_data = loo_dat, fit_V = loo_V, fit_labels = loo_labels)),
      error = function(e) abort(sprintf(
        "Leave-one-cluster-out refit failed when omitting cluster '%s': %s",
        omitted_cluster, conditionMessage(e)
      ))
    )
    loo_inference <- apply_robust_inference(
      loo_base, loo_dat,
      context = sprintf("Leave-one-cluster-out robust inference after omitting '%s'", omitted_cluster)
    )
    loo_terms <- coefficient_names(loo_inference)
    if (!identical(loo_terms, coef_names)) {
      abort(sprintf(
        paste0(
          "Leave-one-cluster-out refit changed the coefficient structure when omitting cluster '%s' ",
          "(full: %s; refit: %s). The model was not silently simplified."
        ),
        omitted_cluster, paste(coef_names, collapse = ","), paste(loo_terms, collapse = ",")
      ))
    }
    loo_beta <- as.numeric(loo_inference$beta)
    n_loo_beta <- length(loo_beta)
    loo_df_candidate <- loo_inference$ddf
    if (is.null(loo_df_candidate) && is.numeric(loo_inference$dfs)) {
      loo_df_candidate <- loo_inference$dfs
    }
    loo_rows[[i]] <- data.frame(
      omitted_cluster = rep(omitted_cluster, n_loo_beta),
      term = loo_terms,
      rows_omitted = rep(sum(!keep), n_loo_beta),
      clusters_remaining = rep(length(unique(loo_dat[[independent_cluster_col]])), n_loo_beta),
      model_type = rep(model_type, n_loo_beta),
      random_formula = rep(
        if (is.null(random_formula)) "none" else paste(deparse(random_formula), collapse = " "),
        n_loo_beta
      ),
      v_subset = rep(v_subset_method, n_loo_beta),
      estimate = loo_beta,
      se = numeric_or_na(loo_inference$se, n_loo_beta),
      statistic = numeric_or_na(loo_inference$zval, n_loo_beta),
      df = numeric_or_na(loo_df_candidate, n_loo_beta),
      p_value = numeric_or_na(loo_inference$pval, n_loo_beta),
      ci_lower = numeric_or_na(loo_inference$ci.lb, n_loo_beta),
      ci_upper = numeric_or_na(loo_inference$ci.ub, n_loo_beta),
      tau2 = numeric_or_na(loo_base$tau2, n_loo_beta),
      sigma2 = rep(component_text(loo_base$sigma2), n_loo_beta),
      rho = rep(component_text(loo_base$rho), n_loo_beta),
      gamma2 = rep(component_text(loo_base$gamma2), n_loo_beta),
      phi = rep(component_text(loo_base$phi), n_loo_beta),
      I2 = numeric_or_na(loo_base$I2, n_loo_beta),
      inference = rep(if (is.null(robust_method)) "model_based" else robust_method, n_loo_beta),
      stringsAsFactors = FALSE
    )
  }
  leave_one_cluster_out <- do.call(rbind, loo_rows)
  leave_one_cluster_out$display_estimate <- back_transform_coefficients(
    leave_one_cluster_out$estimate, leave_one_cluster_out$term
  )
  leave_one_cluster_out$display_ci_lower <- back_transform_coefficients(
    leave_one_cluster_out$ci_lower, leave_one_cluster_out$term
  )
  leave_one_cluster_out$display_ci_upper <- back_transform_coefficients(
    leave_one_cluster_out$ci_upper, leave_one_cluster_out$term
  )
  leave_one_cluster_out$display_note <- ifelse(
    is.na(leave_one_cluster_out$display_estimate) & !is.na(leave_one_cluster_out$estimate),
    "not_back_transformed_non_intercept_coefficient",
    display_transform
  )
}

influence_text <- NULL
if (influence_requested) {
  influence_object <- tryCatch(capture_warnings(stats::influence(model)), error = identity)
  influence_text <- if (inherits(influence_object, "error")) {
    paste0("Influence diagnostics failed: ", conditionMessage(influence_object))
  } else {
    capture.output(print(influence_object))
  }
}

small_study_text <- NULL
if (small_study_test != "none") {
  if (model_type == "multilevel" || !is.null(moderators_formula)) {
    abort("Small-study tests in this CLI are restricted to intercept-only rma.uni models.")
  }
  if (independent_cluster_count < 10L) {
    abort("Small-study tests require at least 10 independent clusters in this conservative workflow.")
  }
  test_object <- tryCatch(
    capture_warnings(if (small_study_test == "egger") metafor::regtest(model) else metafor::ranktest(model)),
    error = function(e) abort(sprintf("Small-study test failed: %s", conditionMessage(e)))
  )
  small_study_text <- c(
    "This is a test of funnel-plot asymmetry/small-study effects, not proof of publication bias.",
    capture.output(print(test_object))
  )
}

trimfill_text <- NULL
trimfill_object <- NULL
if (trimfill_requested) {
  if (model_type == "multilevel" || !is.null(moderators_formula)) {
    abort("--trimfill is restricted to intercept-only rma.uni models.")
  }
  if (independent_cluster_count < 10L) {
    abort("Trim-and-fill requires at least 10 independent clusters in this conservative workflow.")
  }
  trimfill_object <- tryCatch(capture_warnings(metafor::trimfill(model)),
                             error = function(e) abort(sprintf("Trim-and-fill failed: %s", conditionMessage(e))))
  trimfill_text <- c(
    "Trim-and-fill is an exploratory sensitivity model, not a corrected truth; it can be unreliable under heterogeneity.",
    capture.output(print(trimfill_object))
  )
}

if (independent_cluster_count < 5L && model_type != "common") {
  captured_warnings <- c(captured_warnings, "Fewer than five independent clusters: heterogeneity and prediction intervals are especially unstable.")
}
if (!is.null(moderators_formula) && independent_cluster_count < 10L * ncol(moderator_matrix)) {
  captured_warnings <- c(
    captured_warnings,
    sprintf(
      paste0(
        "Meta-regression has %d independent clusters for %d coefficients (%.2f clusters per coefficient); ",
        "treat moderator results as highly exploratory."
      ),
      independent_cluster_count, ncol(moderator_matrix),
      independent_cluster_count / ncol(moderator_matrix)
    )
  )
}
if (!is.null(robust_cluster)) {
  captured_warnings <- c(captured_warnings,
                         sprintf("Robust inference used %d clusters from '%s' and method %s.",
                                 robust_cluster_count, robust_cluster, robust_method))
}

robust_df_values <- if (is.null(robust_cluster)) numeric() else
  coefficients$df[is.finite(coefficients$df)]
robust_coefficient_df <- if (!length(robust_df_values)) {
  "unavailable"
} else {
  available <- is.finite(coefficients$df)
  paste0(coefficients$term[available], ":", format(coefficients$df[available], digits = 17), collapse = ",")
}
robust_min_coefficient_df <- if (!length(robust_df_values)) "unavailable" else
  format(min(robust_df_values), digits = 17)

all_script_owned_files <- c(
  "analysis_manifest.txt", "data_used.csv", "coefficients.csv", "heterogeneity.csv",
  "model.rds", "session_info.txt", "excluded_rows.csv", "predictions.csv",
  "sensitivity_models.csv", "leave_one_cluster_out.csv", "leave_one_out.csv", "influence.txt",
  "small_study_test.txt", "trimfill.txt", "trimfill_model.rds"
)
script_owned_paths <- file.path(output_dir, all_script_owned_files)
if (dir.exists(output_dir) && !overwrite && any(file.exists(script_owned_paths))) {
  abort(sprintf("Known output file(s) already exist. Use --overwrite yes: %s",
                paste(script_owned_paths[file.exists(script_owned_paths)], collapse = ", ")))
}
if (!dir.exists(output_dir)) {
  if (!dir.create(output_dir, recursive = FALSE, showWarnings = FALSE)) abort(sprintf("Could not create output directory: %s", output_dir))
}
if (overwrite) {
  stale_paths <- script_owned_paths[file.exists(script_owned_paths)]
  if (length(stale_paths)) {
    removed <- file.remove(stale_paths)
    if (any(!removed)) abort(sprintf("Could not replace script-owned output(s): %s", paste(stale_paths[!removed], collapse = ", ")))
  }
}

write_csv <- function(x, filename) {
  path <- file.path(output_dir, filename)
  tryCatch(write.csv(x, path, row.names = FALSE, na = "", fileEncoding = "UTF-8"),
           error = function(e) abort(sprintf("Could not write '%s': %s", path, conditionMessage(e))))
}
write_text <- function(x, filename) {
  path <- file.path(output_dir, filename)
  tryCatch(writeLines(x, path, useBytes = TRUE),
           error = function(e) abort(sprintf("Could not write '%s': %s", path, conditionMessage(e))))
}

write_csv(dat, "data_used.csv")
write_csv(coefficients, "coefficients.csv")
write_csv(heterogeneity, "heterogeneity.csv")
if (!is.null(excluded_rows)) write_csv(excluded_rows, "excluded_rows.csv")
if (!is.null(predictions)) write_csv(predictions, "predictions.csv")
if (!is.null(sensitivity_models)) write_csv(sensitivity_models, "sensitivity_models.csv")
if (!is.null(leave_one_cluster_out)) write_csv(leave_one_cluster_out, "leave_one_cluster_out.csv")
if (!is.null(influence_text)) write_text(influence_text, "influence.txt")
if (!is.null(small_study_text)) write_text(small_study_text, "small_study_test.txt")
if (!is.null(trimfill_text)) write_text(trimfill_text, "trimfill.txt")

model_bundle <- list(
  base_model = model,
  inference_model = inference_model,
  configuration = opt,
  analysis_scale = analysis_scale,
  independent_cluster_col = independent_cluster_col,
  independent_cluster_count = independent_cluster_count,
  captured_warnings = unique(captured_warnings)
)
tryCatch(saveRDS(model_bundle, file.path(output_dir, "model.rds")),
         error = function(e) abort(sprintf("Could not save model.rds: %s", conditionMessage(e))))
if (!is.null(trimfill_object)) {
  tryCatch(saveRDS(trimfill_object, file.path(output_dir, "trimfill_model.rds")),
           error = function(e) abort(sprintf("Could not save trimfill_model.rds: %s", conditionMessage(e))))
}
write_text(capture.output(sessionInfo()), "session_info.txt")

manifest <- c(
  "meta_analysis_manifest",
  sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
  sprintf("input=%s", input_path),
  sprintf("output_dir=%s", output_dir),
  sprintf("model_type=%s", model_type),
  sprintf("rows_input=%d", nrow(original_dat)),
  sprintf("rows_used=%d", nrow(dat)),
  sprintf("independent_cluster_col=%s", independent_cluster_col),
  sprintf("independent_clusters_used=%d", independent_cluster_count),
  sprintf("dependence_topology=%s", if (is.null(dependence_topology)) "not_declared" else dependence_topology),
  sprintf("analysis_scale=%s", analysis_scale),
  sprintf("display_transform=%s", display_transform),
  sprintf("confidence_level=%s", level),
  sprintf("model_formula=%s", if (is.null(moderators_formula)) "~ 1" else paste(deparse(moderators_formula), collapse = " ")),
  sprintf("random_formula=%s", if (is.null(random_formula)) "none" else paste(deparse(random_formula), collapse = " ")),
  sprintf("v_matrix=%s", if (is.null(v_matrix_path)) "diagonal_vi" else v_matrix_path),
  sprintf("prediction_requested=%s", if (prediction_requested) "yes" else "no"),
  sprintf("prediction_target=%s", prediction_target_record),
  sprintf("prediction_components=%s", prediction_components_record),
  sprintf("inference=%s", if (is.null(robust_method)) "model_based" else robust_method),
  sprintf("robust_cluster=%s", if (is.null(robust_cluster)) "not_applicable" else robust_cluster),
  sprintf("robust_cluster_count=%s", if (is.null(robust_cluster)) "not_applicable" else robust_cluster_count),
  sprintf("robust_method=%s", if (is.null(robust_method)) "not_applicable" else robust_method),
  sprintf("robust_coefficient_df=%s", if (is.null(robust_cluster)) "not_applicable" else robust_coefficient_df),
  sprintf("robust_min_coefficient_df=%s", if (is.null(robust_cluster)) "not_applicable" else robust_min_coefficient_df),
  "heterogeneity_inference_basis=model_based",
  sprintf("metafor_version=%s", as.character(utils::packageVersion("metafor"))),
  sprintf("clubSandwich_version=%s", if (requireNamespace("clubSandwich", quietly = TRUE)) as.character(utils::packageVersion("clubSandwich")) else "not_installed"),
  sprintf("R_version=%s", R.version.string),
  "command_options:",
  paste0("  --", names(opt), "=", unlist(opt, use.names = FALSE)),
  "captured_warnings:",
  if (length(captured_warnings)) paste0("  - ", unique(captured_warnings)) else "  - none",
  "interpretation_warning=Every heterogeneity.csv row is model_based; cluster-robust methods apply to coefficient inference and do not turn QM/QM_p or heterogeneity statistics into CR0/CR1/CR2 tests.",
  "interpretation_warning=Display columns follow display_transform; non-intercept meta-regression coefficients may intentionally remain only on the analysis scale, and SE always remains on the analysis scale.",
  "interpretation_warning=Prediction intervals and small-study analyses require design- and context-specific interpretation."
)
write_text(manifest, "analysis_manifest.txt")

cat(sprintf(
  "Model completed with %d included effect-size rows from %d independent clusters.\n",
  nrow(dat), independent_cluster_count
))
cat(sprintf("Outputs: %s\n", output_dir))
if (length(captured_warnings)) {
  cat("Captured warnings were recorded in analysis_manifest.txt:\n")
  cat(paste0("- ", unique(captured_warnings), collapse = "\n"), "\n")
}
