#!/usr/bin/env python3
"""Strict validator for correlation, distance, and sampling covariance matrices."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import NoReturn


class ValidationError(ValueError):
    pass


def fail(message: str) -> NoReturn:
    raise ValidationError(message)


def read_csv_rows(path: Path, label: str) -> list[list[str]]:
    if not path.is_file():
        fail(f"{label} does not exist: {path}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except UnicodeDecodeError as exc:
        fail(f"{label} must be UTF-8 CSV: {exc}")
    except OSError as exc:
        fail(f"Could not read {label}: {exc}")
    if not rows:
        fail(f"{label} is empty.")
    if any(len(row) == 0 for row in rows):
        fail(f"{label} contains a blank row; blank rows are not allowed.")
    return rows


def clean_id(value: str, context: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        fail(f"{context} is blank.")
    if cleaned != value:
        fail(f"{context} has leading or trailing whitespace: {value!r}.")
    return cleaned


def read_expected_data(
    path: Path, id_col: str, matrix_type: str, vi_col: str | None
) -> tuple[list[str], dict[str, float] | None, int]:
    rows = read_csv_rows(path, "Data file")
    header = rows[0]
    if any(not name.strip() for name in header):
        fail("Data file contains a blank column name.")
    if len(set(header)) != len(header):
        fail("Data file column names must be unique.")
    if id_col not in header:
        fail(f"Data file does not contain --id-col {id_col!r}.")
    if matrix_type == "sampling_v":
        if not vi_col:
            fail("--vi-col is required for --type sampling_v.")
        if vi_col not in header:
            fail(f"Data file does not contain --vi-col {vi_col!r}.")
    elif vi_col is not None:
        fail("--vi-col is only valid for --type sampling_v.")

    width = len(header)
    id_index = header.index(id_col)
    vi_index = header.index(vi_col) if vi_col else None
    ordered_ids: list[str] = []
    seen: set[str] = set()
    variances: dict[str, float] | None = {} if vi_index is not None else None

    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            fail(
                f"Data file row {line_number} has {len(row)} fields; expected {width}."
            )
        identifier = clean_id(row[id_index], f"Data file {id_col} at row {line_number}")
        if matrix_type == "sampling_v" and identifier in seen:
            fail(
                f"Data {id_col} must be unique for sampling_v; duplicate {identifier!r}."
            )
        if identifier not in seen:
            seen.add(identifier)
            ordered_ids.append(identifier)
        if vi_index is not None:
            raw_vi = row[vi_index].strip()
            try:
                vi = float(raw_vi)
            except ValueError:
                fail(f"Data {vi_col} at row {line_number} is not numeric: {raw_vi!r}.")
            if not math.isfinite(vi) or vi <= 0:
                fail(f"Data {vi_col} at row {line_number} must be finite and > 0.")
            assert variances is not None
            variances[identifier] = vi

    if not ordered_ids:
        fail("Data file contains no data rows.")
    if len(ordered_ids) < 2:
        fail("At least two distinct IDs are required.")
    return ordered_ids, variances, len(rows) - 1


def read_matrix(path: Path) -> tuple[list[str], list[str], list[list[float]]]:
    rows = read_csv_rows(path, "Matrix file")
    header = rows[0]
    if len(header) < 3:
        fail("Matrix CSV must contain an ID column and at least two matrix columns.")
    if not header[0].strip():
        fail("Matrix CSV first column must have a non-blank ID label.")
    column_ids = [clean_id(value, "Matrix column ID") for value in header[1:]]
    if len(set(column_ids)) != len(column_ids):
        fail("Matrix column IDs must be unique.")
    if len(rows) - 1 != len(column_ids):
        fail(
            "Matrix must be square: the number of data rows must equal the number of matrix columns."
        )

    row_ids: list[str] = []
    values: list[list[float]] = []
    expected_width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != expected_width:
            fail(
                f"Matrix row {line_number} has {len(row)} fields; expected {expected_width}."
            )
        row_id = clean_id(row[0], f"Matrix row ID at row {line_number}")
        row_ids.append(row_id)
        numeric_row: list[float] = []
        for column_id, raw in zip(column_ids, row[1:]):
            text = raw.strip()
            if not text:
                fail(f"Matrix value ({row_id}, {column_id}) is blank.")
            try:
                value = float(text)
            except ValueError:
                fail(f"Matrix value ({row_id}, {column_id}) is not numeric: {text!r}.")
            if not math.isfinite(value):
                fail(f"Matrix value ({row_id}, {column_id}) must be finite.")
            numeric_row.append(value)
        values.append(numeric_row)

    if len(set(row_ids)) != len(row_ids):
        fail("Matrix row IDs must be unique.")
    if set(row_ids) != set(column_ids):
        fail("Matrix row IDs and column IDs must be exactly the same set.")
    return row_ids, column_ids, values


def reorder_matrix(
    row_ids: list[str],
    column_ids: list[str],
    values: list[list[float]],
    expected_ids: list[str],
) -> list[list[float]]:
    matrix_ids = set(row_ids)
    expected_set = set(expected_ids)
    if matrix_ids != expected_set:
        missing = sorted(expected_set - matrix_ids)
        extra = sorted(matrix_ids - expected_set)
        details: list[str] = []
        if missing:
            details.append("missing from matrix=" + ",".join(missing))
        if extra:
            details.append("not present in data=" + ",".join(extra))
        fail("Matrix IDs do not exactly match data IDs: " + "; ".join(details) + ".")
    row_index = {identifier: index for index, identifier in enumerate(row_ids)}
    column_index = {identifier: index for index, identifier in enumerate(column_ids)}
    return [
        [values[row_index[row_id]][column_index[column_id]] for column_id in expected_ids]
        for row_id in expected_ids
    ]


def max_abs(matrix: list[list[float]]) -> float:
    return max(abs(value) for row in matrix for value in row)


def require_symmetric(matrix: list[list[float]], tolerance: float) -> float:
    scale = max(1.0, max_abs(matrix))
    threshold = tolerance * scale
    largest = 0.0
    for i in range(len(matrix)):
        for j in range(i + 1, len(matrix)):
            difference = abs(matrix[i][j] - matrix[j][i])
            largest = max(largest, difference)
            if difference > threshold:
                fail(
                    f"Matrix is not symmetric: |M[{i + 1},{j + 1}]-M[{j + 1},{i + 1}]| "
                    f"is {difference:.12g}, exceeding tolerance {threshold:.12g}."
                )
    return largest


def cholesky_positive_definite(
    matrix: list[list[float]], tolerance: float
) -> float:
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    scale = max(1.0, max_abs(matrix))
    threshold = tolerance * scale
    minimum_pivot = math.inf
    for i in range(n):
        for j in range(i + 1):
            remainder = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                minimum_pivot = min(minimum_pivot, remainder)
                if remainder <= threshold:
                    fail(
                        "Correlation matrix is not strictly positive definite "
                        f"(Cholesky pivot {remainder:.12g} <= {threshold:.12g})."
                    )
                lower[i][j] = math.sqrt(remainder)
            else:
                lower[i][j] = remainder / lower[j][j]
    return minimum_pivot


def ldlt_positive_semidefinite(
    matrix: list[list[float]], tolerance: float, label: str
) -> float:
    work = [row[:] for row in matrix]
    n = len(work)
    scale = max(1.0, max_abs(work))
    threshold = tolerance * scale
    minimum_pivot = math.inf

    for k in range(n):
        pivot_index = max(range(k, n), key=lambda index: work[index][index])
        if pivot_index != k:
            work[k], work[pivot_index] = work[pivot_index], work[k]
            for row in work:
                row[k], row[pivot_index] = row[pivot_index], row[k]
        pivot = work[k][k]
        minimum_pivot = min(minimum_pivot, pivot)
        if pivot < -threshold:
            fail(
                f"{label} is not positive semidefinite "
                f"(pivot {pivot:.12g} < {-threshold:.12g})."
            )
        if pivot <= threshold:
            largest_off_diagonal = max(
                (abs(work[i][k]) for i in range(k + 1, n)), default=0.0
            )
            if largest_off_diagonal > threshold:
                fail(
                    f"{label} is not positive semidefinite: a near-zero pivot has "
                    f"off-diagonal magnitude {largest_off_diagonal:.12g}."
                )
            continue
        for i in range(k + 1, n):
            for j in range(i, n):
                updated = work[i][j] - work[i][k] * work[j][k] / pivot
                work[i][j] = updated
                work[j][i] = updated
    return minimum_pivot


def validate_correlation(
    matrix: list[list[float]], tolerance: float
) -> dict[str, float | bool]:
    diagonal_error = max(abs(matrix[i][i] - 1.0) for i in range(len(matrix)))
    if diagonal_error > tolerance:
        fail(
            f"Correlation matrix diagonal must equal 1 within tolerance; maximum error is {diagonal_error:.12g}."
        )
    smallest = min(value for row in matrix for value in row)
    largest = max(value for row in matrix for value in row)
    if smallest < -1.0 - tolerance or largest > 1.0 + tolerance:
        fail("Correlation matrix entries must lie in [-1, 1] within tolerance.")
    minimum_pivot = cholesky_positive_definite(matrix, tolerance)
    return {
        "diagonal_max_error": diagonal_error,
        "minimum_cholesky_pivot": minimum_pivot,
        "positive_definite": True,
    }


def validate_sampling_v(
    matrix: list[list[float]],
    expected_ids: list[str],
    variances: dict[str, float] | None,
    tolerance: float,
) -> dict[str, float | bool]:
    if variances is None:
        fail("Internal error: sampling variances were not loaded.")
    for index, identifier in enumerate(expected_ids):
        diagonal = matrix[index][index]
        expected = variances[identifier]
        threshold = tolerance * max(1.0, abs(expected))
        if diagonal <= 0:
            fail(f"sampling_v diagonal for {identifier!r} must be > 0.")
        if abs(diagonal - expected) > threshold:
            fail(
                f"sampling_v diagonal for {identifier!r} is {diagonal:.12g}, "
                f"but data variance is {expected:.12g}."
            )
    minimum_pivot = ldlt_positive_semidefinite(matrix, tolerance, "sampling_v matrix")
    return {
        "diagonal_matches_vi": True,
        "minimum_ldlt_pivot": minimum_pivot,
        "positive_semidefinite": True,
    }


def validate_distance(
    matrix: list[list[float]], tolerance: float, require_euclidean: bool
) -> dict[str, float | bool]:
    n = len(matrix)
    scale = max(1.0, max_abs(matrix))
    threshold = tolerance * scale
    diagonal_error = max(abs(matrix[i][i]) for i in range(n))
    if diagonal_error > threshold:
        fail(
            f"Distance matrix diagonal must equal 0 within tolerance; maximum error is {diagonal_error:.12g}."
        )
    if min(value for row in matrix for value in row) < -threshold:
        fail("Distance matrix cannot contain negative distances.")
    largest_triangle_violation = 0.0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                violation = matrix[i][j] - matrix[i][k] - matrix[k][j]
                largest_triangle_violation = max(largest_triangle_violation, violation)
                if violation > threshold:
                    fail(
                        "Distance matrix violates the triangle inequality at "
                        f"({i + 1}, {j + 1}, {k + 1}) by {violation:.12g}."
                    )

    report: dict[str, float | bool] = {
        "diagonal_max_error": diagonal_error,
        "nonnegative": True,
        "triangle_inequality": True,
        "largest_triangle_violation": largest_triangle_violation,
        "euclidean": require_euclidean,
    }
    if require_euclidean:
        squared = [[value * value for value in row] for row in matrix]
        row_means = [sum(row) / n for row in squared]
        grand_mean = sum(row_means) / n
        gram = [
            [
                -0.5
                * (squared[i][j] - row_means[i] - row_means[j] + grand_mean)
                for j in range(n)
            ]
            for i in range(n)
        ]
        minimum_pivot = ldlt_positive_semidefinite(
            gram, tolerance, "Double-centered distance Gram matrix"
        )
        report["centered_gram_positive_semidefinite"] = True
        report["centered_gram_minimum_ldlt_pivot"] = minimum_pivot
    return report


def atomic_write_json(path: Path, payload: dict[str, object], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        fail(f"Report already exists: {path}. Use --overwrite yes to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a labeled structure matrix against IDs in a UTF-8 data file. "
            "The validator never reorders or repairs the source matrix."
        )
    )
    parser.add_argument("matrix", type=Path, help="Labeled matrix CSV")
    parser.add_argument("--type", required=True, choices=("correlation", "distance", "sampling_v"))
    parser.add_argument("--data", required=True, type=Path, help="Effect/data CSV containing expected IDs")
    parser.add_argument("--id-col", required=True, help="Data column whose distinct IDs must match the matrix")
    parser.add_argument("--vi-col", help="Sampling-variance column; required only for sampling_v")
    parser.add_argument("--distance-unit", help="Required provenance label for distance matrices")
    parser.add_argument("--distance-method", help="Required provenance label for distance matrices")
    parser.add_argument(
        "--require-euclidean",
        choices=("yes", "no"),
        default="yes",
        help="For distance matrices, require the double-centered Gram matrix to be PSD (default: yes)",
    )
    parser.add_argument("--tolerance", type=float, default=1e-8)
    parser.add_argument("--report", type=Path, help="Optional atomic JSON validation report")
    parser.add_argument("--overwrite", choices=("yes", "no"), default="no")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if not math.isfinite(args.tolerance) or args.tolerance <= 0 or args.tolerance > 1e-2:
            fail("--tolerance must be finite, > 0, and <= 0.01.")
        if args.type == "distance":
            if not args.distance_unit or not args.distance_unit.strip():
                fail("--distance-unit is required for --type distance.")
            if not args.distance_method or not args.distance_method.strip():
                fail("--distance-method is required for --type distance.")
        elif args.distance_unit is not None or args.distance_method is not None:
            fail("--distance-unit and --distance-method are only valid for --type distance.")

        matrix_path = args.matrix.resolve()
        data_path = args.data.resolve()
        if matrix_path == data_path:
            fail("Matrix and data paths must be different files.")
        if args.report and args.report.resolve() in (matrix_path, data_path):
            fail("--report cannot overwrite the matrix or data file.")

        expected_ids, variances, data_rows = read_expected_data(
            data_path, args.id_col, args.type, args.vi_col
        )
        row_ids, column_ids, raw_matrix = read_matrix(matrix_path)
        matrix = reorder_matrix(row_ids, column_ids, raw_matrix, expected_ids)
        symmetry_error = require_symmetric(matrix, args.tolerance)

        if args.type == "correlation":
            checks = validate_correlation(matrix, args.tolerance)
        elif args.type == "sampling_v":
            checks = validate_sampling_v(
                matrix, expected_ids, variances, args.tolerance
            )
        else:
            checks = validate_distance(
                matrix, args.tolerance, args.require_euclidean == "yes"
            )

        report: dict[str, object] = {
            "schema_version": "1.0.0",
            "status": "valid",
            "matrix_type": args.type,
            "matrix_path": str(matrix_path),
            "data_path": str(data_path),
            "id_column": args.id_col,
            "vi_column": args.vi_col,
            "matrix_dimension": len(expected_ids),
            "data_row_count": data_rows,
            "mapped_id_order": expected_ids,
            "matrix_source_row_order": row_ids,
            "matrix_source_column_order": column_ids,
            "symmetry_max_error": symmetry_error,
            "tolerance": args.tolerance,
            "distance_unit": args.distance_unit,
            "distance_method": args.distance_method,
            "checks": checks,
            "repair_applied": False,
            "near_pd_applied": False,
        }
        if args.report:
            atomic_write_json(args.report.resolve(), report, args.overwrite == "yes")
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False)
        sys.stdout.write("\n")
        return 0
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
