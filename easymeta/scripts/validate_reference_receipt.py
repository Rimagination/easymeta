#!/usr/bin/env python3
"""Validate a reference receipt against an EasyMeta route result.

Usage:
    python validate_reference_receipt.py ROUTE.json RECEIPT.json
        [--skill-root DIR] [--reference-routes FILE] [--pretty]

The route file should be the pending output from ``route_synthesis.py``. This
validator exits 1 when the receipt is incomplete or inconsistent. Re-run the
router with ``--reference-receipt`` to obtain an executable route decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from reference_gate import load_json_file, load_reference_routes, validate_receipt


EXIT_OK = 0
EXIT_INVALID = 1
EXIT_INPUT_ERROR = 2
ROUTE_FIELDS = {
    "reference_gate",
    "required_references",
    "required_source_ids",
    "required_living_source_ids",
    "matched_reference_rules",
}


def parser() -> argparse.ArgumentParser:
    skill_root = Path(__file__).resolve().parent.parent
    result = argparse.ArgumentParser(description="Validate an EasyMeta P0-6 reference receipt.")
    result.add_argument("route", type=Path)
    result.add_argument("receipt", type=Path)
    result.add_argument("--skill-root", type=Path, default=skill_root)
    result.add_argument("--reference-routes", type=Path, default=skill_root / "assets" / "reference_routes.json")
    result.add_argument("--pretty", action="store_true")
    return result


def emit(payload: Mapping[str, Any], *, pretty: bool, stream: Any) -> None:
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    stream.write(text + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        route = load_json_file(args.route)
        receipt = load_json_file(args.receipt)
        registry = load_reference_routes(args.reference_routes)
    except RuntimeError as exc:
        emit({"error": "input_error", "message": str(exc)}, pretty=args.pretty, stream=sys.stderr)
        return EXIT_INPUT_ERROR

    if not isinstance(route, dict) or not ROUTE_FIELDS.issubset(route):
        emit(
            {"error": "invalid_route", "message": "route is missing P0-6 reference requirements"},
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INVALID
    gate = route.get("reference_gate")
    if not isinstance(gate, dict) or not {"plan_sha256", "task_stage", "as_of_date", "decision_points"}.issubset(gate):
        emit(
            {"error": "invalid_route", "message": "reference_gate is missing binding metadata"},
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INVALID

    requirements = {name: route[name] for name in ROUTE_FIELDS if name != "reference_gate"}
    issues = validate_receipt(
        receipt,
        plan_sha256=gate["plan_sha256"],
        task_stage=gate["task_stage"],
        as_of_date=gate["as_of_date"],
        decision_points=gate["decision_points"],
        requirements=requirements,
        registry=registry,
        skill_root=args.skill_root,
    )
    if issues:
        emit(
            {"error": "invalid_reference_receipt", "issues": [issue.as_dict() for issue in issues]},
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return EXIT_INVALID
    emit({"status": "passed", "plan_sha256": gate["plan_sha256"]}, pretty=args.pretty, stream=sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
