#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1)

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Conservative sampling covariance builder using metafor::vcalc\n\n",
  "Usage:\n",
  "  Rscript build_sampling_v.R --input FILE --output-v FILE\n",
  "    --vi-col COLUMN --id-col COLUMN --cluster-col COLUMN [design options]\n\n",
  "Required mappings:\n",
  "  --vi-col COLUMN             finite sampling variances > 0\n",
  "  --id-col COLUMN             unique effect IDs used for V row/column names\n",
  "  --cluster-col COLUMN        sampling-dependence cluster\n\n",
  "Explicit design options (nothing is guessed):\n",
  "  --subgroup-col COLUMN       independent subgroup within cluster\n",
  "  --obs-col COLUMN            repeated estimate/scale identifier; requires --rho\n",
  "  --type-col COLUMN           construct/outcome type; requires --rho\n",
  "  --time1-col COLUMN          numeric time for first/only condition; requires --phi\n",
  "  --time2-col COLUMN          numeric time for second condition; requires group fields\n",
  "  --grp1-col COLUMN --grp2-col COLUMN\n",
  "  --w1-col COLUMN --w2-col COLUMN\n",
  "                              all four group/weight mappings are required together\n",
  "  --rho VALUE[,VALUE]         concurrent correlation sensitivity value(s); (-1,1)\n",
  "                              two values required when both obs and type are mapped\n",
  "  --phi VALUE                 non-negative autocorrelation sensitivity value; [0,1)\n\n",
  "Output and audit options:\n",
  "  --manifest FILE             default: OUTPUT-V.manifest.txt\n",
  "  --scenario-label TEXT       optional sensitivity-scenario label recorded in manifest\n",
  "  --overwrite yes|no          default: no\n",
  "  --help\n\n",
  "At least one explicit dependence mechanism (obs/type, time, or shared groups) is required.\n",
  "The script fixes checkpd=TRUE, nearpd=FALSE, sparse=FALSE and never installs packages.\n"
)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0L || "--help" %in% args) {
  cat(help_text)
  quit(save = "no", status = 0L, runLast = FALSE)
}

allowed_options <- c(
  "input", "output-v", "manifest", "vi-col", "id-col", "cluster-col",
  "subgroup-col", "obs-col", "type-col", "time1-col", "time2-col",
  "grp1-col", "grp2-col", "w1-col", "w2-col", "rho", "phi",
  "scenario-label", "overwrite"
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
parse_yes_no <- function(value, label, default = NULL) {
  if (is.null(value)) {
    if (is.null(default)) abort(sprintf("%s must be explicitly set to yes or no.", label))
    return(default)
  }
  value <- tolower(value)
  if (!(value %in% c("yes", "no"))) abort(sprintf("%s must be yes or no.", label))
  value == "yes"
}
parse_numeric_list <- function(value, label, lower, upper, lower_open, upper_open) {
  pieces <- trimws(strsplit(value, ",", fixed = TRUE)[[1L]])
  numbers <- suppressWarnings(as.numeric(pieces))
  if (!length(numbers) || any(!nzchar(pieces)) || any(!is.finite(numbers))) {
    abort(sprintf("%s must contain finite comma-separated numeric value(s).", label))
  }
  lower_bad <- if (lower_open) numbers <= lower else numbers < lower
  upper_bad <- if (upper_open) numbers >= upper else numbers > upper
  if (any(lower_bad | upper_bad)) abort(sprintf("%s contains a value outside its allowed range.", label))
  numbers
}

input_path <- normalizePath(require_opt("input"), winslash = "/", mustWork = FALSE)
output_v_path <- normalizePath(require_opt("output-v"), winslash = "/", mustWork = FALSE)
manifest_path <- if (is.null(get_opt("manifest"))) {
  paste0(output_v_path, ".manifest.txt")
} else {
  normalizePath(get_opt("manifest"), winslash = "/", mustWork = FALSE)
}
vi_col <- require_opt("vi-col")
id_col <- require_opt("id-col")
cluster_col <- require_opt("cluster-col")
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", default = FALSE)

if (!file.exists(input_path)) abort(sprintf("Input file does not exist: %s", input_path))
if (identical(output_v_path, manifest_path)) abort("--output-v and --manifest must be different files.")
for (path in c(output_v_path, manifest_path)) {
  if (!dir.exists(dirname(path))) abort(sprintf("Output parent directory does not exist: %s", dirname(path)))
}
existing_outputs <- c(output_v_path, manifest_path)[file.exists(c(output_v_path, manifest_path))]
if (length(existing_outputs) && !overwrite) {
  abort(sprintf("Output file(s) already exist; use --overwrite yes: %s", paste(existing_outputs, collapse = ", ")))
}

column_options <- c(
  subgroup = "subgroup-col", obs = "obs-col", type = "type-col",
  time1 = "time1-col", time2 = "time2-col", grp1 = "grp1-col", grp2 = "grp2-col",
  w1 = "w1-col", w2 = "w2-col"
)
mapped_columns <- c(vi = vi_col, id = id_col, cluster = cluster_col)
for (arg_name in names(column_options)) {
  column_name <- get_opt(column_options[[arg_name]])
  if (!is.null(column_name)) mapped_columns[[arg_name]] <- column_name
}
if (anyDuplicated(unname(mapped_columns))) {
  duplicated_names <- unique(unname(mapped_columns)[duplicated(unname(mapped_columns))])
  abort(sprintf("Each semantic mapping must use a distinct input column; repeated column(s): %s.",
                paste(duplicated_names, collapse = ", ")))
}

has_obs <- "obs" %in% names(mapped_columns)
has_type <- "type" %in% names(mapped_columns)
has_time1 <- "time1" %in% names(mapped_columns)
has_time2 <- "time2" %in% names(mapped_columns)
group_fields <- c("grp1", "grp2", "w1", "w2") %in% names(mapped_columns)
has_groups <- all(group_fields)
if (any(group_fields) && !has_groups) {
  abort("--grp1-col, --grp2-col, --w1-col, and --w2-col must be supplied together; equal group weights are not assumed.")
}
if (has_time2 && !has_groups) abort("--time2-col is only accepted with all group and weight mappings.")
if (has_groups && has_time1 != has_time2) {
  abort("When group contrasts include time, supply both --time1-col and --time2-col.")
}
if (!(has_obs || has_type || has_time1 || has_groups)) {
  abort("Specify at least one dependence mechanism: obs/type, time1, or shared group/weight fields.")
}

rho <- if (is.null(get_opt("rho"))) NULL else
  parse_numeric_list(get_opt("rho"), "--rho", -1, 1, lower_open = TRUE, upper_open = TRUE)
phi <- if (is.null(get_opt("phi"))) NULL else
  parse_numeric_list(get_opt("phi"), "--phi", 0, 1, lower_open = FALSE, upper_open = TRUE)
if ((has_obs || has_type) && is.null(rho)) abort("--obs-col/--type-col requires an explicit --rho sensitivity value.")
if (!(has_obs || has_type) && !is.null(rho)) abort("--rho is only valid when --obs-col and/or --type-col is supplied.")
expected_rho_length <- if (has_obs && has_type) 2L else 1L
if (!is.null(rho) && length(rho) != expected_rho_length) {
  abort(sprintf("--rho must contain exactly %d value(s) for the selected obs/type design.", expected_rho_length))
}
if (has_time1 && is.null(phi)) abort("--time1-col requires an explicit --phi sensitivity value.")
if (!has_time1 && !is.null(phi)) abort("--phi is only valid when --time1-col is supplied.")
if (!is.null(phi) && length(phi) != 1L) abort("--phi must contain exactly one value.")

dat <- tryCatch(
  read.csv(input_path, check.names = FALSE, fileEncoding = "UTF-8", na.strings = c("", "NA")),
  error = function(e) abort(sprintf("Could not read UTF-8 CSV '%s': %s", input_path, conditionMessage(e)))
)
if (nrow(dat) < 2L) abort("Input must contain at least two effect-size rows.")
if (anyDuplicated(names(dat))) abort("Input column names must be unique.")
missing_columns <- setdiff(unname(mapped_columns), names(dat))
if (length(missing_columns)) abort(sprintf("Mapped input column(s) not found: %s.", paste(missing_columns, collapse = ", ")))
source_rows <- seq_len(nrow(dat))

numeric_column <- function(column_name, label, positive = FALSE) {
  raw <- dat[[column_name]]
  text_value <- trimws(as.character(raw))
  missing <- is.na(raw) | text_value == ""
  value <- suppressWarnings(as.numeric(text_value))
  bad <- missing | is.na(value) | !is.finite(value) | (positive & value <= 0)
  if (any(bad)) {
    rule <- if (positive) "finite and > 0" else "finite numeric"
    abort(sprintf("%s column '%s' must be %s at every row; problem row(s): %s.",
                  label, column_name, rule, paste(source_rows[bad], collapse = ", ")))
  }
  value
}
text_column <- function(column_name, label) {
  raw <- dat[[column_name]]
  value <- trimws(as.character(raw))
  bad <- is.na(raw) | value == ""
  if (any(bad)) {
    abort(sprintf("%s column '%s' has missing/blank value(s) at row(s): %s.",
                  label, column_name, paste(source_rows[bad], collapse = ", ")))
  }
  value
}

dat[[vi_col]] <- numeric_column(vi_col, "--vi-col", positive = TRUE)
ids <- text_column(id_col, "--id-col")
if (anyDuplicated(ids)) abort("--id-col values must be unique.")
dat[[id_col]] <- ids
dat[[cluster_col]] <- text_column(cluster_col, "--cluster-col")
for (name in intersect(c("subgroup", "obs", "type", "grp1", "grp2"), names(mapped_columns))) {
  dat[[mapped_columns[[name]]]] <- text_column(mapped_columns[[name]], paste0("--", column_options[[name]]))
}
for (name in intersect(c("time1", "time2"), names(mapped_columns))) {
  dat[[mapped_columns[[name]]]] <- numeric_column(mapped_columns[[name]], paste0("--", column_options[[name]]))
}
for (name in intersect(c("w1", "w2"), names(mapped_columns))) {
  dat[[mapped_columns[[name]]]] <- numeric_column(mapped_columns[[name]], paste0("--", column_options[[name]]), positive = TRUE)
}

if (!requireNamespace("metafor", quietly = TRUE)) {
  abort(paste0(
    "Required package 'metafor' is not installed in this R library. ",
    "Install it deliberately in the project/library you intend to use. The script installed nothing. ",
    "Current .libPaths(): ", paste(.libPaths(), collapse = "; ")
  ))
}

vcalc_args <- list(
  vi = dat[[vi_col]], cluster = dat[[cluster_col]], data = dat,
  checkpd = TRUE, nearpd = FALSE, sparse = FALSE
)
for (name in intersect(names(column_options), names(mapped_columns))) {
  vcalc_args[[name]] <- dat[[mapped_columns[[name]]]]
}
if (!is.null(rho)) vcalc_args$rho <- rho
if (!is.null(phi)) vcalc_args$phi <- phi

captured_warnings <- character()
V <- tryCatch(
  withCallingHandlers(
    do.call(metafor::vcalc, vcalc_args),
    warning = function(w) {
      captured_warnings <<- c(captured_warnings, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  ),
  error = function(e) abort(sprintf("metafor::vcalc failed: %s", conditionMessage(e)))
)
V <- as.matrix(V)
if (!identical(dim(V), c(nrow(dat), nrow(dat)))) abort("vcalc returned a matrix with unexpected dimensions.")
if (any(!is.finite(V))) abort("vcalc returned missing or non-finite covariance values.")
matrix_scale <- max(abs(V))
tolerance <- sqrt(.Machine$double.eps) * matrix_scale
if (max(abs(V - t(V))) > tolerance) abort("vcalc returned a matrix that is not symmetric within numerical tolerance.")
diagonal_tolerance <- sqrt(.Machine$double.eps) * pmax(abs(dat[[vi_col]]), .Machine$double.xmin)
if (any(abs(diag(V) - dat[[vi_col]]) > diagonal_tolerance)) {
  abort("vcalc output diagonal does not reproduce the supplied sampling variances.")
}
eigenvalues <- eigen((V + t(V)) / 2, symmetric = TRUE, only.values = TRUE)$values
minimum_eigenvalue <- min(eigenvalues)
if (minimum_eigenvalue <= tolerance) {
  abort(sprintf(
    paste0(
      "Constructed V is not positive definite within tolerance (minimum eigenvalue %.6g; tolerance %.6g). ",
      "Review the design and rho/phi assumptions; nearPD repair is intentionally disabled."
    ),
    minimum_eigenvalue, tolerance
  ))
}
rownames(V) <- ids
colnames(V) <- ids

v_output <- data.frame(ids, V, check.names = FALSE, stringsAsFactors = FALSE)
names(v_output)[[1L]] <- id_col
tryCatch(
  write.csv(v_output, output_v_path, row.names = FALSE, na = "", fileEncoding = "UTF-8"),
  error = function(e) abort(sprintf("Could not write V CSV '%s': %s", output_v_path, conditionMessage(e)))
)

format_value <- function(x) if (is.null(x)) "none" else paste(x, collapse = ",")
design_manifest <- vapply(names(column_options), function(name) {
  sprintf("%s_col=%s", name, if (name %in% names(mapped_columns)) mapped_columns[[name]] else "none")
}, character(1))
manifest <- c(
  "sampling_v_manifest",
  sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
  sprintf("input=%s", input_path),
  sprintf("input_md5=%s", unname(tools::md5sum(input_path))),
  sprintf("output_v=%s", output_v_path),
  sprintf("output_v_md5=%s", unname(tools::md5sum(output_v_path))),
  sprintf("rows=%d", nrow(dat)),
  sprintf("unique_clusters=%d", length(unique(dat[[cluster_col]]))),
  sprintf("vi_col=%s", vi_col),
  sprintf("id_col=%s", id_col),
  sprintf("cluster_col=%s", cluster_col),
  design_manifest,
  sprintf("rho=%s", format_value(rho)),
  sprintf("phi=%s", format_value(phi)),
  sprintf("scenario_label=%s", get_opt("scenario-label", "none")),
  "vcalc_checkpd=TRUE",
  "vcalc_nearpd=FALSE",
  "vcalc_sparse=FALSE",
  sprintf("minimum_eigenvalue=%.17g", minimum_eigenvalue),
  sprintf("metafor_version=%s", as.character(utils::packageVersion("metafor"))),
  sprintf("R_version=%s", R.version.string),
  "captured_warnings:",
  if (length(captured_warnings)) paste0("  - ", unique(captured_warnings)) else "  - none",
  "design_warning=V is conditional on the explicitly supplied design fields and rho/phi assumptions; rerun prespecified sensitivity scenarios instead of treating them as known."
)
tryCatch(
  writeLines(manifest, manifest_path, useBytes = TRUE),
  error = function(e) abort(sprintf("Could not write manifest '%s': %s", manifest_path, conditionMessage(e)))
)

cat(sprintf("Constructed %d x %d V matrix across %d clusters.\n",
            nrow(V), ncol(V), length(unique(dat[[cluster_col]]))))
cat(sprintf("V output: %s\nManifest: %s\n", output_v_path, manifest_path))
