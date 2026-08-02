#!/usr/bin/env python3
"""Validate a project guidance/version manifest without judging source authority."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path


FIELDS = [
    "source_id", "source_type", "title", "owner", "official_url", "version_used",
    "published_or_updated", "accessed_at", "applicable_stage", "authority",
    "living_source", "checked_at_milestone", "snapshot_or_archive", "sha256",
    "update_signal", "change_summary", "impact_class", "adoption_decision",
    "protocol_deviation_id", "license_or_copyright", "reviewer", "supersedes",
]
SOURCE_TYPES = {"standard", "reporting", "handbook", "method", "appraisal", "software", "benchmark"}
IMPACT_CLASSES = {"none", "editorial", "reporting", "conduct", "analysis", "software", "license"}
DECISIONS = {"adopted", "not_adopted", "not_applicable", "pending_impact_assessment"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        with args.manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != FIELDS:
                raise ValueError("header must exactly match guidance_manifest_template.csv")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 2

    issues: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        def add(field: str, message: str) -> None:
            issues.append({"row": index, "field": field, "message": message})

        for field in ("source_id", "source_type", "title", "owner", "official_url", "version_used", "accessed_at", "applicable_stage", "authority", "living_source", "impact_class", "adoption_decision", "license_or_copyright", "reviewer"):
            if not row[field].strip():
                add(field, "is required")
        source_id = row["source_id"].strip()
        if source_id in seen:
            add("source_id", "must be unique")
        seen.add(source_id)
        if row["source_type"] not in SOURCE_TYPES:
            add("source_type", "unsupported source type")
        if not row["official_url"].startswith(("https://", "http://")):
            add("official_url", "must be an HTTP(S) URL")
        for field in ("published_or_updated", "accessed_at"):
            if row[field] and not iso_date(row[field]):
                add(field, "must be YYYY-MM-DD")
        living = row["living_source"].lower()
        if living not in {"true", "false"}:
            add("living_source", "must be true or false")
        if living == "true":
            for field in ("checked_at_milestone", "update_signal", "change_summary"):
                if not row[field].strip():
                    add(field, "is required for a living source")
        if row["snapshot_or_archive"] and not SHA256_RE.fullmatch(row["sha256"]):
            add("sha256", "must be a 64-character SHA-256 when a snapshot/archive is declared")
        if row["sha256"] and not SHA256_RE.fullmatch(row["sha256"]):
            add("sha256", "must be a 64-character hexadecimal SHA-256")
        if row["impact_class"] not in IMPACT_CLASSES:
            add("impact_class", "unsupported impact class")
        if row["adoption_decision"] not in DECISIONS:
            add("adoption_decision", "unsupported adoption decision")
        if row["impact_class"] in {"conduct", "analysis"} and row["adoption_decision"] == "adopted" and not row["protocol_deviation_id"].strip():
            add("protocol_deviation_id", "is required when an adopted update changes conduct or analysis")

    result = {"valid": not issues, "rows": len(rows), "issues": issues}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), file=sys.stdout if not issues else sys.stderr)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
