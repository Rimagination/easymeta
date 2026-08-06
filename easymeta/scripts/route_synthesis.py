#!/usr/bin/env python3
"""Deterministically route an evidence-synthesis plan from strict JSON input.

Usage:
    python route_synthesis.py [INPUT.json|-] [--reference-receipt FILE]
        [--output FILE] [--overwrite yes|no] [--pretty]

If INPUT is omitted or is ``-``, JSON is read from standard input. The output
includes the synthesis decision, deterministic reference requirements, a
canonical plan hash, and the P0-6 reference-gate result. ``runner_allowed`` is
false until a receipt bound to the same plan passes. Output is written to
stdout by default, or atomically as UTF-8 when ``--output`` is supplied.

Exit codes:
    0: a route was produced
    1: the JSON object is missing required input or is contradictory
    2: command usage, file I/O, encoding, or JSON parsing failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from reference_gate import (
    build_gate_result,
    load_json_file,
    load_reference_routes,
    resolve_requirements,
)


EXIT_OK = 0
EXIT_INVALID_INPUT = 1
EXIT_INPUT_ERROR = 2
SCHEMA_VERSION = "1.4"

ROUTES = {
    "aggregate_effect_meta",
    "dependent_effect_meta",
    "specialist_route",
    "no_pooling",
}

SPECIALIST_HANDOFFS = {
    "network": "network_meta_analysis_specialist",
    "diagnostic": "diagnostic_test_accuracy_specialist",
    "dose_response": "dose_response_meta_analysis_specialist",
    "ipd": "ipd_meta_analysis_specialist",
    "one_stage_longitudinal": "one_stage_longitudinal_model_specialist",
    "spatiotemporal": "spatiotemporal_model_specialist",
    "phylogenetic": "phylogenetic_meta_analysis_specialist",
    "raw_community_matrix": "community_ecology_raw_data_specialist",
    "community_composition": "community_composition_specialist",
    "multidimensional_biodiversity": "multivariate_biodiversity_specialist",
    "variability_effect": "variability_meta_analysis_specialist",
    "factorial_interaction": "factorial_interaction_meta_specialist",
    "ecosystem_multifunctionality": "ecosystem_multifunctionality_specialist",
    "derived_recovery_stability": "derived_recovery_stability_specialist",
    "second_order_meta": "second_order_evidence_synthesis_specialist",
    "custom_effect_model": "custom_effect_model_review",
    "life_cycle_assessment": "life_cycle_assessment_data_fusion_specialist",
    "latent_class_analysis": "latent_class_model_specialist",
}

ROOT_FIELDS = {"schema_version", "task", "pooling", "data", "specialist_triggers"}
TASK_FIELDS = {
    "product_type",
    "domain",
    "stage",
    "as_of_date",
    "decision_points",
    "audit_targets",
    "conversion_family",
    "topic_tags",
    "appraisal_tools",
    "certainty_frameworks",
}
POOLING_FIELDS = {"eligible", "ineligibility_reason"}
DATA_FIELDS = {
    "level",
    "effect_structure",
    "dependence_topology",
    "dependency_sources",
    "independent_cluster_count",
    "sampling_covariance_status",
    "sampling_v_path",
    "ecology_contract_path",
}
DATA_LEVELS = {"aggregate", "ipd", "raw_community_matrix", "meta_level"}
EFFECT_STRUCTURES = {"independent", "dependent"}
DEPENDENCE_TOPOLOGIES = {"independent", "nested", "one_way", "crossed", "mixed", "unknown"}
DEPENDENCY_SOURCES = {
    "shared_control",
    "repeated_measure",
    "multiple_outcomes",
    "multiple_treatments",
    "species_taxon",
    "spatial",
    "temporal",
    "other",
}
COVARIANCE_STATUSES = {
    "not_needed_verified",
    "provided_validated",
    "derived_exact",
    "derived_delta_method",
    "assumed_sensitivity",
    "unavailable",
}
ECOLOGY_CONTRACT_TRIGGERS = {
    "raw_community_matrix",
    "community_composition",
    "multidimensional_biodiversity",
    "variability_effect",
    "factorial_interaction",
    "ecosystem_multifunctionality",
    "derived_recovery_stability",
}
PRODUCT_TYPES = {
    "protocol",
    "systematic_review",
    "systematic_map",
    "scoping_review",
    "rapid_review",
    "umbrella_review",
    "quantitative_reanalysis",
    "audit",
    "manuscript_report",
}
DOMAINS = {
    "medical",
    "public_health",
    "ecology",
    "evolution",
    "conservation",
    "environmental_science",
    "general_science",
}
STAGES = {
    "planning",
    "search",
    "screening",
    "extraction",
    "appraisal",
    "analysis",
    "interpretation",
    "reporting",
    "audit",
}
DECISION_POINTS = {
    "evidence_synthesis_conduct",
    "question_protocol",
    "search_selection",
    "study_report_linkage",
    "extraction",
    "effect_size",
    "effect_conversion",
    "dependence",
    "synthesis_model",
    "few_studies",
    "small_study_effects",
    "risk_of_bias",
    "certainty",
    "reporting",
    "r_implementation",
    "lineage",
    "source_governance",
    "ai_assistance",
    "benchmark_audit",
    "source_reproduction",
    "review_update",
    "method_claim_audit",
}
AUDIT_TARGETS = {"conduct", "reporting", "effect_model", "software", "appraisal", "citation"}
CONVERSION_FAMILIES = {
    "unit_conversion",
    "ratio_log_transform",
    "correlation_bridge",
    "response_ratio_to_smd",
    "other",
}
TOPIC_TAGS = {"plant_ecology", "biodiversity", "community_ecology", "restoration"}
APPRAISAL_TOOLS = {"rob2", "robins_i", "robins_e", "quadas3", "jbi", "feat", "ceesat", "mates"}
CERTAINTY_FRAMEWORKS = {"grade", "cee_confidence"}


class DuplicateKeyError(ValueError):
    """Raised when an object contains a duplicate JSON member name."""


@dataclass(frozen=True)
class Issue:
    code: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Route a strict JSON synthesis plan without guessing missing decisions.",
        epilog=(
            "INPUT defaults to '-'. Use assets/synthesis_route_template.json as the "
            "complete schema template. Exit codes: 0=route, 1=invalid plan, "
            "2=usage/I/O/JSON error."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="UTF-8 JSON file, or '-' for standard input (default: '-')",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent output JSON; key ordering remains deterministic",
    )
    skill_root = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--reference-receipt",
        type=Path,
        help="P0-6 receipt to validate before allowing an executable route",
    )
    parser.add_argument(
        "--reference-routes",
        type=Path,
        default=skill_root / "assets" / "reference_routes.json",
        help="machine-readable reference-route registry",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Atomically write successful JSON as UTF-8 to this file",
    )
    parser.add_argument(
        "--overwrite",
        choices=("yes", "no"),
        default="no",
        help="Allow --output to replace an existing file (default: no)",
    )
    return parser


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"Duplicate JSON member: {key!r}")
        result[key] = value
    return result


def reject_nonfinite_number(value: str) -> None:
    raise ValueError(f"Non-finite JSON number is not allowed: {value}")


def load_json(input_name: str) -> Any:
    if input_name == "-":
        source = "standard input"
        try:
            raw = sys.stdin.buffer.read().decode("utf-8-sig")
        except UnicodeError as exc:
            raise RuntimeError(f"Could not decode {source} as UTF-8: {exc}") from exc
    else:
        path = Path(input_name)
        source = str(path)
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError(f"Could not read {source}: {exc}") from exc

    if not raw.strip():
        raise RuntimeError(f"No JSON input was provided by {source}.")

    try:
        return json.loads(
            raw,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite_number,
        )
    except (json.JSONDecodeError, DuplicateKeyError, ValueError) as exc:
        raise RuntimeError(f"Invalid JSON from {source}: {exc}") from exc


def add_shape_issues(
    value: Any,
    *,
    path: str,
    required_fields: set[str],
    issues: list[Issue],
) -> Mapping[str, Any] | None:
    if not isinstance(value, dict):
        issues.append(Issue("wrong_type", path, "must be a JSON object"))
        return None

    actual = set(value)
    for name in sorted(required_fields - actual):
        field = f"{path}.{name}" if path else name
        issues.append(Issue("missing_field", field, "is required"))
    for name in sorted(actual - required_fields):
        field = f"{path}.{name}" if path else name
        issues.append(
            Issue(
                "unexpected_field",
                field,
                f"is not allowed by schema {SCHEMA_VERSION}",
            )
        )
    return value


def validate_input(payload: Any) -> tuple[Mapping[str, Any] | None, list[Issue]]:
    issues: list[Issue] = []
    root = add_shape_issues(
        payload, path="", required_fields=ROOT_FIELDS, issues=issues
    )
    if root is None:
        return None, issues

    schema_version = root.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        issues.append(
            Issue(
                "unsupported_value",
                "schema_version",
                f"must equal {SCHEMA_VERSION!r}",
            )
        )

    task = add_shape_issues(
        root.get("task"), path="task", required_fields=TASK_FIELDS, issues=issues
    )
    pooling = add_shape_issues(
        root.get("pooling"),
        path="pooling",
        required_fields=POOLING_FIELDS,
        issues=issues,
    )
    data = add_shape_issues(
        root.get("data"), path="data", required_fields=DATA_FIELDS, issues=issues
    )
    triggers = add_shape_issues(
        root.get("specialist_triggers"),
        path="specialist_triggers",
        required_fields=set(SPECIALIST_HANDOFFS),
        issues=issues,
    )

    task_values: dict[str, Any] = {}
    if task is not None:
        scalar_fields = {
            "product_type": PRODUCT_TYPES,
            "domain": DOMAINS,
            "stage": STAGES,
        }
        for field, supported in scalar_fields.items():
            value = task.get(field)
            if not isinstance(value, str) or value not in supported:
                issues.append(
                    Issue(
                        "unsupported_value",
                        f"task.{field}",
                        "must be one of: " + ", ".join(sorted(supported)),
                    )
                )
            else:
                task_values[field] = value

        raw_as_of = task.get("as_of_date")
        if raw_as_of is not None:
            if not isinstance(raw_as_of, str):
                issues.append(Issue("wrong_type", "task.as_of_date", "must be an ISO date or null"))
            else:
                try:
                    date.fromisoformat(raw_as_of)
                except ValueError:
                    issues.append(Issue("invalid_date", "task.as_of_date", "must be YYYY-MM-DD or null"))
                else:
                    task_values["as_of_date"] = raw_as_of
        else:
            task_values["as_of_date"] = None

        raw_conversion_family = task.get("conversion_family")
        if raw_conversion_family is not None and (
            not isinstance(raw_conversion_family, str)
            or raw_conversion_family not in CONVERSION_FAMILIES
        ):
            issues.append(
                Issue(
                    "unsupported_value",
                    "task.conversion_family",
                    "must be null or one of: " + ", ".join(sorted(CONVERSION_FAMILIES)),
                )
            )
        else:
            task_values["conversion_family"] = raw_conversion_family

        list_fields = {
            "decision_points": (DECISION_POINTS, False),
            "audit_targets": (AUDIT_TARGETS, True),
            "topic_tags": (TOPIC_TAGS, True),
            "appraisal_tools": (APPRAISAL_TOOLS, True),
            "certainty_frameworks": (CERTAINTY_FRAMEWORKS, True),
        }
        for field, (supported, allow_empty) in list_fields.items():
            value = task.get(field)
            if not isinstance(value, list):
                issues.append(Issue("wrong_type", f"task.{field}", "must be an array of supported strings"))
                continue
            if not allow_empty and not value:
                issues.append(Issue("missing_value", f"task.{field}", "must contain at least one decision point"))
            if any(not isinstance(item, str) or item not in supported for item in value):
                issues.append(
                    Issue(
                        "unsupported_value",
                        f"task.{field}",
                        "values must be unique members of: " + ", ".join(sorted(supported)),
                    )
                )
            elif len(value) != len(set(value)):
                issues.append(Issue("duplicate_value", f"task.{field}", "must not contain duplicate values"))
            else:
                task_values[field] = list(value)

        decisions = task_values.get("decision_points", [])
        audit_targets = task_values.get("audit_targets", [])
        conversion_family = task_values.get("conversion_family")
        appraisal_tools = task_values.get("appraisal_tools", [])
        certainty_frameworks = task_values.get("certainty_frameworks", [])
        if "risk_of_bias" in decisions and not appraisal_tools:
            issues.append(Issue("missing_value", "task.appraisal_tools", "must declare at least one tool for a risk-of-bias decision"))
        if "risk_of_bias" not in decisions and appraisal_tools:
            issues.append(Issue("contradiction", "task.appraisal_tools", "must be empty unless risk_of_bias is a requested decision point"))
        if "certainty" in decisions and not certainty_frameworks:
            issues.append(Issue("missing_value", "task.certainty_frameworks", "must declare at least one framework for a certainty decision"))
        if "certainty" not in decisions and certainty_frameworks:
            issues.append(Issue("contradiction", "task.certainty_frameworks", "must be empty unless certainty is a requested decision point"))
        if (task_values.get("stage") == "audit" or "method_claim_audit" in decisions) and not audit_targets:
            issues.append(Issue("missing_value", "task.audit_targets", "must declare at least one audit target for audit work"))
        if task_values.get("stage") != "audit" and "method_claim_audit" not in decisions and audit_targets:
            issues.append(Issue("contradiction", "task.audit_targets", "must be empty unless stage is audit or method_claim_audit is requested"))
        if "effect_conversion" in decisions and conversion_family is None:
            issues.append(Issue("missing_value", "task.conversion_family", "must declare the proposed conversion family"))
        if "effect_conversion" not in decisions and conversion_family is not None:
            issues.append(Issue("contradiction", "task.conversion_family", "must be null unless effect_conversion is requested"))

    eligible: bool | None = None
    reason: str | None = None
    if pooling is not None:
        raw_eligible = pooling.get("eligible")
        if type(raw_eligible) is not bool:
            issues.append(Issue("wrong_type", "pooling.eligible", "must be a boolean"))
        else:
            eligible = raw_eligible

        raw_reason = pooling.get("ineligibility_reason")
        if raw_reason is not None and not isinstance(raw_reason, str):
            issues.append(
                Issue(
                    "wrong_type",
                    "pooling.ineligibility_reason",
                    "must be a non-empty string or null",
                )
            )
        elif isinstance(raw_reason, str):
            if not raw_reason.strip():
                issues.append(
                    Issue(
                        "missing_value",
                        "pooling.ineligibility_reason",
                        "must not be empty when provided",
                    )
                )
            else:
                reason = raw_reason.strip()

        if eligible is True and raw_reason is not None:
            issues.append(
                Issue(
                    "contradiction",
                    "pooling.ineligibility_reason",
                    "must be null when pooling.eligible is true",
                )
            )
        if eligible is False and reason is None:
            issues.append(
                Issue(
                    "missing_value",
                    "pooling.ineligibility_reason",
                    "a non-empty reason is required when pooling.eligible is false",
                )
            )

    level: str | None = None
    effect_structure: str | None = None
    dependence_topology: str | None = None
    dependency_sources: list[str] = []
    independent_cluster_count: int | None = None
    covariance_status: str | None = None
    sampling_v_path: str | None = None
    ecology_contract_path: str | None = None
    if data is not None:
        raw_level = data.get("level")
        if not isinstance(raw_level, str) or raw_level not in DATA_LEVELS:
            issues.append(
                Issue(
                    "unsupported_value",
                    "data.level",
                    "must be one of: aggregate, ipd, raw_community_matrix, meta_level",
                )
            )
        else:
            level = raw_level

        raw_structure = data.get("effect_structure")
        if (
            not isinstance(raw_structure, str)
            or raw_structure not in EFFECT_STRUCTURES
        ):
            issues.append(
                Issue(
                    "unsupported_value",
                    "data.effect_structure",
                    "must be one of: independent, dependent",
                )
            )
        else:
            effect_structure = raw_structure

        raw_topology = data.get("dependence_topology")
        if not isinstance(raw_topology, str) or raw_topology not in DEPENDENCE_TOPOLOGIES:
            issues.append(
                Issue(
                    "unsupported_value",
                    "data.dependence_topology",
                    "must be one of: " + ", ".join(sorted(DEPENDENCE_TOPOLOGIES)),
                )
            )
        else:
            dependence_topology = raw_topology

        raw_sources = data.get("dependency_sources")
        if not isinstance(raw_sources, list):
            issues.append(
                Issue(
                    "wrong_type",
                    "data.dependency_sources",
                    "must be an array of supported dependency-source strings",
                )
            )
        else:
            invalid_sources = [
                value
                for value in raw_sources
                if not isinstance(value, str) or value not in DEPENDENCY_SOURCES
            ]
            if invalid_sources:
                issues.append(
                    Issue(
                        "unsupported_value",
                        "data.dependency_sources",
                        "values must be unique members of: "
                        + ", ".join(sorted(DEPENDENCY_SOURCES)),
                    )
                )
            elif len(raw_sources) != len(set(raw_sources)):
                issues.append(
                    Issue(
                        "duplicate_value",
                        "data.dependency_sources",
                        "must not contain duplicate dependency sources",
                    )
                )
            else:
                dependency_sources = list(raw_sources)

        raw_cluster_count = data.get("independent_cluster_count")
        if raw_cluster_count is not None and (
            type(raw_cluster_count) is not int or raw_cluster_count < 1
        ):
            issues.append(
                Issue(
                    "unsupported_value",
                    "data.independent_cluster_count",
                    "must be a positive integer or null",
                )
            )
        elif isinstance(raw_cluster_count, int):
            independent_cluster_count = raw_cluster_count

        raw_covariance_status = data.get("sampling_covariance_status")
        if (
            not isinstance(raw_covariance_status, str)
            or raw_covariance_status not in COVARIANCE_STATUSES
        ):
            issues.append(
                Issue(
                    "unsupported_value",
                    "data.sampling_covariance_status",
                    "must be one of: " + ", ".join(sorted(COVARIANCE_STATUSES)),
                )
            )
        else:
            covariance_status = raw_covariance_status

        raw_v_path = data.get("sampling_v_path")
        if raw_v_path is not None and (
            not isinstance(raw_v_path, str) or not raw_v_path.strip()
        ):
            issues.append(
                Issue(
                    "wrong_type",
                    "data.sampling_v_path",
                    "must be a non-empty string locator or null",
                )
            )
        elif isinstance(raw_v_path, str):
            sampling_v_path = raw_v_path.strip()

        raw_ecology_path = data.get("ecology_contract_path")
        if raw_ecology_path is not None and (
            not isinstance(raw_ecology_path, str) or not raw_ecology_path.strip()
        ):
            issues.append(
                Issue(
                    "wrong_type",
                    "data.ecology_contract_path",
                    "must be a non-empty string locator or null",
                )
            )
        elif isinstance(raw_ecology_path, str):
            ecology_contract_path = raw_ecology_path.strip()

    if effect_structure == "independent":
        if dependence_topology != "independent":
            issues.append(
                Issue(
                    "contradiction",
                    "data.dependence_topology",
                    "must be 'independent' when effect_structure is independent",
                )
            )
        if dependency_sources:
            issues.append(
                Issue(
                    "contradiction",
                    "data.dependency_sources",
                    "must be empty when effect_structure is independent",
                )
            )
        if covariance_status is not None and covariance_status != "not_needed_verified":
            issues.append(
                Issue(
                    "contradiction",
                    "data.sampling_covariance_status",
                    "must be 'not_needed_verified' for independent effects",
                )
            )
        if sampling_v_path is not None:
            issues.append(
                Issue(
                    "contradiction",
                    "data.sampling_v_path",
                    "must be null for independent effects",
                )
            )
    elif effect_structure == "dependent":
        if dependence_topology == "independent":
            issues.append(
                Issue(
                    "contradiction",
                    "data.dependence_topology",
                    "cannot be 'independent' when effect_structure is dependent",
                )
            )
        if not dependency_sources:
            issues.append(
                Issue(
                    "missing_value",
                    "data.dependency_sources",
                    "at least one dependency source is required for dependent effects",
                )
            )
        if covariance_status == "not_needed_verified":
            issues.append(
                Issue(
                    "contradiction",
                    "data.sampling_covariance_status",
                    "dependent effects cannot declare sampling covariance not needed",
                )
            )
        if covariance_status == "unavailable" and sampling_v_path is not None:
            issues.append(
                Issue(
                    "contradiction",
                    "data.sampling_v_path",
                    "must be null when sampling covariance is unavailable",
                )
            )
        if covariance_status in {
            "provided_validated",
            "derived_exact",
            "derived_delta_method",
            "assumed_sensitivity",
        } and sampling_v_path is None:
            issues.append(
                Issue(
                    "missing_value",
                    "data.sampling_v_path",
                    "a non-empty V-matrix locator is required for dependent effects",
                )
            )

    analysis_decisions = {
        "effect_size",
        "effect_conversion",
        "dependence",
        "synthesis_model",
        "few_studies",
        "small_study_effects",
        "r_implementation",
    }
    if (
        level == "aggregate"
        and task_values.get("stage") in {"analysis", "interpretation", "reporting", "audit"}
        and analysis_decisions.intersection(task_values.get("decision_points", []))
        and independent_cluster_count is None
    ):
        issues.append(
            Issue(
                "missing_value",
                "data.independent_cluster_count",
                "is required for aggregate analysis decisions and must count independent sampling clusters, not effect rows",
            )
        )

    trigger_values: dict[str, bool] = {}
    if triggers is not None:
        for name in SPECIALIST_HANDOFFS:
            value = triggers.get(name)
            if type(value) is not bool:
                issues.append(
                    Issue(
                        "wrong_type",
                        f"specialist_triggers.{name}",
                        "must be a boolean",
                    )
                )
            else:
                trigger_values[name] = value

    task_domain = task_values.get("domain")
    topic_tags = task_values.get("topic_tags", [])
    health_domains = {"medical", "public_health"}
    ecology_domains = {"ecology", "evolution", "conservation", "environmental_science"}
    active_medical = sorted(
        name for name in ("diagnostic", "dose_response", "network")
        if trigger_values.get(name) is True
    )
    if active_medical and task_domain not in health_domains:
        issues.append(
            Issue(
                "contradiction",
                "task.domain",
                "must be medical or public_health for specialist trigger(s): "
                + ", ".join(active_medical),
            )
        )
    active_ecology = sorted(
        name for name in ECOLOGY_CONTRACT_TRIGGERS
        if trigger_values.get(name) is True
    )
    if active_ecology and task_domain not in ecology_domains:
        issues.append(
            Issue(
                "contradiction",
                "task.domain",
                "must be an ecology/environment domain for specialist trigger(s): "
                + ", ".join(active_ecology),
            )
        )
    if topic_tags and task_domain not in ecology_domains:
        issues.append(
            Issue(
                "contradiction",
                "task.topic_tags",
                "plant, biodiversity, community, and restoration tags require an ecology/environment domain",
            )
        )
    if (
        trigger_values.get("diagnostic") is True
        and "risk_of_bias" in task_values.get("decision_points", [])
        and "quadas3" not in task_values.get("appraisal_tools", [])
    ):
        issues.append(
            Issue(
                "contradiction",
                "task.appraisal_tools",
                "diagnostic risk-of-bias appraisal must include quadas3",
            )
        )

    level_trigger_pairs = {
        "ipd": "ipd",
        "raw_community_matrix": "raw_community_matrix",
        "meta_level": "second_order_meta",
    }
    if level is not None:
        for level_name, trigger_name in level_trigger_pairs.items():
            if (level == level_name) != trigger_values.get(trigger_name):
                issues.append(
                    Issue(
                        "contradiction",
                        "data.level",
                        f"data.level={level_name!r} and "
                        f"specialist_triggers.{trigger_name} must agree",
                    )
                )

    ecology_triggers_active = sorted(
        name
        for name in ECOLOGY_CONTRACT_TRIGGERS
        if trigger_values.get(name) is True
    )
    if task_domain in ecology_domains and trigger_values.get("one_stage_longitudinal") is True:
        ecology_triggers_active.append("one_stage_longitudinal")
        ecology_triggers_active.sort()
    if ecology_triggers_active and ecology_contract_path is None:
        issues.append(
            Issue(
                "missing_value",
                "data.ecology_contract_path",
                "a validated biodiversity/ecology contract locator is required for: "
                + ", ".join(ecology_triggers_active),
            )
        )
    if not ecology_triggers_active and ecology_contract_path is not None:
        issues.append(
            Issue(
                "contradiction",
                "data.ecology_contract_path",
                "must be null when no biodiversity/ecology contract trigger is active",
            )
        )

    if issues:
        return None, issues

    # These values are guaranteed by validation; the assertions protect future edits.
    assert eligible is not None
    assert level is not None
    assert effect_structure is not None
    assert dependence_topology is not None
    assert covariance_status is not None
    assert len(trigger_values) == len(SPECIALIST_HANDOFFS)
    return {
        "task": task_values,
        "eligible": eligible,
        "reason": reason,
        "level": level,
        "effect_structure": effect_structure,
        "dependence_topology": dependence_topology,
        "dependency_sources": dependency_sources,
        "independent_cluster_count": independent_cluster_count,
        "covariance_status": covariance_status,
        "sampling_v_path": sampling_v_path,
        "ecology_contract_path": ecology_contract_path,
        "triggers": trigger_values,
    }, []


def route(validated: Mapping[str, Any]) -> dict[str, Any]:
    if not validated["eligible"]:
        result = {
            "route": "no_pooling",
            "runner_allowed": False,
            "stop_reason": validated["reason"],
            "required_handoff": ["structured_narrative_synthesis_or_systematic_map"],
        }
    else:
        active = [
            name for name in SPECIALIST_HANDOFFS if validated["triggers"][name]
        ]
        if active:
            result = {
                "route": "specialist_route",
                "runner_allowed": False,
                "stop_reason": (
                    "Ordinary runner blocked by specialist trigger(s): "
                    + ", ".join(active)
                ),
                "required_handoff": [SPECIALIST_HANDOFFS[name] for name in active],
            }
        elif (
            validated["effect_structure"] == "dependent"
            and validated["covariance_status"] == "unavailable"
        ):
            result = {
                "route": "specialist_route",
                "runner_allowed": False,
                "stop_reason": (
                    "Ordinary runner blocked because dependent effects have no "
                    "audited sampling covariance matrix."
                ),
                "required_handoff": ["sampling_covariance_specialist"],
            }
        elif (
            validated["effect_structure"] == "dependent"
            and validated["dependence_topology"] == "unknown"
        ):
            result = {
                "route": "specialist_route",
                "runner_allowed": False,
                "stop_reason": (
                    "Ordinary runner blocked because the dependence topology is unknown."
                ),
                "required_handoff": ["dependence_structure_specialist"],
            }
        elif validated["effect_structure"] == "dependent":
            result = {
                "route": "dependent_effect_meta",
                "runner_allowed": True,
                "stop_reason": None,
                "required_handoff": [],
            }
        else:
            result = {
                "route": "aggregate_effect_meta",
                "runner_allowed": True,
                "stop_reason": None,
                "required_handoff": [],
            }

    assert result["route"] in ROUTES
    return result


def render_json(payload: Mapping[str, Any], *, pretty: bool) -> str:
    if pretty:
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def emit_json(payload: Mapping[str, Any], *, pretty: bool, stream: Any) -> None:
    stream.write(render_json(payload, pretty=pretty) + "\n")


def normalized_path(path: Path) -> str:
    """Return a case-normalized absolute path for lexical identity checks."""

    return os.path.normcase(os.path.abspath(os.fspath(path)))


def paths_are_same(input_path: Path, output_path: Path) -> bool:
    if normalized_path(input_path) == normalized_path(output_path):
        return True
    try:
        return input_path.exists() and output_path.exists() and os.path.samefile(
            input_path, output_path
        )
    except OSError:
        return False


def validate_output_target(
    input_name: str, output_path: Path | None, *, overwrite: bool
) -> Path | None:
    if output_path is None:
        return None

    target = Path(normalized_path(output_path))
    if input_name != "-" and paths_are_same(Path(input_name), target):
        raise RuntimeError("Output file must not be the same file as the JSON input.")
    if target.exists():
        if target.is_dir():
            raise RuntimeError(f"Output path is a directory, not a file: {target}")
        if not overwrite:
            raise RuntimeError(
                f"Output file already exists; use --overwrite yes to replace it: {target}"
            )
    if not target.parent.exists():
        raise RuntimeError(f"Output parent directory does not exist: {target.parent}")
    if not target.parent.is_dir():
        raise RuntimeError(f"Output parent is not a directory: {target.parent}")
    return target


def atomic_write_utf8(target: Path, text: str, *, overwrite: bool) -> None:
    """Publish complete UTF-8 bytes atomically, cleaning temporary files on error."""

    temporary: Path | None = None
    descriptor: int | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write((text + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())

        if overwrite:
            os.replace(temporary, target)
        else:
            try:
                if os.name == "nt":
                    # Windows rename is atomic and refuses an existing target.
                    os.rename(temporary, target)
                else:
                    # A hard link publishes without the overwrite behavior of
                    # POSIX rename; the temporary name can then be removed.
                    os.link(temporary, target)
                    os.unlink(temporary)
            except OSError as exc:
                if target.exists():
                    raise RuntimeError(
                        "Output file already exists; use --overwrite yes to "
                        f"replace it: {target}"
                    ) from exc
                raise
        temporary = None
    except RuntimeError:
        raise
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"Could not atomically write UTF-8 output {target}: {exc}") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    overwrite = args.overwrite == "yes"
    try:
        output_path = validate_output_target(
            args.input, args.output, overwrite=overwrite
        )
    except RuntimeError as exc:
        emit_json(
            {"error": "output_error", "message": str(exc)},
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INPUT_ERROR

    try:
        payload = load_json(args.input)
    except RuntimeError as exc:
        emit_json(
            {"error": "input_error", "message": str(exc)},
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INPUT_ERROR

    validated, issues = validate_input(payload)
    if issues:
        emit_json(
            {
                "error": "invalid_input",
                "issues": [issue.as_dict() for issue in issues],
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INVALID_INPUT

    assert validated is not None
    try:
        registry = load_reference_routes(args.reference_routes)
        receipt = load_json_file(args.reference_receipt) if args.reference_receipt else None
    except RuntimeError as exc:
        emit_json(
            {"error": "reference_gate_input_error", "message": str(exc)},
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INPUT_ERROR

    result = route(validated)
    provisional_allowed = result["runner_allowed"]
    requirements = resolve_requirements(payload, registry)
    gate = build_gate_result(
        receipt,
        plan=payload,
        requirements=requirements,
        registry=registry,
        skill_root=Path(__file__).resolve().parent.parent,
    )
    result["provisional_runner_allowed"] = provisional_allowed
    result.update(requirements)
    result["reference_gate"] = {
        **gate,
        "decision_points": validated["task"]["decision_points"],
    }
    if gate["status"] != "passed":
        result["runner_allowed"] = False
        if provisional_allowed:
            result["stop_reason"] = "Reference gate blocked execution: " + "; ".join(
                issue["message"] for issue in gate["issues"]
            )
    if output_path is None:
        emit_json(result, pretty=args.pretty, stream=sys.stdout)
    else:
        try:
            atomic_write_utf8(
                output_path, render_json(result, pretty=args.pretty), overwrite=overwrite
            )
        except RuntimeError as exc:
            emit_json(
                {"error": "output_error", "message": str(exc)},
                pretty=args.pretty,
                stream=sys.stderr,
            )
            return EXIT_INPUT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
