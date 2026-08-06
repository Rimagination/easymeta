#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(emmeans)
  library(glmmTMB)
  library(jsonlite)
})

parse_args <- function(args) {
  result <- list()
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (!startsWith(key, "--") || i == length(args)) {
      stop("arguments must use --key value pairs")
    }
    result[[substring(key, 3L)]] <- args[[i + 1L]]
    i <- i + 2L
  }
  result
}

fit_global_intercept <- function(data, outcome) {
  keep <- !is.na(data[[outcome]])
  model_data <- data[keep, , drop = FALSE]
  model_formula <- stats::as.formula(paste0(
    outcome,
    " ~ 1 + (1 | Article_ID) + (1 | `Study type`)"
  ))

  # Targeted reproduction of PBL_stats.R lines 34-60. The authors fit an
  # unweighted Gaussian mixed model for each log-response-ratio outcome.
  model <- glmmTMB::glmmTMB(
    model_formula,
    data = model_data,
    family = gaussian()
  )
  interval <- as.data.frame(stats::confint(
    emmeans::emmeans(model, ~ 1),
    level = 0.95
  ))
  lower_name <- grep("LCL$", names(interval), value = TRUE)
  upper_name <- grep("UCL$", names(interval), value = TRUE)
  if (length(lower_name) != 1L || length(upper_name) != 1L) {
    stop(paste0("could not identify confidence limits for ", outcome))
  }

  list(
    estimate = unname(as.numeric(interval$emmean[[1L]])),
    se = unname(as.numeric(interval$SE[[1L]])),
    ci_lower = unname(as.numeric(interval[[lower_name]][[1L]])),
    ci_upper = unname(as.numeric(interval[[upper_name]][[1L]])),
    n_comparisons = as.integer(stats::nobs(model)),
    n_articles = as.integer(length(unique(model_data$Article_ID))),
    n_study_types = as.integer(length(unique(model_data[["Study type"]]))),
    convergence_code = as.integer(model$fit$convergence),
    positive_definite_hessian = isTRUE(model$sdr$pdHess)
  )
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
if (is.null(args$data) || is.null(args$output)) {
  stop("usage: keck_2025.R --data data.json --output result.json")
}

data <- as.data.frame(jsonlite::read_json(args$data, simplifyVector = TRUE))

payload <- list(
  schema_version = "1.0",
  reproduction_id = "source_keck_2025_global_biodiversity_intercepts",
  analysis_scale = "log_response_ratio",
  weighting = "unweighted_gaussian_mixed_model",
  source_counts = list(
    comparisons = as.integer(nrow(data)),
    articles = as.integer(length(unique(data$Article_ID))),
    reference_sites = as.integer(sum(data$n_reference, na.rm = TRUE)),
    impacted_sites = as.integer(sum(data$n_impacted, na.rm = TRUE))
  ),
  models = list(
    homogeneity = fit_global_intercept(data, "beta_similarity"),
    composition_shift = fit_global_intercept(data, "beta_structure"),
    local_diversity = fit_global_intercept(data, "alpha_diversity")
  ),
  environment = list(
    R = as.character(getRversion()),
    glmmTMB = as.character(packageVersion("glmmTMB")),
    emmeans = as.character(packageVersion("emmeans")),
    jsonlite = as.character(packageVersion("jsonlite"))
  )
)

jsonlite::write_json(
  payload,
  args$output,
  auto_unbox = TRUE,
  pretty = TRUE,
  digits = NA
)
