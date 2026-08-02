#!/usr/bin/env python3
"""Build a strict, machine-readable field-lineage and SHA-256 manifest.

The manifest is written to stdout as JSON.  Optionally, --manifest writes the
same JSON to a file.  Every structured output field must have exactly one
complete lineage row.  Arbitrary binary or text artifacts may be hashed without
participating in field-lineage validation.

Exit codes:
    0: manifest built successfully
    1: lineage or output-field validation failed
    2: usage, input, decoding, parsing, or manifest-write failure
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import locale
import os
import platform
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


TOOL_VERSION = "1.1.0"
EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_ERROR = 2

REQUIRED_LINEAGE_HEADERS = {
    "output_file",
    "output_field",
    "source_fields",
    "transform",
    "formula_or_code",
}
SUPPORTED_OUTPUT_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".ndjson"}


class ManifestArgumentParser(argparse.ArgumentParser):
    """Emit JSON for command-line errors so every tool response is parseable."""

    def error(self, message: str) -> None:
        emit_json(
            {
                "status": "error",
                "errors": [{"code": "USAGE_ERROR", "message": message}],
            },
            stream=sys.stderr,
        )
        raise SystemExit(EXIT_INPUT_ERROR)


def emit_json(payload: Mapping[str, Any], *, stream: Any = sys.stdout) -> None:
    json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
    stream.write("\n")


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = ManifestArgumentParser(
        description=(
            "Hash reproducibility inputs, analysis scripts, structured outputs, and "
            "arbitrary artifacts; validate complete output field lineage; and emit a "
            "JSON manifest."
        ),
        epilog=(
            "Supported output formats for field coverage: CSV, TSV, JSON, JSONL, "
            "and NDJSON. Exit codes: 0=success, 1=lineage validation failure, "
            "2=usage/input/write failure."
        ),
    )
    parser.add_argument(
        "--lineage",
        required=True,
        type=Path,
        help="CSV with output_file, output_field, source_fields, transform, and formula_or_code",
    )
    parser.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        type=Path,
        help="Input file to hash; repeat for multiple inputs",
    )
    parser.add_argument(
        "--script",
        dest="scripts",
        action="append",
        required=True,
        type=Path,
        help="Analysis or transformation script to hash; repeat for multiple scripts",
    )
    parser.add_argument(
        "--output",
        dest="outputs",
        action="append",
        required=True,
        type=Path,
        help="Structured output file to hash and check for field coverage; repeat as needed",
    )
    parser.add_argument(
        "--artifact",
        dest="artifacts",
        action="append",
        default=[],
        type=Path,
        help=(
            "Arbitrary ordinary file to hash without field-lineage validation "
            "(for example model.rds or a log); repeat as needed"
        ),
    )
    parser.add_argument(
        "--seed",
        required=True,
        help="Random seed, or an explicit value such as 'not_applicable'",
    )
    parser.add_argument(
        "--environment",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Additional non-secret environment/version fact; repeat as needed",
    )
    parser.add_argument(
        "--warning",
        action="append",
        default=[],
        help="Known reproducibility warning to preserve; repeat as needed",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional JSON destination; stdout always receives the manifest",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Lineage and structured-text encoding (default: utf-8-sig)",
    )
    return parser


def resolve_unique_paths(paths: Sequence[Path], category: str) -> list[Path]:
    resolved: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        absolute = path.expanduser().resolve()
        key = os.path.normcase(str(absolute))
        if key in seen:
            raise ValueError(f"duplicate {category} path: {path}")
        seen.add(key)
        resolved.append(absolute)
    return resolved


def require_files(paths: Sequence[Path], category: str) -> None:
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"{category} file does not exist: {path}")
        if not path.is_file():
            raise OSError(f"{category} path is not a regular file: {path}")


def reject_artifact_path_conflicts(
    artifacts: Sequence[Path],
    *,
    lineage: Path,
    inputs: Sequence[Path],
    scripts: Sequence[Path],
    outputs: Sequence[Path],
    manifest: Path | None,
) -> None:
    reserved: dict[str, str] = {os.path.normcase(str(lineage)): "lineage"}
    for category, paths in (("input", inputs), ("script", scripts), ("output", outputs)):
        for path in paths:
            reserved[os.path.normcase(str(path))] = category
    if manifest is not None:
        reserved[os.path.normcase(str(manifest))] = "manifest"

    for artifact in artifacts:
        conflict = reserved.get(os.path.normcase(str(artifact)))
        if conflict is not None:
            raise ValueError(f"artifact path conflicts with {conflict} path: {artifact}")


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def file_record(path: Path, *, role: str | None = None) -> dict[str, Any]:
    digest, size = sha256_file(path)
    record: dict[str, Any] = {
        "path": str(path),
        "sha256": digest,
        "size_bytes": size,
    }
    if role is not None:
        record["role"] = role
    return record


def parse_environment(items: Sequence[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"environment entry must use KEY=VALUE: {item!r}")
        key, value = (part.strip() for part in item.split("=", 1))
        if not key or not value:
            raise ValueError(f"environment entry must have a non-empty key and value: {item!r}")
        if key in values:
            raise ValueError(f"duplicate environment key: {key}")
        values[key] = value
    return values


def validate_header(fieldnames: Sequence[str] | None) -> list[str]:
    if not fieldnames:
        raise ValueError("lineage CSV has no header row")
    normalized = [clean(name) for name in fieldnames]
    if any(not name for name in normalized):
        raise ValueError("lineage CSV has a blank header")
    duplicates = sorted({name for name in normalized if normalized.count(name) > 1})
    if duplicates:
        raise ValueError(f"lineage CSV has duplicate headers: {', '.join(duplicates)}")
    missing = sorted(REQUIRED_LINEAGE_HEADERS - set(normalized))
    if missing:
        raise ValueError(f"lineage CSV is missing required columns: {', '.join(missing)}")
    return normalized


def read_lineage_rows(path: Path, encoding: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        normalized_header = validate_header(reader.fieldnames)
        reader.fieldnames = normalized_header
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"lineage row {row_number} has cells beyond the header")
            normalized = {clean(key): clean(value) for key, value in row.items()}
            if not any(normalized.values()):
                continue
            missing_values = [name for name in sorted(REQUIRED_LINEAGE_HEADERS) if not normalized.get(name)]
            if missing_values:
                raise ValueError(
                    f"lineage row {row_number} has blank required values: {', '.join(missing_values)}"
                )
            normalized["_row_number"] = str(row_number)
            rows.append(normalized)
    if not rows:
        raise ValueError("lineage CSV has no non-empty data rows")
    return rows


def tabular_fields(path: Path, delimiter: str, encoding: str) -> set[str]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter, strict=True)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"output has no header row: {path}") from exc
    fields = [clean(name) for name in header]
    if any(not name for name in fields):
        raise ValueError(f"output has a blank field name: {path}")
    duplicates = sorted({name for name in fields if fields.count(name) > 1})
    if duplicates:
        raise ValueError(f"output has duplicate fields ({', '.join(duplicates)}): {path}")
    return set(fields)


def object_fields(value: Any, path: Path) -> set[str]:
    if isinstance(value, dict):
        if not value:
            raise ValueError(f"JSON output object has no fields: {path}")
        return {str(key) for key in value}
    if isinstance(value, list):
        if not value:
            raise ValueError(f"JSON output array is empty, so field coverage cannot be verified: {path}")
        if any(not isinstance(item, dict) for item in value):
            raise ValueError(f"JSON output array must contain only objects: {path}")
        fields = {str(key) for item in value for key in item}
        if not fields:
            raise ValueError(f"JSON output objects have no fields: {path}")
        return fields
    raise ValueError(f"JSON output must be an object or an array of objects: {path}")


def json_fields(path: Path, encoding: str) -> set[str]:
    with path.open("r", encoding=encoding) as handle:
        return object_fields(json.load(handle), path)


def json_lines_fields(path: Path, encoding: str) -> set[str]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding=encoding) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSON-lines record {line_number} is not an object: {path}")
            records.append(value)
    return object_fields(records, path)


def discover_output_fields(path: Path, encoding: str) -> set[str]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_OUTPUT_SUFFIXES:
        raise ValueError(
            f"unsupported output format {suffix or '<none>'!r}; cannot prove field-lineage completeness: {path}"
        )
    if suffix == ".csv":
        return tabular_fields(path, ",", encoding)
    if suffix == ".tsv":
        return tabular_fields(path, "\t", encoding)
    if suffix == ".json":
        return json_fields(path, encoding)
    return json_lines_fields(path, encoding)


def output_aliases(path: Path) -> set[str]:
    aliases = {
        os.path.normcase(str(path)),
        os.path.normcase(path.name),
        os.path.normcase(path.as_posix()),
    }
    try:
        aliases.add(os.path.normcase(str(path.relative_to(Path.cwd()))))
    except ValueError:
        pass
    return aliases


def match_output_file(token: str, outputs: Sequence[Path], lineage_path: Path) -> Path:
    token_path = Path(token).expanduser()
    exact_aliases = {
        os.path.normcase(str(token_path.resolve())),
        os.path.normcase(str((lineage_path.parent / token_path).resolve())),
    }
    exact_matches = [path for path in outputs if os.path.normcase(str(path)) in exact_aliases]
    if len(exact_matches) == 1:
        return exact_matches[0]

    candidate_aliases = {
        os.path.normcase(token),
        os.path.normcase(token_path.as_posix()),
        os.path.normcase(token_path.name),
    }
    matches = [path for path in outputs if output_aliases(path) & candidate_aliases]
    if not matches:
        raise ValueError(f"lineage output_file does not match any --output path: {token!r}")
    if len(matches) > 1:
        raise ValueError(f"lineage output_file is ambiguous across --output paths: {token!r}")
    return matches[0]


def validate_lineage(
    rows: Sequence[Mapping[str, str]],
    outputs: Sequence[Path],
    lineage_path: Path,
    encoding: str,
) -> list[dict[str, Any]]:
    expected = {path: discover_output_fields(path, encoding) for path in outputs}
    documented: dict[Path, set[str]] = {path: set() for path in outputs}
    result: list[dict[str, Any]] = []

    for row in rows:
        row_number = row["_row_number"]
        output = match_output_file(row["output_file"], outputs, lineage_path)
        output_field = row["output_field"]
        if output_field in documented[output]:
            raise ValueError(
                f"duplicate lineage for output field {output_field!r} in {output} (row {row_number})"
            )
        documented[output].add(output_field)
        sources = [field.strip() for field in row["source_fields"].split(";") if field.strip()]
        if not sources:
            raise ValueError(f"lineage row {row_number} has no source_fields entries")
        result.append(
            {
                "output_file": str(output),
                "output_field": output_field,
                "source_fields": sources,
                "transform": row["transform"],
                "formula_or_code": row["formula_or_code"],
                "notes": row.get("notes", ""),
            }
        )

    for output in outputs:
        missing = sorted(expected[output] - documented[output])
        stale = sorted(documented[output] - expected[output])
        if missing:
            raise ValueError(f"incomplete field lineage for {output}; missing: {', '.join(missing)}")
        if stale:
            raise ValueError(f"lineage names fields absent from {output}: {', '.join(stale)}")

    result.sort(key=lambda item: (item["output_file"], item["output_field"]))
    return result


def write_manifest(path: Path, payload: Mapping[str, Any]) -> None:
    destination = path.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, destination)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    lineage_path = args.lineage.expanduser().resolve()
    builder_path = Path(__file__).resolve()
    inputs = resolve_unique_paths(args.inputs, "input")
    analysis_scripts = resolve_unique_paths(args.scripts, "script")
    outputs = resolve_unique_paths(args.outputs, "output")
    artifacts = resolve_unique_paths(args.artifacts, "artifact")
    require_files([lineage_path], "lineage")
    require_files(inputs, "input")
    require_files(analysis_scripts, "script")
    require_files(outputs, "output")
    require_files(artifacts, "artifact")

    if not clean(args.seed):
        raise ValueError("seed must be non-empty; use 'not_applicable' when randomness is absent")

    manifest_path = args.manifest.expanduser().resolve() if args.manifest else None
    tracked_paths = {os.path.normcase(str(path)) for path in [lineage_path, *inputs, *analysis_scripts, *outputs]}
    if manifest_path is not None and os.path.normcase(str(manifest_path)) in tracked_paths:
        raise ValueError("--manifest must not overwrite a lineage, input, script, or output file")
    reject_artifact_path_conflicts(
        artifacts,
        lineage=lineage_path,
        inputs=inputs,
        scripts=[*analysis_scripts, builder_path],
        outputs=outputs,
        manifest=manifest_path,
    )

    lineage_rows = read_lineage_rows(lineage_path, args.encoding)
    field_lineage = validate_lineage(lineage_rows, outputs, lineage_path, args.encoding)
    user_environment = parse_environment(args.environment)

    script_records = [file_record(path, role="analysis_or_transform") for path in analysis_scripts]
    if builder_path not in analysis_scripts:
        script_records.append(file_record(builder_path, role="lineage_builder"))

    try:
        preferred_encoding = locale.getencoding()
    except AttributeError:  # pragma: no cover - for older supported Python runtimes
        preferred_encoding = locale.getpreferredencoding(False)

    return {
        "schema_version": "1.1",
        "status": "ok",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "lineage_definition": file_record(lineage_path),
        "inputs": [file_record(path) for path in inputs],
        "scripts": script_records,
        "outputs": [file_record(path) for path in outputs],
        "artifacts": [file_record(path, role="artifact") for path in artifacts],
        "field_lineage": field_lineage,
        "seed": clean(args.seed),
        "environment": {
            "tool_name": "build_lineage_manifest",
            "tool_version": TOOL_VERSION,
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "os_name": os.name,
            "preferred_encoding": preferred_encoding,
            "user_supplied": user_environment,
        },
        "warnings": [clean(item) for item in args.warning if clean(item)],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = build_manifest(args)
        if args.manifest:
            write_manifest(args.manifest, payload)
    except json.JSONDecodeError as exc:
        emit_json(
            {"status": "error", "errors": [{"code": "INPUT_FAILURE", "message": str(exc)}]},
            stream=sys.stderr,
        )
        return EXIT_INPUT_ERROR
    except ValueError as exc:
        emit_json(
            {"status": "error", "errors": [{"code": "VALIDATION_FAILURE", "message": str(exc)}]},
            stream=sys.stderr,
        )
        return EXIT_VALIDATION_ERROR
    except (OSError, UnicodeError, LookupError, csv.Error) as exc:
        emit_json(
            {"status": "error", "errors": [{"code": "INPUT_FAILURE", "message": str(exc)}]},
            stream=sys.stderr,
        )
        return EXIT_INPUT_ERROR

    emit_json(payload)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
