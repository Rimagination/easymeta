#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE, warn = 1)

RAW_SCHEMA_VERSION <- "1.0.0"
ANALYSIS_EFFECT_SCHEMA_VERSION <- "1.0.0"
COMPLEX_EFFECT_CONTRACT_VERSION <- "1.1.0"
RAW_DATA_STAGE <- "raw_extraction"
ANALYSIS_EFFECT_DATA_STAGE <- "analysis_effect"
CALCULATOR_VERSION <- "1.1.0"
VALID_ANALYSIS_SCALES <- c(
  "identity", "log", "fisher-z", "logit", "arcsine_difference", "arcsine",
  "sqrt_difference", "sqrt"
)

abort <- function(message, status = 2L) {
  if (exists(".complex_cleanup_paths", envir = .GlobalEnv, inherits = FALSE)) {
    unlink(get(".complex_cleanup_paths", envir = .GlobalEnv), recursive = FALSE, force = FALSE)
  }
  cat(sprintf("ERROR: %s\n", message), file = stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

help_text <- paste0(
  "Conservative complex-design raw_extraction -> analysis_effect calculator\n\n",
  "Usage:\n",
  "  Rscript calculate_complex_effects.R --input FILE --output FILE [options]\n\n",
  "Supported row-level complex_design values:\n",
  "  paired_continuous_md       paired MD from mean_difference + sd_difference, or\n",
  "                             two condition means/SDs + an explicit correlation\n",
  "  crossover_continuous_md    same numeric routes, but carryover_cleared=yes and\n",
  "                             carryover_assessment_source are mandatory\n",
  "  two_group_change_md        intervention-minus-comparator change-score MD\n",
  "  baci_additive_md           additive (impact post-pre) - (control post-pre) MD\n",
  "  cluster_adjusted_generic   already reported design-adjusted estimate plus exactly\n",
  "                             one uncertainty route: se, vi, or complete CI\n\n",
  "Options:\n",
  "  --allow-asymmetric-ci yes|no   default: no; applies only when deriving SE from CI\n",
  "  --overwrite yes|no             default: no\n",
  "  --help\n\n",
  "Input must retain the complete raw_extraction 1.0.0 contract and declare\n",
  "complex_effect_contract_version=1.1.0. Every row must explicitly declare its design,\n",
  "applicability, scale, formula pathway, and assumptions. Assumed correlations require\n",
  "both assumption_set_id and correlation_source. The script never uses n_total or\n",
  "effective_sample_size to manufacture a cluster-adjusted estimate.\n\n",
  "Output retains all source fields, adds design/assumption audit fields, and declares the\n",
  "analysis_effect 1.0.0 contract accepted by validate_extraction.py --stage analysis.\n",
  "One output file must contain exactly one analysis_scale. The tool uses base R only,\n",
  "installs nothing, guesses nothing, and stops on incomplete or contradictory inputs.\n"
)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0L || "--help" %in% args) {
  cat(help_text)
  quit(save = "no", status = 0L, runLast = FALSE)
}

allowed_options <- c("input", "output", "allow-asymmetric-ci", "overwrite")

parse_cli <- function(x) {
  out <- list()
  i <- 1L
  while (i <= length(x)) {
    token <- x[[i]]
    if (!startsWith(token, "--")) {
      abort(sprintf("Unexpected positional argument '%s'. Use --help.", token))
    }
    key <- substring(token, 3L)
    if (!(key %in% allowed_options)) abort(sprintf("Unknown option '--%s'. Use --help.", key))
    if (!is.null(out[[key]])) abort(sprintf("Option '--%s' was supplied more than once.", key))
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

input_path <- normalizePath(require_opt("input"), winslash = "/", mustWork = FALSE)
output_path <- normalizePath(require_opt("output"), winslash = "/", mustWork = FALSE)
overwrite <- parse_yes_no(get_opt("overwrite"), "--overwrite", default = FALSE)
allow_asymmetric <- parse_yes_no(
  get_opt("allow-asymmetric-ci"), "--allow-asymmetric-ci", default = FALSE
)

if (!file.exists(input_path)) abort(sprintf("Input file does not exist: %s", input_path))
if (dir.exists(output_path)) abort("--output must be a file path, not a directory.")
if (identical(tolower(input_path), tolower(output_path))) abort("--input and --output must be different files.")
output_parent <- dirname(output_path)
if (!dir.exists(output_parent)) abort(sprintf("Output directory does not exist: %s", output_parent))

stem <- sub("(\\.[^./\\\\]+)$", "", output_path)
manifest_path <- paste0(stem, ".manifest.txt")
prospective_outputs <- c(output_path, manifest_path)
if (!overwrite && any(file.exists(prospective_outputs))) {
  abort(sprintf(
    "Output already exists. Use --overwrite yes to replace known outputs: %s",
    paste(prospective_outputs[file.exists(prospective_outputs)], collapse = ", ")
  ))
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
required_complex_columns <- c(
  "complex_effect_contract_version", "complex_design", "design_applicable",
  "design_applicability_basis", "carryover_cleared", "carryover_assessment_source",
  "reported_value_scale", "target_analysis_scale", "contrast_definition",
  "paired_input_pathway", "n_pairs", "mean_difference", "sd_difference",
  "mean_condition_1", "sd_condition_1", "mean_condition_2", "sd_condition_2",
  "paired_correlation", "paired_correlation_status", "change_definition",
  "group_independence", "independence_basis", "mean_change_intervention",
  "sd_change_intervention", "sd_pre_intervention", "sd_post_intervention",
  "pre_post_correlation_intervention", "intervention_sd_pathway",
  "intervention_correlation_status", "mean_change_comparator", "sd_change_comparator",
  "sd_pre_comparator", "sd_post_comparator", "pre_post_correlation_comparator",
  "comparator_sd_pathway", "comparator_correlation_status", "assumption_set_id",
  "correlation_source", "cluster_adjusted_estimate", "cluster_adjustment_method",
  "cluster_adjustment_source", "uncertainty_type", "ci_distribution", "ci_df",
  "effective_sample_size"
)

missing_contract_columns <- setdiff(
  c(required_raw_contract_columns, required_complex_columns), names(dat)
)
if (length(missing_contract_columns)) {
  abort(sprintf(
    "Input is not a complete complex raw_extraction contract; missing column(s): %s.",
    paste(missing_contract_columns, collapse = ", ")
  ))
}

is_blank <- function(value) {
  length(value) == 0L || is.na(value) || trimws(as.character(value)) == ""
}
text_at <- function(i, column_name, required = FALSE) {
  value <- dat[[column_name]][[i]]
  if (is_blank(value)) {
    if (required) abort(sprintf("Column '%s' is blank at physical CSV row %d.", column_name, i + 1L))
    return("")
  }
  trimws(as.character(value))
}
number_at <- function(i, column_name, required = FALSE, lower = -Inf, upper = Inf,
                      lower_open = FALSE, upper_open = FALSE) {
  raw <- text_at(i, column_name, required = required)
  if (!nzchar(raw)) return(NA_real_)
  value <- suppressWarnings(as.numeric(raw))
  if (length(value) != 1L || is.na(value) || !is.finite(value)) {
    abort(sprintf("Column '%s' must contain a finite number at physical CSV row %d.", column_name, i + 1L))
  }
  lower_bad <- if (lower_open) value <= lower else value < lower
  upper_bad <- if (upper_open) value >= upper else value > upper
  if (lower_bad || upper_bad) {
    abort(sprintf("Column '%s' is outside its allowed range at physical CSV row %d.", column_name, i + 1L))
  }
  value
}
integer_at <- function(i, column_name, required = FALSE, minimum = -Inf) {
  value <- number_at(i, column_name, required = required)
  if (is.na(value)) return(NA_real_)
  if (abs(value - round(value)) > sqrt(.Machine$double.eps) || value < minimum) {
    abort(sprintf(
      "Column '%s' must be an integer >= %s at physical CSV row %d.",
      column_name, minimum, i + 1L
    ))
  }
  value
}
require_blank <- function(i, column_names, context) {
  used <- column_names[!vapply(column_names, function(x) is_blank(dat[[x]][[i]]), logical(1))]
  if (length(used)) {
    abort(sprintf(
      "%s does not use column(s) %s; clear them at physical CSV row %d to avoid an ambiguous pathway.",
      context, paste(used, collapse = ", "), i + 1L
    ))
  }
}

blank_contract_rows <- unique(unlist(lapply(required_raw_value_columns, function(column_name) {
  which(vapply(dat[[column_name]], is_blank, logical(1)))
})))
if (length(blank_contract_rows)) {
  abort(sprintf(
    "Required raw_extraction provenance/identity values are blank at physical CSV row(s): %s.",
    paste(blank_contract_rows + 1L, collapse = ", ")
  ))
}
if (any(as.character(dat$schema_version) != RAW_SCHEMA_VERSION)) {
  bad <- which(as.character(dat$schema_version) != RAW_SCHEMA_VERSION) + 1L
  abort(sprintf("Input schema_version must be %s; invalid physical CSV row(s): %s.",
                RAW_SCHEMA_VERSION, paste(bad, collapse = ", ")))
}
if (any(as.character(dat$data_stage) != RAW_DATA_STAGE)) {
  bad <- which(as.character(dat$data_stage) != RAW_DATA_STAGE) + 1L
  abort(sprintf("Input data_stage must be %s; invalid physical CSV row(s): %s.",
                RAW_DATA_STAGE, paste(bad, collapse = ", ")))
}
if (any(as.character(dat$complex_effect_contract_version) != COMPLEX_EFFECT_CONTRACT_VERSION)) {
  bad <- which(as.character(dat$complex_effect_contract_version) != COMPLEX_EFFECT_CONTRACT_VERSION) + 1L
  abort(sprintf(
    "complex_effect_contract_version must be %s; invalid physical CSV row(s): %s.",
    COMPLEX_EFFECT_CONTRACT_VERSION, paste(bad, collapse = ", ")
  ))
}
if (anyDuplicated(as.character(dat$effect_id))) abort("Input effect_id values must be unique.")

derived_audit_fields <- c(
  "complex_effect_route", "design_formula", "sd_derivation", "correlations_used",
  "assumption_audit", "uncertainty_route", "cluster_adjustment_audit",
  "effective_sample_size_audit", "effect_orientation"
)
reserved <- c(
  "source_schema_version", "source_data_stage", "source_file", "source_file_md5", "source_row",
  "calculation_method", "calculator_version", "calculated_at_utc", "yi", "vi", "sei", "measure",
  "analysis_scale", "display_transform", derived_audit_fields
)
collisions <- intersect(reserved, names(dat))
if (length(collisions)) {
  abort(sprintf("Input already contains reserved output column(s): %s. Rename them before running.",
                paste(collisions, collapse = ", ")))
}

paired_fields <- c(
  "paired_input_pathway", "n_pairs", "mean_difference", "sd_difference",
  "mean_condition_1", "sd_condition_1", "mean_condition_2", "sd_condition_2",
  "paired_correlation", "paired_correlation_status"
)
change_fields <- c(
  "change_definition", "group_independence", "independence_basis",
  "mean_change_intervention", "sd_change_intervention", "sd_pre_intervention",
  "sd_post_intervention", "pre_post_correlation_intervention", "intervention_sd_pathway",
  "intervention_correlation_status", "mean_change_comparator", "sd_change_comparator",
  "sd_pre_comparator", "sd_post_comparator", "pre_post_correlation_comparator",
  "comparator_sd_pathway", "comparator_correlation_status"
)
cluster_fields <- c(
  "cluster_adjusted_estimate", "cluster_adjustment_method", "cluster_adjustment_source",
  "uncertainty_type", "ci_distribution", "ci_df", "effective_sample_size"
)

correlation_record <- function(i, value_column, status_column, label) {
  status <- tolower(text_at(i, status_column, required = TRUE))
  status <- parse_choice(status, c("not_used", "reported", "assumed"),
                         sprintf("%s at physical CSV row %d", status_column, i + 1L))
  if (status == "not_used") {
    if (!is_blank(dat[[value_column]][[i]])) {
      abort(sprintf(
        "%s is present but %s=not_used at physical CSV row %d.",
        value_column, status_column, i + 1L
      ))
    }
    return(list(used = FALSE, status = status, value = NA_real_, label = label))
  }
  value <- number_at(i, value_column, required = TRUE, lower = -1, upper = 1,
                     lower_open = TRUE, upper_open = TRUE)
  if (!nzchar(text_at(i, "correlation_source", required = FALSE))) {
    abort(sprintf("correlation_source is required for %s at physical CSV row %d.", label, i + 1L))
  }
  if (status == "assumed" && !nzchar(text_at(i, "assumption_set_id", required = FALSE))) {
    abort(sprintf(
      "assumption_set_id is required when %s is assumed at physical CSV row %d.",
      label, i + 1L
    ))
  }
  list(used = TRUE, status = status, value = value, label = label)
}

change_sd <- function(i, group_label, pathway_column, change_sd_column, pre_sd_column,
                      post_sd_column, correlation_column, correlation_status_column) {
  pathway <- tolower(text_at(i, pathway_column, required = TRUE))
  pathway <- parse_choice(
    pathway, c("reported_change_sd", "derived_pre_post"),
    sprintf("%s at physical CSV row %d", pathway_column, i + 1L)
  )
  if (pathway == "reported_change_sd") {
    sd_value <- number_at(i, change_sd_column, required = TRUE, lower = 0, lower_open = TRUE)
    require_blank(i, c(pre_sd_column, post_sd_column), paste(group_label, "reported change SD pathway"))
    corr <- correlation_record(i, correlation_column, correlation_status_column, group_label)
    if (corr$used) {
      abort(sprintf(
        "%s uses a reported change SD, so its pre-post correlation must be not_used at physical CSV row %d.",
        group_label, i + 1L
      ))
    }
    return(list(sd = sd_value, corr = corr, audit = paste0(group_label, ":reported_change_sd")))
  }

  require_blank(i, change_sd_column, paste(group_label, "derived pre-post SD pathway"))
  pre_sd <- number_at(i, pre_sd_column, required = TRUE, lower = 0)
  post_sd <- number_at(i, post_sd_column, required = TRUE, lower = 0)
  corr <- correlation_record(i, correlation_column, correlation_status_column, group_label)
  if (!corr$used) {
    abort(sprintf(
      "%s derived_pre_post pathway requires an explicit correlation at physical CSV row %d.",
      group_label, i + 1L
    ))
  }
  variance <- pre_sd^2 + post_sd^2 - 2 * corr$value * pre_sd * post_sd
  if (!is.finite(variance) || variance <= 0) {
    abort(sprintf(
      "%s derived change-score variance must be > 0 at physical CSV row %d.",
      group_label, i + 1L
    ))
  }
  list(
    sd = sqrt(variance), corr = corr,
    audit = sprintf("%s:sqrt(sd_pre^2+sd_post^2-2*r*sd_pre*sd_post)", group_label)
  )
}

display_transform_for <- function(scale) {
  if (scale == "log") return("exp")
  if (scale == "fisher-z") return("tanh")
  if (scale == "logit") return("plogis")
  "identity_or_measure_specific"
}

measure_scale_ok <- function(effect_measure, scale) {
  mapping <- list(
    OR = "log", RR = "log", HR = "log", IRR = "log", ROM = "log", PETO = "log",
    PLN = "log", IRLN = "log", MNLN = "log", SDLN = "log", CVLN = "log",
    FISHER_Z = "fisher-z", ZCOR = "fisher-z", PLO = "logit",
    AS = "arcsine_difference", PAS = "arcsine", IRSD = "sqrt_difference", IRS = "sqrt",
    CORRELATION = c("identity", "fisher-z"),
    PROPORTION = c("identity", "log", "logit", "arcsine"),
    OTHER = VALID_ANALYSIS_SCALES
  )
  allowed <- mapping[[effect_measure]]
  if (is.null(allowed)) allowed <- "identity"
  scale %in% allowed
}

n <- nrow(dat)
yi <- vi <- rep(NA_real_, n)
measure <- analysis_scale <- display_transform <- rep("", n)
calculation_method <- complex_effect_route <- design_formula <- sd_derivation <- rep("", n)
correlations_used <- assumption_audit <- uncertainty_route <- rep("", n)
cluster_adjustment_audit <- effective_sample_size_audit <- effect_orientation <- rep("", n)
assumed_correlation <- rep(FALSE, n)

supported_designs <- c(
  "paired_continuous_md", "crossover_continuous_md", "two_group_change_md",
  "baci_additive_md", "cluster_adjusted_generic"
)

for (i in seq_len(n)) {
  design <- tolower(text_at(i, "complex_design", required = TRUE))
  design <- parse_choice(design, supported_designs,
                         sprintf("complex_design at physical CSV row %d", i + 1L))
  applicable <- tolower(text_at(i, "design_applicable", required = TRUE))
  if (applicable != "yes") {
    abort(sprintf(
      "design_applicable must be yes; design is inapplicable or unresolved at physical CSV row %d.",
      i + 1L
    ))
  }
  text_at(i, "design_applicability_basis", required = TRUE)
  carryover <- tolower(text_at(i, "carryover_cleared", required = TRUE))

  if (design == "crossover_continuous_md") {
    if (carryover != "yes") {
      abort(sprintf(
        "crossover_continuous_md requires carryover_cleared=yes; no/unclear carryover blocks the effect at physical CSV row %d.",
        i + 1L
      ))
    }
    text_at(i, "carryover_assessment_source", required = TRUE)
  } else {
    if (carryover != "not_applicable") {
      abort(sprintf(
        "%s requires carryover_cleared=not_applicable at physical CSV row %d.",
        design, i + 1L
      ))
    }
    if (nzchar(text_at(i, "carryover_assessment_source", required = FALSE))) {
      abort(sprintf(
        "carryover_assessment_source must be blank when carryover is not applicable at physical CSV row %d.",
        i + 1L
      ))
    }
  }

  effect_measure <- toupper(text_at(i, "effect_measure", required = TRUE))
  reported_scale <- tolower(text_at(i, "reported_value_scale", required = TRUE))
  target_scale <- tolower(text_at(i, "target_analysis_scale", required = TRUE))
  target_scale <- parse_choice(
    target_scale, VALID_ANALYSIS_SCALES,
    sprintf("target_analysis_scale at physical CSV row %d", i + 1L)
  )

  if (design %in% c("paired_continuous_md", "crossover_continuous_md")) {
    require_blank(i, c(change_fields, cluster_fields), design)
    if (effect_measure != "MD" || reported_scale != "identity" || target_scale != "identity") {
      abort(sprintf("%s requires effect_measure=MD and identity reported/analysis scales at physical CSV row %d.",
                    design, i + 1L))
    }
    if (tolower(text_at(i, "contrast_definition", required = TRUE)) != "condition_1_minus_condition_2") {
      abort(sprintf("%s requires contrast_definition=condition_1_minus_condition_2 at physical CSV row %d.",
                    design, i + 1L))
    }
    n_pairs <- integer_at(i, "n_pairs", required = TRUE, minimum = 2)
    pathway <- tolower(text_at(i, "paired_input_pathway", required = TRUE))
    pathway <- parse_choice(
      pathway, c("direct_difference", "derived_from_conditions"),
      sprintf("paired_input_pathway at physical CSV row %d", i + 1L)
    )
    if (pathway == "direct_difference") {
      mean_diff <- number_at(i, "mean_difference", required = TRUE)
      sd_diff <- number_at(i, "sd_difference", required = TRUE, lower = 0, lower_open = TRUE)
      require_blank(
        i, c("mean_condition_1", "sd_condition_1", "mean_condition_2", "sd_condition_2"),
        paste(design, "direct difference pathway")
      )
      corr <- correlation_record(i, "paired_correlation", "paired_correlation_status", "paired")
      if (corr$used) abort(sprintf("direct_difference must not use a correlation at physical CSV row %d.", i + 1L))
      sd_derivation[[i]] <- "reported_sd_difference"
      correlations_used[[i]] <- "none"
      calculation_method[[i]] <- paste0("complex:", design, ":direct_difference")
    } else {
      require_blank(i, c("mean_difference", "sd_difference"), paste(design, "derived pathway"))
      mean_1 <- number_at(i, "mean_condition_1", required = TRUE)
      mean_2 <- number_at(i, "mean_condition_2", required = TRUE)
      sd_1 <- number_at(i, "sd_condition_1", required = TRUE, lower = 0)
      sd_2 <- number_at(i, "sd_condition_2", required = TRUE, lower = 0)
      corr <- correlation_record(i, "paired_correlation", "paired_correlation_status", "paired")
      if (!corr$used) abort(sprintf("derived_from_conditions requires an explicit correlation at physical CSV row %d.", i + 1L))
      mean_diff <- mean_1 - mean_2
      variance_diff <- sd_1^2 + sd_2^2 - 2 * corr$value * sd_1 * sd_2
      if (!is.finite(variance_diff) || variance_diff <= 0) {
        abort(sprintf("Derived paired difference variance must be > 0 at physical CSV row %d.", i + 1L))
      }
      sd_diff <- sqrt(variance_diff)
      sd_derivation[[i]] <- "sqrt(sd_condition_1^2+sd_condition_2^2-2*r*sd_condition_1*sd_condition_2)"
      correlations_used[[i]] <- sprintf("paired=%s(%s)", format(corr$value, digits = 15), corr$status)
      assumed_correlation[[i]] <- corr$status == "assumed"
      calculation_method[[i]] <- paste0("complex:", design, ":derived_from_conditions")
    }
    yi[[i]] <- mean_diff
    vi[[i]] <- sd_diff^2 / n_pairs
    measure[[i]] <- "MD"
    analysis_scale[[i]] <- "identity"
    display_transform[[i]] <- display_transform_for("identity")
    complex_effect_route[[i]] <- design
    design_formula[[i]] <- "MD=mean(condition_1-condition_2); vi=SD(condition_1-condition_2)^2/n_pairs"
    uncertainty_route[[i]] <- "sampling_variance_from_sd_difference_and_n_pairs"
    cluster_adjustment_audit[[i]] <- "not_applicable"
    effective_sample_size_audit[[i]] <- "not_used"
    effect_orientation[[i]] <- "condition_1_minus_condition_2"
  } else if (design %in% c("two_group_change_md", "baci_additive_md")) {
    require_blank(i, c(paired_fields, cluster_fields), design)
    if (effect_measure != "MD" || reported_scale != "identity" || target_scale != "identity") {
      abort(sprintf("%s requires effect_measure=MD and identity reported/analysis scales at physical CSV row %d.",
                    design, i + 1L))
    }
    if (tolower(text_at(i, "contrast_definition", required = TRUE)) != "intervention_minus_comparator") {
      abort(sprintf("%s requires contrast_definition=intervention_minus_comparator at physical CSV row %d.",
                    design, i + 1L))
    }
    if (tolower(text_at(i, "change_definition", required = TRUE)) != "post_minus_pre") {
      abort(sprintf("%s requires change_definition=post_minus_pre at physical CSV row %d.", design, i + 1L))
    }
    if (tolower(text_at(i, "group_independence", required = TRUE)) != "yes") {
      abort(sprintf("%s requires independent intervention/impact and comparator/control groups at physical CSV row %d.",
                    design, i + 1L))
    }
    text_at(i, "independence_basis", required = TRUE)
    n_intervention <- integer_at(i, "n_intervention", required = TRUE, minimum = 2)
    n_comparator <- integer_at(i, "n_comparator", required = TRUE, minimum = 2)
    mean_change_intervention <- number_at(i, "mean_change_intervention", required = TRUE)
    mean_change_comparator <- number_at(i, "mean_change_comparator", required = TRUE)
    intervention <- change_sd(
      i, "intervention", "intervention_sd_pathway", "sd_change_intervention",
      "sd_pre_intervention", "sd_post_intervention", "pre_post_correlation_intervention",
      "intervention_correlation_status"
    )
    comparator <- change_sd(
      i, "comparator", "comparator_sd_pathway", "sd_change_comparator",
      "sd_pre_comparator", "sd_post_comparator", "pre_post_correlation_comparator",
      "comparator_correlation_status"
    )
    used_corrs <- list(intervention$corr, comparator$corr)
    used_corrs <- used_corrs[vapply(used_corrs, function(x) x$used, logical(1))]
    correlations_used[[i]] <- if (!length(used_corrs)) {
      "none"
    } else {
      paste(vapply(used_corrs, function(x) {
        sprintf("%s=%s(%s)", x$label, format(x$value, digits = 15), x$status)
      }, character(1)), collapse = ";")
    }
    assumed_correlation[[i]] <- any(vapply(used_corrs, function(x) x$status == "assumed", logical(1)))
    yi[[i]] <- mean_change_intervention - mean_change_comparator
    vi[[i]] <- intervention$sd^2 / n_intervention + comparator$sd^2 / n_comparator
    measure[[i]] <- "MD"
    analysis_scale[[i]] <- "identity"
    display_transform[[i]] <- display_transform_for("identity")
    complex_effect_route[[i]] <- design
    design_formula[[i]] <- "MD=(intervention_post-intervention_pre)-(comparator_post-comparator_pre); vi=SD_change_intervention^2/n_intervention+SD_change_comparator^2/n_comparator"
    sd_derivation[[i]] <- paste(intervention$audit, comparator$audit, sep = ";")
    uncertainty_route[[i]] <- "independent_group_change_score_sampling_variance"
    calculation_method[[i]] <- paste0("complex:", design, ":additive_change_contrast")
    cluster_adjustment_audit[[i]] <- "not_applicable"
    effective_sample_size_audit[[i]] <- "not_used"
    effect_orientation[[i]] <- "intervention_or_impact_minus_comparator_or_control"
  } else {
    require_blank(i, c(paired_fields, change_fields), design)
    if (tolower(text_at(i, "contrast_definition", required = TRUE)) != "reported_adjusted_effect") {
      abort(sprintf("cluster_adjusted_generic requires contrast_definition=reported_adjusted_effect at physical CSV row %d.", i + 1L))
    }
    if (tolower(text_at(i, "cluster_adjusted_estimate", required = TRUE)) != "yes") {
      abort(sprintf(
        "cluster_adjusted_generic requires an already reported design-adjusted estimate; effective sample size alone is forbidden at physical CSV row %d.",
        i + 1L
      ))
    }
    adjustment_method <- text_at(i, "cluster_adjustment_method", required = TRUE)
    adjustment_source <- text_at(i, "cluster_adjustment_source", required = TRUE)
    if (!is_blank(dat$assumption_set_id[[i]]) || !is_blank(dat$correlation_source[[i]])) {
      abort(sprintf(
        "cluster_adjusted_generic does not reconstruct effects from correlations; clear assumption_set_id/correlation_source at physical CSV row %d.",
        i + 1L
      ))
    }
    estimate <- number_at(i, "effect_estimate", required = TRUE)
    uncertainty <- tolower(text_at(i, "uncertainty_type", required = TRUE))
    uncertainty <- parse_choice(
      uncertainty, c("se", "vi", "ci"),
      sprintf("uncertainty_type at physical CSV row %d", i + 1L)
    )
    direct_scales <- VALID_ANALYSIS_SCALES
    if (reported_scale %in% direct_scales) {
      if (reported_scale != target_scale) {
        abort(sprintf(
          "Already analysis-scale cluster estimates require reported_value_scale=target_analysis_scale at physical CSV row %d.",
          i + 1L
        ))
      }
      transform <- identity
    } else if (reported_scale == "natural_ratio") {
      if (!(effect_measure %in% c("OR", "RR", "HR", "IRR", "ROM", "PETO")) || target_scale != "log") {
        abort(sprintf("natural_ratio requires a ratio effect_measure and target_analysis_scale=log at physical CSV row %d.", i + 1L))
      }
      if (uncertainty != "ci") {
        abort(sprintf("natural_ratio accepts only a complete CI; natural-scale SE/vi are not treated as log-scale uncertainty at physical CSV row %d.", i + 1L))
      }
      transform <- log
    } else if (reported_scale == "natural_correlation") {
      if (!(effect_measure %in% c("COR", "UCOR", "CORRELATION")) || target_scale != "fisher-z") {
        abort(sprintf("natural_correlation requires a correlation effect_measure and target_analysis_scale=fisher-z at physical CSV row %d.", i + 1L))
      }
      if (uncertainty != "ci") {
        abort(sprintf("natural_correlation accepts only a complete CI; natural-scale SE/vi are not treated as Fisher-z uncertainty at physical CSV row %d.", i + 1L))
      }
      transform <- atanh
    } else {
      abort(sprintf(
        "reported_value_scale must be an analysis scale, natural_ratio, or natural_correlation at physical CSV row %d.",
        i + 1L
      ))
    }
    if (!measure_scale_ok(effect_measure, target_scale)) {
      abort(sprintf(
        "effect_measure=%s is incompatible with target_analysis_scale=%s at physical CSV row %d.",
        effect_measure, target_scale, i + 1L
      ))
    }

    effect_scale <- tolower(text_at(i, "effect_scale", required = TRUE))
    expected_effect_scales <- if (reported_scale %in% c("natural_ratio", "natural_correlation")) {
      "natural"
    } else if (reported_scale == "log") {
      "log"
    } else {
      c("natural", "raw", "standardized")
    }
    if (!(effect_scale %in% expected_effect_scales)) {
      abort(sprintf(
        "effect_scale=%s contradicts reported_value_scale=%s at physical CSV row %d.",
        effect_scale, reported_scale, i + 1L
      ))
    }

    if (uncertainty == "se") {
      require_blank(i, c("variance", "ci_lower", "ci_upper", "ci_level", "ci_distribution", "ci_df"),
                    "cluster_adjusted_generic se pathway")
      sei_value <- number_at(i, "se", required = TRUE, lower = 0, lower_open = TRUE)
      yi_value <- estimate
      vi_value <- sei_value^2
      uncertainty_route[[i]] <- "reported_adjusted_se_on_analysis_scale"
    } else if (uncertainty == "vi") {
      require_blank(i, c("se", "ci_lower", "ci_upper", "ci_level", "ci_distribution", "ci_df"),
                    "cluster_adjusted_generic vi pathway")
      vi_value <- number_at(i, "variance", required = TRUE, lower = 0, lower_open = TRUE)
      yi_value <- estimate
      uncertainty_route[[i]] <- "reported_adjusted_variance_on_analysis_scale"
    } else {
      require_blank(i, c("se", "variance"), "cluster_adjusted_generic CI pathway")
      lower <- number_at(i, "ci_lower", required = TRUE)
      upper <- number_at(i, "ci_upper", required = TRUE)
      ci_level <- number_at(i, "ci_level", required = TRUE, lower = 0, upper = 1,
                            lower_open = TRUE, upper_open = TRUE)
      ci_distribution <- tolower(text_at(i, "ci_distribution", required = TRUE))
      ci_distribution <- parse_choice(
        ci_distribution, c("normal", "t"),
        sprintf("ci_distribution at physical CSV row %d", i + 1L)
      )
      if (reported_scale == "natural_ratio" && any(c(estimate, lower, upper) <= 0)) {
        abort(sprintf("Natural ratio estimate and CI bounds must be > 0 at physical CSV row %d.", i + 1L))
      }
      if (reported_scale == "natural_correlation" && any(abs(c(estimate, lower, upper)) >= 1)) {
        abort(sprintf("Natural correlation estimate and CI bounds must be strictly within (-1,1) at physical CSV row %d.", i + 1L))
      }
      yi_value <- transform(estimate)
      lower_analysis <- transform(lower)
      upper_analysis <- transform(upper)
      if (!all(is.finite(c(yi_value, lower_analysis, upper_analysis))) ||
          lower_analysis >= upper_analysis || yi_value <= lower_analysis || yi_value >= upper_analysis) {
        abort(sprintf("Transformed estimate must lie strictly inside its CI at physical CSV row %d.", i + 1L))
      }
      alpha <- 1 - ci_level
      if (ci_distribution == "normal") {
        require_blank(i, "ci_df", "normal CI pathway")
        critical <- qnorm(1 - alpha / 2)
      } else {
        df_value <- number_at(i, "ci_df", required = TRUE, lower = 0, lower_open = TRUE)
        critical <- qt(1 - alpha / 2, df = df_value)
      }
      asymmetry <- abs(yi_value - (lower_analysis + upper_analysis) / 2) /
        (upper_analysis - lower_analysis)
      if (asymmetry > 0.05 && !allow_asymmetric) {
        abort(sprintf(
          "CI is notably asymmetric on the analysis scale at physical CSV row %d. Confirm a compatible interval and use --allow-asymmetric-ci yes only if justified.",
          i + 1L
        ))
      }
      sei_value <- (upper_analysis - lower_analysis) / (2 * critical)
      vi_value <- sei_value^2
      uncertainty_route[[i]] <- paste0("reported_adjusted_ci:", ci_distribution)
    }

    effective_n <- number_at(i, "effective_sample_size", required = FALSE)
    if (!is.na(effective_n) && (effective_n <= 0 || abs(effective_n - round(effective_n)) > sqrt(.Machine$double.eps))) {
      abort(sprintf("effective_sample_size, when recorded, must be a positive integer at physical CSV row %d.", i + 1L))
    }
    yi[[i]] <- yi_value
    vi[[i]] <- vi_value
    measure[[i]] <- "GEN"
    analysis_scale[[i]] <- target_scale
    display_transform[[i]] <- display_transform_for(target_scale)
    complex_effect_route[[i]] <- design
    design_formula[[i]] <- "yi=reported design-adjusted estimate on target analysis scale; vi=reported vi, reported SE^2, or CI-derived SE^2"
    sd_derivation[[i]] <- "not_applicable"
    correlations_used[[i]] <- "none"
    uncertainty_route[[i]] <- uncertainty_route[[i]]
    calculation_method[[i]] <- paste0("complex:cluster_adjusted_generic:", reported_scale, ":", uncertainty)
    cluster_adjustment_audit[[i]] <- paste0("method=", adjustment_method, ";source=", adjustment_source)
    effective_sample_size_audit[[i]] <- if (is.na(effective_n)) {
      "not_recorded;not_used"
    } else {
      paste0("recorded=", format(effective_n, scientific = FALSE, trim = TRUE), ";not_used")
    }
    effect_orientation[[i]] <- "reported_adjusted_effect"
  }

  if (!is.finite(yi[[i]]) || !is.finite(vi[[i]]) || vi[[i]] <= 0) {
    abort(sprintf("Final yi/vi must be finite and vi > 0 at physical CSV row %d.", i + 1L))
  }

  if (assumed_correlation[[i]]) {
    assumption_audit[[i]] <- paste0(
      "assumed_correlation;assumption_set_id=", text_at(i, "assumption_set_id", required = TRUE),
      ";correlation_source=", text_at(i, "correlation_source", required = TRUE)
    )
  } else if (correlations_used[[i]] != "none") {
    assumption_audit[[i]] <- paste0(
      "reported_correlation;correlation_source=", text_at(i, "correlation_source", required = TRUE)
    )
  } else {
    if (nzchar(text_at(i, "assumption_set_id", required = FALSE)) ||
        nzchar(text_at(i, "correlation_source", required = FALSE))) {
      abort(sprintf(
        "assumption_set_id/correlation_source are populated but no correlation is used at physical CSV row %d.",
        i + 1L
      ))
    }
    assumption_audit[[i]] <- "no_correlation_assumption"
  }
}

scales <- unique(analysis_scale)
if (length(scales) != 1L) {
  detail <- paste(vapply(scales, function(scale) {
    paste0(scale, "=rows ", paste(which(analysis_scale == scale) + 1L, collapse = ","))
  }, character(1)), collapse = "; ")
  abort(sprintf(
    "One analysis_effect CSV must use one analysis_scale; split this input before calculation. Found %s.",
    detail
  ))
}

source_file_md5 <- unname(tools::md5sum(input_path))
calculated_at_utc <- format(Sys.time(), format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
source_payload <- dat[, setdiff(names(dat), c("schema_version", "data_stage")), drop = FALSE]
result <- data.frame(
  schema_version = rep(ANALYSIS_EFFECT_SCHEMA_VERSION, n),
  data_stage = rep(ANALYSIS_EFFECT_DATA_STAGE, n),
  source_schema_version = as.character(dat$schema_version),
  source_data_stage = as.character(dat$data_stage),
  source_file = rep(input_path, n),
  source_file_md5 = rep(source_file_md5, n),
  source_row = seq_len(n) + 1L,
  calculation_method = calculation_method,
  calculator_version = rep(CALCULATOR_VERSION, n),
  calculated_at_utc = rep(calculated_at_utc, n),
  check.names = FALSE,
  stringsAsFactors = FALSE
)
result <- data.frame(result, source_payload, check.names = FALSE, stringsAsFactors = FALSE)
result$complex_effect_route <- complex_effect_route
result$design_formula <- design_formula
result$sd_derivation <- sd_derivation
result$correlations_used <- correlations_used
result$assumption_audit <- assumption_audit
result$uncertainty_route <- uncertainty_route
result$cluster_adjustment_audit <- cluster_adjustment_audit
result$effective_sample_size_audit <- effective_sample_size_audit
result$effect_orientation <- effect_orientation
result$yi <- yi
result$vi <- vi
result$sei <- sqrt(vi)
result$measure <- measure
result$analysis_scale <- analysis_scale
result$display_transform <- display_transform

manifest <- c(
  "complex_effect_size_calculation_manifest",
  sprintf("timestamp=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
  sprintf("input=%s", input_path),
  sprintf("input_md5=%s", source_file_md5),
  sprintf("source_schema_version=%s", RAW_SCHEMA_VERSION),
  sprintf("source_data_stage=%s", RAW_DATA_STAGE),
  sprintf("complex_effect_contract_version=%s", COMPLEX_EFFECT_CONTRACT_VERSION),
  sprintf("output=%s", output_path),
  sprintf("output_schema_version=%s", ANALYSIS_EFFECT_SCHEMA_VERSION),
  sprintf("output_data_stage=%s", ANALYSIS_EFFECT_DATA_STAGE),
  sprintf("calculator_version=%s", CALCULATOR_VERSION),
  sprintf("designs=%s", paste(sort(unique(complex_effect_route)), collapse = ",")),
  sprintf("analysis_scale=%s", scales[[1L]]),
  sprintf("rows_input=%d", n),
  sprintf("rows_output=%d", nrow(result)),
  sprintf("rows_with_assumed_correlation=%d", sum(assumed_correlation)),
  sprintf("allow_asymmetric_ci=%s", if (allow_asymmetric) "yes" else "no"),
  sprintf("R_version=%s", R.version.string),
  "command_options:",
  paste0("  --", names(opt), "=", unlist(opt, use.names = FALSE)),
  "guardrail=cluster_adjusted_generic never uses n_total or effective_sample_size in yi/vi.",
  "warning=Effect orientation, estimand compatibility, dependence, and model choice remain the analyst's responsibility."
)

write_csv <- function(x, path) {
  tryCatch(
    write.csv(x, path, row.names = FALSE, na = "", fileEncoding = "UTF-8"),
    error = function(e) abort(sprintf("Could not write '%s': %s", path, conditionMessage(e)))
  )
}

csv_tmp <- tempfile(pattern = ".complex-effects-", tmpdir = output_parent, fileext = ".csv")
manifest_tmp <- tempfile(pattern = ".complex-effects-", tmpdir = output_parent, fileext = ".manifest.txt")
.complex_cleanup_paths <- c(csv_tmp, manifest_tmp)
write_csv(result, csv_tmp)
tryCatch(
  writeLines(manifest, manifest_tmp, useBytes = TRUE),
  error = function(e) abort(sprintf("Could not write temporary manifest: %s", conditionMessage(e)))
)

if (overwrite) {
  for (path in prospective_outputs[file.exists(prospective_outputs)]) {
    status <- unlink(path, recursive = FALSE, force = FALSE)
    if (status != 0L) abort(sprintf("Could not replace script-owned output: %s", path))
  }
}
if (!file.rename(csv_tmp, output_path)) abort(sprintf("Could not atomically publish output: %s", output_path))
if (!file.rename(manifest_tmp, manifest_path)) {
  unlink(output_path, recursive = FALSE, force = FALSE)
  abort(sprintf("Could not atomically publish manifest: %s", manifest_path))
}
.complex_cleanup_paths <- character()

cat(sprintf("Wrote %d complex effect-size rows to %s\n", nrow(result), output_path))
cat(sprintf("Manifest: %s\n", manifest_path))
