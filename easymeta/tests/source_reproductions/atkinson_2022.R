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

make_vcv <- function(data, variance_col, cluster_col, rho = 0.5) {
  variances <- as.numeric(data[[variance_col]])
  if (any(!is.finite(variances)) || any(variances <= 0)) {
    stop(paste0("invalid sampling variances in ", variance_col))
  }
  result <- diag(variances)
  groups <- split(seq_len(nrow(data)), data[[cluster_col]], drop = TRUE)
  for (indices in groups) {
    if (length(indices) < 2L) next
    pairs <- utils::combn(indices, 2L)
    for (column in seq_len(ncol(pairs))) {
      first <- pairs[1L, column]
      second <- pairs[2L, column]
      covariance <- rho * sqrt(variances[[first]] * variances[[second]])
      result[first, second] <- covariance
      result[second, first] <- covariance
    }
  }
  result
}

effect_pair <- function(data, mean_2, sd_2, n_2) {
  common <- list(
    n1i = as.numeric(data$t_quad_n),
    n2i = as.numeric(data[[n_2]]),
    m1i = as.numeric(data$t_mean),
    m2i = as.numeric(data[[mean_2]]),
    sd1i = as.numeric(data$t_sd),
    sd2i = as.numeric(data[[sd_2]])
  )
  rom <- do.call(metafor::escalc, c(list(measure = "ROM"), common))
  vr <- do.call(metafor::escalc, c(list(measure = "VR"), common))
  cvr <- do.call(metafor::escalc, c(list(measure = "CVR"), common))
  data$yi_mean <- rom$yi
  data$vi_mean <- rom$vi
  data$yi_vr <- vr$yi
  data$vi_vr <- vr$vi
  data$yi_cvr <- cvr$yi
  data$vi_cvr <- cvr$vi
  data
}

fit_model <- function(data, outcome, covariance) {
  model <- metafor::rma.mv(
    yi = data[[paste0("yi_", outcome)]],
    V = covariance,
    random = list(~1 | id, ~1 | plot_id, ~1 | unit),
    method = "REML",
    data = data
  )
  prediction <- predict(model)
  list(
    estimate = unname(as.numeric(model$b[[1L]])),
    se = unname(as.numeric(model$se[[1L]])),
    ci_lower = unname(as.numeric(model$ci.lb[[1L]])),
    ci_upper = unname(as.numeric(model$ci.ub[[1L]])),
    pi_lower = unname(as.numeric(prediction$pi.lb[[1L]])),
    pi_upper = unname(as.numeric(prediction$pi.ub[[1L]])),
    k_effects = as.integer(model$k),
    n_studies = as.integer(length(unique(data$id)))
  )
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
if (is.null(args$data) || is.null(args$output)) {
  stop("usage: atkinson_2022.R --data variation_data.csv --output result.json")
}

raw <- read.csv(args$data, stringsAsFactors = FALSE, check.names = FALSE)

unrestored <- raw[!is.na(raw$c_mean), , drop = FALSE]
unrestored <- effect_pair(unrestored, "c_mean", "c_sd", "c_quad_n")
unrestored <- unrestored[!is.na(unrestored$vi_vr), , drop = FALSE]
unrestored$unit <- factor(seq_len(nrow(unrestored)))

reference <- raw[!is.na(raw$r_mean) & !is.na(raw$r_sd) & raw$r_sd != 0, , drop = FALSE]
reference$r_quad_n <- as.numeric(reference$r_quad_n)
reference <- reference[reference$r_quad_n > 1, , drop = FALSE]
reference$ref_shared_ctrl <- interaction(
  reference$id,
  reference$r_mean,
  reference$r_sd,
  drop = TRUE,
  lex.order = TRUE
)
reference <- effect_pair(reference, "r_mean", "r_sd", "r_quad_n")
reference$unit <- factor(seq_len(nrow(reference)))

models <- list()
for (outcome in c("cvr", "vr", "mean")) {
  models[[paste0(outcome, "_unrestored")]] <- fit_model(
    unrestored,
    outcome,
    make_vcv(unrestored, paste0("vi_", outcome), "shared_ctrl", rho = 0.5)
  )
  models[[paste0(outcome, "_reference")]] <- fit_model(
    reference,
    outcome,
    make_vcv(reference, paste0("vi_", outcome), "ref_shared_ctrl", rho = 0.5)
  )
}

payload <- list(
  schema_version = "1.0",
  reproduction_id = "source_atkinson_2022_table_s1",
  analysis_scale = "log",
  comparison_direction = "restored_over_comparator",
  assumed_within_shared_control_rho = 0.5,
  models = models,
  environment = list(
    R = as.character(getRversion()),
    metafor = as.character(packageVersion("metafor")),
    jsonlite = as.character(packageVersion("jsonlite"))
  )
)

jsonlite::write_json(payload, args$output, auto_unbox = TRUE, pretty = TRUE, digits = NA)

