#!/usr/bin/env python3
"""Validate an ecology/biodiversity estimand contract before specialist routing."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
ROOT_FIELDS = {
    "schema_version", "contract_id", "route_type", "outcome",
    "scale_and_completeness", "dependence", "multifunctionality",
    "factorial_interaction", "recovery", "provenance",
}
OUTCOME_FIELDS = {
    "outcome_id", "name", "estimand", "zero_effect", "direction", "unit",
    "diversity_component", "diversity_dimension", "measure_family",
    "metric_name", "hill_q", "input_data_type", "reported_form",
    "analysis_form", "entropy_log_base", "observed_or_estimated",
    "composition_type",
}
SCALE_FIELDS = {
    "grain_area", "grain_unit", "spatial_extent", "extent_unit",
    "n_sampling_units", "sampling_effort_definition", "standardization_method",
    "observed_coverage", "target_coverage", "species_density_or_total_richness",
}
DEPENDENCE_FIELDS = {
    "independent_unit", "dependency_sources", "sampling_covariance_status",
    "sampling_v_path", "true_effect_structure", "coefficient_inference",
    "prediction_target",
}
MULTIFUNCTION_FIELDS = {
    "applicable", "function_registry_path", "construction", "hill_q",
    "thresholds", "weights_declared", "function_set_sensitivity",
}
INTERACTION_FIELDS = {
    "applicable", "interaction_scale", "cell_order", "contrast_coefficients",
    "cell_statistics_path", "cell_covariance_status", "cell_covariance_path",
    "nonlinearity_and_confounding_check",
}
RECOVERY_FIELDS = {
    "applicable", "comparator_type", "reference_model_source",
    "target_dimensions", "n_timepoints", "time_covariance_status",
    "persistence_window",
}
PROVENANCE_FIELDS = {
    "source_locator", "formula_or_code_path", "assumption_set_id", "reviewer",
    "verification_status",
}

ROUTES = {
    "alpha_diversity", "gamma_diversity", "beta_diversity",
    "community_composition", "multidimensional_biodiversity", "variability",
    "multifunctionality", "factorial_interaction", "longitudinal_recovery",
    "restoration_comparison", "genetic_diversity_change",
}
DIVERSITY_COMPONENTS = {"alpha", "beta", "gamma", "composition", "not_applicable"}
DIVERSITY_DIMENSIONS = {"taxonomic", "phylogenetic", "functional", "genetic", "not_applicable"}
MEASURE_FAMILIES = {
    "richness", "effective_diversity", "evenness", "dissimilarity", "turnover",
    "nestedness", "homogeneity", "composition_shift", "genetic_diversity",
    "variability", "multifunctionality", "interaction", "recovery",
}
INPUT_TYPES = {
    "abundance", "incidence", "summary_statistic", "distance_matrix",
    "factorial_cells", "time_series", "function_matrix",
}
FORMS = {"richness", "entropy", "effective_diversity", "index", "distance", "other"}
COMPOSITION_TYPES = {
    "not_applicable", "bray_curtis", "jaccard", "turnover", "nestedness",
    "homogeneity", "composition_shift", "other",
}
COVARIANCE_STATUSES = {
    "not_needed_verified", "provided_validated", "derived_exact",
    "derived_delta_method", "assumed_sensitivity", "unavailable",
}
STANDARDIZATION = {"none", "coverage", "rarefaction", "asymptotic_estimation", "model_based"}
RECOVERY_DIMENSIONS = {
    "resistance", "initial_response", "return_rate", "distance_to_reference",
    "completeness", "persistence",
}


class DuplicateKeyError(ValueError):
    pass


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def load(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=no_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite number {value}")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"could not read valid UTF-8 JSON: {exc}") from exc


def validate(payload: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    def issue(field: str, message: str, code: str = "invalid") -> None:
        issues.append({"code": code, "field": field, "message": message})

    def exact_object(value: Any, field: str, expected: set[str]) -> Mapping[str, Any] | None:
        if not isinstance(value, dict):
            issue(field, "must be an object", "wrong_type")
            return None
        for name in sorted(expected - set(value)):
            issue(f"{field}.{name}" if field else name, "is required", "missing_field")
        for name in sorted(set(value) - expected):
            issue(f"{field}.{name}" if field else name, "is not allowed", "unexpected_field")
        return value

    def nonempty(value: Any, field: str, *, nullable: bool = False) -> str | None:
        if nullable and value is None:
            return None
        if not isinstance(value, str) or not value.strip() or value.startswith("REPLACE_WITH_"):
            issue(field, "must be a completed non-empty string", "missing_value")
            return None
        return value.strip()

    def enum(value: Any, field: str, allowed: set[str], *, nullable: bool = False) -> str | None:
        if nullable and value is None:
            return None
        if not isinstance(value, str) or value not in allowed:
            issue(field, "must be one of: " + ", ".join(sorted(allowed)), "unsupported_value")
            return None
        return value

    def number(value: Any, field: str, *, positive: bool = False, nullable: bool = False) -> float | None:
        if nullable and value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            issue(field, "must be a finite number", "wrong_type")
            return None
        if positive and value <= 0:
            issue(field, "must be greater than zero", "out_of_range")
        return float(value)

    root = exact_object(payload, "", ROOT_FIELDS)
    if root is None:
        return issues
    if root.get("schema_version") != SCHEMA_VERSION:
        issue("schema_version", f"must equal {SCHEMA_VERSION!r}", "unsupported_value")
    nonempty(root.get("contract_id"), "contract_id")
    route = enum(root.get("route_type"), "route_type", ROUTES)

    outcome = exact_object(root.get("outcome"), "outcome", OUTCOME_FIELDS)
    scale = exact_object(root.get("scale_and_completeness"), "scale_and_completeness", SCALE_FIELDS)
    dependence = exact_object(root.get("dependence"), "dependence", DEPENDENCE_FIELDS)
    multifunction = exact_object(root.get("multifunctionality"), "multifunctionality", MULTIFUNCTION_FIELDS)
    interaction = exact_object(root.get("factorial_interaction"), "factorial_interaction", INTERACTION_FIELDS)
    recovery = exact_object(root.get("recovery"), "recovery", RECOVERY_FIELDS)
    provenance = exact_object(root.get("provenance"), "provenance", PROVENANCE_FIELDS)

    if outcome is not None:
        for key in ("outcome_id", "name", "estimand", "zero_effect", "direction", "unit", "metric_name"):
            nonempty(outcome.get(key), f"outcome.{key}")
        component = enum(outcome.get("diversity_component"), "outcome.diversity_component", DIVERSITY_COMPONENTS)
        dimension = enum(outcome.get("diversity_dimension"), "outcome.diversity_dimension", DIVERSITY_DIMENSIONS)
        family = enum(outcome.get("measure_family"), "outcome.measure_family", MEASURE_FAMILIES)
        enum(outcome.get("input_data_type"), "outcome.input_data_type", INPUT_TYPES)
        reported_form = enum(outcome.get("reported_form"), "outcome.reported_form", FORMS)
        analysis_form = enum(outcome.get("analysis_form"), "outcome.analysis_form", FORMS)
        enum(outcome.get("observed_or_estimated"), "outcome.observed_or_estimated", {"observed", "estimated", "not_applicable"})
        composition_type = enum(outcome.get("composition_type"), "outcome.composition_type", COMPOSITION_TYPES)
        q = number(outcome.get("hill_q"), "outcome.hill_q", nullable=True)
        if q is not None and q < 0:
            issue("outcome.hill_q", "must be zero or greater", "out_of_range")
        if family == "effective_diversity" and q is None:
            issue("outcome.hill_q", "is required for effective diversity", "missing_value")
        entropy_base = number(outcome.get("entropy_log_base"), "outcome.entropy_log_base", nullable=True)
        if reported_form == "entropy" and analysis_form == "effective_diversity":
            if entropy_base is None:
                issue("outcome.entropy_log_base", "is required when entropy is converted to effective diversity", "missing_value")
            elif entropy_base <= 0 or entropy_base == 1:
                issue("outcome.entropy_log_base", "must be positive and not equal to one", "out_of_range")
        if route in {"alpha_diversity", "gamma_diversity", "beta_diversity", "community_composition", "multidimensional_biodiversity"}:
            if component == "not_applicable" or dimension == "not_applicable":
                issue("outcome", "biodiversity routes require component and dimension identities", "missing_value")
        if route == "community_composition":
            if component != "composition":
                issue("outcome.diversity_component", "must be 'composition' for community_composition", "contradiction")
            if composition_type in {None, "not_applicable"}:
                issue("outcome.composition_type", "must identify the composition metric family", "missing_value")

    if scale is not None:
        spatial_route = route in {"alpha_diversity", "gamma_diversity", "beta_diversity", "community_composition", "multidimensional_biodiversity"}
        grain = number(scale.get("grain_area"), "scale_and_completeness.grain_area", positive=True, nullable=not spatial_route)
        extent = number(scale.get("spatial_extent"), "scale_and_completeness.spatial_extent", positive=True, nullable=not spatial_route)
        if spatial_route:
            nonempty(scale.get("grain_unit"), "scale_and_completeness.grain_unit")
            nonempty(scale.get("extent_unit"), "scale_and_completeness.extent_unit")
            n_units = number(scale.get("n_sampling_units"), "scale_and_completeness.n_sampling_units", positive=True)
            if n_units is not None and not n_units.is_integer():
                issue("scale_and_completeness.n_sampling_units", "must be an integer", "wrong_type")
            nonempty(scale.get("sampling_effort_definition"), "scale_and_completeness.sampling_effort_definition")
        method = enum(scale.get("standardization_method"), "scale_and_completeness.standardization_method", STANDARDIZATION)
        for key in ("observed_coverage", "target_coverage"):
            value = number(scale.get(key), f"scale_and_completeness.{key}", nullable=True)
            if value is not None and not (0 < value <= 1):
                issue(f"scale_and_completeness.{key}", "must be in (0, 1]", "out_of_range")
        if method == "coverage" and scale.get("target_coverage") is None:
            issue("scale_and_completeness.target_coverage", "is required for coverage standardization", "missing_value")
        enum(scale.get("species_density_or_total_richness"), "scale_and_completeness.species_density_or_total_richness", {"species_density", "total_richness", "not_applicable"})
        if grain is not None and extent is not None and scale.get("grain_unit") == scale.get("extent_unit") and extent < grain:
            issue("scale_and_completeness.spatial_extent", "cannot be smaller than grain when units match", "contradiction")

    if dependence is not None:
        nonempty(dependence.get("independent_unit"), "dependence.independent_unit")
        sources = dependence.get("dependency_sources")
        if not isinstance(sources, list) or any(not isinstance(x, str) or not x.strip() for x in sources):
            issue("dependence.dependency_sources", "must be an array of non-empty strings", "wrong_type")
            sources = []
        status = enum(dependence.get("sampling_covariance_status"), "dependence.sampling_covariance_status", COVARIANCE_STATUSES)
        v_path = nonempty(dependence.get("sampling_v_path"), "dependence.sampling_v_path", nullable=True)
        if sources and status == "not_needed_verified":
            issue("dependence.sampling_covariance_status", "cannot be not_needed_verified when dependencies are declared", "contradiction")
        if status in {"provided_validated", "derived_exact", "derived_delta_method", "assumed_sensitivity"} and v_path is None:
            issue("dependence.sampling_v_path", "is required for the declared covariance status", "missing_value")
        structures = dependence.get("true_effect_structure")
        if not isinstance(structures, list) or not structures or any(not isinstance(x, str) or not x.strip() for x in structures):
            issue("dependence.true_effect_structure", "must be a non-empty array", "missing_value")
        nonempty(dependence.get("coefficient_inference"), "dependence.coefficient_inference")
        nonempty(dependence.get("prediction_target"), "dependence.prediction_target")

    if multifunction is not None:
        applicable = multifunction.get("applicable")
        if type(applicable) is not bool:
            issue("multifunctionality.applicable", "must be boolean", "wrong_type")
        if route == "multifunctionality" and applicable is not True:
            issue("multifunctionality.applicable", "must be true for this route", "contradiction")
        if applicable is True:
            nonempty(multifunction.get("function_registry_path"), "multifunctionality.function_registry_path")
            construction = enum(multifunction.get("construction"), "multifunctionality.construction", {"mean", "single_threshold", "multi_threshold", "hill_number", "multivariate"})
            q = number(multifunction.get("hill_q"), "multifunctionality.hill_q", nullable=True)
            if construction == "hill_number" and (q is None or q < 0):
                issue("multifunctionality.hill_q", "must be zero or greater for hill_number", "missing_value")
            thresholds = multifunction.get("thresholds")
            if not isinstance(thresholds, list) or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in thresholds):
                issue("multifunctionality.thresholds", "must be an array of numbers", "wrong_type")
            elif construction in {"single_threshold", "multi_threshold"} and not thresholds:
                issue("multifunctionality.thresholds", "cannot be empty for a threshold construction", "missing_value")
            for key in ("weights_declared", "function_set_sensitivity"):
                if type(multifunction.get(key)) is not bool:
                    issue(f"multifunctionality.{key}", "must be boolean", "wrong_type")

    if interaction is not None:
        applicable = interaction.get("applicable")
        if type(applicable) is not bool:
            issue("factorial_interaction.applicable", "must be boolean", "wrong_type")
        if route == "factorial_interaction" and applicable is not True:
            issue("factorial_interaction.applicable", "must be true for this route", "contradiction")
        if applicable is True:
            enum(interaction.get("interaction_scale"), "factorial_interaction.interaction_scale", {"additive", "multiplicative_log"})
            if interaction.get("cell_order") != ["Y00", "Y10", "Y01", "Y11"]:
                issue("factorial_interaction.cell_order", "must equal [Y00, Y10, Y01, Y11]", "unsupported_value")
            if interaction.get("contrast_coefficients") != [1, -1, -1, 1]:
                issue("factorial_interaction.contrast_coefficients", "must equal [1, -1, -1, 1] for the declared cell order", "unsupported_value")
            nonempty(interaction.get("cell_statistics_path"), "factorial_interaction.cell_statistics_path")
            cell_status = enum(interaction.get("cell_covariance_status"), "factorial_interaction.cell_covariance_status", COVARIANCE_STATUSES)
            cell_path = nonempty(interaction.get("cell_covariance_path"), "factorial_interaction.cell_covariance_path", nullable=True)
            if cell_status in {"provided_validated", "derived_exact", "derived_delta_method", "assumed_sensitivity"} and cell_path is None:
                issue("factorial_interaction.cell_covariance_path", "is required for the declared covariance status", "missing_value")
            nonempty(interaction.get("nonlinearity_and_confounding_check"), "factorial_interaction.nonlinearity_and_confounding_check")

    if recovery is not None:
        applicable = recovery.get("applicable")
        if type(applicable) is not bool:
            issue("recovery.applicable", "must be boolean", "wrong_type")
        if route in {"longitudinal_recovery", "restoration_comparison"} and applicable is not True:
            issue("recovery.applicable", "must be true for this route", "contradiction")
        if applicable is True:
            comparator = enum(recovery.get("comparator_type"), "recovery.comparator_type", {"degraded", "reference", "baseline"})
            reference = nonempty(recovery.get("reference_model_source"), "recovery.reference_model_source", nullable=True)
            dimensions = recovery.get("target_dimensions")
            if not isinstance(dimensions, list) or not dimensions or any(x not in RECOVERY_DIMENSIONS for x in dimensions):
                issue("recovery.target_dimensions", "must be a non-empty array of supported recovery dimensions", "unsupported_value")
                dimensions = []
            if (comparator == "reference" or "completeness" in dimensions or "distance_to_reference" in dimensions) and reference is None:
                issue("recovery.reference_model_source", "is required for reference-based recovery", "missing_value")
            n_timepoints = number(recovery.get("n_timepoints"), "recovery.n_timepoints", positive=True)
            if n_timepoints is not None and not n_timepoints.is_integer():
                issue("recovery.n_timepoints", "must be an integer", "wrong_type")
            if any(x in dimensions for x in ("return_rate", "persistence")) and (n_timepoints is None or n_timepoints < 2):
                issue("recovery.n_timepoints", "must be at least two for rate or persistence", "out_of_range")
            enum(recovery.get("time_covariance_status"), "recovery.time_covariance_status", COVARIANCE_STATUSES)
            if "persistence" in dimensions:
                nonempty(recovery.get("persistence_window"), "recovery.persistence_window")

    if provenance is not None:
        for key in ("source_locator", "formula_or_code_path", "assumption_set_id", "reviewer"):
            nonempty(provenance.get(key), f"provenance.{key}")
        enum(provenance.get("verification_status"), "provenance.verification_status", {"draft", "verified", "adjudicated"})
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    try:
        payload = load(args.contract)
    except RuntimeError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    issues = validate(payload)
    result = {
        "valid": not issues,
        "schema_version": SCHEMA_VERSION,
        "contract_id": payload.get("contract_id") if isinstance(payload, dict) else None,
        "route_type": payload.get("route_type") if isinstance(payload, dict) else None,
        "issues": issues,
    }
    stream = sys.stdout if not issues else sys.stderr
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), file=stream)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
