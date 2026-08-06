#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(metafor)
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

fit_diversity <- function(data, diversity_name) {
  subset <- data[data$diversity_index == diversity_name, , drop = FALSE]
  continuous <- subset[subset$patch_type == "continuous", c(
    "refshort", "diversity_value", "sd", "n_pairs"
  )]
  fragmented <- subset[subset$patch_type == "fragmented", c(
    "refshort", "diversity_value", "sd", "n_pairs"
  )]
  names(continuous)[-1L] <- paste0("continuous_", names(continuous)[-1L])
  names(fragmented)[-1L] <- paste0("fragmented_", names(fragmented)[-1L])
  wide <- merge(continuous, fragmented, by = "refshort", all = FALSE, sort = TRUE)
  effects <- metafor::escalc(
    measure = "ROM",
    m1i = continuous_diversity_value,
    m2i = fragmented_diversity_value,
    sd1i = continuous_sd,
    sd2i = fragmented_sd,
    n1i = continuous_n_pairs,
    n2i = fragmented_n_pairs,
    data = wide
  )
  model <- metafor::rma.uni(yi, vi, data = effects, method = "REML")
  prediction <- predict(model)
  list(
    estimate = unname(as.numeric(model$b[[1L]])),
    se = unname(as.numeric(model$se[[1L]])),
    ci_lower = unname(as.numeric(model$ci.lb[[1L]])),
    ci_upper = unname(as.numeric(model$ci.ub[[1L]])),
    pi_lower = unname(as.numeric(prediction$pi.lb[[1L]])),
    pi_upper = unname(as.numeric(prediction$pi.ub[[1L]])),
    tau2 = unname(as.numeric(model$tau2)),
    k_studies = as.integer(model$k)
  )
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
if (is.null(args$data) || is.null(args$output)) {
  stop("usage: goncalves_2025.R --data diversity_of_2.csv --output result.json")
}

data <- read.csv(args$data, stringsAsFactors = FALSE, check.names = FALSE)
models <- list(
  alpha_all_pairs = fit_diversity(data, "alpha"),
  beta_all_pairs = fit_diversity(data, "beta"),
  gamma_all_pairs = fit_diversity(data, "gamma")
)

payload <- list(
  schema_version = "1.0",
  reproduction_id = "source_goncalves_2025_overall_lrr",
  analysis_scale = "log",
  comparison_direction = "continuous_over_fragmented",
  models = models,
  environment = list(
    R = as.character(getRversion()),
    metafor = as.character(packageVersion("metafor")),
    jsonlite = as.character(packageVersion("jsonlite"))
  )
)

jsonlite::write_json(payload, args$output, auto_unbox = TRUE, pretty = TRUE, digits = NA)

