#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1, encoding = "UTF-8")

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Two-stage linear dose-response meta-analysis using GLS and metafor\n\n",
  "Usage:\n",
  "  Rscript run_dose_response.R --input FILE --v-matrix FILE --output-dir DIR\n",
  "    [--level PERCENT] [--overwrite yes|no]\n\n",
  "Fixed input contract:\n",
  "  effect_id, study, dose_difference, yi\n",
  "  --v-matrix is a complete effect-by-effect sampling covariance CSV whose\n",
  "  first column is effect_id and whose remaining headers are effect IDs.\n\n",
  "Rules:\n",
  "  yi is the non-reference versus reference effect on one declared analysis scale.\n",
  "  Each study must contain at least two distinct non-zero dose differences.\n",
  "  Stage 1 fits yi = slope * dose_difference through the origin by GLS.\n",
  "  Stage 2 pools study slopes with REML and Knapp-Hartung inference.\n",
  "  Cross-study covariance, nonlinear curves, intercepts, and reconstructed V are rejected.\n"
)

allowed_options <- c("input", "v-matrix", "output-dir", "level", "overwrite")

parse_cli <- function(x) {
  if (!length(x) || "--help" %in% x) {
    cat(help_text)
    quit(save = "no", status = 0L, runLast = FALSE)
  }
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

opt <- parse_cli(commandArgs(trailingOnly = TRUE))
get_opt <- function(name, default = NULL) if (is.null(opt[[name]])) default else opt[[name]]
require_opt <- function(name) {
  value <- get_opt(name)
  if (is.null(value) || !nzchar(value)) abort(sprintf("Missing required option '--%s'.", name))
  value
}
parse_choice <- function(value, choices, label) {
  value <- tolower(value)
  if (!(value %in% choices)) abort(sprintf("%s must be one of: %s.", label, paste(choices, collapse = ", ")))
  value
}
parse_yes_no <- function(value, label, default = FALSE) {
  if (is.null(value)) return(default)
  parse_choice(value, c("yes", "no"), label) == "yes"
}
parse_number <- function(value, label, lower = -Inf, upper = Inf, lower_open = FALSE) {
  number <- suppressWarnings(as.numeric(value))
  if (length(number) != 1L || is.na(number) || !is.finite(number)) abort(sprintf("%s must be one finite number.", label))
  if ((lower_open && number <= lower) || (!lower_open && number < lower) || number > upper) abort(sprintf("%s is outside the allowed range.", label))
  number
}

input_path <- normalizePath(require_opt("input"), winslash = "/", mustWork = FALSE)
v_path <- normalizePath(require_opt("v-matrix"), winslash = "/", mustWork = FALSE)
output_dir <- normalizePath(require_opt("output-dir"), winslash = "/", mustWork = FALSE)
level <- parse_number(get_opt("level", "95"), "--level", 0, 100, lower_open = TRUE)
if (level >= 100) abort("--level must be less than 100.")
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", FALSE)

for (path in c(input_path, v_path)) {
  if (!file.exists(path) || dir.exists(path)) abort(sprintf("Required input file does not exist: %s", path))
}
if (identical(input_path, v_path)) abort("--input and --v-matrix must be different files.")
if (!requireNamespace("metafor", quietly = TRUE)) abort("Package 'metafor' is required; the script never installs packages.")
if (utils::packageVersion("metafor") < "5.0.1") abort("metafor >= 5.0.1 is required.")

owned_files <- c(
  "analysis_manifest.txt", "data_used.csv", "study_slopes.csv", "pooled_slope.csv",
  "heterogeneity.csv", "model.rds", "session_info.txt"
)

preflight_output <- function(path, replace, owned) {
  parent <- dirname(path)
  if (!dir.exists(parent)) abort(sprintf("Parent directory for --output-dir does not exist: %s", parent))
  if (file.exists(path) && !dir.exists(path)) abort("--output-dir points to a file, not a directory.")
  if (dir.exists(path)) {
    entries <- list.files(path, all.files = TRUE, no.. = TRUE, recursive = FALSE)
    if (!replace) abort("--output-dir already exists; no files were written. Use --overwrite yes only for a script-owned output directory.")
    info <- if (length(entries)) file.info(file.path(path, entries)) else NULL
    unknown <- setdiff(entries, owned)
    if (length(unknown) || (length(entries) && any(info$isdir))) {
      abort(sprintf("Refusing to replace output containing unknown files or subdirectories: %s", paste(if (length(unknown)) unknown else entries[info$isdir], collapse = ", ")))
    }
  }
}
preflight_output(output_dir, overwrite, owned_files)
for (path in c(input_path, v_path)) {
  if (startsWith(path, paste0(output_dir, "/"))) abort("Inputs must not be located inside --output-dir because overwrite is transactional.")
}

read_csv_utf8 <- function(path, label) {
  dat <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, fileEncoding = "UTF-8"),
    error = function(e) abort(sprintf("Could not read UTF-8 %s CSV '%s': %s", label, path, conditionMessage(e)))
  )
  if (anyDuplicated(names(dat))) abort(sprintf("%s CSV has duplicate column names.", label))
  dat
}

parse_finite <- function(x, label) {
  text <- trimws(as.character(x))
  number <- suppressWarnings(as.numeric(text))
  if (any(!nzchar(text)) || any(!is.finite(number))) abort(sprintf("Column '%s' must contain finite non-missing numeric values.", label))
  number
}

dat <- read_csv_utf8(input_path, "input")
required <- c("effect_id", "study", "dose_difference", "yi")
missing <- setdiff(required, names(dat))
if (length(missing)) abort(sprintf("Input CSV is missing required column(s): %s.", paste(missing, collapse = ", ")))
if (!nrow(dat)) abort("Input CSV has no data rows.")
for (name in c("effect_id", "study")) {
  dat[[name]] <- trimws(as.character(dat[[name]]))
  if (any(is.na(dat[[name]])) || any(!nzchar(dat[[name]]))) abort(sprintf("Column '%s' must be non-empty for every row.", name))
}
if (anyDuplicated(dat$effect_id)) abort(sprintf("effect_id must be unique; duplicate(s): %s.", paste(unique(dat$effect_id[duplicated(dat$effect_id)]), collapse = ", ")))
dat$dose_difference <- parse_finite(dat$dose_difference, "dose_difference")
dat$yi <- parse_finite(dat$yi, "yi")
if (any(dat$dose_difference == 0)) abort("Reference-dose rows (dose_difference = 0) are not accepted; supply non-reference contrasts only.")

study_order <- unique(dat$study)
if (length(study_order) < 3L) abort("At least three independent studies are required to pool study-specific slopes.")
for (s in study_order) {
  doses <- unique(dat$dose_difference[dat$study == s])
  if (length(doses) < 2L) abort(sprintf("Study '%s' must contain at least two distinct non-reference dose differences.", s))
}

read_v_matrix <- function(path, ids) {
  raw <- read_csv_utf8(path, "V-matrix")
  if (ncol(raw) != nrow(raw) + 1L) abort("V-matrix CSV must contain one ID column plus a square numeric matrix.")
  if (!identical(names(raw)[[1L]], "effect_id")) abort("The first V-matrix column must be named 'effect_id'.")
  row_ids <- trimws(as.character(raw[[1L]]))
  col_ids <- names(raw)[-1L]
  if (any(!nzchar(row_ids)) || any(!nzchar(col_ids)) || anyDuplicated(row_ids) || anyDuplicated(col_ids)) abort("V-matrix row and column IDs must be non-empty and unique.")
  if (!setequal(row_ids, col_ids)) abort("V-matrix row and column ID sets differ.")
  if (!setequal(ids, row_ids)) abort("V-matrix IDs must exactly match all input effect_id values; positional matching is forbidden.")
  matrix_text <- as.matrix(raw[-1L])
  values <- suppressWarnings(as.numeric(matrix_text))
  if (length(values) != length(matrix_text) || any(!is.finite(values))) abort("V-matrix entries must all be finite numeric values.")
  V0 <- matrix(values, nrow = nrow(raw), ncol = nrow(raw), dimnames = list(row_ids, col_ids))
  V <- V0[ids, ids, drop = FALSE]
  scale <- max(1, max(abs(V)))
  tol <- sqrt(.Machine$double.eps) * scale
  if (max(abs(V - t(V))) > tol) abort("V-matrix must be symmetric within numerical tolerance.")
  if (any(diag(V) <= 0)) abort("V-matrix diagonal variances must be strictly positive.")
  eig <- eigen((V + t(V)) / 2, symmetric = TRUE, only.values = TRUE)$values
  if (min(eig) <= tol) abort(sprintf("V-matrix must be positive definite; minimum eigenvalue %.6g is not above tolerance %.6g.", min(eig), tol))
  list(V = V, tolerance = tol, minimum_eigenvalue = min(eig))
}

v_info <- read_v_matrix(v_path, dat$effect_id)
V <- v_info$V
different_study <- outer(dat$study, dat$study, FUN = "!=")
if (any(abs(V[different_study]) > v_info$tolerance)) abort("Two-stage GLS requires block-diagonal V by study; non-zero cross-study covariance was found.")

study_slopes <- vector("list", length(study_order))
names(study_slopes) <- study_order
for (s in study_order) {
  idx <- which(dat$study == s)
  Vs <- V[idx, idx, drop = FALSE]
  condition_number <- kappa(Vs, exact = TRUE)
  if (!is.finite(condition_number) || condition_number > 1e12) abort(sprintf("Within-study V is numerically ill-conditioned for study '%s' (kappa=%.6g).", s, condition_number))
  W <- tryCatch(solve(Vs), error = function(e) abort(sprintf("Could not invert within-study V for study '%s': %s", s, conditionMessage(e))))
  x <- matrix(dat$dose_difference[idx], ncol = 1L)
  y <- matrix(dat$yi[idx], ncol = 1L)
  information <- as.numeric(t(x) %*% W %*% x)
  if (!is.finite(information) || information <= 0) abort(sprintf("Non-positive GLS information for study '%s'.", s))
  slope <- as.numeric(t(x) %*% W %*% y) / information
  variance <- 1 / information
  study_slopes[[s]] <- data.frame(
    study = s, effects = length(idx), distinct_nonreference_doses = length(unique(dat$dose_difference[idx])),
    slope = slope, slope_variance = variance, slope_se = sqrt(variance),
    v_condition_number = condition_number, stringsAsFactors = FALSE
  )
}
study_slopes <- do.call(rbind, study_slopes)
rownames(study_slopes) <- NULL

captured_warnings <- character()
fit <- tryCatch(
  withCallingHandlers(
    metafor::rma.uni(
      yi = study_slopes$slope, vi = study_slopes$slope_variance,
      method = "REML", test = "knha", level = level
    ),
    warning = function(w) {
      captured_warnings <<- c(captured_warnings, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  ),
  error = function(e) abort(sprintf("Stage-2 slope pooling failed: %s", conditionMessage(e)))
)
severe_warning <- grepl("converg|Hessian|not positive definite|singular|cannot be fitted", captured_warnings, ignore.case = TRUE)
if (any(severe_warning)) abort(sprintf("Stage-2 model emitted a convergence/identifiability warning: %s", paste(unique(captured_warnings[severe_warning]), collapse = " | ")))
if (length(fit$beta) != 1L || any(!is.finite(c(fit$beta, fit$se, fit$ci.lb, fit$ci.ub, fit$tau2)))) abort("Stage-2 model returned incomplete or non-finite estimates.")

prediction <- tryCatch(
  stats::predict(fit, level = level),
  error = function(e) abort(sprintf("Could not calculate the random-effects prediction interval: %s", conditionMessage(e)))
)
pooled_slope <- data.frame(
  estimand = "linear_effect_change_per_one_dose_difference_unit",
  estimate = as.numeric(fit$beta), se = as.numeric(fit$se), df = as.numeric(fit$ddf),
  statistic = as.numeric(fit$zval), p_value = as.numeric(fit$pval), ci_level = level,
  ci_lower = as.numeric(fit$ci.lb), ci_upper = as.numeric(fit$ci.ub),
  prediction_lower = as.numeric(prediction$pi.lb), prediction_upper = as.numeric(prediction$pi.ub),
  stringsAsFactors = FALSE
)
heterogeneity <- data.frame(
  tau2 = as.numeric(fit$tau2), tau = sqrt(as.numeric(fit$tau2)),
  Q = as.numeric(fit$QE), Q_df = as.numeric(fit$k - fit$p), Q_p_value = as.numeric(fit$QEp),
  I2_percent = as.numeric(fit$I2), H2 = as.numeric(fit$H2),
  inference_basis = "model_based", stringsAsFactors = FALSE
)

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- if (length(script_arg)) normalizePath(sub("^--file=", "", script_arg[[1L]]), winslash = "/", mustWork = FALSE) else "unknown"
input_md5 <- unname(tools::md5sum(input_path))
v_md5 <- unname(tools::md5sum(v_path))

write_csv_utf8 <- function(x, path) utils::write.csv(x, path, row.names = FALSE, na = "", fileEncoding = "UTF-8")
write_text_utf8 <- function(x, path) writeLines(enc2utf8(x), path, useBytes = TRUE)
write_transaction <- function(path, replace, owned, writer) {
  parent <- dirname(path)
  token <- paste0(Sys.getpid(), "-", sample.int(1000000000L, 1L))
  staging <- file.path(parent, paste0(".", basename(path), ".tmp-", token))
  backup <- file.path(parent, paste0(".", basename(path), ".bak-", token))
  if (!dir.create(staging, recursive = FALSE, showWarnings = FALSE)) abort(sprintf("Could not create staging directory: %s", staging))
  on.exit(if (dir.exists(staging)) unlink(staging, recursive = TRUE, force = TRUE), add = TRUE)
  tryCatch(writer(staging), error = function(e) abort(sprintf("Could not write staged outputs: %s", conditionMessage(e))))
  staged <- list.files(staging, all.files = TRUE, no.. = TRUE, recursive = FALSE)
  if (!setequal(staged, owned) || any(file.info(file.path(staging, staged))$isdir)) abort("Internal error: staged output set does not match the declared script-owned files.")
  if (dir.exists(path)) {
    if (!replace) abort("Internal error: overwrite preflight changed before commit.")
    if (!file.rename(path, backup)) abort("Could not move the existing output directory aside for atomic replacement.")
    if (!file.rename(staging, path)) {
      file.rename(backup, path)
      abort("Could not commit staged outputs; the prior output directory was restored.")
    }
    if (unlink(backup, recursive = TRUE, force = TRUE) != 0L) warning(sprintf("Committed outputs, but could not remove backup directory: %s", backup), call. = FALSE)
  } else if (!file.rename(staging, path)) abort("Could not atomically commit the staged output directory.")
}

write_transaction(output_dir, overwrite, owned_files, function(stage) {
  write_csv_utf8(dat, file.path(stage, "data_used.csv"))
  write_csv_utf8(study_slopes, file.path(stage, "study_slopes.csv"))
  write_csv_utf8(pooled_slope, file.path(stage, "pooled_slope.csv"))
  write_csv_utf8(heterogeneity, file.path(stage, "heterogeneity.csv"))
  saveRDS(list(stage2_model = fit, study_slopes = study_slopes, sampling_V = V, configuration = opt), file.path(stage, "model.rds"))
  write_text_utf8(capture.output(sessionInfo()), file.path(stage, "session_info.txt"))
  hashed_outputs <- setdiff(owned_files, "analysis_manifest.txt")
  output_hashes <- unname(tools::md5sum(file.path(stage, hashed_outputs)))
  manifest <- c(
    "dose_response_manifest",
    sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
    sprintf("input=%s", input_path), sprintf("input_md5=%s", input_md5),
    sprintf("v_matrix=%s", v_path), sprintf("v_matrix_md5=%s", v_md5),
    sprintf("script=%s", script_path), sprintf("script_md5=%s", if (file.exists(script_path)) unname(tools::md5sum(script_path)) else "unknown"),
    sprintf("effect_rows=%d", nrow(dat)), sprintf("independent_studies=%d", length(study_order)),
    "stage1_model=GLS_through_origin_yi_equals_slope_times_dose_difference",
    "stage2_model=random_effects_pool_of_study_slopes", "tau_method=REML", "test=knha",
    sprintf("confidence_level=%s", level), sprintf("v_minimum_eigenvalue=%.17g", v_info$minimum_eigenvalue),
    sprintf("metafor_version=%s", as.character(utils::packageVersion("metafor"))), sprintf("R_version=%s", R.version.string),
    "output_limit=linear_slope_only_no_nonlinear_curve_no_intercept_no_absolute_effect_extrapolation",
    paste0("output_md5[", hashed_outputs, "]=", output_hashes),
    "command_options:", paste0("  --", names(opt), "=", unlist(opt, use.names = FALSE)),
    "captured_warnings:", if (length(captured_warnings)) paste0("  - ", unique(captured_warnings)) else "  - none",
    "interpretation_warning=The pooled slope is per one unit of the supplied dose_difference and remains on the yi analysis scale.",
    "interpretation_warning=The model assumes linearity through the reference origin within every study; assess nonlinear dose-response with a different specialist workflow."
  )
  write_text_utf8(manifest, file.path(stage, "analysis_manifest.txt"))
})

cat(sprintf("Dose-response model completed for %d studies. Outputs: %s\n", length(study_order), output_dir))
