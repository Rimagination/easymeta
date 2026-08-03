#!/usr/bin/env python3
"""Resolve and validate EasyMeta's auditable reference-routing gate.

This module verifies files, identifiers, hashes, section locators, decision
mappings, and living-source check dates. It records an attestation; it cannot
prove that a human or model actually understood a source.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


REFERENCE_ROUTE_SCHEMA_VERSION = "1.0"
RECEIPT_SCHEMA_VERSION = "1.0"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ADOPTION_DECISIONS = {"adopted", "adopted_with_modification", "not_adopted_with_reason"}

RECEIPT_FIELDS = {
    "schema_version",
    "plan_sha256",
    "task_stage",
    "attested_by",
    "attested_at",
    "reference_files",
    "source_records",
}
REFERENCE_FILE_FIELDS = {
    "path",
    "sha256",
    "sections_used",
    "decision_mapping",
}
DECISION_MAPPING_FIELDS = {"decision_id", "applied_rule"}
SOURCE_RECORD_FIELDS = {
    "source_id",
    "version_used",
    "accessed_at",
    "checked_at_milestone",
    "adoption_decision",
    "change_summary",
}


@dataclass(frozen=True)
class GateIssue:
    code: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


class DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"Duplicate JSON member: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_number(value: str) -> None:
    raise ValueError(f"Non-finite JSON number is not allowed: {value}")


def load_json_file(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"Could not read UTF-8 JSON {path}: {exc}") from exc
    try:
        return json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_number,
        )
    except (json.JSONDecodeError, DuplicateKeyError, ValueError) as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _value_at(payload: Mapping[str, Any], dotted_path: str) -> Any:
    value: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _predicate_matches(payload: Mapping[str, Any], predicate: Mapping[str, Any]) -> bool:
    path = predicate["path"]
    operator = predicate["operator"]
    actual = _value_at(payload, path)
    if operator == "equals":
        return actual == predicate["value"]
    if operator == "in":
        return actual in predicate["values"]
    if operator == "contains":
        return isinstance(actual, list) and predicate["value"] in actual
    if operator == "intersects":
        return isinstance(actual, list) and bool(set(actual) & set(predicate["values"]))
    raise RuntimeError(f"Unsupported reference-route operator {operator!r}")


def _validate_predicate(predicate: Any, *, field: str) -> None:
    if not isinstance(predicate, dict):
        raise RuntimeError(f"{field} must be an object")
    operator = predicate.get("operator")
    expected = {"path", "operator", "value"} if operator in {"equals", "contains"} else {"path", "operator", "values"}
    if operator not in {"equals", "in", "contains", "intersects"}:
        raise RuntimeError(f"{field}.operator is unsupported")
    if set(predicate) != expected:
        raise RuntimeError(f"{field} fields must exactly equal {sorted(expected)}")
    if not isinstance(predicate["path"], str) or not predicate["path"].strip():
        raise RuntimeError(f"{field}.path must be a non-empty string")
    if "values" in predicate and (not isinstance(predicate["values"], list) or not predicate["values"]):
        raise RuntimeError(f"{field}.values must be a non-empty array")


def load_reference_routes(path: Path) -> Mapping[str, Any]:
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        raise RuntimeError("Reference-route registry must be a JSON object")
    if set(payload) != {"schema_version", "receipt_schema_version", "source_metadata", "rules"}:
        raise RuntimeError("Reference-route registry has missing or unexpected root fields")
    if payload["schema_version"] != REFERENCE_ROUTE_SCHEMA_VERSION:
        raise RuntimeError(f"Reference-route schema must equal {REFERENCE_ROUTE_SCHEMA_VERSION!r}")
    if payload["receipt_schema_version"] != RECEIPT_SCHEMA_VERSION:
        raise RuntimeError(f"Receipt schema must equal {RECEIPT_SCHEMA_VERSION!r}")

    sources = payload["source_metadata"]
    if not isinstance(sources, dict) or not sources:
        raise RuntimeError("source_metadata must be a non-empty object")
    for source_id, metadata in sources.items():
        if not isinstance(source_id, str) or not source_id:
            raise RuntimeError("source_metadata keys must be non-empty strings")
        if not isinstance(metadata, dict) or set(metadata) != {"living"} or type(metadata["living"]) is not bool:
            raise RuntimeError(f"source_metadata.{source_id} must contain exactly one boolean living field")

    rules = payload["rules"]
    if not isinstance(rules, list) or not rules:
        raise RuntimeError("rules must be a non-empty array")
    seen_rule_ids: set[str] = set()
    for index, rule in enumerate(rules):
        field = f"rules[{index}]"
        if not isinstance(rule, dict) or set(rule) != {"id", "match", "required_reference_files", "required_source_ids"}:
            raise RuntimeError(f"{field} has missing or unexpected fields")
        rule_id = rule["id"]
        if not isinstance(rule_id, str) or not rule_id or rule_id in seen_rule_ids:
            raise RuntimeError(f"{field}.id must be a unique non-empty string")
        seen_rule_ids.add(rule_id)
        match = rule["match"]
        if not isinstance(match, dict) or not set(match).issubset({"all", "any"}) or not match:
            raise RuntimeError(f"{field}.match must contain all and/or any")
        for group in ("all", "any"):
            if group in match:
                predicates = match[group]
                if not isinstance(predicates, list) or not predicates:
                    raise RuntimeError(f"{field}.match.{group} must be a non-empty array")
                for pred_index, predicate in enumerate(predicates):
                    _validate_predicate(predicate, field=f"{field}.match.{group}[{pred_index}]")
        files = rule["required_reference_files"]
        source_ids = rule["required_source_ids"]
        if not isinstance(files, list) or any(not isinstance(item, str) or not item for item in files):
            raise RuntimeError(f"{field}.required_reference_files must be a string array")
        if len(files) != len(set(files)):
            raise RuntimeError(f"{field}.required_reference_files must not contain duplicates")
        for item in files:
            pure = PurePosixPath(item)
            if pure.is_absolute() or ".." in pure.parts or not item.startswith("references/"):
                raise RuntimeError(f"{field} contains an unsafe reference path: {item!r}")
        if not isinstance(source_ids, list) or any(not isinstance(item, str) or item not in sources for item in source_ids):
            raise RuntimeError(f"{field}.required_source_ids contains an unknown source")
        if len(source_ids) != len(set(source_ids)):
            raise RuntimeError(f"{field}.required_source_ids must not contain duplicates")
    return payload


def resolve_requirements(plan: Mapping[str, Any], registry: Mapping[str, Any]) -> dict[str, Any]:
    matched: list[str] = []
    references: set[str] = set()
    source_ids: set[str] = set()
    for rule in registry["rules"]:
        match = rule["match"]
        all_matches = all(_predicate_matches(plan, item) for item in match.get("all", []))
        any_matches = not match.get("any") or any(
            _predicate_matches(plan, item) for item in match["any"]
        )
        if all_matches and any_matches:
            matched.append(rule["id"])
            references.update(rule["required_reference_files"])
            source_ids.update(rule["required_source_ids"])

    living = sorted(
        source_id
        for source_id in source_ids
        if registry["source_metadata"][source_id]["living"]
    )
    return {
        "required_references": sorted(references),
        "required_source_ids": sorted(source_ids),
        "required_living_source_ids": living,
        "matched_reference_rules": sorted(matched),
    }


def _shape_issues(value: Any, expected: set[str], field: str, issues: list[GateIssue]) -> Mapping[str, Any] | None:
    if not isinstance(value, dict):
        issues.append(GateIssue("wrong_type", field, "must be a JSON object"))
        return None
    actual = set(value)
    for name in sorted(expected - actual):
        issues.append(GateIssue("missing_field", f"{field}.{name}" if field else name, "is required"))
    for name in sorted(actual - expected):
        issues.append(GateIssue("unexpected_field", f"{field}.{name}" if field else name, "is not allowed"))
    return value


def _date_value(value: Any, *, field: str, issues: list[GateIssue]) -> date | None:
    if not isinstance(value, str):
        issues.append(GateIssue("wrong_type", field, "must be an ISO date (YYYY-MM-DD)"))
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        issues.append(GateIssue("invalid_date", field, "must be an ISO date (YYYY-MM-DD)"))
        return None


def _safe_reference_path(skill_root: Path, relative: Any, *, field: str, issues: list[GateIssue]) -> Path | None:
    if not isinstance(relative, str) or not relative:
        issues.append(GateIssue("wrong_type", field, "must be a non-empty relative POSIX path"))
        return None
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        issues.append(GateIssue("path_outside_allowed_root", field, "must stay inside the skill root and use POSIX separators"))
        return None
    root = skill_root.resolve()
    candidate = (root / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        issues.append(GateIssue("path_outside_allowed_root", field, "resolves outside the skill root"))
        return None
    if not candidate.is_file():
        issues.append(GateIssue("missing_reference_file", field, f"does not resolve to a file: {relative}"))
        return None
    return candidate


def validate_receipt(
    receipt: Any,
    *,
    plan_sha256: str,
    task_stage: str,
    as_of_date: str | None,
    decision_points: Sequence[str],
    requirements: Mapping[str, Any],
    registry: Mapping[str, Any],
    skill_root: Path,
) -> list[GateIssue]:
    issues: list[GateIssue] = []
    root = _shape_issues(receipt, RECEIPT_FIELDS, "", issues)
    if root is None:
        return issues

    if root.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        issues.append(GateIssue("unsupported_value", "schema_version", f"must equal {RECEIPT_SCHEMA_VERSION!r}"))
    if root.get("plan_sha256") != plan_sha256:
        issues.append(GateIssue("plan_binding_mismatch", "plan_sha256", "does not match the canonical synthesis plan"))
    if root.get("task_stage") != task_stage:
        issues.append(GateIssue("stage_binding_mismatch", "task_stage", "does not match task.stage"))
    if not isinstance(root.get("attested_by"), str) or not root["attested_by"].strip():
        issues.append(GateIssue("missing_value", "attested_by", "must identify the accountable reviewer or agent run"))

    as_of = _date_value(as_of_date, field="task.as_of_date", issues=issues) if as_of_date is not None else None
    if as_of_date is None:
        issues.append(GateIssue("missing_as_of_date", "task.as_of_date", "is required before a reference receipt can pass"))
    attested = _date_value(root.get("attested_at"), field="attested_at", issues=issues)
    if as_of is not None and attested is not None and attested > as_of:
        issues.append(GateIssue("future_date", "attested_at", "cannot be after task.as_of_date"))

    expected_files = set(requirements["required_references"])
    file_records = root.get("reference_files")
    seen_files: set[str] = set()
    if not isinstance(file_records, list):
        issues.append(GateIssue("wrong_type", "reference_files", "must be an array"))
    else:
        for index, item in enumerate(file_records):
            field = f"reference_files[{index}]"
            record = _shape_issues(item, REFERENCE_FILE_FIELDS, field, issues)
            if record is None:
                continue
            relative = record.get("path")
            if isinstance(relative, str):
                if relative in seen_files:
                    issues.append(GateIssue("duplicate_reference_path", f"{field}.path", "must be unique"))
                seen_files.add(relative)
            candidate = _safe_reference_path(skill_root, relative, field=f"{field}.path", issues=issues)
            claimed_hash = record.get("sha256")
            if not isinstance(claimed_hash, str) or not SHA256_PATTERN.fullmatch(claimed_hash):
                issues.append(GateIssue("invalid_sha256", f"{field}.sha256", "must be 64 lowercase hexadecimal characters"))
            elif candidate is not None and file_sha256(candidate) != claimed_hash:
                issues.append(GateIssue("sha256_mismatch", f"{field}.sha256", "does not match the current file bytes"))

            sections = record.get("sections_used")
            file_text: str | None = None
            if candidate is not None:
                try:
                    file_text = candidate.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeError):
                    file_text = None
            if not isinstance(sections, list) or not sections or any(not isinstance(value, str) or not value.strip() for value in sections):
                issues.append(GateIssue("missing_chapter_mapping", f"{field}.sections_used", "must contain non-empty section locators"))
            else:
                for section_index, section in enumerate(sections):
                    if file_text is not None and section not in file_text:
                        issues.append(GateIssue("unknown_section_locator", f"{field}.sections_used[{section_index}]", "was not found verbatim in the referenced local file"))

            mappings = record.get("decision_mapping")
            if not isinstance(mappings, list) or not mappings:
                issues.append(GateIssue("missing_decision_mapping", f"{field}.decision_mapping", "must map the reference to at least one decision"))
            else:
                allowed_decisions = set(decision_points) | set(requirements["matched_reference_rules"])
                for mapping_index, mapping in enumerate(mappings):
                    mapping_field = f"{field}.decision_mapping[{mapping_index}]"
                    mapped = _shape_issues(mapping, DECISION_MAPPING_FIELDS, mapping_field, issues)
                    if mapped is None:
                        continue
                    decision_id = mapped.get("decision_id")
                    if not isinstance(decision_id, str) or decision_id not in allowed_decisions:
                        issues.append(GateIssue("unknown_decision_id", f"{mapping_field}.decision_id", "must name a requested decision point or matched reference rule"))
                    if not isinstance(mapped.get("applied_rule"), str) or not mapped["applied_rule"].strip():
                        issues.append(GateIssue("missing_value", f"{mapping_field}.applied_rule", "must state how the source affected the decision"))

    if seen_files != expected_files:
        missing = sorted(expected_files - seen_files)
        extra = sorted(seen_files - expected_files)
        issues.append(GateIssue("reference_set_mismatch", "reference_files", f"must exactly match required references; missing={missing}, extra={extra}"))

    expected_sources = set(requirements["required_source_ids"])
    living_sources = set(requirements["required_living_source_ids"])
    source_records = root.get("source_records")
    seen_sources: set[str] = set()
    if not isinstance(source_records, list):
        issues.append(GateIssue("wrong_type", "source_records", "must be an array"))
    else:
        for index, item in enumerate(source_records):
            field = f"source_records[{index}]"
            record = _shape_issues(item, SOURCE_RECORD_FIELDS, field, issues)
            if record is None:
                continue
            source_id = record.get("source_id")
            if isinstance(source_id, str):
                if source_id in seen_sources:
                    issues.append(GateIssue("duplicate_source_id", f"{field}.source_id", "must be unique"))
                seen_sources.add(source_id)
                if source_id not in registry["source_metadata"]:
                    issues.append(GateIssue("unknown_source_id", f"{field}.source_id", "is not registered"))
            if not isinstance(record.get("version_used"), str) or not record["version_used"].strip():
                issues.append(GateIssue("missing_value", f"{field}.version_used", "must record the version or page state used"))
            accessed = _date_value(record.get("accessed_at"), field=f"{field}.accessed_at", issues=issues)
            if as_of is not None and accessed is not None and accessed > as_of:
                issues.append(GateIssue("future_date", f"{field}.accessed_at", "cannot be after task.as_of_date"))
            if source_id in living_sources and as_of is not None and accessed is not None and accessed != as_of:
                issues.append(GateIssue("living_guidance_stale", f"{field}.accessed_at", "living guidance must be checked on task.as_of_date"))
            if record.get("checked_at_milestone") != task_stage:
                issues.append(GateIssue("milestone_mismatch", f"{field}.checked_at_milestone", "must equal task.stage"))
            if record.get("adoption_decision") not in ADOPTION_DECISIONS:
                issues.append(GateIssue("unsupported_value", f"{field}.adoption_decision", "must record a supported adoption decision"))
            if not isinstance(record.get("change_summary"), str) or not record["change_summary"].strip():
                issues.append(GateIssue("missing_value", f"{field}.change_summary", "must summarize the update check and decision impact"))

    if seen_sources != expected_sources:
        missing = sorted(expected_sources - seen_sources)
        extra = sorted(seen_sources - expected_sources)
        issues.append(GateIssue("source_set_mismatch", "source_records", f"must exactly match required source IDs; missing={missing}, extra={extra}"))
    return issues


def build_gate_result(
    receipt: Any | None,
    *,
    plan: Mapping[str, Any],
    requirements: Mapping[str, Any],
    registry: Mapping[str, Any],
    skill_root: Path,
) -> dict[str, Any]:
    plan_hash = canonical_sha256(plan)
    task = plan["task"]
    if receipt is None:
        issues = [GateIssue("missing_reference_receipt", "reference_receipt", "a validated receipt is required before a runner can be allowed")]
        status = "pending"
    else:
        issues = validate_receipt(
            receipt,
            plan_sha256=plan_hash,
            task_stage=task["stage"],
            as_of_date=task["as_of_date"],
            decision_points=task["decision_points"],
            requirements=requirements,
            registry=registry,
            skill_root=skill_root,
        )
        status = "passed" if not issues else "failed"
    return {
        "status": status,
        "plan_sha256": plan_hash,
        "task_stage": task["stage"],
        "as_of_date": task["as_of_date"],
        "issues": [issue.as_dict() for issue in issues],
        "attestation_boundary": "verifies the audit record, not human or model comprehension",
    }
