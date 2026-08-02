#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1)

RAW_SCHEMA_VERSION <- "1.0.0"
ANALYSIS_EFFECT_SCHEMA_VERSION <- "1.0.0"
RAW_DATA_STAGE <- "raw_extraction"
ANALYSIS_EFFECT_DATA_STAGE <- "analysis_effect"
CALCULATOR_VERSION <- "1.0.0"
VALID_ANALYSIS_SCALES <- c(
  "identity", "log", "fisher-z", "logit", "arcsine_difference", "arcsine",
  "sqrt_difference", "sqrt"
)

abort <- function(message, status = 2L) {
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Conservative raw_extraction -> analysis_effect calculator\n\n",
  "Usage:\n",
  "  Rscript calculate_effect_sizes.R --input FILE --output FILE --measure CODE [options]\n\n",
  "Supported CODE routes and required column mappings:\n",
  "  OR RR RD AS PETO      --ai-col --bi-col --ci-col --di-col\n",
  "  MD SMD SMDH ROM       --m1i-col --m2i-col --sd1i-col --sd2i-col --n1i-col --n2i-col\n",
  "  IRR IRD IRSD          --x1i-col --x2i-col --t1i-col --t2i-col\n",
  "  COR UCOR ZCOR         --ri-col --ni-col\n",
  "  PR PLN PLO PRZ PAS    --xi-col --ni-col\n",
  "  IR IRLN IRS           --xi-col --ti-col\n",
  "  MN MNLN CVLN          --mi-col --sdi-col --ni-col\n",
  "  SDLN                  --sdi-col --ni-col\n",
  "  MC SMCC SMCR SMCRH    --m1i-col --m2i-col --sd1i-col --sd2i-col --ri-col --ni-col\n",
  "  GEN                   --yi-col --uncertainty vi|se|ci --input-scale analysis|ratio|correlation\n\n",
  "GEN uncertainty options:\n",
  "  vi: --vi-col (input must already be on analysis scale)\n",
  "  se: --se-col (input must already be on analysis scale)\n",
  "  ci: --ci-lb-col --ci-ub-col --ci-level PERCENT --ci-distribution normal|t\n",
  "      For t intervals, provide exactly one of --df NUMBER or --df-col COLUMN.\n",
  "      With --input-scale analysis, also provide --analysis-scale explicitly.\n\n",
  "Zero-count options (never inferred):\n",
  "  --zero-policy none|only0|all|if0all\n",
  "  --add NUMBER                         required unless policy is none\n",
  "  --drop-double-zero yes|no            required when double-zero rows occur\n\n",
  "Other options:\n",
  "  --study-id-col COLUMN\n",
  "  --bias-correction yes|no             required for SMD/SMDH/ROM/SMCC/SMCR/SMCRH\n",
  "  --vtype CODE                         required for SMD/SMDH/ROM/COR/UCOR\n",
  "  --allow-asymmetric-ci yes|no         default: no\n",
  "  --analysis-scale LABEL               required for GEN input already on its analysis scale\n",
  "  --na-action fail|omit                default: fail; omit writes .excluded.csv\n",
  "  --overwrite yes|no                   default: no\n",
  "  --help\n\n",
  "Input must declare schema_version=1.0.0 and data_stage=raw_extraction and retain provenance fields.\n",
  "Output declares schema_version=1.0.0 and data_stage=analysis_effect; it retains source fields plus\n",
  "source file/hash/row, calculation metadata, yi, vi, sei, measure, analysis_scale, and display_transform.\n",
  "GEN uses base R; escalc routes require metafor. The tool never installs packages, guesses columns/scales,\n",
  "or silently applies continuity corrections.\n"
)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0L || "--help" %in% args) {
  cat(help_text)
  quit(save = "no", status = 0L, runLast = FALSE)
}

allowed_options <- c(
  "input", "output", "measure", "study-id-col", "na-action", "overwrite",
  "ai-col", "bi-col", "ci-col", "di-col", "n1i-col", "n2i-col",
  "m1i-col", "m2i-col", "sd1i-col", "sd2i-col",
  "x1i-col", "x2i-col", "t1i-col", "t2i-col",
  "ri-col", "ni-col", "xi-col", "ti-col", "mi-col", "sdi-col",
  "yi-col", "vi-col", "se-col", "ci-lb-col", "ci-ub-col",
  "uncertainty", "input-scale", "ci-level", "ci-distribution", "df", "df-col",
  "zero-policy", "add", "drop-double-zero", "bias-correction", "vtype",
  "allow-asymmetric-ci", "analysis-scale"
)

parse_cli <- function(x) {
  out <- list()
  i <- 1L
  while (i <= length(x)) {
    token <- x[[i]]
    if (!startsWith(token, "--")) {
      abort(sprintf("Unexpected positional argument '%s'. Use --help.", token))
    }
    key <- substring(token, 3L)
    if (!(key %in% allowed_options)) {
      abort(sprintf("Unknown option '--%s'. Use --help.", key))
    }
    if (!is.null(out[[key]])) {
      abort(sprintf("Option '--%s' was supplied more than once.", key))
    }
    if (i == length(x) || startsWith(x[[i + 1L]], "--")) {
      abort(sprintf("Option '--%s' requires a value.", key))
    }
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
  if (!(value %in% choices)) {
    abort(sprintf("%s must be one of: %s.", label, paste(choices, collapse = ", ")))
  }
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
  if (length(number) != 1L || is.na(number) || !is.finite(number)) {
    abort(sprintf("%s must be one finite number.", label))
  }
  lower_bad <- if (lower_open) number <= lower else number < lower
  upper_bad <- if (upper_open) number >= upper else number > upper
  if (lower_bad || upper_bad) {
    abort(sprintf("%s is outside the allowed range.", label))
  }
  number
}

input_path <- normalizePath(require_opt("input"), winslash = "/", mustWork = FALSE)
output_path <- normalizePath(require_opt("output"), winslash = "/", mustWork = FALSE)
measure <- toupper(require_opt("measure"))
na_action <- parse_choice(tolower(get_opt("na-action", "fail")), c("fail", "omit"), "--na-action")
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", default = FALSE)
allow_asymmetric <- parse_yes_no(get_opt("allow-asymmetric-ci"), "--allow-asymmetric-ci", default = FALSE)

supported_measures <- c(
  "OR", "RR", "RD", "AS", "PETO",
  "MD", "SMD", "SMDH", "ROM",
  "IRR", "IRD", "IRSD", "COR", "UCOR", "ZCOR",
  "PR", "PLN", "PLO", "PRZ", "PAS",
  "IR", "IRLN", "IRS", "MN", "MNLN", "SDLN", "CVLN",
  "MC", "SMCC", "SMCR", "SMCRH", "GEN"
)
if (!(measure %in% supported_measures)) {
  abort(sprintf("Unsupported --measure '%s'. Supported values: %s.",
                measure, paste(supported_measures, collapse = ", ")))
}
if (!file.exists(input_path)) abort(sprintf("Input file does not exist: %s", input_path))
if (dir.exists(output_path)) abort("--output must be a file path, not a directory.")
output_parent <- dirname(output_path)
if (!dir.exists(output_parent)) abort(sprintf("Output directory does not exist: %s", output_parent))

stem <- sub("(\\.[^./\\\\]+)$", "", output_path)
manifest_path <- paste0(stem, ".manifest.txt")
excluded_path <- paste0(stem, ".excluded.csv")
prospective_outputs <- c(output_path, manifest_path, excluded_path)
if (!overwrite && any(file.exists(prospective_outputs))) {
  abort(sprintf("Output already exists. Use --overwrite yes to replace known outputs: %s",
                paste(prospective_outputs[file.exists(prospective_outputs)], collapse = ", ")))
}

dat <- tryCatch(
  read.csv(input_path, check.names = FALSE, fileEncoding = "UTF-8", na.strings = c("", "NA")),
  error = function(e) abort(sprintf("Could not read UTF-8 CSV '%s': %s", input_path, conditionMessage(e)))
)
if (nrow(dat) == 0L) abort("Input contains no data rows.")
if (anyDuplicated(names(dat))) abort("Input column names must be unique.")

required_raw_contract_columns <- c(
  "schema_version", "data_stage", "study_id", "report_id", "effect_id", "citation",
  "publication_year", "study_design", "population", "exposure_intervention", "comparator",
  "outcome", "outcome_definition", "timepoint", "effect_measure", "effect_scale",
  "effect_estimate", "se", "variance", "ci_lower", "ci_upper", "ci_level", "n_total",
  "direction", "unit", "dependency_cluster", "risk_of_bias", "source_locator", "extractor",
  "verifier", "extraction_date", "data_status", "ai_assisted", "ai_system_id"
)
required_raw_value_columns <- c(
  "schema_version", "data_stage", "study_id", "report_id", "effect_id", "citation",
  "publication_year", "study_design", "population", "exposure_intervention", "comparator",
  "outcome", "outcome_definition", "timepoint", "effect_measure", "n_total", "direction",
  "unit", "source_locator", "extractor", "verifier", "extraction_date", "data_status",
  "ai_assisted"
)
missing_contract_columns <- setdiff(required_raw_contract_columns, names(dat))
if (length(missing_contract_columns)) {
  abort(sprintf(
    "Input is not a complete raw_extraction contract; missing column(s): %s.",
    paste(missing_contract_columns, collapse = ", ")
  ))
}
blank_contract_rows <- unique(unlist(lapply(required_raw_value_columns, function(column_name) {
  raw <- dat[[column_name]]
  which(is.na(raw) | trimws(as.character(raw)) == "")
})))
if (length(blank_contract_rows)) {
  abort(sprintf(
    "Required raw_extraction provenance/identity values are blank at physical CSV row(s): %s.",
    paste(blank_contract_rows + 1L, collapse = ", ")
  ))
}
if (any(as.character(dat$schema_version) != RAW_SCHEMA_VERSION)) {
  bad <- which(as.character(dat$schema_version) != RAW_SCHEMA_VERSION) + 1L
  abort(sprintf(
    "Input schema_version must be %s for raw_extraction; invalid physical CSV row(s): %s.",
    RAW_SCHEMA_VERSION, paste(bad, collapse = ", ")
  ))
}
if (any(as.character(dat$data_stage) != RAW_DATA_STAGE)) {
  bad <- which(as.character(dat$data_stage) != RAW_DATA_STAGE) + 1L
  abort(sprintf(
    "Input data_stage must be %s; invalid physical CSV row(s): %s.",
    RAW_DATA_STAGE, paste(bad, collapse = ", ")
  ))
}
if (anyDuplicated(as.character(dat$effect_id))) abort("Input effect_id values must be unique.")

reserved <- c(
  "source_schema_version", "source_data_stage", "source_file", "source_file_md5", "source_row",
  "calculation_method", "calculator_version", "calculated_at_utc", "yi", "vi", "sei", "measure",
  "analysis_scale", "display_transform"
)
collisions <- intersect(reserved, names(dat))
if (length(collisions)) {
  abort(sprintf("Input already contains reserved output column(s): %s. Rename them before running.",
                paste(collisions, collapse = ", ")))
}
dat$source_row <- seq_len(nrow(dat)) + 1L
source_file_md5 <- unname(tools::md5sum(input_path))

numeric_column <- function(column_name, label) {
  if (!(column_name %in% names(dat))) abort(sprintf("%s refers to missing column '%s'.", label, column_name))
  raw <- dat[[column_name]]
  text_value <- trimws(as.character(raw))
  missing <- is.na(raw) | text_value == ""
  value <- suppressWarnings(as.numeric(text_value))
  bad <- !missing & is.na(value)
  if (any(bad)) {
    abort(sprintf("Column '%s' contains non-numeric values at source row(s): %s.",
                  column_name, paste(dat$source_row[bad], collapse = ", ")))
  }
  value[missing] <- NA_real_
  value
}

mapped_numeric <- function(option_name) {
  numeric_column(require_opt(option_name), paste0("--", option_name))
}

inputs <- list()
route <- NULL
if (measure %in% c("OR", "RR", "RD", "AS", "PETO")) {
  route <- "binary"
  inputs <- list(
    ai = mapped_numeric("ai-col"), bi = mapped_numeric("bi-col"),
    ci = mapped_numeric("ci-col"), di = mapped_numeric("di-col")
  )
} else if (measure %in% c("MD", "SMD", "SMDH", "ROM")) {
  route <- "continuous"
  inputs <- list(
    m1i = mapped_numeric("m1i-col"), m2i = mapped_numeric("m2i-col"),
    sd1i = mapped_numeric("sd1i-col"), sd2i = mapped_numeric("sd2i-col"),
    n1i = mapped_numeric("n1i-col"), n2i = mapped_numeric("n2i-col")
  )
} else if (measure %in% c("IRR", "IRD", "IRSD")) {
  route <- "rate_comparison"
  inputs <- list(
    x1i = mapped_numeric("x1i-col"), x2i = mapped_numeric("x2i-col"),
    t1i = mapped_numeric("t1i-col"), t2i = mapped_numeric("t2i-col")
  )
} else if (measure %in% c("COR", "UCOR", "ZCOR")) {
  route <- "correlation"
  inputs <- list(ri = mapped_numeric("ri-col"), ni = mapped_numeric("ni-col"))
} else if (measure %in% c("PR", "PLN", "PLO", "PRZ", "PAS")) {
  route <- "proportion"
  inputs <- list(xi = mapped_numeric("xi-col"), ni = mapped_numeric("ni-col"))
} else if (measure %in% c("IR", "IRLN", "IRS")) {
  route <- "incidence"
  inputs <- list(xi = mapped_numeric("xi-col"), ti = mapped_numeric("ti-col"))
} else if (measure %in% c("MN", "MNLN", "CVLN")) {
  route <- "single_mean"
  inputs <- list(
    mi = mapped_numeric("mi-col"), sdi = mapped_numeric("sdi-col"),
    ni = mapped_numeric("ni-col")
  )
} else if (measure == "SDLN") {
  route <- "single_sd"
  inputs <- list(sdi = mapped_numeric("sdi-col"), ni = mapped_numeric("ni-col"))
} else if (measure %in% c("MC", "SMCC", "SMCR", "SMCRH")) {
  route <- "change"
  inputs <- list(
    m1i = mapped_numeric("m1i-col"), m2i = mapped_numeric("m2i-col"),
    sd1i = mapped_numeric("sd1i-col"), sd2i = mapped_numeric("sd2i-col"),
    ri = mapped_numeric("ri-col"), ni = mapped_numeric("ni-col")
  )
} else {
  route <- "generic"
  inputs <- list(yi = mapped_numeric("yi-col"))
  uncertainty <- parse_choice(tolower(require_opt("uncertainty")), c("vi", "se", "ci"), "--uncertainty")
  if (uncertainty == "vi") inputs$vi <- mapped_numeric("vi-col")
  if (uncertainty == "se") inputs$sei <- mapped_numeric("se-col")
  if (uncertainty == "ci") {
    inputs$ci.lb <- mapped_numeric("ci-lb-col")
    inputs$ci.ub <- mapped_numeric("ci-ub-col")
    if (tolower(get_opt("ci-distribution", "")) == "t" && !is.null(get_opt("df-col"))) {
      inputs$df <- mapped_numeric("df-col")
    }
  }
}

if (!is.null(get_opt("study-id-col"))) {
  id_col <- get_opt("study-id-col")
  if (!(id_col %in% names(dat))) abort(sprintf("--study-id-col refers to missing column '%s'.", id_col))
  id_text <- trimws(as.character(dat[[id_col]]))
  inputs$study_id_check <- ifelse(is.na(dat[[id_col]]) | id_text == "", NA_real_, 1)
}

complete <- complete.cases(as.data.frame(inputs, check.names = FALSE))
excluded_rows <- list()
if (any(!complete)) {
  missing_details <- vapply(which(!complete), function(i) {
    missing_names <- names(inputs)[vapply(inputs, function(x) is.na(x[[i]]), logical(1))]
    paste(missing_names, collapse = ";")
  }, character(1))
  if (na_action == "fail") {
    abort(sprintf(
      "Missing required values at source row(s): %s. Fix them or explicitly use --na-action omit.",
      paste(dat$source_row[!complete], collapse = ", ")
    ))
  }
  excluded <- dat[!complete, , drop = FALSE]
  excluded$exclusion_reason <- paste0("missing_required:", missing_details)
  excluded_rows[[length(excluded_rows) + 1L]] <- excluded
  dat <- dat[complete, , drop = FALSE]
  inputs <- lapply(inputs, function(x) x[complete])
}
inputs$study_id_check <- NULL
if (nrow(dat) == 0L) abort("No complete rows remain after explicit omission.")

bad_finite <- unique(unlist(lapply(inputs, function(x) which(!is.finite(x)))))
if (length(bad_finite)) {
  abort(sprintf("Required numeric inputs contain non-finite values at source row(s): %s.",
                paste(dat$source_row[bad_finite], collapse = ", ")))
}

check_integer_nonnegative <- function(x, label) {
  bad <- x < 0 | abs(x - round(x)) > sqrt(.Machine$double.eps)
  if (any(bad)) abort(sprintf("%s must contain non-negative integers; invalid source row(s): %s.",
                              label, paste(dat$source_row[bad], collapse = ", ")))
}
check_sample_size <- function(x, label, minimum = 2) {
  bad <- x < minimum | abs(x - round(x)) > sqrt(.Machine$double.eps)
  if (any(bad)) abort(sprintf("%s must contain integers >= %s; invalid source row(s): %s.",
                              label, minimum, paste(dat$source_row[bad], collapse = ", ")))
}

if (route == "binary") {
  lapply(names(inputs), function(nm) check_integer_nonnegative(inputs[[nm]], nm))
  if (any(inputs$ai + inputs$bi <= 0 | inputs$ci + inputs$di <= 0)) {
    abort("Each binary group must have a positive row total.")
  }
}
if (route == "continuous") {
  check_sample_size(inputs$n1i, "n1i")
  check_sample_size(inputs$n2i, "n2i")
  if (any(inputs$sd1i < 0 | inputs$sd2i < 0)) abort("Standard deviations cannot be negative.")
  if (measure %in% c("SMD", "SMDH") && any(inputs$sd1i == 0 & inputs$sd2i == 0)) {
    abort("SMD is undefined when both group SDs are zero.")
  }
  if (measure == "ROM" && any(inputs$m1i <= 0 | inputs$m2i <= 0)) {
    abort("ROM requires strictly positive means in both groups.")
  }
}
if (route == "rate_comparison") {
  check_integer_nonnegative(inputs$x1i, "x1i")
  check_integer_nonnegative(inputs$x2i, "x2i")
  if (any(inputs$t1i <= 0 | inputs$t2i <= 0)) abort("Person-time values must be > 0.")
}
if (route == "correlation") {
  if (any(inputs$ri <= -1 | inputs$ri >= 1)) abort("Correlations must be strictly between -1 and 1.")
  check_sample_size(inputs$ni, "ni", minimum = if (measure == "ZCOR") 4 else 3)
}
if (route == "proportion") {
  check_integer_nonnegative(inputs$xi, "xi")
  check_sample_size(inputs$ni, "ni", minimum = 1)
  if (any(inputs$xi > inputs$ni)) abort("Event counts xi cannot exceed ni.")
}
if (route == "incidence") {
  check_integer_nonnegative(inputs$xi, "xi")
  if (any(inputs$ti <= 0)) abort("Person-time ti must be > 0.")
}
if (route %in% c("single_mean", "single_sd")) {
  check_sample_size(inputs$ni, "ni")
  if (any(inputs$sdi <= 0)) abort("sdi must be > 0 for single-group mean/dispersion measures.")
  if (measure %in% c("MNLN", "CVLN") && any(inputs$mi <= 0)) abort(sprintf("%s requires mi > 0.", measure))
}
if (route == "change") {
  check_sample_size(inputs$ni, "ni")
  if (any(inputs$sd1i < 0 | inputs$sd2i < 0)) abort("Standard deviations cannot be negative.")
  if (any(inputs$ri <= -1 | inputs$ri >= 1)) abort("Pre-post correlations must be strictly between -1 and 1.")
}

analysis_scale_map <- c(
  OR = "log", RR = "log", PETO = "log", IRR = "log", ROM = "log",
  PLN = "log", IRLN = "log", MNLN = "log", SDLN = "log", CVLN = "log",
  PLO = "logit", ZCOR = "fisher-z", AS = "arcsine_difference", PAS = "arcsine",
  IRSD = "sqrt_difference", IRS = "sqrt"
)
display_transform_map <- c(log = "exp", `fisher-z` = "tanh", logit = "plogis")

if (route == "generic") {
  input_scale <- parse_choice(tolower(require_opt("input-scale")),
                              c("analysis", "ratio", "correlation"), "--input-scale")
  declared_analysis_scale <- get_opt("analysis-scale")
  if (input_scale == "analysis") {
    if (is.null(declared_analysis_scale)) {
      abort("GEN with --input-scale analysis requires --analysis-scale; the calculator will not guess the yi/vi scale.")
    }
    declared_analysis_scale <- parse_choice(
      tolower(declared_analysis_scale), VALID_ANALYSIS_SCALES, "--analysis-scale"
    )
  } else if (!is.null(declared_analysis_scale)) {
    inferred_scale <- if (input_scale == "ratio") "log" else "fisher-z"
    declared_analysis_scale <- parse_choice(
      tolower(declared_analysis_scale), VALID_ANALYSIS_SCALES, "--analysis-scale"
    )
    if (declared_analysis_scale != inferred_scale) {
      abort(sprintf(
        "--input-scale %s implies --analysis-scale %s, not %s.",
        input_scale, inferred_scale, declared_analysis_scale
      ))
    }
  }
  if (uncertainty %in% c("vi", "se") && input_scale != "analysis") {
    abort("GEN with vi/se requires --input-scale analysis. Supply already log/Fisher-z transformed estimates and uncertainty, or provide a CI for conversion.")
  }
  yi <- inputs$yi
  if (uncertainty == "vi") {
    vi <- inputs$vi
    if (any(vi <= 0)) abort("GEN sampling variances must be > 0.")
  } else if (uncertainty == "se") {
    if (any(inputs$sei <= 0)) abort("GEN standard errors must be > 0.")
    vi <- inputs$sei^2
  } else {
    ci_level <- parse_number(require_opt("ci-level"), "--ci-level", lower = 0, upper = 100,
                             lower_open = TRUE, upper_open = TRUE)
    ci_distribution <- parse_choice(tolower(require_opt("ci-distribution")), c("normal", "t"),
                                    "--ci-distribution")
    transform <- switch(input_scale, analysis = identity, ratio = log, correlation = atanh)
    if (input_scale == "ratio" && any(inputs$yi <= 0 | inputs$ci.lb <= 0 | inputs$ci.ub <= 0)) {
      abort("Ratio estimates and CI bounds must all be > 0 before log transformation.")
    }
    if (input_scale == "correlation" &&
        any(abs(inputs$yi) >= 1 | abs(inputs$ci.lb) >= 1 | abs(inputs$ci.ub) >= 1)) {
      abort("Correlation estimates and CI bounds must be strictly between -1 and 1.")
    }
    yi <- transform(inputs$yi)
    lower <- transform(inputs$ci.lb)
    upper <- transform(inputs$ci.ub)
    if (any(lower >= upper | yi <= lower | yi >= upper)) {
      abort("Each transformed point estimate must lie strictly inside its transformed CI.")
    }
    asymmetry <- abs(yi - (lower + upper) / 2) / (upper - lower)
    if (any(asymmetry > 0.05) && !allow_asymmetric) {
      abort(sprintf(
        "CI is notably asymmetric on the analysis scale at source row(s): %s. Confirm it is a Wald CI and rerun with --allow-asymmetric-ci yes only if justified.",
        paste(dat$source_row[asymmetry > 0.05], collapse = ", ")
      ))
    }
    alpha <- 1 - ci_level / 100
    if (ci_distribution == "normal") {
      if (!is.null(get_opt("df")) || !is.null(get_opt("df-col"))) abort("Do not supply df for a normal CI.")
      critical <- rep(qnorm(1 - alpha / 2), nrow(dat))
    } else {
      if (!xor(is.null(get_opt("df")), is.null(get_opt("df-col")))) {
        abort("For a t CI, provide exactly one of --df or --df-col.")
      }
      if (!is.null(get_opt("df"))) {
        df_value <- parse_number(get_opt("df"), "--df", lower = 0, lower_open = TRUE)
        critical <- rep(qt(1 - alpha / 2, df = df_value), nrow(dat))
      } else {
        df_values <- inputs$df
        if (length(df_values) != nrow(dat) || any(!is.finite(df_values) | df_values <= 0)) {
          abort("All t-distribution degrees of freedom must be finite and > 0.")
        }
        critical <- qt(1 - alpha / 2, df = df_values)
      }
    }
    sei <- (upper - lower) / (2 * critical)
    vi <- sei^2
  }
  analysis_scale <- switch(
    input_scale,
    analysis = declared_analysis_scale,
    ratio = "log",
    correlation = "fisher-z"
  )
  calculation_method <- sprintf(
    "GEN:%s:%s%s",
    input_scale,
    uncertainty,
    if (uncertainty == "ci") paste0(":", ci_distribution) else ""
  )
} else {
  if (!is.null(get_opt("analysis-scale"))) {
    abort("--analysis-scale is only accepted for GEN; escalc routes determine it from --measure.")
  }
  if (!requireNamespace("metafor", quietly = TRUE)) {
    abort(paste0(
      "This escalc route requires package 'metafor', which is not installed in the active R library. ",
      "The script did not install anything. Current .libPaths(): ",
      paste(.libPaths(), collapse = "; ")
    ))
  }
  corrected_measures <- c("SMD", "SMDH", "ROM", "SMCC", "SMCR", "SMCRH")
  variance_choice_measures <- c("SMD", "SMDH", "ROM", "COR", "UCOR")
  escalc_args <- c(list(measure = measure), inputs)
  if (measure %in% corrected_measures) {
    escalc_args$correct <- parse_yes_no(get_opt("bias-correction"), "--bias-correction")
  } else if (!is.null(get_opt("bias-correction"))) {
    abort(sprintf("--bias-correction is not exposed for measure %s.", measure))
  }
  if (measure %in% variance_choice_measures) {
    escalc_args$vtype <- toupper(require_opt("vtype"))
  } else if (!is.null(get_opt("vtype"))) {
    escalc_args$vtype <- toupper(get_opt("vtype"))
  }

  frequency_route <- route %in% c("binary", "rate_comparison", "proportion", "incidence")
  zero_policy <- get_opt("zero-policy")
  add_value <- get_opt("add")
  drop_value <- get_opt("drop-double-zero")
  double_zero <- rep(FALSE, nrow(dat))
  problematic_zero <- rep(FALSE, nrow(dat))
  if (route == "binary") {
    problematic_zero <- (inputs$ai == 0 | inputs$bi == 0 | inputs$ci == 0 | inputs$di == 0) &
      measure %in% c("OR", "RR")
    double_zero <- (inputs$ai == 0 & inputs$ci == 0) | (inputs$bi == 0 & inputs$di == 0)
  } else if (route == "rate_comparison") {
    problematic_zero <- (inputs$x1i == 0 | inputs$x2i == 0) & measure == "IRR"
    double_zero <- inputs$x1i == 0 & inputs$x2i == 0
  } else if (route == "proportion") {
    problematic_zero <- (inputs$xi == 0 | inputs$xi == inputs$ni) & measure %in% c("PLN", "PLO", "PRZ")
  } else if (route == "incidence") {
    problematic_zero <- inputs$xi == 0 & measure == "IRLN"
  }

  if (any(problematic_zero) && is.null(zero_policy)) {
    abort(sprintf(
      "Zero counts affect measure %s at source row(s): %s. Explicitly choose --zero-policy and, if needed, --add.",
      measure, paste(dat$source_row[problematic_zero], collapse = ", ")
    ))
  }
  if (any(double_zero) && is.null(drop_value)) {
    abort(sprintf(
      "Double-zero rows occur at source row(s): %s. Explicitly choose --drop-double-zero yes or no.",
      paste(dat$source_row[double_zero], collapse = ", ")
    ))
  }
  if (frequency_route) {
    zero_policy <- parse_choice(tolower(if (is.null(zero_policy)) "none" else zero_policy),
                                c("none", "only0", "all", "if0all"), "--zero-policy")
    if (zero_policy == "none") {
      if (!is.null(add_value)) abort("--add cannot be supplied when --zero-policy is none.")
      add_number <- 0
    } else {
      add_number <- parse_number(require_opt("add"), "--add", lower = 0, lower_open = TRUE)
    }
    drop_double_zero <- parse_yes_no(drop_value, "--drop-double-zero", default = FALSE)
    escalc_args$to <- zero_policy
    escalc_args$add <- add_number
    escalc_args$drop00 <- drop_double_zero
  } else if (!is.null(zero_policy) || !is.null(add_value) || !is.null(drop_value)) {
    abort("Zero-count options are only valid for frequency/count routes.")
  } else {
    drop_double_zero <- FALSE
  }

  esc <- tryCatch(
    do.call(metafor::escalc, escalc_args),
    error = function(e) abort(sprintf("metafor::escalc failed: %s", conditionMessage(e)))
  )
  yi <- as.numeric(esc$yi)
  vi <- as.numeric(esc$vi)
  invalid <- !is.finite(yi) | !is.finite(vi) | vi <= 0
  expected_drop <- frequency_route && drop_double_zero
  expected_drop_rows <- if (isTRUE(expected_drop)) double_zero else rep(FALSE, nrow(dat))
  unexpected <- invalid & !expected_drop_rows
  if (any(unexpected)) {
    abort(sprintf(
      "Effect sizes are non-estimable or have non-positive variance at source row(s): %s. Review zeros, inputs, and the selected measure; nothing was silently dropped.",
      paste(dat$source_row[unexpected], collapse = ", ")
    ))
  }
  if (any(expected_drop_rows)) {
    excluded <- dat[expected_drop_rows, , drop = FALSE]
    excluded$exclusion_reason <- "explicit_drop_double_zero"
    excluded_rows[[length(excluded_rows) + 1L]] <- excluded
    keep <- !expected_drop_rows
    dat <- dat[keep, , drop = FALSE]
    yi <- yi[keep]
    vi <- vi[keep]
  }
  analysis_scale <- if (measure %in% names(analysis_scale_map)) analysis_scale_map[[measure]] else "identity"
  calculation_method <- sprintf("metafor::escalc(measure=%s)", measure)
}

if (length(yi) == 0L || any(!is.finite(yi)) || any(!is.finite(vi)) || any(vi <= 0)) {
  abort("Final yi/vi values must be finite and vi must be > 0.")
}

display_transform <- if (analysis_scale %in% names(display_transform_map)) {
  display_transform_map[[analysis_scale]]
} else {
  "identity_or_measure_specific"
}

calculated_at_utc <- format(Sys.time(), format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
source_payload <- dat[, setdiff(names(dat), c("schema_version", "data_stage", "source_row")), drop = FALSE]
result <- data.frame(
  schema_version = rep(ANALYSIS_EFFECT_SCHEMA_VERSION, nrow(dat)),
  data_stage = rep(ANALYSIS_EFFECT_DATA_STAGE, nrow(dat)),
  source_schema_version = as.character(dat$schema_version),
  source_data_stage = as.character(dat$data_stage),
  source_file = rep(input_path, nrow(dat)),
  source_file_md5 = rep(source_file_md5, nrow(dat)),
  source_row = dat$source_row,
  calculation_method = rep(calculation_method, nrow(dat)),
  calculator_version = rep(CALCULATOR_VERSION, nrow(dat)),
  calculated_at_utc = rep(calculated_at_utc, nrow(dat)),
  check.names = FALSE,
  stringsAsFactors = FALSE
)
result <- data.frame(result, source_payload, check.names = FALSE, stringsAsFactors = FALSE)
result$yi <- yi
result$vi <- vi
result$sei <- sqrt(vi)
result$measure <- measure
result$analysis_scale <- analysis_scale
result$display_transform <- display_transform

write_csv <- function(x, path) {
  tryCatch(
    write.csv(x, path, row.names = FALSE, na = "", fileEncoding = "UTF-8"),
    error = function(e) abort(sprintf("Could not write '%s': %s", path, conditionMessage(e)))
  )
}
if (overwrite && !length(excluded_rows) && file.exists(excluded_path)) {
  unlink_status <- unlink(excluded_path, recursive = FALSE, force = FALSE)
  if (unlink_status != 0L) {
    abort(sprintf("Could not remove stale script-owned excluded-row output: %s", excluded_path))
  }
}
write_csv(result, output_path)

if (length(excluded_rows)) {
  excluded_all <- do.call(rbind, excluded_rows)
  if (!overwrite && file.exists(excluded_path)) {
    abort(sprintf("Excluded-row output already exists: %s. Use --overwrite yes.", excluded_path))
  }
  write_csv(excluded_all, excluded_path)
}

manifest <- c(
  "effect_size_calculation_manifest",
  sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
  sprintf("input=%s", input_path),
  sprintf("input_md5=%s", source_file_md5),
  sprintf("source_schema_version=%s", RAW_SCHEMA_VERSION),
  sprintf("source_data_stage=%s", RAW_DATA_STAGE),
  sprintf("output=%s", output_path),
  sprintf("output_schema_version=%s", ANALYSIS_EFFECT_SCHEMA_VERSION),
  sprintf("output_data_stage=%s", ANALYSIS_EFFECT_DATA_STAGE),
  sprintf("calculator_version=%s", CALCULATOR_VERSION),
  sprintf("measure=%s", measure),
  sprintf("route=%s", route),
  sprintf("calculation_method=%s", calculation_method),
  sprintf("analysis_scale=%s", analysis_scale),
  sprintf("display_transform=%s", display_transform),
  sprintf("rows_input=%d", nrow(read.csv(input_path, check.names = FALSE, fileEncoding = "UTF-8", nrows = -1L))),
  sprintf("rows_output=%d", nrow(result)),
  sprintf("na_action=%s", na_action),
  sprintf("allow_asymmetric_ci=%s", if (allow_asymmetric) "yes" else "no"),
  sprintf(
    "metafor_version=%s",
    if (requireNamespace("metafor", quietly = TRUE)) {
      as.character(utils::packageVersion("metafor"))
    } else {
      "not_installed_not_used_for_GEN"
    }
  ),
  sprintf("R_version=%s", R.version.string),
  "command_options:",
  paste0("  --", names(opt), "=", unlist(opt, use.names = FALSE)),
  "warning=Effect orientation, estimand compatibility, dependence, and model choice remain the analyst's responsibility."
)
tryCatch(
  writeLines(manifest, manifest_path, useBytes = TRUE),
  error = function(e) abort(sprintf("Could not write manifest '%s': %s", manifest_path, conditionMessage(e)))
)

cat(sprintf("Wrote %d effect-size rows to %s\n", nrow(result), output_path))
cat(sprintf("Manifest: %s\n", manifest_path))
if (length(excluded_rows)) cat(sprintf("Excluded rows: %s\n", excluded_path))
