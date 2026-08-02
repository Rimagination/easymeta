#!/usr/bin/env python3
"""Compare two independent extraction CSVs without adjudicating any value.

The comparison grain is ``effect_id`` plus field.  Every comparable cell is
written with both literal values and a deterministic difference type.  A
previous comparison can be supplied as a human resolution ledger; every
substantive difference must then have a final value, evidence, adjudicator,
and ISO date.  This program validates and carries those human decisions into
an audit output, but never creates a curated extraction table.

Exit codes:
    0: no substantive differences, or every substantive difference resolved
    1: extraction or resolution-ledger validation failed
    2: usage, path, encoding, CSV, or output failure
    3: comparison written, but substantive differences remain unresolved
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, timezone, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_ERROR = 2
EXIT_UNRESOLVED = 3
SCHEMA_VERSION = "1.0.0"
KEY_FIELD = "effect_id"
PRESENCE_FIELD = "__record_presence__"
OUTPUT_HEADERS = [
    "schema_version",
    "difference_id",
    "effect_id",
    "field",
    "reviewer_a_value",
    "reviewer_b_value",
    "difference_type",
    "is_substantive",
    "resolution_status",
    "final_value",
    "evidence",
    "adjudicator",
    "adjudication_date",
]
SUBSTANTIVE_TYPES = {"missing_difference", "numeric_difference", "text_difference"}
NONRESOLUTION_MARKERS = {
    "",
    "na",
    "n/a",
    "none",
    "not_applicable",
    "not applicable",
    "pending",
    "tbd",
    "todo",
    "unknown",
    "unresolved",
}


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    file: str | None = None
    row: int | None = None
    effect_id: str | None = None
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


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Compare two extraction CSVs cell by cell; never auto-adjudicate.",
        epilog=(
            "Exit codes: 0=resolved/identical, 1=invalid data or ledger, "
            "2=usage/I/O/CSV failure, 3=unresolved substantive differences."
        ),
    )
    parser.add_argument("reviewer_a", type=Path, help="First independent UTF-8 extraction CSV")
    parser.add_argument("reviewer_b", type=Path, help="Second independent UTF-8 extraction CSV")
    parser.add_argument("--output", type=Path, required=True, help="New comparison CSV; must not exist")
    parser.add_argument(
        "--resolution-ledger",
        type=Path,
        help="Completed comparison ledger to validate; it is never used to alter either extraction",
    )
    return parser


def normalized_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def paths_are_same(left: Path, right: Path) -> bool:
    if normalized_path(left) == normalized_path(right):
        return True
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError:
        return False


def validate_paths(inputs: Sequence[Path], output: Path) -> tuple[list[Path], Path]:
    resolved_inputs = [Path(normalized_path(path)) for path in inputs]
    target = Path(normalized_path(output))
    for path in resolved_inputs:
        if not path.exists():
            raise RuntimeError(f"input CSV does not exist: {path}")
        if not path.is_file():
            raise RuntimeError(f"input path is not a regular file: {path}")
        if paths_are_same(path, target):
            raise RuntimeError(f"output must not be the same file as an input: {path}")
    if len({normalized_path(path) for path in resolved_inputs}) != len(resolved_inputs):
        raise RuntimeError("reviewer_a, reviewer_b, and resolution ledger must be distinct files")
    if target.exists():
        raise RuntimeError(f"output already exists and will not be overwritten: {target}")
    if not target.parent.exists() or not target.parent.is_dir():
        raise RuntimeError(f"output parent directory does not exist: {target.parent}")
    return resolved_inputs, target


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            raw_header = next(reader)
        except StopIteration as exc:
            raise RuntimeError(f"CSV has no header row: {path}") from exc
        header = [str(name).strip() for name in raw_header]
        if any(not name for name in header):
            raise RuntimeError(f"CSV contains a blank header: {path}")
        duplicates = sorted({name for name in header if header.count(name) > 1})
        if duplicates:
            raise RuntimeError(f"CSV has duplicate headers in {path}: {', '.join(duplicates)}")
        rows: list[dict[str, str]] = []
        for row_number, values in enumerate(reader, start=2):
            if not values or not any(value != "" for value in values):
                continue
            if len(values) != len(header):
                raise RuntimeError(
                    f"CSV row {row_number} has {len(values)} cells but header has {len(header)}: {path}"
                )
            if any("\x00" in value for value in values):
                raise RuntimeError(f"CSV row {row_number} contains a NUL byte: {path}")
            rows.append(dict(zip(header, values)))
    return header, rows


def index_extraction(path: Path) -> tuple[list[str], dict[str, dict[str, str]], list[Issue]]:
    header, rows = read_csv_rows(path)
    issues: list[Issue] = []
    if KEY_FIELD not in header:
        issues.append(Issue("MISSING_EFFECT_ID_COLUMN", "required column effect_id is missing", file=str(path)))
        return header, {}, issues
    if PRESENCE_FIELD in header:
        issues.append(
            Issue(
                "RESERVED_FIELD",
                f"{PRESENCE_FIELD} is reserved for missing-record comparisons",
                file=str(path),
            )
        )
    indexed: dict[str, dict[str, str]] = {}
    seen_at: dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):
        literal_id = row.get(KEY_FIELD, "")
        effect_id = literal_id.strip()
        if not effect_id:
            issues.append(Issue("MISSING_EFFECT_ID", "effect_id is blank", file=str(path), row=row_number))
            continue
        if literal_id != effect_id:
            issues.append(
                Issue(
                    "PADDED_EFFECT_ID",
                    "effect_id must not contain leading or trailing whitespace",
                    file=str(path),
                    row=row_number,
                    effect_id=effect_id,
                )
            )
        if effect_id in indexed:
            issues.append(
                Issue(
                    "DUPLICATE_EFFECT_ID",
                    f"effect_id already appears at row {seen_at[effect_id]}",
                    file=str(path),
                    row=row_number,
                    effect_id=effect_id,
                )
            )
        else:
            indexed[effect_id] = row
            seen_at[effect_id] = row_number
    if not rows:
        issues.append(Issue("NO_EXTRACTIONS", "CSV contains no non-empty extraction rows", file=str(path)))
    return header, indexed, issues


def decimal_value(value: str) -> Decimal | None:
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = Decimal(candidate)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split()).casefold()


def classify(left: str, right: str) -> str:
    if left == right:
        return "exact_match"
    if not left.strip() or not right.strip():
        return "missing_difference"
    left_number = decimal_value(left)
    right_number = decimal_value(right)
    if left_number is not None and right_number is not None:
        return "format_difference" if left_number == right_number else "numeric_difference"
    if normalized_text(left) == normalized_text(right):
        return "format_difference"
    return "text_difference"


def make_difference_id(effect_id: str, field: str) -> str:
    digest = hashlib.sha256(f"{effect_id}\0{field}".encode("utf-8")).hexdigest()[:24]
    return f"diff_{digest}"


def comparison_row(effect_id: str, field: str, left: str, right: str) -> dict[str, str]:
    difference_type = classify(left, right)
    substantive = difference_type in SUBSTANTIVE_TYPES
    return {
        "schema_version": SCHEMA_VERSION,
        "difference_id": make_difference_id(effect_id, field),
        "effect_id": effect_id,
        "field": field,
        "reviewer_a_value": left,
        "reviewer_b_value": right,
        "difference_type": difference_type,
        "is_substantive": "yes" if substantive else "no",
        "resolution_status": "unresolved" if substantive else "not_required",
        "final_value": "",
        "evidence": "",
        "adjudicator": "",
        "adjudication_date": "",
    }


def build_comparison(
    header_a: Sequence[str],
    rows_a: Mapping[str, Mapping[str, str]],
    header_b: Sequence[str],
    rows_b: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    fields = [name for name in header_a if name != KEY_FIELD]
    fields.extend(name for name in header_b if name != KEY_FIELD and name not in fields)
    effect_ids = list(rows_a)
    effect_ids.extend(effect_id for effect_id in rows_b if effect_id not in rows_a)
    comparison: list[dict[str, str]] = []
    for effect_id in effect_ids:
        in_a = effect_id in rows_a
        in_b = effect_id in rows_b
        if not (in_a and in_b):
            comparison.append(
                comparison_row(
                    effect_id,
                    PRESENCE_FIELD,
                    "present" if in_a else "",
                    "present" if in_b else "",
                )
            )
        row_a = rows_a.get(effect_id, {})
        row_b = rows_b.get(effect_id, {})
        for field in fields:
            comparison.append(comparison_row(effect_id, field, row_a.get(field, ""), row_b.get(field, "")))
    return comparison


def parse_iso_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must use canonical YYYY-MM-DD")
    return parsed


def unresolved_marker(value: str) -> bool:
    return value.strip().casefold().replace("-", "_") in NONRESOLUTION_MARKERS


def validate_ledger(
    path: Path, comparison: Sequence[dict[str, str]]
) -> tuple[list[Issue], dict[tuple[str, str], dict[str, str]]]:
    header, rows = read_csv_rows(path)
    issues: list[Issue] = []
    if header != OUTPUT_HEADERS:
        issues.append(
            Issue(
                "LEDGER_SCHEMA_MISMATCH",
                "resolution ledger headers must exactly match extraction_adjudication_template.csv",
                file=str(path),
            )
        )
        return issues, {}

    expected = {(row["effect_id"], row["field"]): row for row in comparison}
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    immutable = [
        "schema_version",
        "difference_id",
        "effect_id",
        "field",
        "reviewer_a_value",
        "reviewer_b_value",
        "difference_type",
        "is_substantive",
    ]
    for row_number, row in enumerate(rows, start=2):
        key = (row["effect_id"], row["field"])
        if key in indexed:
            issues.append(
                Issue(
                    "DUPLICATE_LEDGER_CELL",
                    "ledger repeats an effect_id + field cell",
                    file=str(path),
                    row=row_number,
                    effect_id=key[0],
                    field=key[1],
                )
            )
            continue
        indexed[key] = row
        source = expected.get(key)
        if source is None:
            issues.append(
                Issue(
                    "STALE_LEDGER_CELL",
                    "ledger cell does not exist in the current comparison",
                    file=str(path),
                    row=row_number,
                    effect_id=key[0],
                    field=key[1],
                )
            )
            continue
        for field in immutable:
            if row[field] != source[field]:
                issues.append(
                    Issue(
                        "LEDGER_SOURCE_MISMATCH",
                        f"{field} no longer matches the current comparison",
                        file=str(path),
                        row=row_number,
                        effect_id=key[0],
                        field=field,
                    )
                )

        substantive = source["is_substantive"] == "yes"
        status = row["resolution_status"].strip().casefold()
        if substantive:
            if status != "resolved":
                issues.append(
                    Issue(
                        "UNRESOLVED_DIFFERENCE",
                        "every substantive difference must have resolution_status=resolved",
                        file=str(path),
                        row=row_number,
                        effect_id=key[0],
                        field=key[1],
                    )
                )
            for field in ("final_value", "evidence", "adjudicator", "adjudication_date"):
                value = row[field].strip()
                if unresolved_marker(value):
                    issues.append(
                        Issue(
                            "MISSING_RESOLUTION_FIELD",
                            (
                                "substantive differences require a meaningful value; use "
                                "final_value=__MISSING__ when intentional absence is adjudicated"
                            ),
                            file=str(path),
                            row=row_number,
                            effect_id=key[0],
                            field=field,
                        )
                    )
            raw_date = row["adjudication_date"].strip()
            if raw_date and not unresolved_marker(raw_date):
                try:
                    adjudication_date = parse_iso_date(raw_date)
                except ValueError:
                    issues.append(
                        Issue(
                            "INVALID_ADJUDICATION_DATE",
                            "use canonical ISO date YYYY-MM-DD",
                            file=str(path),
                            row=row_number,
                            effect_id=key[0],
                            field="adjudication_date",
                        )
                    )
                else:
                    if adjudication_date > datetime.now(timezone.utc).date():
                        issues.append(
                            Issue(
                                "FUTURE_ADJUDICATION_DATE",
                                "adjudication date cannot be in the future (UTC)",
                                file=str(path),
                                row=row_number,
                                effect_id=key[0],
                                field="adjudication_date",
                            )
                        )
        else:
            if status != "not_required":
                issues.append(
                    Issue(
                        "UNEXPECTED_RESOLUTION",
                        "non-substantive cells must have resolution_status=not_required",
                        file=str(path),
                        row=row_number,
                        effect_id=key[0],
                        field=key[1],
                    )
                )
            if any(row[field] != "" for field in ("final_value", "evidence", "adjudicator", "adjudication_date")):
                issues.append(
                    Issue(
                        "NON_SUBSTANTIVE_ADJUDICATION",
                        "do not adjudicate exact matches or format-only differences",
                        file=str(path),
                        row=row_number,
                        effect_id=key[0],
                        field=key[1],
                    )
                )

    for key in expected.keys() - indexed.keys():
        issues.append(
            Issue(
                "MISSING_LEDGER_CELL",
                "ledger must retain every comparison cell, including non-substantive cells",
                file=str(path),
                effect_id=key[0],
                field=key[1],
            )
        )
    return issues, indexed


def apply_validated_ledger(
    comparison: Sequence[dict[str, str]], ledger: Mapping[tuple[str, str], Mapping[str, str]]
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for source in comparison:
        row = dict(source)
        resolved = ledger[(row["effect_id"], row["field"])]
        for field in ("resolution_status", "final_value", "evidence", "adjudicator", "adjudication_date"):
            row[field] = resolved[field]
        output.append(row)
    return output


def rows_as_csv(rows: Iterable[Mapping[str, str]]) -> bytes:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=OUTPUT_HEADERS, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def atomic_write_no_clobber(target: Path, payload: bytes) -> None:
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
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
            raise RuntimeError(f"output already exists and will not be overwritten: {target}") from exc
        raise RuntimeError(f"could not atomically write UTF-8 output {target}: {exc}") from exc
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
    input_paths = [args.reviewer_a, args.reviewer_b]
    if args.resolution_ledger is not None:
        input_paths.append(args.resolution_ledger)
    try:
        resolved, output = validate_paths(input_paths, args.output)
        path_a, path_b = resolved[:2]
        ledger_path = resolved[2] if len(resolved) == 3 else None
        header_a, rows_a, issues_a = index_extraction(path_a)
        header_b, rows_b, issues_b = index_extraction(path_b)
    except (RuntimeError, OSError, UnicodeError, csv.Error) as exc:
        emit({"status": "error", "errors": [{"code": "INPUT_FAILURE", "message": str(exc)}]}, sys.stderr)
        return EXIT_INPUT_ERROR

    issues = issues_a + issues_b
    if issues:
        emit({"status": "error", "errors": [issue.as_json() for issue in issues]}, sys.stderr)
        return EXIT_VALIDATION_ERROR

    comparison = build_comparison(header_a, rows_a, header_b, rows_b)
    ledger_used = False
    if ledger_path is not None:
        try:
            ledger_issues, ledger = validate_ledger(ledger_path, comparison)
        except (RuntimeError, OSError, UnicodeError, csv.Error) as exc:
            emit({"status": "error", "errors": [{"code": "LEDGER_INPUT_FAILURE", "message": str(exc)}]}, sys.stderr)
            return EXIT_INPUT_ERROR
        if ledger_issues:
            emit({"status": "error", "errors": [issue.as_json() for issue in ledger_issues]}, sys.stderr)
            return EXIT_VALIDATION_ERROR
        comparison = apply_validated_ledger(comparison, ledger)
        ledger_used = True

    substantive = sum(row["is_substantive"] == "yes" for row in comparison)
    unresolved = sum(
        row["is_substantive"] == "yes" and row["resolution_status"] != "resolved" for row in comparison
    )
    try:
        atomic_write_no_clobber(output, rows_as_csv(comparison))
    except RuntimeError as exc:
        emit({"status": "error", "errors": [{"code": "OUTPUT_FAILURE", "message": str(exc)}]}, sys.stderr)
        return EXIT_INPUT_ERROR

    payload = {
        "status": "ok" if unresolved == 0 else "unresolved",
        "output": str(output),
        "cells": len(comparison),
        "substantive_differences": substantive,
        "unresolved_substantive_differences": unresolved,
        "resolution_ledger_validated": ledger_used,
        "automatic_adjudication": False,
    }
    emit(payload, sys.stdout if unresolved == 0 else sys.stderr)
    return EXIT_OK if unresolved == 0 else EXIT_UNRESOLVED


if __name__ == "__main__":
    raise SystemExit(main())
