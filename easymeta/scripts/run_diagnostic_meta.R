#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1, encoding = "UTF-8")

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Single-threshold bivariate diagnostic meta-analysis using metafor::rma.mv\n\n",
  "Usage:\n",
  "  Rscript run_diagnostic_meta.R --input FILE --output-dir DIR\n",
  "    --zero-strategy reject|continuity [--continuity-correction VALUE]\n",
  "    [--level PERCENT] [--overwrite yes|no]\n\n",
  "Input columns (fixed contract):\n",
  "  study_id, threshold_id, tp, fp, fn, tn\n\n",
  "Rules:\n",
  "  One 2x2 table per study is required; repeated/multiple thresholds are rejected.\n",
  "  reject: fail if any cell is zero.\n",
  "  continuity: require --continuity-correction in (0,1]; add it to all four\n",
  "              cells only in a study whose table contains at least one zero.\n",
  "  The fitted model is a bivariate logit random-effects model with an UN\n",
  "  study-level covariance. Outputs are limited to summary sensitivity and\n",
  "  specificity; no SROC, AUC, likelihood ratios, DOR, or multi-threshold model.\n"
)

allowed_options <- c(
  "input", "output-dir", "zero-strategy", "continuity-correction", "level", "overwrite"
)

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
  if ((lower_open && number <= lower) || (!lower_open && number < lower) || number > upper) {
    abort(sprintf("%s is outside the allowed range.", label))
  }
  number
}

input_path <- normalizePath(require_opt("input"), winslash = "/", mustWork = FALSE)
output_dir <- normalizePath(require_opt("output-dir"), winslash = "/", mustWork = FALSE)
zero_strategy <- parse_choice(require_opt("zero-strategy"), c("reject", "continuity"), "--zero-strategy")
level <- parse_number(get_opt("level", "95"), "--level", 0, 100, lower_open = TRUE)
if (level >= 100) abort("--level must be less than 100.")
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", FALSE)

if (zero_strategy == "continuity") {
  correction <- parse_number(require_opt("continuity-correction"), "--continuity-correction", 0, 1, lower_open = TRUE)
} else {
  if (!is.null(get_opt("continuity-correction"))) abort("--continuity-correction is only valid with --zero-strategy continuity.")
  correction <- NA_real_
}

if (!file.exists(input_path) || dir.exists(input_path)) abort(sprintf("Input CSV does not exist or is not a file: %s", input_path))
if (!requireNamespace("metafor", quietly = TRUE)) abort("Package 'metafor' is required; the script never installs packages.")
if (utils::packageVersion("metafor") < "5.0.1") abort("metafor >= 5.0.1 is required.")

owned_files <- c(
  "analysis_manifest.txt", "data_used.csv", "long_effects.csv", "summary_measures.csv",
  "random_effects.csv", "model.rds", "session_info.txt"
)

preflight_output <- function(path, replace, owned) {
  parent <- dirname(path)
  if (!dir.exists(parent)) abort(sprintf("Parent directory for --output-dir does not exist: %s", parent))
  if (file.exists(path) && !dir.exists(path)) abort("--output-dir points to a file, not a directory.")
  if (dir.exists(path)) {
    entries <- list.files(path, all.files = TRUE, no.. = TRUE, recursive = FALSE)
    if (!replace) abort("--output-dir already exists; no files were written. Use --overwrite yes only for a script-owned output directory.")
    unknown <- setdiff(entries, owned)
    entry_info <- if (length(entries)) file.info(file.path(path, entries)) else NULL
    if (length(unknown) || (length(entries) && any(entry_info$isdir))) {
      abort(sprintf(
        "Refusing to replace --output-dir because it contains unknown files or subdirectories: %s",
        paste(if (length(unknown)) unknown else entries[entry_info$isdir], collapse = ", ")
      ))
    }
  }
}

preflight_output(output_dir, overwrite, owned_files)
output_prefix <- paste0(output_dir, "/")
if (startsWith(paste0(input_path, if (dir.exists(input_path)) "/" else ""), output_prefix)) {
  abort("Input must not be located inside --output-dir because overwrite is transactional.")
}

read_csv_utf8 <- function(path) {
  dat <- tryCatch(
    utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, fileEncoding = "UTF-8"),
    error = function(e) abort(sprintf("Could not read UTF-8 CSV '%s': %s", path, conditionMessage(e)))
  )
  if (anyDuplicated(names(dat))) abort("Input CSV has duplicate column names.")
  dat
}

require_columns <- function(dat, required) {
  missing <- setdiff(required, names(dat))
  if (length(missing)) abort(sprintf("Input CSV is missing required column(s): %s.", paste(missing, collapse = ", ")))
}

parse_count <- function(x, label) {
  text <- trimws(as.character(x))
  number <- suppressWarnings(as.numeric(text))
  if (any(!nzchar(text)) || any(!is.finite(number))) abort(sprintf("Column '%s' must contain finite non-missing counts.", label))
  if (any(number < 0) || any(abs(number - round(number)) > sqrt(.Machine$double.eps))) {
    abort(sprintf("Column '%s' must contain non-negative integer counts.", label))
  }
  number
}

dat <- read_csv_utf8(input_path)
require_columns(dat, c("study_id", "threshold_id", "tp", "fp", "fn", "tn"))
if (!nrow(dat)) abort("Input CSV has no data rows.")
for (name in c("study_id", "threshold_id")) {
  dat[[name]] <- trimws(as.character(dat[[name]]))
  if (any(!nzchar(dat[[name]])) || any(is.na(dat[[name]]))) abort(sprintf("Column '%s' must be non-empty for every row.", name))
}
if (anyDuplicated(dat$study_id)) {
  repeated <- unique(dat$study_id[duplicated(dat$study_id)])
  abort(sprintf(
    "Multiple/repeated threshold rows are not supported; one 2x2 table per study is required. Repeated study_id(s): %s.",
    paste(repeated, collapse = ", ")
  ))
}
for (name in c("tp", "fp", "fn", "tn")) dat[[name]] <- parse_count(dat[[name]], name)
if (nrow(dat) < 4L) abort("At least four independent studies are required for the bivariate random-effects model.")
if (any(dat$tp + dat$fn <= 0)) abort("Every study must include at least one diseased participant (tp + fn > 0).")
if (any(dat$tn + dat$fp <= 0)) abort("Every study must include at least one non-diseased participant (tn + fp > 0).")

cell_matrix <- as.matrix(dat[c("tp", "fp", "fn", "tn")])
has_zero <- rowSums(cell_matrix == 0) > 0
if (zero_strategy == "reject" && any(has_zero)) {
  abort(sprintf(
    "Zero cell(s) found for study_id(s) %s under --zero-strategy reject.",
    paste(dat$study_id[has_zero], collapse = ", ")
  ))
}

adjusted <- cell_matrix
if (zero_strategy == "continuity" && any(has_zero)) adjusted[has_zero, ] <- adjusted[has_zero, , drop = FALSE] + correction
colnames(adjusted) <- paste0("adjusted_", c("tp", "fp", "fn", "tn"))
dat_used <- cbind(dat, zero_corrected = has_zero, as.data.frame(adjusted, check.names = FALSE))

tp <- adjusted[, "adjusted_tp"]
fp <- adjusted[, "adjusted_fp"]
fn <- adjusted[, "adjusted_fn"]
tn <- adjusted[, "adjusted_tn"]
sensitivity <- tp / (tp + fn)
specificity <- tn / (tn + fp)
if (any(sensitivity <= 0 | sensitivity >= 1 | specificity <= 0 | specificity >= 1)) {
  abort("Adjusted sensitivity/specificity must lie strictly within (0,1); review counts and zero strategy.")
}

long_dat <- rbind(
  data.frame(
    study_id = dat$study_id, threshold_id = dat$threshold_id, outcome = "sensitivity",
    proportion = sensitivity, yi = stats::qlogis(sensitivity), vi = 1 / tp + 1 / fn,
    stringsAsFactors = FALSE
  ),
  data.frame(
    study_id = dat$study_id, threshold_id = dat$threshold_id, outcome = "specificity",
    proportion = specificity, yi = stats::qlogis(specificity), vi = 1 / tn + 1 / fp,
    stringsAsFactors = FALSE
  )
)
long_dat$outcome <- factor(long_dat$outcome, levels = c("sensitivity", "specificity"))
X <- stats::model.matrix(~ outcome - 1, data = long_dat)
colnames(X) <- c("sensitivity", "specificity")

captured_warnings <- character()
fit <- tryCatch(
  withCallingHandlers(
    metafor::rma.mv(
      yi = long_dat$yi, V = diag(long_dat$vi), mods = X, intercept = FALSE,
      random = ~ outcome | study_id, struct = "UN", data = long_dat,
      method = "REML", test = "t", dfs = "contain", level = level
    ),
    warning = function(w) {
      captured_warnings <<- c(captured_warnings, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  ),
  error = function(e) abort(sprintf("Bivariate metafor::rma.mv model failed: %s", conditionMessage(e)))
)
severe_warning <- grepl("converg|Hessian|not positive definite|singular|cannot be fitted", captured_warnings, ignore.case = TRUE)
if (any(severe_warning)) abort(sprintf("Model emitted a convergence/identifiability warning: %s", paste(unique(captured_warnings[severe_warning]), collapse = " | ")))
if (length(fit$beta) != 2L || any(!is.finite(fit$beta)) || any(!is.finite(fit$vb))) abort("Model returned incomplete or non-finite fixed-effect estimates.")
if (length(fit$tau2) != 2L || any(!is.finite(fit$tau2)) || length(fit$rho) != 1L || !is.finite(fit$rho)) {
  abort("Model did not return two random-effect variances and one correlation; the bivariate model is not identifiable.")
}
variance_boundary_tolerance <- 1e-8
variance_on_boundary <- as.numeric(fit$tau2) <= variance_boundary_tolerance
correlation_weakly_identified <- any(variance_on_boundary)

ddf <- rep_len(as.numeric(fit$ddf), 2L)
summary_measures <- data.frame(
  outcome = c("sensitivity", "specificity"),
  estimate_logit = as.numeric(fit$beta),
  se_logit = as.numeric(fit$se),
  df = ddf,
  statistic = as.numeric(fit$zval),
  p_value = as.numeric(fit$pval),
  ci_level = level,
  ci_lower_logit = as.numeric(fit$ci.lb),
  ci_upper_logit = as.numeric(fit$ci.ub),
  estimate = stats::plogis(as.numeric(fit$beta)),
  ci_lower = stats::plogis(as.numeric(fit$ci.lb)),
  ci_upper = stats::plogis(as.numeric(fit$ci.ub)),
  stringsAsFactors = FALSE
)
random_effects <- data.frame(
  component = c("sensitivity_logit_variance", "specificity_logit_variance", "logit_correlation"),
  estimate = c(as.numeric(fit$tau2), as.numeric(fit$rho)),
  inference_basis = "model_based",
  on_boundary = c(variance_on_boundary, correlation_weakly_identified),
  interpretation_note = c(
    ifelse(variance_on_boundary, "variance_at_or_below_boundary_tolerance", "variance_above_boundary_tolerance"),
    if (correlation_weakly_identified) "correlation_is_weakly_identified_when_either_variance_is_on_boundary" else "correlation_interpretable_subject_to_model_assumptions"
  ),
  stringsAsFactors = FALSE
)
long_out <- long_dat
long_out$outcome <- as.character(long_out$outcome)

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- if (length(script_arg)) normalizePath(sub("^--file=", "", script_arg[[1L]]), winslash = "/", mustWork = FALSE) else "unknown"
input_md5 <- unname(tools::md5sum(input_path))

write_csv_utf8 <- function(x, path) {
  utils::write.csv(x, path, row.names = FALSE, na = "", fileEncoding = "UTF-8")
}
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
  } else if (!file.rename(staging, path)) {
    abort("Could not atomically commit the staged output directory.")
  }
}

write_transaction(output_dir, overwrite, owned_files, function(stage) {
  write_csv_utf8(dat_used, file.path(stage, "data_used.csv"))
  write_csv_utf8(long_out, file.path(stage, "long_effects.csv"))
  write_csv_utf8(summary_measures, file.path(stage, "summary_measures.csv"))
  write_csv_utf8(random_effects, file.path(stage, "random_effects.csv"))
  saveRDS(list(model = fit, configuration = opt, zero_corrected_studies = dat$study_id[has_zero]), file.path(stage, "model.rds"))
  write_text_utf8(capture.output(sessionInfo()), file.path(stage, "session_info.txt"))
  hashed_outputs <- setdiff(owned_files, "analysis_manifest.txt")
  output_hashes <- unname(tools::md5sum(file.path(stage, hashed_outputs)))
  manifest <- c(
    "diagnostic_meta_manifest",
    sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
    sprintf("input=%s", input_path),
    sprintf("input_md5=%s", input_md5),
    sprintf("script=%s", script_path),
    sprintf("script_md5=%s", if (file.exists(script_path)) unname(tools::md5sum(script_path)) else "unknown"),
    sprintf("rows=%d", nrow(dat)),
    sprintf("independent_studies=%d", nrow(dat)),
    sprintf("zero_strategy=%s", zero_strategy),
    sprintf("continuity_correction=%s", if (is.na(correction)) "none" else format(correction, digits = 17)),
    sprintf("zero_corrected_studies=%d", sum(has_zero)),
    "model=bivariate_logit_rma.mv",
    "random_structure=UN_outcome_within_study",
    "method=REML",
    "test=t",
    "dfs=contain",
    sprintf("confidence_level=%s", level),
    sprintf("variance_boundary_tolerance=%s", format(variance_boundary_tolerance, scientific = TRUE)),
    sprintf("random_effect_boundary_detected=%s", if (any(variance_on_boundary)) "yes" else "no"),
    sprintf("random_effect_correlation_weakly_identified=%s", if (correlation_weakly_identified) "yes" else "no"),
    sprintf("metafor_version=%s", as.character(utils::packageVersion("metafor"))),
    sprintf("R_version=%s", R.version.string),
    "output_limit=no_SROC_no_AUC_no_likelihood_ratios_no_DOR_no_multi_threshold_inference",
    paste0("output_md5[", hashed_outputs, "]=", output_hashes),
    "command_options:",
    paste0("  --", names(opt), "=", unlist(opt, use.names = FALSE)),
    "captured_warnings:",
    if (length(captured_warnings)) paste0("  - ", unique(captured_warnings)) else "  - none",
    "interpretation_warning=Summary sensitivity and specificity are conditional on one 2x2 table per study and the declared zero-cell strategy.",
    "interpretation_warning=Different study thresholds can induce threshold heterogeneity that this single-threshold-per-study model does not resolve.",
    if (correlation_weakly_identified) "interpretation_warning=At least one random-effect variance is on the numerical boundary; do not interpret the estimated random-effect correlation substantively." else NULL
  )
  write_text_utf8(manifest, file.path(stage, "analysis_manifest.txt"))
})

cat(sprintf("Diagnostic model completed for %d studies. Outputs: %s\n", nrow(dat), output_dir))
