#!/usr/bin/env python3
"""Validate the report-to-study identity map used before extraction.

The validator blocks missing sources or primary reports, an unexplained report
mapped to multiple studies, and every unresolved participant/sample overlap.
It never guesses report clusters or rewrites the map.

Exit codes:
    0: map is valid
    1: one or more map validation errors
    2: usage, path, encoding, CSV, or output failure
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_ERROR = 2
SCHEMA_VERSION = "1.0.0"
REQUIRED_HEADERS = {
    "schema_version",
    "study_id",
    "report_id",
    "report_role",
    "is_primary_report",
    "source_type",
    "source_locator",
    "mapping_evidence",
    "multi_study_reason",
    "overlap_status",
    "overlap_with_report_ids",
    "overlap_evidence",
    "overlap_resolution",
    "reviewer_1",
    "reviewer_2",
    "adjudicator",
    "decision_date",
    "notes",
}
REPORT_ROLES = {
    "primary",
    "secondary",
    "protocol",
    "registry",
    "supplement",
    "correction",
    "data",
    "code",
    "other",
}
SOURCE_TYPES = {
    "journal_article",
    "preprint",
    "registry",
    "protocol",
    "thesis",
    "conference_abstract",
    "institutional_report",
    "supplement",
    "dataset",
    "correction",
    "other",
}
OVERLAP_STATUSES = {
    "none",
    "resolved_same_study",
    "resolved_distinct_studies",
    "unresolved",
}
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


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    row: int | None = None
    study_id: str | None = None
    report_id: str | None = None
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


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Validate a study-report map without inferring or rewriting study identity.",
        epilog="Exit codes: 0=valid, 1=validation errors, 2=usage/input/output failure.",
    )
    parser.add_argument("map_csv", type=Path, help="UTF-8 study-report map CSV")
    parser.add_argument(
        "--json-report",
        type=Path,
        help="Atomically write a new UTF-8 JSON validation report; existing files are never replaced",
    )
    return parser


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def validate_paths(input_path: Path, report_path: Path | None) -> tuple[Path, Path | None]:
    source = Path(normalized_path(input_path))
    if not source.exists():
        raise RuntimeError(f"study-report map does not exist: {source}")
    if not source.is_file():
        raise RuntimeError(f"study-report map is not a regular file: {source}")
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


def split_report_ids(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in value.split(";")]


def validate_map(path: Path) -> tuple[list[Issue], dict[str, Any]]:
    header, numbered_rows = read_csv(path)
    issues: list[Issue] = []
    missing_headers = sorted(REQUIRED_HEADERS - set(header))
    if missing_headers:
        issues.append(Issue("MISSING_COLUMNS", f"required columns missing: {', '.join(missing_headers)}"))
        return issues, {"rows": len(numbered_rows), "studies": 0, "reports": 0}
    if not numbered_rows:
        issues.append(Issue("NO_MAPPINGS", "CSV contains no non-empty mapping rows"))
        return issues, {"rows": 0, "studies": 0, "reports": 0}

    rows_by_study: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    rows_by_report: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    report_to_studies: dict[str, set[str]] = defaultdict(set)
    seen_pairs: dict[tuple[str, str], int] = {}
    overlap_counts: Counter[str] = Counter()

    for row_number, row in numbered_rows:
        study_id = clean(row["study_id"])
        report_id = clean(row["report_id"])
        context = {"row": row_number, "study_id": study_id or None, "report_id": report_id or None}

        for field in (
            "schema_version",
            "study_id",
            "report_id",
            "report_role",
            "is_primary_report",
            "source_type",
            "source_locator",
            "mapping_evidence",
            "overlap_status",
            "reviewer_1",
            "reviewer_2",
            "decision_date",
        ):
            if not clean(row[field]):
                issues.append(Issue("MISSING_VALUE", "required value is blank", field=field, **context))

        if row["study_id"] != study_id or row["report_id"] != report_id:
            issues.append(
                Issue(
                    "PADDED_IDENTIFIER",
                    "study_id and report_id must not contain leading or trailing whitespace",
                    field="study_id/report_id",
                    **context,
                )
            )
        if clean(row["schema_version"]) and clean(row["schema_version"]) != SCHEMA_VERSION:
            issues.append(
                Issue(
                    "UNSUPPORTED_SCHEMA_VERSION",
                    f"schema_version must equal {SCHEMA_VERSION}",
                    field="schema_version",
                    **context,
                )
            )

        role = token(row["report_role"])
        if role and role not in REPORT_ROLES:
            issues.append(
                Issue(
                    "UNKNOWN_REPORT_ROLE",
                    f"use one of {sorted(REPORT_ROLES)}",
                    field="report_role",
                    **context,
                )
            )
        primary = token(row["is_primary_report"])
        if primary not in {"yes", "no"}:
            issues.append(
                Issue("INVALID_PRIMARY_FLAG", "use yes or no", field="is_primary_report", **context)
            )
        elif primary == "yes" and role != "primary":
            issues.append(
                Issue(
                    "PRIMARY_ROLE_MISMATCH",
                    "is_primary_report=yes requires report_role=primary",
                    field="report_role",
                    **context,
                )
            )
        elif primary == "no" and role == "primary":
            issues.append(
                Issue(
                    "PRIMARY_ROLE_MISMATCH",
                    "report_role=primary requires is_primary_report=yes",
                    field="is_primary_report",
                    **context,
                )
            )

        source_type = token(row["source_type"])
        if source_type and source_type not in SOURCE_TYPES:
            issues.append(
                Issue(
                    "UNKNOWN_SOURCE_TYPE",
                    f"use one of {sorted(SOURCE_TYPES)}",
                    field="source_type",
                    **context,
                )
            )
        if not meaningful(row["source_locator"]):
            issues.append(
                Issue(
                    "MISSING_SOURCE",
                    "source_locator must identify a DOI, URL, repository path, accession, or citation",
                    field="source_locator",
                    **context,
                )
            )
        if not meaningful(row["mapping_evidence"]):
            issues.append(
                Issue(
                    "MISSING_MAPPING_EVIDENCE",
                    "mapping_evidence must explain why the report belongs to this study",
                    field="mapping_evidence",
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
        raw_date = clean(row["decision_date"])
        if raw_date:
            try:
                decision_date = parse_date(raw_date)
            except ValueError:
                issues.append(
                    Issue(
                        "INVALID_DECISION_DATE",
                        "use canonical ISO date YYYY-MM-DD",
                        field="decision_date",
                        **context,
                    )
                )
            else:
                if decision_date > datetime.now(timezone.utc).date():
                    issues.append(
                        Issue(
                            "FUTURE_DECISION_DATE",
                            "decision date cannot be in the future (UTC)",
                            field="decision_date",
                            **context,
                        )
                    )

        overlap_status = token(row["overlap_status"])
        overlap_counts[overlap_status] += 1
        if overlap_status not in OVERLAP_STATUSES:
            issues.append(
                Issue(
                    "UNKNOWN_OVERLAP_STATUS",
                    f"use one of {sorted(OVERLAP_STATUSES)}",
                    field="overlap_status",
                    **context,
                )
            )
        elif overlap_status == "unresolved":
            issues.append(
                Issue(
                    "UNRESOLVED_OVERLAP",
                    "unresolved participant/sample overlap blocks synthesis",
                    field="overlap_status",
                    **context,
                )
            )
        elif overlap_status == "none":
            if any(
                clean(row[field])
                for field in ("overlap_with_report_ids", "overlap_evidence", "overlap_resolution")
            ):
                issues.append(
                    Issue(
                        "CONTRADICTORY_OVERLAP_FIELDS",
                        "overlap_status=none requires all overlap detail fields to be blank",
                        field="overlap_status",
                        **context,
                    )
                )
        elif overlap_status in {"resolved_same_study", "resolved_distinct_studies"}:
            for field in ("overlap_with_report_ids", "overlap_evidence", "overlap_resolution", "adjudicator"):
                if not meaningful(row[field]):
                    issues.append(
                        Issue(
                            "INCOMPLETE_OVERLAP_RESOLUTION",
                            "resolved overlap requires linked reports, evidence, resolution, and adjudicator",
                            field=field,
                            **context,
                        )
                    )

        if study_id and report_id:
            pair = (study_id, report_id)
            if pair in seen_pairs:
                issues.append(
                    Issue(
                        "DUPLICATE_MAPPING",
                        f"mapping already appears at row {seen_pairs[pair]}",
                        **context,
                    )
                )
            else:
                seen_pairs[pair] = row_number
            rows_by_study[study_id].append((row_number, row))
            rows_by_report[report_id].append((row_number, row))
            report_to_studies[report_id].add(study_id)

    for study_id, study_rows in rows_by_study.items():
        primary_rows = [
            (row_number, row)
            for row_number, row in study_rows
            if token(row["is_primary_report"]) == "yes"
        ]
        if not primary_rows:
            issues.append(
                Issue(
                    "MISSING_PRIMARY_REPORT",
                    "every study must designate exactly one primary report",
                    study_id=study_id,
                    field="is_primary_report",
                )
            )
        elif len(primary_rows) > 1:
            issues.append(
                Issue(
                    "MULTIPLE_PRIMARY_REPORTS",
                    "every study must designate exactly one primary report",
                    study_id=study_id,
                    field="is_primary_report",
                )
            )

    for report_id, report_rows in rows_by_report.items():
        studies = report_to_studies[report_id]
        report_context = {"report_id": report_id}
        source_pairs = {
            (token(row["source_type"]), clean(row["source_locator"])) for _, row in report_rows
        }
        if len(source_pairs) > 1:
            issues.append(
                Issue(
                    "INCONSISTENT_REPORT_SOURCE",
                    "the same report_id must keep one source_type and source_locator",
                    field="source_type/source_locator",
                    **report_context,
                )
            )
        if len(studies) > 1:
            reasons = {clean(row["multi_study_reason"]) for _, row in report_rows}
            if any(not meaningful(reason) for reason in reasons):
                issues.append(
                    Issue(
                        "UNEXPLAINED_MULTI_STUDY_REPORT",
                        "a report mapped to multiple studies requires a reason on every mapping row",
                        field="multi_study_reason",
                        **report_context,
                    )
                )
            if len(reasons) != 1:
                issues.append(
                    Issue(
                        "INCONSISTENT_MULTI_STUDY_REASON",
                        "all mappings for a multi-study report must use the same reason",
                        field="multi_study_reason",
                        **report_context,
                    )
                )

    known_reports = set(rows_by_report)
    for row_number, row in numbered_rows:
        status = token(row["overlap_status"])
        if status not in {"resolved_same_study", "resolved_distinct_studies"}:
            continue
        study_id = clean(row["study_id"])
        report_id = clean(row["report_id"])
        linked = split_report_ids(row["overlap_with_report_ids"])
        if any(not value for value in linked):
            issues.append(
                Issue(
                    "BLANK_OVERLAP_REFERENCE",
                    "semicolon-separated overlap report IDs must not contain blanks",
                    row=row_number,
                    study_id=study_id,
                    report_id=report_id,
                    field="overlap_with_report_ids",
                )
            )
        if len(set(linked)) != len(linked):
            issues.append(
                Issue(
                    "DUPLICATE_OVERLAP_REFERENCE",
                    "overlap report IDs must be unique",
                    row=row_number,
                    study_id=study_id,
                    report_id=report_id,
                    field="overlap_with_report_ids",
                )
            )
        for linked_report in linked:
            if linked_report == report_id:
                issues.append(
                    Issue(
                        "SELF_OVERLAP_REFERENCE",
                        "a report cannot cite itself as the overlapping report",
                        row=row_number,
                        study_id=study_id,
                        report_id=report_id,
                        field="overlap_with_report_ids",
                    )
                )
            elif linked_report not in known_reports:
                issues.append(
                    Issue(
                        "UNKNOWN_OVERLAP_REPORT",
                        f"linked report_id is not present in the map: {linked_report}",
                        row=row_number,
                        study_id=study_id,
                        report_id=report_id,
                        field="overlap_with_report_ids",
                    )
                )
            elif status == "resolved_same_study" and study_id not in report_to_studies[linked_report]:
                issues.append(
                    Issue(
                        "SAME_STUDY_OVERLAP_CONTRADICTION",
                        f"linked report {linked_report} is not mapped to study {study_id}",
                        row=row_number,
                        study_id=study_id,
                        report_id=report_id,
                        field="overlap_with_report_ids",
                    )
                )
            elif status == "resolved_distinct_studies" and study_id in report_to_studies[linked_report]:
                issues.append(
                    Issue(
                        "DISTINCT_STUDY_OVERLAP_CONTRADICTION",
                        f"linked report {linked_report} is also mapped to study {study_id}",
                        row=row_number,
                        study_id=study_id,
                        report_id=report_id,
                        field="overlap_with_report_ids",
                    )
                )

    summary = {
        "rows": len(numbered_rows),
        "studies": len(rows_by_study),
        "reports": len(rows_by_report),
        "multi_study_reports": sum(len(studies) > 1 for studies in report_to_studies.values()),
        "overlap_statuses": dict(sorted(overlap_counts.items())),
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
    try:
        source, report_target = validate_paths(args.map_csv, args.json_report)
        issues, summary = validate_map(source)
    except (RuntimeError, OSError, UnicodeError, csv.Error) as exc:
        emit({"status": "error", "errors": [{"code": "INPUT_FAILURE", "message": str(exc)}]}, sys.stderr)
        return EXIT_INPUT_ERROR

    payload = {
        "status": "ok" if not issues else "error",
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
