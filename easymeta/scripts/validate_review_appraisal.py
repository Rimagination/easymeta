#!/usr/bin/env python3
"""Validate CEESAT/MATES appraisal targets and layer-separation invariants."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path


FIELDS = [
    "appraisal_id", "review_id", "question_id", "product_type", "tool_id",
    "tool_version", "model_id", "target_selection_rule", "target_selection_deviation",
    "deviation_rationale", "documents_examined", "item_id", "judgment",
    "support_locator", "not_reported_does_not_prove_not_done",
    "aggregation_forbidden", "assessor", "assessed_at", "notes",
]
TOOLS = {"CEESAT_REVIEW", "CEESAT_OVERVIEW", "MATES"}
PRODUCTS = {"evidence_review", "evidence_overview", "environmental_meta_analysis"}


def truth(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    try:
        with args.ledger.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != FIELDS:
                raise ValueError("header must exactly match review_level_appraisal_template.csv")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 2

    issues: list[dict[str, object]] = []
    invariant: dict[str, tuple[str, ...]] = {}
    seen_items: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=2):
        def add(field: str, message: str) -> None:
            issues.append({"row": index, "field": field, "message": message})

        for field in ("appraisal_id", "review_id", "product_type", "tool_id", "tool_version", "documents_examined", "item_id", "judgment", "support_locator", "assessor", "assessed_at"):
            if not row[field].strip():
                add(field, "is required")
        tool = row["tool_id"]
        product = row["product_type"]
        if tool not in TOOLS:
            add("tool_id", "unsupported tool")
        if product not in PRODUCTS:
            add("product_type", "unsupported product type")
        if tool == "CEESAT_REVIEW":
            if row["tool_version"] != "2.2":
                add("tool_version", "CEESAT_REVIEW must use v2.2")
            if product != "evidence_review":
                add("product_type", "CEESAT_REVIEW only applies to evidence_review")
            if not row["question_id"].strip():
                add("question_id", "is required because CEESAT evaluates a question/hypothesis")
            if row["model_id"].strip():
                add("model_id", "must be empty for CEESAT")
        if tool == "CEESAT_OVERVIEW" and product != "evidence_overview":
            add("product_type", "CEESAT_OVERVIEW only applies to evidence_overview")
        if tool == "MATES":
            if product != "environmental_meta_analysis":
                add("product_type", "MATES only applies to environmental_meta_analysis")
            if not row["model_id"].strip():
                add("model_id", "exactly one target Meta analysis/model is required")
            rule = row["target_selection_rule"].strip()
            deviation = truth(row["target_selection_deviation"])
            if not rule:
                add("target_selection_rule", "is required for MATES")
            if deviation is None:
                add("target_selection_deviation", "must be true or false")
            if rule != "first_meta_analysis_in_paper" and deviation is not True:
                add("target_selection_deviation", "must be true when not using the standard first-analysis rule")
            if deviation is True and not row["deviation_rationale"].strip():
                add("deviation_rationale", "is required for a target-selection deviation")
        for field in ("not_reported_does_not_prove_not_done", "aggregation_forbidden"):
            if truth(row[field]) is not True:
                add(field, "must be true")
        try:
            date.fromisoformat(row["assessed_at"])
        except ValueError:
            add("assessed_at", "must be YYYY-MM-DD")
        key = (row["appraisal_id"], row["item_id"])
        if key in seen_items:
            add("item_id", "must be unique within appraisal_id")
        seen_items.add(key)
        signature = tuple(row[field] for field in ("review_id", "question_id", "product_type", "tool_id", "tool_version", "model_id", "target_selection_rule", "target_selection_deviation"))
        previous = invariant.setdefault(row["appraisal_id"], signature)
        if signature != previous:
            add("appraisal_id", "target fields must be invariant within one appraisal")

    result = {"valid": not issues, "rows": len(rows), "issues": issues}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), file=sys.stdout if not issues else sys.stderr)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
