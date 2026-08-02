#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1, encoding = "UTF-8")

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Connected contrast-based common-effect network consistency model using metafor::rma.mv\n\n",
  "Usage:\n",
  "  Rscript run_network_meta.R --input FILE --output-dir DIR\n",
  "    --reference-treatment LABEL [--v-matrix FILE]\n",
  "    [--level PERCENT] [--overwrite yes|no]\n\n",
  "Fixed input contract:\n",
  "  effect_id, study, treatment_a, treatment_b, yi, vi\n",
  "  yi is the effect of treatment_b versus treatment_a on one analysis scale.\n\n",
  "Rules:\n",
  "  The treatment graph must be connected. Each two-arm study contributes one row.\n",
  "  A multi-arm study contributes an independent connected set of m-1 contrasts and\n",
  "  requires a complete effect-by-effect V CSV (first column effect_id).\n",
  "  The model estimates common-effect consistency basic parameters and every pairwise\n",
  "  contrast. It does not rank treatments and does not establish consistency.\n"
)

allowed_options <- c("input", "output-dir", "reference-treatment", "v-matrix", "level", "overwrite")

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
output_dir <- normalizePath(require_opt("output-dir"), winslash = "/", mustWork = FALSE)
reference_treatment <- trimws(require_opt("reference-treatment"))
if (!nzchar(reference_treatment)) abort("--reference-treatment must be non-empty.")
v_path <- if (is.null(get_opt("v-matrix"))) NULL else normalizePath(get_opt("v-matrix"), winslash = "/", mustWork = FALSE)
level <- parse_number(get_opt("level", "95"), "--level", 0, 100, lower_open = TRUE)
if (level >= 100) abort("--level must be less than 100.")
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", FALSE)

if (!file.exists(input_path) || dir.exists(input_path)) abort(sprintf("Input CSV does not exist: %s", input_path))
if (!is.null(v_path) && (!file.exists(v_path) || dir.exists(v_path))) abort(sprintf("V-matrix CSV does not exist: %s", v_path))
if (!is.null(v_path) && identical(input_path, v_path)) abort("--input and --v-matrix must be different files.")
if (!requireNamespace("metafor", quietly = TRUE)) abort("Package 'metafor' is required; the script never installs packages.")
if (utils::packageVersion("metafor") < "5.0.1") abort("metafor >= 5.0.1 is required.")

owned_files <- c(
  "analysis_manifest.txt", "data_used.csv", "basic_parameters.csv", "all_comparisons.csv",
  "model_fit.csv", "model.rds", "session_info.txt"
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
for (path in Filter(Negate(is.null), list(input_path, v_path))) {
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
required <- c("effect_id", "study", "treatment_a", "treatment_b", "yi", "vi")
missing <- setdiff(required, names(dat))
if (length(missing)) abort(sprintf("Input CSV is missing required column(s): %s.", paste(missing, collapse = ", ")))
if (!nrow(dat)) abort("Input CSV has no data rows.")
for (name in c("effect_id", "study", "treatment_a", "treatment_b")) {
  dat[[name]] <- trimws(as.character(dat[[name]]))
  if (any(is.na(dat[[name]])) || any(!nzchar(dat[[name]]))) abort(sprintf("Column '%s' must be non-empty for every row.", name))
}
if (anyDuplicated(dat$effect_id)) abort(sprintf("effect_id must be unique; duplicate(s): %s.", paste(unique(dat$effect_id[duplicated(dat$effect_id)]), collapse = ", ")))
if (any(dat$treatment_a == dat$treatment_b)) abort("treatment_a and treatment_b must differ in every row.")
dat$yi <- parse_finite(dat$yi, "yi")
dat$vi <- parse_finite(dat$vi, "vi")
if (any(dat$vi <= 0)) abort("Column 'vi' must contain strictly positive sampling variances.")

treatments <- unique(c(dat$treatment_a, dat$treatment_b))
if (!(reference_treatment %in% treatments)) abort("--reference-treatment is not present in the treatment network.")
if (length(treatments) < 2L) abort("At least two treatments are required.")

is_connected_edges <- function(vertices, a, b, start) {
  reached <- start
  repeat {
    adjacent <- unique(c(b[a %in% reached], a[b %in% reached]))
    next_reached <- unique(c(reached, adjacent))
    if (length(next_reached) == length(reached)) break
    reached <- next_reached
  }
  setequal(reached, vertices)
}
if (!is_connected_edges(treatments, dat$treatment_a, dat$treatment_b, reference_treatment)) {
  abort("Treatment network is disconnected; a single consistency model is not defined.")
}

study_order <- unique(dat$study)
multiarm_studies <- character()
for (s in study_order) {
  idx <- which(dat$study == s)
  arms <- unique(c(dat$treatment_a[idx], dat$treatment_b[idx]))
  pair_key <- vapply(idx, function(i) paste(sort(c(dat$treatment_a[[i]], dat$treatment_b[[i]])), collapse = "\r"), character(1))
  if (anyDuplicated(pair_key)) abort(sprintf("Study '%s' contains a repeated treatment contrast.", s))
  if (length(arms) == 2L && length(idx) != 1L) abort(sprintf("Two-arm study '%s' must contribute exactly one contrast row.", s))
  if (length(arms) > 2L) {
    multiarm_studies <- c(multiarm_studies, s)
    if (length(idx) != length(arms) - 1L || !is_connected_edges(arms, dat$treatment_a[idx], dat$treatment_b[idx], arms[[1L]])) {
      abort(sprintf("Multi-arm study '%s' must contribute a connected independent set of m-1 contrasts.", s))
    }
  }
}
if (length(multiarm_studies) && is.null(v_path)) {
  abort(sprintf("A complete --v-matrix is mandatory for multi-arm study/studies: %s.", paste(multiarm_studies, collapse = ", ")))
}

read_v_matrix <- function(path, ids, expected_vi, studies) {
  raw <- read_csv_utf8(path, "V-matrix")
  if (ncol(raw) != nrow(raw) + 1L) abort("V-matrix CSV must contain one ID column plus a square numeric matrix.")
  if (!identical(names(raw)[[1L]], "effect_id")) abort("The first V-matrix column must be named 'effect_id'.")
  row_ids <- trimws(as.character(raw[[1L]]))
  col_ids <- names(raw)[-1L]
  if (any(!nzchar(row_ids)) || any(!nzchar(col_ids)) || anyDuplicated(row_ids) || anyDuplicated(col_ids)) abort("V-matrix row and column IDs must be non-empty and unique.")
  if (!setequal(row_ids, col_ids)) abort("V-matrix row and column ID sets differ.")
  if (!setequal(ids, row_ids)) abort("V-matrix IDs must exactly match all input effect_id values; positional matching is forbidden.")
  text <- as.matrix(raw[-1L])
  values <- suppressWarnings(as.numeric(text))
  if (length(values) != length(text) || any(!is.finite(values))) abort("V-matrix entries must all be finite numeric values.")
  V0 <- matrix(values, nrow = nrow(raw), ncol = nrow(raw), dimnames = list(row_ids, col_ids))
  V <- V0[ids, ids, drop = FALSE]
  scale <- max(1, max(abs(V)))
  tol <- sqrt(.Machine$double.eps) * scale
  if (max(abs(V - t(V))) > tol) abort("V-matrix must be symmetric within numerical tolerance.")
  diag_tol <- sqrt(.Machine$double.eps) * pmax(1, abs(expected_vi))
  if (any(abs(diag(V) - expected_vi) > diag_tol)) abort("V-matrix diagonal must reproduce input vi in effect_id order.")
  eig <- eigen((V + t(V)) / 2, symmetric = TRUE, only.values = TRUE)$values
  if (min(eig) <= tol) abort(sprintf("V-matrix must be positive definite; minimum eigenvalue %.6g is not above tolerance %.6g.", min(eig), tol))
  cross_study <- outer(studies, studies, FUN = "!=")
  if (any(abs(V[cross_study]) > tol)) abort("Sampling covariance between independent studies must be zero.")
  list(V = V, minimum_eigenvalue = min(eig))
}

if (is.null(v_path)) {
  V <- diag(dat$vi)
  dimnames(V) <- list(dat$effect_id, dat$effect_id)
  v_minimum_eigenvalue <- min(dat$vi)
  covariance_source <- "diagonal_vi"
} else {
  v_info <- read_v_matrix(v_path, dat$effect_id, dat$vi, dat$study)
  V <- v_info$V
  v_minimum_eigenvalue <- v_info$minimum_eigenvalue
  covariance_source <- v_path
}

ordered_treatments <- c(reference_treatment, sort(setdiff(treatments, reference_treatment)))
nonreference <- ordered_treatments[-1L]
X <- matrix(0, nrow = nrow(dat), ncol = length(nonreference))
colnames(X) <- paste0("d", seq_along(nonreference))
for (i in seq_len(nrow(dat))) {
  if (dat$treatment_b[[i]] != reference_treatment) X[i, match(dat$treatment_b[[i]], nonreference)] <- X[i, match(dat$treatment_b[[i]], nonreference)] + 1
  if (dat$treatment_a[[i]] != reference_treatment) X[i, match(dat$treatment_a[[i]], nonreference)] <- X[i, match(dat$treatment_a[[i]], nonreference)] - 1
}
if (qr(X)$rank != ncol(X)) abort("Network consistency design matrix is rank deficient despite graph checks.")
if (nrow(X) <= ncol(X)) abort("The network has no residual degrees of freedom; add independent studies before fitting.")

captured_warnings <- character()
fit <- tryCatch(
  withCallingHandlers(
    metafor::rma.mv(
      yi = dat$yi, V = V, mods = X, intercept = FALSE,
      random = ~ 1 | effect_id, sigma2 = 0, data = dat,
      method = "REML", test = "z", level = level
    ),
    warning = function(w) {
      captured_warnings <<- c(captured_warnings, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  ),
  error = function(e) abort(sprintf("Network consistency model failed: %s", conditionMessage(e)))
)
severe_warning <- grepl("converg|Hessian|not positive definite|singular|cannot be fitted|redundant", captured_warnings, ignore.case = TRUE)
if (any(severe_warning)) abort(sprintf("Network model emitted a convergence/identifiability warning: %s", paste(unique(captured_warnings[severe_warning]), collapse = " | ")))
if (length(fit$beta) != length(nonreference) || any(!is.finite(fit$beta)) || any(!is.finite(fit$vb))) abort("Network model returned incomplete or non-finite basic parameters.")

zcrit <- stats::qnorm(1 - (1 - level / 100) / 2)
contrast_result <- function(cvec) {
  estimate <- as.numeric(crossprod(cvec, as.numeric(fit$beta)))
  variance <- as.numeric(t(cvec) %*% fit$vb %*% cvec)
  if (!is.finite(variance) || variance <= 0) abort("A requested network contrast has non-positive variance.")
  se <- sqrt(variance)
  statistic <- estimate / se
  c(estimate = estimate, se = se, statistic = statistic, p_value = 2 * stats::pnorm(-abs(statistic)),
    ci_lower = estimate - zcrit * se, ci_upper = estimate + zcrit * se)
}
treatment_vector <- function(treatment) {
  out <- rep(0, length(nonreference))
  if (treatment != reference_treatment) out[match(treatment, nonreference)] <- 1
  out
}

basic_parameters <- do.call(rbind, lapply(nonreference, function(treatment) {
  result <- contrast_result(treatment_vector(treatment))
  data.frame(
    reference_treatment = reference_treatment, treatment = treatment,
    direction = "treatment_minus_reference", estimate = result[["estimate"]], se = result[["se"]],
    statistic = result[["statistic"]], p_value = result[["p_value"]], ci_level = level,
    ci_lower = result[["ci_lower"]], ci_upper = result[["ci_upper"]], stringsAsFactors = FALSE
  )
}))

pairs <- utils::combn(ordered_treatments, 2L, simplify = FALSE)
all_comparisons <- do.call(rbind, lapply(pairs, function(pair) {
  a <- pair[[1L]]
  b <- pair[[2L]]
  result <- contrast_result(treatment_vector(b) - treatment_vector(a))
  data.frame(
    treatment_a = a, treatment_b = b, direction = "treatment_b_minus_treatment_a",
    estimate = result[["estimate"]], se = result[["se"]], statistic = result[["statistic"]],
    p_value = result[["p_value"]], ci_level = level, ci_lower = result[["ci_lower"]],
    ci_upper = result[["ci_upper"]], stringsAsFactors = FALSE
  )
}))
rownames(all_comparisons) <- NULL
model_fit <- data.frame(
  statistic = "QE_global_residual_misfit", value = as.numeric(fit$QE),
  df = as.numeric(fit$k - fit$p), p_value = as.numeric(fit$QEp),
  interpretation = "Not a design-by-treatment or node-splitting inconsistency test",
  stringsAsFactors = FALSE
)

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- if (length(script_arg)) normalizePath(sub("^--file=", "", script_arg[[1L]]), winslash = "/", mustWork = FALSE) else "unknown"
input_md5 <- unname(tools::md5sum(input_path))
v_md5 <- if (is.null(v_path)) "not_applicable" else unname(tools::md5sum(v_path))

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
  write_csv_utf8(basic_parameters, file.path(stage, "basic_parameters.csv"))
  write_csv_utf8(all_comparisons, file.path(stage, "all_comparisons.csv"))
  write_csv_utf8(model_fit, file.path(stage, "model_fit.csv"))
  saveRDS(list(model = fit, treatment_order = ordered_treatments, design_matrix = X, sampling_V = V, configuration = opt), file.path(stage, "model.rds"))
  write_text_utf8(capture.output(sessionInfo()), file.path(stage, "session_info.txt"))
  hashed_outputs <- setdiff(owned_files, "analysis_manifest.txt")
  output_hashes <- unname(tools::md5sum(file.path(stage, hashed_outputs)))
  manifest <- c(
    "network_meta_manifest",
    sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
    sprintf("input=%s", input_path), sprintf("input_md5=%s", input_md5),
    sprintf("v_matrix=%s", if (is.null(v_path)) "none" else v_path), sprintf("v_matrix_md5=%s", v_md5),
    sprintf("script=%s", script_path), sprintf("script_md5=%s", if (file.exists(script_path)) unname(tools::md5sum(script_path)) else "unknown"),
    sprintf("effect_rows=%d", nrow(dat)), sprintf("independent_studies=%d", length(study_order)),
    sprintf("treatments=%d", length(ordered_treatments)), sprintf("reference_treatment=%s", reference_treatment),
    sprintf("multiarm_studies=%s", if (length(multiarm_studies)) paste(multiarm_studies, collapse = ",") else "none"),
    sprintf("sampling_covariance_source=%s", covariance_source), sprintf("v_minimum_eigenvalue=%.17g", v_minimum_eigenvalue),
    "model=contrast_based_common_effect_consistency_GLS_rma.mv", "heterogeneity_variance=fixed_zero", "test=z",
    sprintf("confidence_level=%s", level), sprintf("metafor_version=%s", as.character(utils::packageVersion("metafor"))), sprintf("R_version=%s", R.version.string),
    "output_limit=basic_parameters_and_all_pairwise_contrasts_only_no_ranking_no_SUCRA_no_Pscores",
    "inconsistency_status=not_evaluated_and_not_resolved",
    paste0("output_md5[", hashed_outputs, "]=", output_hashes),
    "command_options:", paste0("  --", names(opt), "=", unlist(opt, use.names = FALSE)),
    "captured_warnings:", if (length(captured_warnings)) paste0("  - ", unique(captured_warnings)) else "  - none",
    "interpretation_warning=All estimates assume consistency and a common true treatment effect for each network contrast.",
    "interpretation_warning=QE is global residual lack-of-fit and must not be reported as proof that direct and indirect evidence are consistent."
  )
  write_text_utf8(manifest, file.path(stage, "analysis_manifest.txt"))
})

cat(sprintf("Network consistency model completed for %d treatments and %d studies. Outputs: %s\n", length(ordered_treatments), length(study_order), output_dir))
