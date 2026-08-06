#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(metafor)
  library(readxl)
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

shared_control_v <- function(group) {
  shared_variance <- group$mono_SD_I[[1L]]^2 /
    (group$mono_N_I[[1L]] * group$mono_I[[1L]]^2)
  result <- matrix(shared_variance, nrow = nrow(group), ncol = nrow(group))
  diag(result) <- group$vi_I
  result
}

coefficient_record <- function(model, coefficient) {
  index <- match(coefficient, rownames(model$b))
  if (is.na(index)) stop(paste0("missing coefficient: ", coefficient))
  list(
    estimate = unname(as.numeric(model$b[index, 1L])),
    se = unname(as.numeric(model$se[[index]])),
    ci_lower = unname(as.numeric(model$ci.lb[[index]])),
    ci_upper = unname(as.numeric(model$ci.ub[[index]]))
  )
}

fit_delta_nbe <- function(data) {
  model_data <- data[!is.na(data$del_yi_I), , drop = FALSE]
  model <- metafor::rma.mv(
    yi = del_yi_I,
    V = del_vi_I,
    mods = ~ size + age + richness,
    random = list(~1 | experiment / id),
    method = "REML",
    data = model_data
  )
  newmods <- matrix(c(
    mean(model_data$size),
    mean(model_data$age),
    mean(model_data$richness)
  ), nrow = 1L)
  marginal <- predict(model, newmods = newmods)
  list(
    marginal_estimate = unname(as.numeric(marginal$pred[[1L]])),
    ci_lower = unname(as.numeric(marginal$ci.lb[[1L]])),
    ci_upper = unname(as.numeric(marginal$ci.ub[[1L]])),
    k_effects = as.integer(model$k),
    n_experiments = as.integer(length(unique(model_data$experiment)))
  )
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
if (is.null(args$data) || is.null(args$output)) {
  stop("usage: cheng_2024.R --data data.xlsx --output result.json")
}

all_data <- as.data.frame(readxl::read_excel(args$data))

# Reproduce code.R lines 16-18 exactly: observations that share the same
# monoculture summary receive the same common-control identifier.
all_data$n2 <- all_data$mono_I^5 + all_data$mono_SD_I^5 + all_data$mono_N_I^2
all_data$common_id <- as.numeric(factor(
  all_data$n2,
  levels = unique(all_data$n2)
))

data <- all_data[all_data$invader_type == "all", , drop = FALSE]
sampling_v <- metafor::bldiag(lapply(
  split(data, data$common_id),
  shared_control_v
))
model_data <- data[!is.na(data$mono_I), , drop = FALSE]

# Targeted reproduction of the authors' main all-invader NBE model in
# code.R lines 40-49. This does not run the paper's complete figure suite.
model <- metafor::rma.mv(
  yi = yi_I,
  V = sampling_v,
  mods = ~ manipulation + size + age + richness,
  random = list(~1 | experiment / id),
  method = "REML",
  data = model_data
)
manipulation_test <- anova(model, btt = 2L)

coefficient_names <- rownames(model$b)
coefficients <- setNames(
  lapply(coefficient_names, function(name) coefficient_record(model, name)),
  coefficient_names
)

payload <- list(
  schema_version = "1.0",
  reproduction_id = "source_cheng_2024_main_nbe_all_invaders",
  analysis_scale = "log_response_ratio",
  comparison_direction = "resident_monoculture_over_mixture_for_invader_performance",
  source_counts = list(
    all_invader_observations = as.integer(nrow(data)),
    all_invader_experiments = as.integer(length(unique(data$experiment)))
  ),
  models = list(
    nbe_all = list(
      coefficients = coefficients,
      manipulation_test = list(
        qm = unname(as.numeric(manipulation_test$QM[[1L]])),
        df = unname(as.integer(manipulation_test$QMdf[[1L]])),
        p_value = unname(as.numeric(manipulation_test$QMp[[1L]]))
      ),
      sigma2_experiment = unname(as.numeric(model$sigma2[[1L]])),
      sigma2_observation = unname(as.numeric(model$sigma2[[2L]])),
      k_effects = as.integer(model$k),
      n_experiments = as.integer(length(unique(model_data$experiment)))
    ),
    delta_nbe_warming = fit_delta_nbe(data[data$warming == "1", , drop = FALSE]),
    delta_nbe_drought = fit_delta_nbe(data[data$drought == "1", , drop = FALSE])
  ),
  environment = list(
    R = as.character(getRversion()),
    metafor = as.character(packageVersion("metafor")),
    readxl = as.character(packageVersion("readxl")),
    jsonlite = as.character(packageVersion("jsonlite"))
  )
)

jsonlite::write_json(payload, args$output, auto_unbox = TRUE, pretty = TRUE, digits = NA)
