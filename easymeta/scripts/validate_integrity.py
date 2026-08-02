#!/usr/bin/env python3
"""Validate per-object publication, data, and code integrity checks.

Every non-empty row must identify a paper/data/code object and record
checked_at, status, source, disposition, and sensitivity_analysis.  Unknown or
unchecked objects fail.  Any non-clear hit also fails unless both disposition
and sensitivity_analysis contain an explicit, non-pending resolution.

Exit codes:
    0: all objects are checked and all hits are disposed
    1: one or more validation errors
    2: usage, input, encoding, or CSV parsing failure
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_ERROR = 2

REQUIRED_HEADERS = {
    "object_type",
    "object_id",
    "checked_at",
    "status",
    "source",
    "disposition",
    "sensitivity_analysis",
}
REQUIRED_VALUES = REQUIRED_HEADERS
OBJECT_TYPES = {"paper", "data", "code"}
STATUSES = {
    "clear",
    "correction",
    "comment",
    "expression_of_concern",
    "retraction",
    "withdrawal",
    "version_update",
    "unknown",
}
UNRESOLVED_MARKERS = {
    "",
    "unknown",
    "unchecked",
    "not_checked",
    "not checked",
    "pending",
    "unresolved",
    "tbd",
    "todo",
    "n/a",
    "na",
    "none",
    "not_applicable",
    "not applicable",
    "not_required",
    "not required",
}


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    row: int | None = None
    field: str | None = None
    object_type: str | None = None
    object_id: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit(
            {
                "status": "error",
                "errors": [{"code": "USAGE_ERROR", "message": message}],
            },
            stream=sys.stderr,
        )
        raise SystemExit(EXIT_INPUT_ERROR)


def emit(payload: Mapping[str, Any], *, stream: Any = sys.stdout) -> None:
    json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
    stream.write("\n")


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def normalize_token(value: object) -> str:
    return clean(value).casefold().replace("-", "_").replace(" ", "_")


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description=(
            "Validate that every paper/data/code object has a dated integrity check "
            "and that every non-clear hit has an explicit disposition and sensitivity analysis."
        ),
        epilog="Exit codes: 0=valid, 1=validation errors, 2=usage/input failure.",
    )
    parser.add_argument("csv_file", type=Path, help="Publication-integrity CSV to validate")
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Input encoding (default: utf-8-sig, which also accepts a UTF-8 BOM)",
    )
    return parser


def validate_headers(fieldnames: Sequence[str] | None) -> tuple[list[str], list[Issue]]:
    if not fieldnames:
        return [], [Issue("MISSING_HEADER", "CSV has no header row")]
    normalized = [clean(name) for name in fieldnames]
    issues: list[Issue] = []
    if any(not name for name in normalized):
        issues.append(Issue("BLANK_HEADER", "CSV contains a blank column name"))
    duplicates = sorted({name for name in normalized if name and normalized.count(name) > 1})
    if duplicates:
        issues.append(Issue("DUPLICATE_HEADER", f"duplicate columns: {', '.join(duplicates)}"))
    missing = sorted(REQUIRED_HEADERS - set(normalized))
    if missing:
        issues.append(Issue("MISSING_COLUMNS", f"required columns missing: {', '.join(missing)}"))
    return normalized, issues


def parse_checked_at(raw: str) -> date:
    candidate = raw.strip()
    try:
        parsed_date = date.fromisoformat(candidate)
    except ValueError:
        datetime_text = candidate[:-1] + "+00:00" if candidate.endswith(("Z", "z")) else candidate
        parsed_datetime = datetime.fromisoformat(datetime_text)
        parsed_date = parsed_datetime.date()
    return parsed_date


def is_unresolved(value: str) -> bool:
    normalized = normalize_token(value)
    return normalized in {marker.replace(" ", "_") for marker in UNRESOLVED_MARKERS}


def validate_row(row: Mapping[str, object], row_number: int) -> list[Issue]:
    object_type = normalize_token(row.get("object_type"))
    object_id = clean(row.get("object_id"))
    context = {"row": row_number, "object_type": object_type or None, "object_id": object_id or None}
    issues: list[Issue] = []

    for field in sorted(REQUIRED_VALUES):
        if not clean(row.get(field)):
            issues.append(Issue("MISSING_VALUE", "required value is blank", field=field, **context))

    if object_type and object_type not in OBJECT_TYPES:
        issues.append(
            Issue(
                "UNKNOWN_OBJECT_TYPE",
                f"use one of {sorted(OBJECT_TYPES)}",
                field="object_type",
                **context,
            )
        )

    status = normalize_token(row.get("status"))
    if status and status not in STATUSES:
        issues.append(
            Issue("UNKNOWN_STATUS", f"use one of {sorted(STATUSES)}", field="status", **context)
        )

    checked_at = clean(row.get("checked_at"))
    if checked_at:
        try:
            checked_date = parse_checked_at(checked_at)
        except ValueError:
            issues.append(
                Issue(
                    "INVALID_CHECKED_AT",
                    "use ISO 8601 date or datetime, e.g. 2026-08-02 or 2026-08-02T10:30:00Z",
                    field="checked_at",
                    **context,
                )
            )
        else:
            if checked_date > datetime.now(timezone.utc).date():
                issues.append(
                    Issue(
                        "FUTURE_CHECKED_AT",
                        "integrity check date cannot be in the future (UTC)",
                        field="checked_at",
                        **context,
                    )
                )

    if status == "unknown":
        issues.append(
            Issue(
                "UNCHECKED_STATUS",
                "status=unknown does not establish a completed integrity check",
                field="status",
                **context,
            )
        )

    if status and status != "clear" and status in STATUSES:
        disposition = clean(row.get("disposition"))
        sensitivity = clean(row.get("sensitivity_analysis"))
        if is_unresolved(disposition):
            issues.append(
                Issue(
                    "UNDISPOSED_HIT",
                    "non-clear status requires an explicit resolved disposition",
                    field="disposition",
                    **context,
                )
            )
        if is_unresolved(sensitivity):
            issues.append(
                Issue(
                    "UNRESOLVED_SENSITIVITY_ANALYSIS",
                    (
                        "non-clear status requires a completed sensitivity analysis or an explicit "
                        "justification, e.g. 'not_required: object excluded from all syntheses'"
                    ),
                    field="sensitivity_analysis",
                    **context,
                )
            )

    return issues


def read_and_validate(path: Path, encoding: str) -> tuple[list[Issue], int, Counter[str], Counter[str]]:
    issues: list[Issue] = []
    rows_count = 0
    statuses: Counter[str] = Counter()
    object_types: Counter[str] = Counter()
    seen: dict[tuple[str, str], int] = {}

    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        fieldnames, header_issues = validate_headers(reader.fieldnames)
        issues.extend(header_issues)
        if header_issues:
            return issues, rows_count, statuses, object_types
        reader.fieldnames = fieldnames

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                issues.append(Issue("EXTRA_CELLS", "row has data beyond the header", row=row_number))
            if not any(clean(value) for key, value in row.items() if key is not None):
                continue
            rows_count += 1
            object_type = normalize_token(row.get("object_type"))
            object_id = clean(row.get("object_id"))
            status = normalize_token(row.get("status"))
            if object_type:
                object_types[object_type] += 1
            if status:
                statuses[status] += 1
            issues.extend(validate_row(row, row_number))

            if object_type and object_id:
                key = (object_type, object_id.casefold())
                if key in seen:
                    issues.append(
                        Issue(
                            "DUPLICATE_OBJECT",
                            f"object is already recorded at row {seen[key]}",
                            row=row_number,
                            field="object_id",
                            object_type=object_type,
                            object_id=object_id,
                        )
                    )
                else:
                    seen[key] = row_number

    if rows_count == 0:
        issues.append(Issue("NO_OBJECTS", "CSV contains no non-empty object rows"))
    return issues, rows_count, statuses, object_types


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = args.csv_file.expanduser().resolve()
    try:
        if not path.exists():
            raise FileNotFoundError(f"integrity CSV does not exist: {path}")
        if not path.is_file():
            raise OSError(f"integrity CSV is not a regular file: {path}")
        issues, rows_count, statuses, object_types = read_and_validate(path, args.encoding)
    except (OSError, UnicodeError, LookupError, csv.Error) as exc:
        emit(
            {"status": "error", "errors": [{"code": "INPUT_FAILURE", "message": str(exc)}]},
            stream=sys.stderr,
        )
        return EXIT_INPUT_ERROR

    payload = {
        "status": "ok" if not issues else "error",
        "file": str(path),
        "rows": rows_count,
        "object_types": dict(sorted(object_types.items())),
        "statuses": dict(sorted(statuses.items())),
        "errors": [issue.as_json() for issue in issues],
        "summary": {"errors": len(issues)},
    }
    emit(payload, stream=sys.stdout if not issues else sys.stderr)
    return EXIT_OK if not issues else EXIT_VALIDATION_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
