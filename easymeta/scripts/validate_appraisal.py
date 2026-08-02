#!/usr/bin/env python3
"""Validate generic, human-final risk-of-bias and certainty ledgers.

The schemas store domain evidence and independent human judgements without
reproducing any proprietary tool's signalling questions.  The validator is
structural only: it never calculates scores, domain judgements, upgrades,
downgrades, overall risk, or final certainty.

Exit codes:
    0: appraisal ledger is valid
    1: one or more appraisal validation errors
    2: usage, path, encoding, CSV, or output failure
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence


EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_ERROR = 2
SCHEMA_VERSION = "1.0.0"

COMMON_HEADERS = {
    "schema_version",
    "appraisal_type",
    "domain_id",
    "domain_label",
    "tool_name",
    "tool_version",
    "tool_variant",
    "supporting_source_id",
    "supporting_locator",
    "supporting_evidence",
    "reviewer_1",
    "judgement_1",
    "rationale_1",
    "reviewer_2",
    "judgement_2",
    "rationale_2",
    "adjudication_status",
    "adjudicator",
    "adjudication_date",
    "adjudication_rationale",
    "final_domain_judgement",
    "final_domain_rationale",
    "human_final_confirmed",
    "final_decider",
    "final_decision_date",
    "automation_used",
    "automation_role",
    "notes",
}
RISK_HEADERS = COMMON_HEADERS | {
    "study_id",
    "result_id",
    "overall_judgement",
    "overall_rationale",
}
CERTAINTY_HEADERS = COMMON_HEADERS | {
    "evidence_body_id",
    "population",
    "comparison",
    "outcome",
    "time_horizon",
    "estimand",
    "starting_certainty",
    "final_certainty",
    "final_certainty_rationale",
}
TYPE_HEADERS = {
    "risk_of_bias": RISK_HEADERS,
    "certainty": CERTAINTY_HEADERS,
}
ADJUDICATION_STATUSES = {"agreement", "adjudicated"}
EMPTY_MARKERS = {
    "",
    "na",
    "n/a",
    "none",
    "unknown",
    "pending",
    "tbd",
    "todo",
    "unresolved",
    "not_checked",
    "not checked",
}
BANNED_HEADER_TOKENS = {
    "score",
    "scores",
    "points",
    "total_score",
    "quality_score",
    "weighted_score",
    "quality_weight",
    "automatic_upgrade",
    "automatic_downgrade",
}


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    row: int | None = None
    assessment_id: str | None = None
    domain_id: str | None = None
    field: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit({"status": "error", "errors": [{"code": "USAGE_ERROR", "message": message}]}, sys.stderr)
        raise SystemExit(EXIT_INPUT_ERROR)


def emit(payload: Mapping[str, Any], stream: Any) -> None:
    json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
    stream.write("\n")


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def token(value: object) -> str:
    return clean(value).casefold().replace("-", "_").replace(" ", "_")


def meaningful(value: object) -> bool:
    return clean(value).casefold().replace("-", "_") not in EMPTY_MARKERS


def same_judgement(left: object, right: object) -> bool:
    normalize = lambda value: " ".join(clean(value).casefold().split())
    return normalize(left) == normalize(right)


def numeric_only(value: object) -> bool:
    candidate = clean(value)
    if not candidate:
        return False
    try:
        parsed = Decimal(candidate)
    except InvalidOperation:
        return False
    return parsed.is_finite()


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Validate generic risk-of-bias or body-of-evidence certainty CSVs.",
        epilog="Exit codes: 0=valid, 1=validation errors, 2=usage/input/output failure.",
    )
    parser.add_argument(
        "kind",
        choices=("risk-of-bias", "certainty"),
        help="risk-of-bias is result-level; certainty is evidence-body-level",
    )
    parser.add_argument("csv_file", type=Path, help="UTF-8 appraisal CSV")
    parser.add_argument(
        "--json-report",
        type=Path,
        help="Atomically write a new UTF-8 JSON report; existing files are never replaced",
    )
    return parser


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def validate_paths(input_path: Path, report_path: Path | None) -> tuple[Path, Path | None]:
    source = Path(normalized_path(input_path))
    if not source.exists():
        raise RuntimeError(f"appraisal CSV does not exist: {source}")
    if not source.is_file():
        raise RuntimeError(f"appraisal CSV is not a regular file: {source}")
    if report_path is None:
        return source, None
    target = Path(normalized_path(report_path))
    if normalized_path(source) == normalized_path(target):
        raise RuntimeError("JSON report must not be the same path as the input CSV")
    if target.exists():
        raise RuntimeError(f"JSON report already exists and will not be overwritten: {target}")
    if not target.parent.exists() or not target.parent.is_dir():
        raise RuntimeError(f"JSON report parent directory does not exist: {target.parent}")
    return source, target


def read_csv(path: Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            raw_header = next(reader)
        except StopIteration as exc:
            raise RuntimeError("CSV has no header row") from exc
        header = [name.strip() for name in raw_header]
        if any(not name for name in header):
            raise RuntimeError("CSV contains a blank column name")
        duplicates = sorted({name for name in header if header.count(name) > 1})
        if duplicates:
            raise RuntimeError(f"CSV contains duplicate columns: {', '.join(duplicates)}")
        rows: list[tuple[int, dict[str, str]]] = []
        for row_number, values in enumerate(reader, start=2):
            if not values or not any(value != "" for value in values):
                continue
            if len(values) != len(header):
                raise RuntimeError(
                    f"CSV row {row_number} has {len(values)} cells but header has {len(header)}"
                )
            if any("\x00" in value for value in values):
                raise RuntimeError(f"CSV row {row_number} contains a NUL byte")
            rows.append((row_number, dict(zip(header, values))))
    return header, rows


def parse_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must use canonical YYYY-MM-DD")
    return parsed


def header_policy_issues(header: Sequence[str]) -> list[Issue]:
    issues: list[Issue] = []
    for name in header:
        normalized = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
        parts = set(normalized.split("_"))
        if (
            normalized in BANNED_HEADER_TOKENS
            or normalized.endswith("_score")
            or normalized.endswith("_points")
            or normalized.endswith("_weight")
            or "score" in parts
        ):
            issues.append(
                Issue(
                    "SCORING_COLUMN_FORBIDDEN",
                    "appraisal schemas must not contain scores, point totals, or quality weights",
                    field=name,
                )
            )
        if (
            "signaling" in parts
            or "signalling" in parts
            or normalized.startswith("sq_")
            or normalized.startswith("question_")
        ):
            issues.append(
                Issue(
                    "SIGNALLING_QUESTION_COLUMN_FORBIDDEN",
                    "store generic domain support; do not copy tool signalling questions into this schema",
                    field=name,
                )
            )
        if ("automatic" in parts or "auto" in parts) and (
            "upgrade" in parts or "downgrade" in parts
        ):
            issues.append(
                Issue(
                    "AUTOMATIC_CERTAINTY_CHANGE_FORBIDDEN",
                    "automatic upgrading or downgrading is forbidden",
                    field=name,
                )
            )
    return issues


def assessment_id(kind: str, row: Mapping[str, str]) -> str:
    return clean(row["result_id"] if kind == "risk_of_bias" else row["evidence_body_id"])


def validate_common_row(
    kind: str, row_number: int, row: Mapping[str, str], issues: list[Issue]
) -> None:
    current_id = assessment_id(kind, row)
    domain_id = clean(row["domain_id"])
    context = {"row": row_number, "assessment_id": current_id or None, "domain_id": domain_id or None}
    expected_type = kind

    if clean(row["schema_version"]) != SCHEMA_VERSION:
        issues.append(
            Issue(
                "UNSUPPORTED_SCHEMA_VERSION",
                f"schema_version must equal {SCHEMA_VERSION}",
                field="schema_version",
                **context,
            )
        )
    if token(row["appraisal_type"]) != expected_type:
        issues.append(
            Issue(
                "APPRAISAL_TYPE_MISMATCH",
                f"appraisal_type must equal {expected_type}",
                field="appraisal_type",
                **context,
            )
        )

    for field in (
        "domain_id",
        "domain_label",
        "tool_name",
        "tool_version",
        "supporting_source_id",
        "supporting_locator",
        "supporting_evidence",
        "reviewer_1",
        "judgement_1",
        "rationale_1",
        "reviewer_2",
        "judgement_2",
        "rationale_2",
        "adjudication_status",
        "final_domain_judgement",
        "final_domain_rationale",
        "human_final_confirmed",
        "final_decider",
        "final_decision_date",
        "automation_used",
        "automation_role",
    ):
        if not clean(row[field]):
            issues.append(Issue("MISSING_VALUE", "required value is blank", field=field, **context))

    for field in ("tool_name", "tool_version", "supporting_source_id", "supporting_locator", "supporting_evidence"):
        if clean(row[field]) and not meaningful(row[field]):
            issues.append(
                Issue(
                    "NONINFORMATIVE_VALUE",
                    "value must identify the selected tool/version or auditable source location",
                    field=field,
                    **context,
                )
            )

    reviewer_1 = clean(row["reviewer_1"])
    reviewer_2 = clean(row["reviewer_2"])
    if reviewer_1 and reviewer_2 and reviewer_1.casefold() == reviewer_2.casefold():
        issues.append(
            Issue(
                "REVIEWERS_NOT_INDEPENDENT",
                "reviewer_1 and reviewer_2 must identify different people",
                field="reviewer_2",
                **context,
            )
        )

    for field in ("judgement_1", "judgement_2", "final_domain_judgement"):
        if numeric_only(row[field]):
            issues.append(
                Issue(
                    "NUMERIC_JUDGEMENT_FORBIDDEN",
                    "judgements must be named categories, never numeric scores",
                    field=field,
                    **context,
                )
            )

    status = token(row["adjudication_status"])
    judgements_agree = same_judgement(row["judgement_1"], row["judgement_2"])
    if status not in ADJUDICATION_STATUSES:
        issues.append(
            Issue(
                "UNKNOWN_ADJUDICATION_STATUS",
                "use agreement or adjudicated",
                field="adjudication_status",
                **context,
            )
        )
    elif judgements_agree:
        if status != "agreement":
            issues.append(
                Issue(
                    "ADJUDICATION_STATUS_CONTRADICTION",
                    "matching independent judgements require adjudication_status=agreement",
                    field="adjudication_status",
                    **context,
                )
            )
        if clean(row["final_domain_judgement"]) and not same_judgement(
            row["final_domain_judgement"], row["judgement_1"]
        ):
            issues.append(
                Issue(
                    "AGREEMENT_FINAL_MISMATCH",
                    "when reviewers agree, final_domain_judgement must preserve that judgement",
                    field="final_domain_judgement",
                    **context,
                )
            )
        if any(clean(row[field]) for field in ("adjudicator", "adjudication_date", "adjudication_rationale")):
            issues.append(
                Issue(
                    "UNEXPECTED_ADJUDICATION",
                    "agreement rows must leave adjudication-only fields blank",
                    field="adjudicator/adjudication_date/adjudication_rationale",
                    **context,
                )
            )
    else:
        if status != "adjudicated":
            issues.append(
                Issue(
                    "UNADJUDICATED_DISAGREEMENT",
                    "different independent judgements require adjudication_status=adjudicated",
                    field="adjudication_status",
                    **context,
                )
            )
        for field in ("adjudicator", "adjudication_date", "adjudication_rationale"):
            if not meaningful(row[field]):
                issues.append(
                    Issue(
                        "INCOMPLETE_ADJUDICATION",
                        "reviewer disagreement requires adjudicator, date, and rationale",
                        field=field,
                        **context,
                    )
                )

    for field in ("adjudication_date", "final_decision_date"):
        raw_date = clean(row[field])
        if not raw_date:
            continue
        try:
            parsed_date = parse_date(raw_date)
        except ValueError:
            issues.append(
                Issue(
                    "INVALID_DATE",
                    "use canonical ISO date YYYY-MM-DD",
                    field=field,
                    **context,
                )
            )
        else:
            if parsed_date > datetime.now(timezone.utc).date():
                issues.append(
                    Issue(
                        "FUTURE_DATE",
                        "appraisal dates cannot be in the future (UTC)",
                        field=field,
                        **context,
                    )
                )

    if token(row["human_final_confirmed"]) != "yes":
        issues.append(
            Issue(
                "HUMAN_FINAL_REQUIRED",
                "human_final_confirmed must equal yes; machine proposals are never final",
                field="human_final_confirmed",
                **context,
            )
        )
    automation_used = token(row["automation_used"])
    automation_role = token(row["automation_role"])
    if automation_used not in {"yes", "no"}:
        issues.append(
            Issue("INVALID_AUTOMATION_FLAG", "use yes or no", field="automation_used", **context)
        )
    elif automation_used == "no" and automation_role != "none":
        issues.append(
            Issue(
                "AUTOMATION_ROLE_CONTRADICTION",
                "automation_used=no requires automation_role=none",
                field="automation_role",
                **context,
            )
        )
    elif automation_used == "yes" and automation_role != "support_only":
        issues.append(
            Issue(
                "AUTOMATED_FINAL_FORBIDDEN",
                "automation may be recorded only as support_only; it cannot make final judgements",
                field="automation_role",
                **context,
            )
        )


def validate_appraisal(path: Path, kind: str) -> tuple[list[Issue], dict[str, Any]]:
    header, numbered_rows = read_csv(path)
    issues = header_policy_issues(header)
    required = TYPE_HEADERS[kind]
    missing_headers = sorted(required - set(header))
    if missing_headers:
        issues.append(Issue("MISSING_COLUMNS", f"required columns missing: {', '.join(missing_headers)}"))
        return issues, {"rows": len(numbered_rows), "assessments": 0, "domains": 0}
    if not numbered_rows:
        issues.append(Issue("NO_APPRAISALS", "CSV contains no non-empty appraisal rows"))
        return issues, {"rows": 0, "assessments": 0, "domains": 0}

    rows_by_assessment: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    seen_domains: dict[tuple[str, str], int] = {}
    adjudication_counts: Counter[str] = Counter()

    for row_number, row in numbered_rows:
        current_id = assessment_id(kind, row)
        domain_id = clean(row["domain_id"])
        context = {"row": row_number, "assessment_id": current_id or None, "domain_id": domain_id or None}
        id_fields = ("study_id", "result_id") if kind == "risk_of_bias" else (
            "evidence_body_id",
            "population",
            "comparison",
            "outcome",
            "time_horizon",
            "estimand",
        )
        for field in id_fields:
            if not clean(row[field]):
                issues.append(Issue("MISSING_VALUE", "required assessment identity is blank", field=field, **context))

        validate_common_row(kind, row_number, row, issues)
        adjudication_counts[token(row["adjudication_status"])] += 1

        if kind == "risk_of_bias":
            for field in ("overall_judgement", "overall_rationale"):
                if not clean(row[field]):
                    issues.append(Issue("MISSING_VALUE", "result-level final conclusion is blank", field=field, **context))
            if numeric_only(row["overall_judgement"]):
                issues.append(
                    Issue(
                        "NUMERIC_JUDGEMENT_FORBIDDEN",
                        "overall judgement must be a named category, never a score",
                        field="overall_judgement",
                        **context,
                    )
                )
        else:
            for field in ("starting_certainty", "final_certainty", "final_certainty_rationale"):
                if not clean(row[field]):
                    issues.append(Issue("MISSING_VALUE", "body-level certainty conclusion is blank", field=field, **context))
            for field in ("starting_certainty", "final_certainty"):
                if numeric_only(row[field]):
                    issues.append(
                        Issue(
                            "NUMERIC_CERTAINTY_FORBIDDEN",
                            "certainty must be a named category, never a numeric score",
                            field=field,
                            **context,
                        )
                    )

        if current_id and domain_id:
            key = (current_id, domain_id)
            if key in seen_domains:
                issues.append(
                    Issue(
                        "DUPLICATE_DOMAIN",
                        f"assessment/domain already appears at row {seen_domains[key]}",
                        **context,
                    )
                )
            else:
                seen_domains[key] = row_number
            rows_by_assessment[current_id].append((row_number, row))

    for current_id, assessment_rows in rows_by_assessment.items():
        if kind == "risk_of_bias":
            invariant_fields = (
                "study_id",
                "tool_name",
                "tool_version",
                "tool_variant",
                "overall_judgement",
                "overall_rationale",
                "human_final_confirmed",
                "final_decider",
                "final_decision_date",
            )
        else:
            invariant_fields = (
                "population",
                "comparison",
                "outcome",
                "time_horizon",
                "estimand",
                "tool_name",
                "tool_version",
                "tool_variant",
                "starting_certainty",
                "final_certainty",
                "final_certainty_rationale",
                "human_final_confirmed",
                "final_decider",
                "final_decision_date",
            )
        for field in invariant_fields:
            values = {clean(row[field]) for _, row in assessment_rows}
            if len(values) > 1:
                issues.append(
                    Issue(
                        "INCONSISTENT_ASSESSMENT_FIELD",
                        f"{field} must be identical across all domains in one assessment",
                        assessment_id=current_id,
                        field=field,
                    )
                )

    summary = {
        "rows": len(numbered_rows),
        "assessments": len(rows_by_assessment),
        "domains": len(seen_domains),
        "adjudication_statuses": dict(sorted(adjudication_counts.items())),
        "scores_calculated": False,
        "automatic_final_judgements": False,
    }
    return issues, summary


def atomic_write_json_no_clobber(target: Path, payload: Mapping[str, Any]) -> None:
    data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "nt":
            os.rename(temporary, target)
        else:
            os.link(temporary, target)
            os.unlink(temporary)
        temporary = None
    except OSError as exc:
        if target.exists():
            raise RuntimeError(f"JSON report already exists and will not be overwritten: {target}") from exc
        raise RuntimeError(f"could not atomically write UTF-8 JSON report {target}: {exc}") from exc
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
    kind = args.kind.replace("-", "_")
    try:
        source, report_target = validate_paths(args.csv_file, args.json_report)
        issues, summary = validate_appraisal(source, kind)
    except (RuntimeError, OSError, UnicodeError, csv.Error) as exc:
        emit({"status": "error", "errors": [{"code": "INPUT_FAILURE", "message": str(exc)}]}, sys.stderr)
        return EXIT_INPUT_ERROR

    payload = {
        "status": "ok" if not issues else "error",
        "kind": kind,
        "file": str(source),
        **summary,
        "errors": [issue.as_json() for issue in issues],
        "summary": {"errors": len(issues)},
    }
    if report_target is not None:
        try:
            atomic_write_json_no_clobber(report_target, payload)
        except RuntimeError as exc:
            emit({"status": "error", "errors": [{"code": "OUTPUT_FAILURE", "message": str(exc)}]}, sys.stderr)
            return EXIT_INPUT_ERROR
    emit(payload, sys.stdout if not issues else sys.stderr)
    return EXIT_OK if not issues else EXIT_VALIDATION_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
