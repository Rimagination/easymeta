#!/usr/bin/env python3
"""Validate a medical/ecology meta-analysis effect-extraction CSV.

Exit codes:
    0: clean, or warnings explicitly allowed with --allow-warnings
    1: one or more validation errors
    2: command usage, input, encoding, or CSV parsing failure
    3: warnings only (default policy requires review)
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence


EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_ERROR = 2
EXIT_WARNINGS = 3

RAW_STAGE = "raw_extraction"
ANALYSIS_STAGE = "analysis_effect"
RAW_SCHEMA_VERSION = "1.0.0"
ANALYSIS_SCHEMA_VERSION = "1.0.0"
STAGE_ALIASES = {"raw": RAW_STAGE, "analysis": ANALYSIS_STAGE}
SUPPORTED_SCHEMA_VERSIONS = {
    RAW_STAGE: {RAW_SCHEMA_VERSION},
    ANALYSIS_STAGE: {ANALYSIS_SCHEMA_VERSION},
}

RAW_REQUIRED_HEADERS = {
    "schema_version",
    "data_stage",
    "study_id",
    "report_id",
    "effect_id",
    "citation",
    "publication_year",
    "study_design",
    "population",
    "exposure_intervention",
    "comparator",
    "outcome",
    "outcome_definition",
    "timepoint",
    "effect_measure",
    "effect_scale",
    "effect_estimate",
    "se",
    "variance",
    "ci_lower",
    "ci_upper",
    "ci_level",
    "n_total",
    "direction",
    "unit",
    "dependency_cluster",
    "risk_of_bias",
    "source_locator",
    "extractor",
    "verifier",
    "extraction_date",
    "data_status",
    "ai_assisted",
    "ai_system_id",
}

RAW_REQUIRED_VALUES = {
    "schema_version",
    "data_stage",
    "study_id",
    "report_id",
    "effect_id",
    "citation",
    "publication_year",
    "study_design",
    "population",
    "exposure_intervention",
    "comparator",
    "outcome",
    "outcome_definition",
    "timepoint",
    "effect_measure",
    "n_total",
    "direction",
    "unit",
    "source_locator",
    "extractor",
    "verifier",
    "extraction_date",
    "data_status",
    "ai_assisted",
}

ANALYSIS_PROVENANCE_FIELDS = {
    "source_schema_version",
    "source_data_stage",
    "source_file",
    "source_file_md5",
    "source_row",
    "calculation_method",
    "calculator_version",
    "calculated_at_utc",
}

ANALYSIS_FIELDS = {
    "yi",
    "vi",
    "sei",
    "measure",
    "analysis_scale",
    "display_transform",
}

ANALYSIS_REQUIRED_HEADERS = RAW_REQUIRED_HEADERS | ANALYSIS_PROVENANCE_FIELDS | ANALYSIS_FIELDS
ANALYSIS_REQUIRED_VALUES = RAW_REQUIRED_VALUES | ANALYSIS_PROVENANCE_FIELDS | ANALYSIS_FIELDS

OPTIONAL_NUMERIC_FIELDS = {
    "n_intervention",
    "n_comparator",
    "events_intervention",
    "events_comparator",
    "mean_intervention",
    "sd_intervention",
    "mean_comparator",
    "sd_comparator",
}

INTEGER_FIELDS = {
    "publication_year",
    "n_total",
    "n_intervention",
    "n_comparator",
    "events_intervention",
    "events_comparator",
}

EFFECT_MEASURES = {
    "AS",
    "MD",
    "SMD",
    "SMDH",
    "HEDGES_G",
    "ROM",
    "RR",
    "OR",
    "HR",
    "IRR",
    "IRD",
    "IRSD",
    "RD",
    "COR",
    "UCOR",
    "ZCOR",
    "CORRELATION",
    "FISHER_Z",
    "PR",
    "PLN",
    "PLO",
    "PRZ",
    "PAS",
    "PROPORTION",
    "IR",
    "IRLN",
    "IRS",
    "MN",
    "MNLN",
    "SDLN",
    "CVLN",
    "MC",
    "SMCC",
    "SMCR",
    "SMCRH",
    "PETO",
    "OTHER",
}

EFFECT_SCALES = {"natural", "log", "raw", "standardized"}
ANALYSIS_SCALES = {
    "identity",
    "log",
    "fisher-z",
    "logit",
    "arcsine_difference",
    "arcsine",
    "sqrt_difference",
    "sqrt",
}

CALCULATION_MEASURES = {
    "OR", "RR", "RD", "AS", "PETO", "MD", "SMD", "SMDH", "ROM",
    "IRR", "IRD", "IRSD", "COR", "UCOR", "ZCOR", "PR", "PLN", "PLO",
    "PRZ", "PAS", "IR", "IRLN", "IRS", "MN", "MNLN", "SDLN", "CVLN",
    "MC", "SMCC", "SMCR", "SMCRH", "GEN",
}

MEASURE_ANALYSIS_SCALES = {
    "OR": {"log"},
    "RR": {"log"},
    "HR": {"log"},
    "IRR": {"log"},
    "ROM": {"log"},
    "PETO": {"log"},
    "PLN": {"log"},
    "IRLN": {"log"},
    "MNLN": {"log"},
    "SDLN": {"log"},
    "CVLN": {"log"},
    "FISHER_Z": {"fisher-z"},
    "ZCOR": {"fisher-z"},
    "PLO": {"logit"},
    "AS": {"arcsine_difference"},
    "PAS": {"arcsine"},
    "IRSD": {"sqrt_difference"},
    "IRS": {"sqrt"},
    "CORRELATION": {"identity", "fisher-z"},
    "PROPORTION": {"identity", "log", "logit", "arcsine"},
    "OTHER": ANALYSIS_SCALES,
}

DISPLAY_TRANSFORMS = {"log": "exp", "fisher-z": "tanh", "logit": "plogis"}

DIRECTIONS = {
    "higher_favors_intervention",
    "lower_favors_intervention",
    "higher_favors_exposure",
    "lower_favors_exposure",
    "higher_is_harmful",
    "higher_is_beneficial",
    "not_applicable",
}

DATA_STATUSES = {"extracted", "verified", "adjudicated", "queried"}
YES_NO = {"yes", "no"}
RATIO_MEASURES = {"ROM", "RR", "OR", "HR", "IRR"}


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str
    row: int | None = None
    field: str | None = None

    def render(self) -> str:
        location = []
        if self.row is not None:
            location.append(f"row={self.row}")
        if self.field:
            location.append(f"field={self.field}")
        where = " " + " ".join(location) if location else ""
        return f"{self.severity}{where} code={self.code}: {self.message}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a versioned raw_extraction or analysis_effect CSV using "
            "only the Python standard library. Warnings return exit code 3 "
            "unless --allow-warnings is set."
        ),
        epilog=(
            "Exit codes: 0=clean/allowed warnings, 1=data errors, "
            "2=usage or input failure, 3=warnings only."
        ),
    )
    parser.add_argument("csv_file", type=Path, help="Path to the extraction CSV")
    parser.add_argument(
        "--stage",
        choices=("raw", "analysis", "auto"),
        default="auto",
        help=(
            "Contract to validate: raw=raw_extraction, analysis=analysis_effect, "
            "auto=infer from data_stage (default: auto)"
        ),
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Input text encoding (default: utf-8-sig, which also accepts a UTF-8 BOM)",
    )
    parser.add_argument(
        "--tolerance",
        type=positive_finite_float,
        default=1e-6,
        help="Relative and absolute tolerance for variance ~= SE^2 (default: 1e-6)",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Return 0 when warnings are the only issues; warnings are still printed",
    )
    return parser


def positive_finite_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return parsed


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def parse_number(
    row: Mapping[str, object],
    field: str,
    row_number: int,
    issues: list[Issue],
    *,
    required: bool = False,
) -> float | None:
    raw = clean(row.get(field))
    if not raw:
        if required:
            issues.append(Issue("ERROR", "MISSING_VALUE", "required value is blank", row_number, field))
        return None
    try:
        value = float(raw)
    except ValueError:
        issues.append(Issue("ERROR", "INVALID_NUMBER", f"not a number: {raw!r}", row_number, field))
        return None
    if not math.isfinite(value):
        issues.append(Issue("ERROR", "NONFINITE_NUMBER", "NaN and infinity are not allowed", row_number, field))
        return None
    return value


def parse_integer(
    row: Mapping[str, object],
    field: str,
    row_number: int,
    issues: list[Issue],
    *,
    required: bool = False,
) -> int | None:
    value = parse_number(row, field, row_number, issues, required=required)
    if value is None:
        return None
    if not value.is_integer():
        issues.append(Issue("ERROR", "NOT_INTEGER", "must be a whole number", row_number, field))
        return None
    return int(value)


def validate_headers(fieldnames: Sequence[str] | None, stage: str) -> list[Issue]:
    issues: list[Issue] = []
    if not fieldnames:
        return [Issue("ERROR", "MISSING_HEADER", "CSV has no header row")]

    normalized = [clean(name) for name in fieldnames]
    blank_count = sum(not name for name in normalized)
    if blank_count:
        issues.append(Issue("ERROR", "BLANK_HEADER", f"{blank_count} blank column name(s)"))

    duplicates = sorted({name for name in normalized if name and normalized.count(name) > 1})
    if duplicates:
        issues.append(Issue("ERROR", "DUPLICATE_HEADER", f"duplicate column name(s): {', '.join(duplicates)}"))

    required_headers = RAW_REQUIRED_HEADERS if stage == RAW_STAGE else ANALYSIS_REQUIRED_HEADERS
    missing = sorted(required_headers - set(normalized))
    if missing:
        issues.append(Issue("ERROR", "MISSING_COLUMNS", f"required column(s) missing: {', '.join(missing)}"))
    return issues


def detect_stage(
    fieldnames: Sequence[str] | None,
    rows: Sequence[Mapping[str, object]],
    requested_stage: str,
) -> tuple[str | None, list[Issue]]:
    if requested_stage in STAGE_ALIASES:
        return STAGE_ALIASES[requested_stage], []

    normalized_headers = {clean(name) for name in (fieldnames or [])}
    if "data_stage" not in normalized_headers:
        return None, [
            Issue(
                "ERROR",
                "MISSING_DATA_STAGE",
                "auto detection requires a data_stage column; use --stage only to select a contract, not to bypass metadata",
                field="data_stage",
            )
        ]

    declared = {clean(row.get("data_stage")) for row in rows if any(clean(value) for value in row.values())}
    declared.discard("")
    if len(declared) > 1:
        return None, [
            Issue(
                "ERROR",
                "MIXED_DATA_STAGES",
                f"one CSV must contain exactly one data_stage, found: {', '.join(sorted(declared))}",
                field="data_stage",
            )
        ]
    if len(declared) == 1:
        stage = next(iter(declared))
        if stage not in SUPPORTED_SCHEMA_VERSIONS:
            return None, [
                Issue(
                    "ERROR",
                    "UNKNOWN_DATA_STAGE",
                    f"use {RAW_STAGE!r} or {ANALYSIS_STAGE!r}",
                    field="data_stage",
                )
            ]
        return stage, []

    analysis_signature = {"yi", "vi", "analysis_scale"}
    if analysis_signature <= normalized_headers:
        return ANALYSIS_STAGE, []
    return RAW_STAGE, []


def validate_required_values(
    row: Mapping[str, object], row_number: int, issues: list[Issue], stage: str
) -> None:
    required_values = RAW_REQUIRED_VALUES if stage == RAW_STAGE else ANALYSIS_REQUIRED_VALUES
    for field in sorted(required_values):
        if not clean(row.get(field)):
            issues.append(Issue("ERROR", "MISSING_VALUE", "required value is blank", row_number, field))


def validate_contract_metadata(
    row: Mapping[str, object], row_number: int, issues: list[Issue], stage: str
) -> None:
    declared_stage = clean(row.get("data_stage"))
    if declared_stage and declared_stage != stage:
        issues.append(
            Issue(
                "ERROR",
                "DATA_STAGE_MISMATCH",
                f"selected contract requires data_stage={stage!r}, found {declared_stage!r}",
                row_number,
                "data_stage",
            )
        )

    version = clean(row.get("schema_version"))
    supported = SUPPORTED_SCHEMA_VERSIONS[stage]
    if version and version not in supported:
        issues.append(
            Issue(
                "ERROR",
                "UNSUPPORTED_SCHEMA_VERSION",
                f"supported {stage} schema_version(s): {', '.join(sorted(supported))}; found {version!r}",
                row_number,
                "schema_version",
            )
        )

    if stage == ANALYSIS_STAGE:
        source_stage = clean(row.get("source_data_stage"))
        if source_stage and source_stage != RAW_STAGE:
            issues.append(
                Issue(
                    "ERROR",
                    "INVALID_SOURCE_DATA_STAGE",
                    f"analysis_effect provenance must point to source_data_stage={RAW_STAGE!r}",
                    row_number,
                    "source_data_stage",
                )
            )
        source_version = clean(row.get("source_schema_version"))
        if source_version and source_version not in SUPPORTED_SCHEMA_VERSIONS[RAW_STAGE]:
            issues.append(
                Issue(
                    "ERROR",
                    "UNSUPPORTED_SOURCE_SCHEMA_VERSION",
                    f"supported raw source schema_version(s): {', '.join(sorted(SUPPORTED_SCHEMA_VERSIONS[RAW_STAGE]))}",
                    row_number,
                    "source_schema_version",
                )
            )


def validate_controlled_values(
    row: Mapping[str, object], row_number: int, issues: list[Issue], stage: str
) -> None:
    measure = clean(row.get("effect_measure")).upper()
    if measure and measure not in EFFECT_MEASURES:
        issues.append(
            Issue(
                "ERROR",
                "UNKNOWN_EFFECT_MEASURE",
                f"use one of {sorted(EFFECT_MEASURES)}; use OTHER for a documented custom measure",
                row_number,
                "effect_measure",
            )
        )

    scale = clean(row.get("effect_scale")).lower()
    if scale and scale not in EFFECT_SCALES:
        issues.append(
            Issue("ERROR", "UNKNOWN_EFFECT_SCALE", f"use one of {sorted(EFFECT_SCALES)}", row_number, "effect_scale")
        )

    direction = clean(row.get("direction")).lower()
    if direction and direction not in DIRECTIONS:
        issues.append(
            Issue("ERROR", "UNKNOWN_DIRECTION", f"use one of {sorted(DIRECTIONS)}", row_number, "direction")
        )

    status = clean(row.get("data_status")).lower()
    if status and status not in DATA_STATUSES:
        issues.append(
            Issue("ERROR", "UNKNOWN_DATA_STATUS", f"use one of {sorted(DATA_STATUSES)}", row_number, "data_status")
        )

    ai_assisted = clean(row.get("ai_assisted")).lower()
    if ai_assisted and ai_assisted not in YES_NO:
        issues.append(Issue("ERROR", "INVALID_YES_NO", "use yes or no", row_number, "ai_assisted"))
    if ai_assisted == "yes" and not clean(row.get("ai_system_id")):
        issues.append(
            Issue(
                "ERROR",
                "MISSING_AI_SYSTEM_ID",
                "ai_system_id is required when ai_assisted=yes",
                row_number,
                "ai_system_id",
            )
        )

    if stage != ANALYSIS_STAGE:
        return

    calculation_measure = clean(row.get("measure")).upper()
    if calculation_measure and calculation_measure not in CALCULATION_MEASURES:
        issues.append(
            Issue(
                "ERROR",
                "UNKNOWN_CALCULATION_MEASURE",
                f"use one of {sorted(CALCULATION_MEASURES)}",
                row_number,
                "measure",
            )
        )

    analysis_scale = clean(row.get("analysis_scale")).lower()
    if analysis_scale and analysis_scale not in ANALYSIS_SCALES:
        issues.append(
            Issue(
                "ERROR",
                "UNKNOWN_ANALYSIS_SCALE",
                f"use one of {sorted(ANALYSIS_SCALES)}",
                row_number,
                "analysis_scale",
            )
        )
    elif analysis_scale:
        semantic_measure = measure
        allowed_scales = MEASURE_ANALYSIS_SCALES.get(semantic_measure, {"identity"})
        if analysis_scale not in allowed_scales:
            issues.append(
                Issue(
                    "ERROR",
                    "MEASURE_SCALE_MISMATCH",
                    f"{semantic_measure} requires analysis_scale in {sorted(allowed_scales)}, found {analysis_scale!r}",
                    row_number,
                    "analysis_scale",
                )
            )

        expected_transform = DISPLAY_TRANSFORMS.get(analysis_scale, "identity_or_measure_specific")
        display_transform = clean(row.get("display_transform"))
        if display_transform and display_transform != expected_transform:
            issues.append(
                Issue(
                    "ERROR",
                    "DISPLAY_TRANSFORM_MISMATCH",
                    f"analysis_scale={analysis_scale!r} requires display_transform={expected_transform!r}",
                    row_number,
                    "display_transform",
                )
            )


def validate_numeric_fields(
    row: Mapping[str, object],
    row_number: int,
    issues: list[Issue],
    tolerance: float,
    stage: str,
) -> None:
    year = parse_integer(row, "publication_year", row_number, issues)
    if year is not None and not 1600 <= year <= date.today().year + 1:
        issues.append(
            Issue(
                "ERROR",
                "YEAR_OUT_OF_RANGE",
                f"expected a year from 1600 to {date.today().year + 1}",
                row_number,
                "publication_year",
            )
        )

    n_total = parse_integer(row, "n_total", row_number, issues)
    if n_total is not None and n_total <= 0:
        issues.append(Issue("ERROR", "NONPOSITIVE_SAMPLE", "must be greater than zero", row_number, "n_total"))

    reported_fields = ("effect_estimate", "ci_lower", "ci_upper", "ci_level", "se", "variance")
    values: dict[str, float | None] = {}
    for field in reported_fields:
        values[field] = parse_number(row, field, row_number, issues)

    for field in sorted(OPTIONAL_NUMERIC_FIELDS - INTEGER_FIELDS):
        values[field] = parse_number(row, field, row_number, issues)

    optional_integers: dict[str, int | None] = {}
    for field in sorted((OPTIONAL_NUMERIC_FIELDS & INTEGER_FIELDS)):
        optional_integers[field] = parse_integer(row, field, row_number, issues)

    se = values["se"]
    variance = values["variance"]
    estimate = values["effect_estimate"]
    lower = values["ci_lower"]
    upper = values["ci_upper"]
    ci_level = values["ci_level"]

    if any(clean(row.get(field)) for field in reported_fields) and not clean(row.get("effect_scale")):
        issues.append(
            Issue(
                "ERROR",
                "MISSING_EFFECT_SCALE",
                "effect_scale is required when a reported estimate, uncertainty, or CI is present",
                row_number,
                "effect_scale",
            )
        )

    if any(clean(row.get(field)) for field in ("ci_lower", "ci_upper", "ci_level")):
        for field in ("effect_estimate", "ci_lower", "ci_upper", "ci_level"):
            if not clean(row.get(field)):
                issues.append(
                    Issue(
                        "ERROR",
                        "INCOMPLETE_REPORTED_CI",
                        "a reported CI requires effect_estimate, ci_lower, ci_upper, and ci_level",
                        row_number,
                        field,
                    )
                )

    if (se is not None or variance is not None) and estimate is None:
        issues.append(
            Issue(
                "ERROR",
                "UNCERTAINTY_WITHOUT_ESTIMATE",
                "reported se/variance requires effect_estimate on the same effect_scale",
                row_number,
                "effect_estimate",
            )
        )
    if se is not None and se <= 0:
        issues.append(Issue("ERROR", "NONPOSITIVE_SE", "must be greater than zero", row_number, "se"))
    if variance is not None and variance <= 0:
        issues.append(Issue("ERROR", "NONPOSITIVE_VARIANCE", "must be greater than zero", row_number, "variance"))
    if se is not None and variance is not None and se > 0 and variance > 0:
        expected = se * se
        if not math.isclose(variance, expected, rel_tol=tolerance, abs_tol=tolerance):
            issues.append(
                Issue(
                    "ERROR",
                    "SE_VARIANCE_MISMATCH",
                    f"variance={variance:g}, but se^2={expected:g} (tolerance={tolerance:g})",
                    row_number,
                    "se/variance",
                )
            )

    if ci_level is not None and not 0 < ci_level < 1:
        issues.append(
            Issue("ERROR", "CI_LEVEL_OUT_OF_RANGE", "use a proportion strictly between 0 and 1, e.g. 0.95", row_number, "ci_level")
        )

    if lower is not None and upper is not None:
        if lower >= upper:
            issues.append(Issue("ERROR", "CI_ORDER", "ci_lower must be less than ci_upper", row_number, "ci_lower/ci_upper"))
        if estimate is not None and not lower <= estimate <= upper:
            issues.append(
                Issue("ERROR", "ESTIMATE_OUTSIDE_CI", "effect_estimate must lie within the confidence interval", row_number, "effect_estimate")
            )

    measure = clean(row.get("effect_measure")).upper()
    scale = clean(row.get("effect_scale")).lower()
    if scale == "natural" and estimate is not None and lower is not None and upper is not None:
        if measure in RATIO_MEASURES and min(estimate, lower, upper) <= 0:
            issues.append(
                Issue("ERROR", "NONPOSITIVE_RATIO", "natural-scale ratio effects and confidence limits must be positive", row_number, "effect_estimate/ci")
            )
        if measure in {"CORRELATION", "RD"} and any(value < -1 or value > 1 for value in (estimate, lower, upper)):
            issues.append(
                Issue("ERROR", "EFFECT_OUT_OF_RANGE", f"natural-scale {measure} values must be within [-1, 1]", row_number, "effect_estimate/ci")
            )
        if measure == "PROPORTION" and any(value < 0 or value > 1 for value in (estimate, lower, upper)):
            issues.append(
                Issue("ERROR", "EFFECT_OUT_OF_RANGE", "natural-scale proportions must be within [0, 1]", row_number, "effect_estimate/ci")
            )

    for field, value in optional_integers.items():
        if value is not None and value < 0:
            issues.append(Issue("ERROR", "NEGATIVE_COUNT", "must be zero or greater", row_number, field))

    for field in ("sd_intervention", "sd_comparator"):
        value = values.get(field)
        if value is not None and value < 0:
            issues.append(Issue("ERROR", "NEGATIVE_SD", "standard deviation cannot be negative", row_number, field))

    n_intervention = optional_integers.get("n_intervention")
    n_comparator = optional_integers.get("n_comparator")
    events_intervention = optional_integers.get("events_intervention")
    events_comparator = optional_integers.get("events_comparator")

    if n_intervention is not None and events_intervention is not None and events_intervention > n_intervention:
        issues.append(
            Issue("ERROR", "EVENTS_EXCEED_SAMPLE", "events_intervention cannot exceed n_intervention", row_number, "events_intervention")
        )
    if n_comparator is not None and events_comparator is not None and events_comparator > n_comparator:
        issues.append(
            Issue("ERROR", "EVENTS_EXCEED_SAMPLE", "events_comparator cannot exceed n_comparator", row_number, "events_comparator")
        )
    if n_total is not None and n_intervention is not None and n_comparator is not None:
        grouped_total = n_intervention + n_comparator
        if grouped_total > n_total:
            issues.append(
                Issue("ERROR", "GROUPS_EXCEED_TOTAL", "n_intervention + n_comparator cannot exceed n_total", row_number, "n_total")
            )
        elif grouped_total != n_total:
            issues.append(
                Issue(
                    "WARNING",
                    "GROUPS_DO_NOT_SUM_TO_TOTAL",
                    "group sizes do not sum to n_total; confirm extra arms, exclusions, or the analysis sample",
                    row_number,
                    "n_total",
                )
            )

    if stage == ANALYSIS_STAGE:
        yi = parse_number(row, "yi", row_number, issues)
        vi = parse_number(row, "vi", row_number, issues)
        sei = parse_number(row, "sei", row_number, issues)
        source_row = parse_integer(row, "source_row", row_number, issues)

        if vi is not None and vi <= 0:
            issues.append(Issue("ERROR", "NONPOSITIVE_VI", "vi must be greater than zero", row_number, "vi"))
        if sei is not None and sei <= 0:
            issues.append(Issue("ERROR", "NONPOSITIVE_SEI", "sei must be greater than zero", row_number, "sei"))
        if vi is not None and sei is not None and vi > 0 and sei > 0:
            expected = sei * sei
            if not math.isclose(vi, expected, rel_tol=tolerance, abs_tol=tolerance):
                issues.append(
                    Issue(
                        "ERROR",
                        "VI_SEI_MISMATCH",
                        f"vi={vi:g}, but sei^2={expected:g} on analysis_scale (tolerance={tolerance:g})",
                        row_number,
                        "vi/sei/analysis_scale",
                    )
                )
        if source_row is not None and source_row < 2:
            issues.append(
                Issue(
                    "ERROR",
                    "INVALID_SOURCE_ROW",
                    "source_row is the physical CSV row and must be at least 2",
                    row_number,
                    "source_row",
                )
            )

        source_md5 = clean(row.get("source_file_md5")).lower()
        if source_md5 and (len(source_md5) != 32 or any(ch not in "0123456789abcdef" for ch in source_md5)):
            issues.append(
                Issue(
                    "ERROR",
                    "INVALID_SOURCE_MD5",
                    "source_file_md5 must contain exactly 32 hexadecimal characters",
                    row_number,
                    "source_file_md5",
                )
            )

        calculated_at = clean(row.get("calculated_at_utc"))
        if calculated_at:
            try:
                parsed_timestamp = datetime.fromisoformat(calculated_at.replace("Z", "+00:00"))
                utc_offset = parsed_timestamp.utcoffset()
                if parsed_timestamp.tzinfo is None or utc_offset is None or utc_offset.total_seconds() != 0:
                    raise ValueError("UTC timezone is required")
            except ValueError:
                issues.append(
                    Issue(
                        "ERROR",
                        "INVALID_CALCULATION_TIMESTAMP",
                        "use an ISO 8601 UTC timestamp, e.g. 2026-08-02T00:00:00Z",
                        row_number,
                        "calculated_at_utc",
                    )
                )


def validate_date_and_reviewers(row: Mapping[str, object], row_number: int, issues: list[Issue]) -> None:
    raw_date = clean(row.get("extraction_date"))
    if raw_date:
        try:
            date.fromisoformat(raw_date)
        except ValueError:
            issues.append(Issue("ERROR", "INVALID_DATE", "use ISO format YYYY-MM-DD", row_number, "extraction_date"))

    extractor = clean(row.get("extractor")).casefold()
    verifier = clean(row.get("verifier")).casefold()
    if extractor and verifier and extractor == verifier:
        issues.append(
            Issue(
                "WARNING",
                "SAME_EXTRACTOR_AND_VERIFIER",
                "extractor and verifier are identical; confirm the planned independent review procedure",
                row_number,
                "extractor/verifier",
            )
        )


def validate_rows(
    rows: Iterable[Mapping[str, object]], tolerance: float, stage: str
) -> tuple[list[Issue], int]:
    issues: list[Issue] = []
    seen_effects: dict[str, int] = {}
    effects_by_study: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    analysis_scales: dict[str, list[int]] = defaultdict(list)
    data_rows = 0

    for row_number, row in enumerate(rows, start=2):
        if None in row:
            extras = row.get(None)
            issues.append(
                Issue("ERROR", "EXTRA_CELLS", f"row has data beyond the header: {extras!r}", row_number)
            )

        if not any(clean(value) for key, value in row.items() if key is not None):
            continue
        data_rows += 1

        validate_required_values(row, row_number, issues, stage)
        validate_contract_metadata(row, row_number, issues, stage)
        validate_controlled_values(row, row_number, issues, stage)
        validate_numeric_fields(row, row_number, issues, tolerance, stage)
        validate_date_and_reviewers(row, row_number, issues)

        if stage == ANALYSIS_STAGE:
            analysis_scale = clean(row.get("analysis_scale")).lower()
            if analysis_scale:
                analysis_scales[analysis_scale].append(row_number)

        effect_id = clean(row.get("effect_id"))
        if effect_id:
            if effect_id in seen_effects:
                issues.append(
                    Issue(
                        "ERROR",
                        "DUPLICATE_EFFECT_ID",
                        f"also used at row {seen_effects[effect_id]}",
                        row_number,
                        "effect_id",
                    )
                )
            else:
                seen_effects[effect_id] = row_number

        study_id = clean(row.get("study_id"))
        if study_id and effect_id:
            effects_by_study[study_id].append((effect_id, row_number, clean(row.get("dependency_cluster"))))

    if data_rows == 0:
        issues.append(Issue("WARNING", "NO_DATA_ROWS", "CSV contains a header but no non-empty data rows"))

    for study_id, effects in sorted(effects_by_study.items()):
        if len(effects) > 1:
            missing_clusters = [effect_id for effect_id, _row, cluster in effects if not cluster]
            cluster_note = ""
            if missing_clusters:
                cluster_note = f" Missing dependency_cluster for: {', '.join(missing_clusters)}."
            issues.append(
                Issue(
                    "WARNING",
                    "MULTIPLE_EFFECTS_PER_STUDY",
                    f"study_id={study_id!r} has {len(effects)} effect rows; review duplication and model statistical dependence.{cluster_note}",
                )
            )

    if stage == ANALYSIS_STAGE and len(analysis_scales) > 1:
        detail = "; ".join(
            f"{scale}: rows {','.join(map(str, row_numbers))}"
            for scale, row_numbers in sorted(analysis_scales.items())
        )
        issues.append(
            Issue(
                "ERROR",
                "MIXED_ANALYSIS_SCALES",
                f"one analysis_effect CSV must use one analysis_scale for yi/vi; found {detail}",
                field="yi/vi/analysis_scale",
            )
        )

    return issues, data_rows


def read_and_validate(
    path: Path, encoding: str, tolerance: float, requested_stage: str
) -> tuple[list[Issue], int, str]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        rows = list(reader)
        stage, stage_issues = detect_stage(reader.fieldnames, rows, requested_stage)
        if stage is None:
            return stage_issues, 0, "undetermined"
        header_issues = validate_headers(reader.fieldnames, stage)
        if any(issue.severity == "ERROR" for issue in header_issues):
            return stage_issues + header_issues, 0, stage
        row_issues, data_rows = validate_rows(rows, tolerance, stage)
        return stage_issues + header_issues + row_issues, data_rows, stage


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        issues, data_rows, stage = read_and_validate(
            args.csv_file, args.encoding, args.tolerance, args.stage
        )
    except (OSError, UnicodeError, LookupError, csv.Error) as exc:
        print(f"FATAL code=INPUT_FAILURE: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    errors = [issue for issue in issues if issue.severity == "ERROR"]
    warnings = [issue for issue in issues if issue.severity == "WARNING"]
    for issue in issues:
        print(issue.render())
    print(f"SUMMARY stage={stage} rows={data_rows} errors={len(errors)} warnings={len(warnings)}")

    if errors:
        return EXIT_VALIDATION_ERROR
    if warnings and not args.allow_warnings:
        return EXIT_WARNINGS
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
