#!/usr/bin/env python3
"""Validate the machine-readable ecology benchmark suite contract."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASEBOOK = ROOT / "references" / "plant-biodiversity-benchmark-casebook.md"
SOURCE_REGISTRY = ROOT / "references" / "source-registry.md"

ROOT_FIELDS = {"schema_version", "minimum_families", "minimum_cases_per_family", "cases"}
CASE_FIELDS = {
    "id",
    "benchmark_id",
    "source_registry_ids",
    "family",
    "test_type",
    "fixture_kind",
    "executor",
    "delegate_id",
    "expected",
    "oracle",
    "acceptance_levels",
    "source_replication_status",
    "expected_failure_code",
}
TEST_TYPES = {
    "exact_reproduction",
    "conceptual_reimplementation",
    "router_rejection",
    "modern_reanalysis",
}
FIXTURE_KINDS = {"synthetic", "public_snapshot"}
EXECUTORS = {"ecology_case", "p1_case"}
EXPECTED = {"pass", "reject"}
ORACLES = {"numeric", "contract", "route", "matrix", "stop_rule"}
LEVELS = {f"L{i}" for i in range(7)}
REPLICATION_STATUSES = {"pending", "verified", "not_applicable"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
BENCHMARK_RE = re.compile(r"^BENCH-[A-Z0-9-]+-[0-9]{4}$")


class ContractError(ValueError):
    pass


def exact_object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    missing = sorted(fields - set(value))
    extra = sorted(set(value) - fields)
    if missing or extra:
        raise ContractError(f"{label} fields mismatch; missing={missing}, extra={extra}")
    return value


def nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value.strip()


def positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 1:
        raise ContractError(f"{label} must be a positive integer")
    return value


def validate(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"could not read benchmark JSON: {exc}") from exc

    root = exact_object(payload, ROOT_FIELDS, "root")
    if root["schema_version"] != "1.0":
        raise ContractError("schema_version must equal '1.0'")
    minimum_families = positive_int(root["minimum_families"], "minimum_families")
    minimum_cases = positive_int(root["minimum_cases_per_family"], "minimum_cases_per_family")
    cases = root["cases"]
    if not isinstance(cases, list) or not cases:
        raise ContractError("cases must be a non-empty array")

    casebook_text = CASEBOOK.read_text(encoding="utf-8")
    registry_text = SOURCE_REGISTRY.read_text(encoding="utf-8")
    seen: set[str] = set()
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, raw_case in enumerate(cases):
        label = f"cases[{index}]"
        case = exact_object(raw_case, CASE_FIELDS, label)
        case_id = nonempty_text(case["id"], f"{label}.id")
        if not ID_RE.fullmatch(case_id):
            raise ContractError(f"{label}.id has an unsupported format")
        if case_id in seen:
            raise ContractError(f"duplicate case id: {case_id}")
        seen.add(case_id)

        benchmark_id = nonempty_text(case["benchmark_id"], f"{label}.benchmark_id")
        if not BENCHMARK_RE.fullmatch(benchmark_id) or benchmark_id not in casebook_text:
            raise ContractError(f"{label}.benchmark_id is not registered in the casebook")

        source_ids = case["source_registry_ids"]
        if not isinstance(source_ids, list) or not source_ids or any(
            not isinstance(item, str) or not item.strip() for item in source_ids
        ):
            raise ContractError(f"{label}.source_registry_ids must be a non-empty string array")
        for source_id in source_ids:
            if f"`{source_id}`" not in registry_text:
                raise ContractError(f"{label} references unregistered source id: {source_id}")

        family = nonempty_text(case["family"], f"{label}.family")
        test_type = nonempty_text(case["test_type"], f"{label}.test_type")
        fixture_kind = nonempty_text(case["fixture_kind"], f"{label}.fixture_kind")
        executor = nonempty_text(case["executor"], f"{label}.executor")
        expected = nonempty_text(case["expected"], f"{label}.expected")
        oracle = nonempty_text(case["oracle"], f"{label}.oracle")
        replication = nonempty_text(
            case["source_replication_status"], f"{label}.source_replication_status"
        )
        if test_type not in TEST_TYPES:
            raise ContractError(f"{label}.test_type is unsupported")
        if fixture_kind not in FIXTURE_KINDS:
            raise ContractError(f"{label}.fixture_kind is unsupported")
        if executor not in EXECUTORS:
            raise ContractError(f"{label}.executor is unsupported")
        if expected not in EXPECTED:
            raise ContractError(f"{label}.expected is unsupported")
        if oracle not in ORACLES:
            raise ContractError(f"{label}.oracle is unsupported")
        if replication not in REPLICATION_STATUSES:
            raise ContractError(f"{label}.source_replication_status is unsupported")

        delegate_id = case["delegate_id"]
        if executor == "p1_case":
            nonempty_text(delegate_id, f"{label}.delegate_id")
        elif delegate_id is not None:
            raise ContractError(f"{label}.delegate_id must be null for ecology_case")

        levels = case["acceptance_levels"]
        if not isinstance(levels, list) or not levels or len(levels) != len(set(levels)):
            raise ContractError(f"{label}.acceptance_levels must be a non-empty unique array")
        if any(level not in LEVELS for level in levels):
            raise ContractError(f"{label}.acceptance_levels contains an unsupported level")

        failure_code = case["expected_failure_code"]
        if expected == "reject":
            nonempty_text(failure_code, f"{label}.expected_failure_code")
        elif failure_code is not None:
            raise ContractError(f"{label}.expected_failure_code must be null for pass cases")

        if fixture_kind == "synthetic" and test_type in {"exact_reproduction", "modern_reanalysis"}:
            raise ContractError(f"{label} cannot claim source reproduction from a synthetic fixture")
        if test_type in {"exact_reproduction", "modern_reanalysis"} and replication != "verified":
            raise ContractError(f"{label} reproduction claims require verified source replication")
        if replication == "verified" and fixture_kind != "public_snapshot":
            raise ContractError(f"{label} verified replication requires a public_snapshot fixture")

        by_family[family].append(case)

    if len(by_family) < minimum_families:
        raise ContractError(
            f"suite has {len(by_family)} families; minimum_families={minimum_families}"
        )
    for family, family_cases in sorted(by_family.items()):
        if len(family_cases) < minimum_cases:
            raise ContractError(
                f"family {family!r} has {len(family_cases)} cases; minimum={minimum_cases}"
            )
        pass_count = sum(case["expected"] == "pass" for case in family_cases)
        reject_count = sum(case["expected"] == "reject" for case in family_cases)
        if pass_count < 1 or reject_count < 2:
            raise ContractError(
                f"family {family!r} requires at least one pass and two reject cases"
            )

    return {
        "valid": True,
        "schema_version": root["schema_version"],
        "case_count": len(cases),
        "family_count": len(by_family),
        "families": sorted(by_family),
        "verified_source_replications": sum(
            case["source_replication_status"] == "verified" for case in cases
        ),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_ecology_benchmarks.py SUITE.json", file=sys.stderr)
        return 2
    try:
        result = validate(Path(sys.argv[1]))
    except ContractError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
