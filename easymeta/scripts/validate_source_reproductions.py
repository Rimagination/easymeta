#!/usr/bin/env python3
"""Validate the frozen-source and numerical-oracle reproduction manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests" / "source_reproduction_cases.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MD5 = re.compile(r"^[0-9a-f]{32}$")
ALLOWED_CLASSIFICATIONS = {
    "exact_reproduction",
    "targeted_reproduction",
    "modern_reanalysis",
}
ALLOWED_STATUSES = {"verified", "pending", "not_run", "failed", "blocked"}
ALLOWED_LICENSE_STATUSES = {"declared", "not_stated", "restricted"}


class ManifestError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def relative_path(value: Any, label: str) -> PurePosixPath:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty path")
    path = PurePosixPath(value)
    require(not path.is_absolute(), f"{label} must be relative")
    require(".." not in path.parts, f"{label} cannot traverse outside the asset root")
    return path


def https_url(value: Any, label: str) -> None:
    require(isinstance(value, str) and value.startswith("https://"), f"{label} must use https")


def validate_artifact(case_id: str, artifact: dict[str, Any], seen: set[str]) -> None:
    artifact_id = artifact.get("id")
    require(isinstance(artifact_id, str) and artifact_id, f"{case_id}: artifact id is required")
    require(artifact_id not in seen, f"{case_id}: duplicate artifact id {artifact_id}")
    seen.add(artifact_id)
    relative_path(artifact.get("path"), f"{case_id}/{artifact_id}.path")
    require(isinstance(artifact.get("size"), int) and artifact["size"] > 0,
            f"{case_id}/{artifact_id}: positive byte size is required")
    checksums = artifact.get("checksums")
    require(isinstance(checksums, dict), f"{case_id}/{artifact_id}: checksums are required")
    sha256 = checksums.get("sha256", "")
    require(isinstance(sha256, str) and SHA256.fullmatch(sha256) is not None,
            f"{case_id}/{artifact_id}: lowercase SHA-256 is required")
    if "md5" in checksums:
        md5 = checksums["md5"]
        require(isinstance(md5, str) and MD5.fullmatch(md5) is not None,
                f"{case_id}/{artifact_id}: invalid MD5")
    acquisition = artifact.get("acquisition")
    require(isinstance(acquisition, dict), f"{case_id}/{artifact_id}: acquisition is required")
    mode = acquisition.get("mode")
    require(mode in {"direct", "figshare_version_file", "zenodo_record_file"},
            f"{case_id}/{artifact_id}: unsupported acquisition mode {mode}")
    if mode == "direct":
        https_url(acquisition.get("download_url"), f"{case_id}/{artifact_id}.download_url")
    else:
        https_url(acquisition.get("metadata_url"), f"{case_id}/{artifact_id}.metadata_url")
        require(isinstance(acquisition.get("file_name"), str) and acquisition["file_name"],
                f"{case_id}/{artifact_id}: resolver file_name is required")
        if mode == "figshare_version_file":
            require(acquisition["file_name"] == PurePosixPath(artifact["path"]).name,
                    f"{case_id}/{artifact_id}: Figshare file_name must match artifact path")
    require(artifact.get("redistribution") in {"cc_by_4_0", "gpl_3_0", "external_only"},
            f"{case_id}/{artifact_id}: redistribution rule is required")
    if "extract_to" in artifact:
        relative_path(artifact["extract_to"], f"{case_id}/{artifact_id}.extract_to")
        require(str(artifact["path"]).lower().endswith(".zip"),
                f"{case_id}/{artifact_id}: only zip extraction is supported")


def validate_input(case_id: str, item: dict[str, Any], seen: set[str]) -> None:
    name = item.get("name")
    require(isinstance(name, str) and name, f"{case_id}: input name is required")
    require(name not in seen, f"{case_id}: duplicate input name {name}")
    seen.add(name)
    relative_path(item.get("path"), f"{case_id}/{name}.path")
    require(isinstance(item.get("size"), int) and item["size"] > 0,
            f"{case_id}/{name}: positive input size is required")
    sha256 = item.get("sha256", "")
    require(isinstance(sha256, str) and SHA256.fullmatch(sha256) is not None,
            f"{case_id}/{name}: lowercase input SHA-256 is required")
    require(isinstance(item.get("role"), str) and item["role"],
            f"{case_id}/{name}: input role is required")


def validate_assertion(case_id: str, assertion: dict[str, Any], seen: set[str]) -> None:
    path = assertion.get("path")
    require(isinstance(path, str) and path.startswith("/"),
            f"{case_id}: oracle path must be a JSON pointer")
    require(path not in seen, f"{case_id}: duplicate oracle path {path}")
    seen.add(path)
    expected = assertion.get("expected")
    abs_tol = assertion.get("abs_tol")
    rel_tol = assertion.get("rel_tol")
    require(isinstance(abs_tol, (int, float)) and abs_tol >= 0,
            f"{case_id}{path}: non-negative abs_tol is required")
    require(isinstance(rel_tol, (int, float)) and rel_tol >= 0,
            f"{case_id}{path}: non-negative rel_tol is required")
    if isinstance(expected, bool):
        require(abs_tol == 0 and rel_tol == 0,
                f"{case_id}{path}: boolean assertions require zero tolerance")
    else:
        require(isinstance(expected, (int, float)),
                f"{case_id}{path}: numeric or boolean expected value is required")


def validate_case(case: dict[str, Any], seen_ids: set[str]) -> None:
    case_id = case.get("id")
    require(isinstance(case_id, str) and case_id, "case id is required")
    require(case_id not in seen_ids, f"duplicate case id {case_id}")
    seen_ids.add(case_id)
    require(isinstance(case.get("benchmark_id"), str) and case["benchmark_id"].startswith("BENCH-"),
            f"{case_id}: benchmark_id is required")
    require(case.get("classification") in ALLOWED_CLASSIFICATIONS,
            f"{case_id}: invalid classification")
    require(case.get("verification_status") in ALLOWED_STATUSES,
            f"{case_id}: invalid verification_status")
    require(isinstance(case.get("scope"), str) and case["scope"].strip(),
            f"{case_id}: scope is required")

    article = case.get("article")
    require(isinstance(article, dict), f"{case_id}: article metadata is required")
    require(isinstance(article.get("doi"), str) and article["doi"].startswith("10."),
            f"{case_id}: article DOI is required")
    https_url(article.get("url"), f"{case_id}.article.url")
    require(isinstance(article.get("citation"), str) and article["citation"],
            f"{case_id}: article citation is required")

    release = case.get("source_release")
    require(isinstance(release, dict), f"{case_id}: source_release is required")
    require(release.get("provider") in {"OSF", "Figshare", "Zenodo"},
            f"{case_id}: unsupported source provider")
    require(isinstance(release.get("record_id"), str) and release["record_id"],
            f"{case_id}: source record_id is required")
    require(isinstance(release.get("version"), str) and release["version"].strip(),
            f"{case_id}: frozen source version is required")
    require(str(release["version"]).lower() not in {"latest", "main", "master"},
            f"{case_id}: floating source version is forbidden")
    require(release.get("license_status") in ALLOWED_LICENSE_STATUSES,
            f"{case_id}: explicit license status is required")
    require(isinstance(release.get("license"), str) and release["license"],
            f"{case_id}: license value is required, including not_stated")
    https_url(release.get("landing_url"), f"{case_id}.source_release.landing_url")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(release.get("accessed_at", ""))) is not None,
            f"{case_id}: accessed_at must be YYYY-MM-DD")

    artifacts = case.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, f"{case_id}: artifacts are required")
    artifact_ids: set[str] = set()
    for artifact in artifacts:
        require(isinstance(artifact, dict), f"{case_id}: artifact entries must be objects")
        validate_artifact(case_id, artifact, artifact_ids)

    inputs = case.get("inputs")
    require(isinstance(inputs, list) and inputs, f"{case_id}: frozen inputs are required")
    input_names: set[str] = set()
    for item in inputs:
        require(isinstance(item, dict), f"{case_id}: input entries must be objects")
        validate_input(case_id, item, input_names)

    execution = case.get("execution")
    require(isinstance(execution, dict), f"{case_id}: execution contract is required")
    adapter = relative_path(execution.get("adapter"), f"{case_id}.execution.adapter")
    adapter_path = ROOT / Path(*adapter.parts)
    require(adapter_path.is_file(), f"{case_id}: adapter does not exist: {adapter}")
    adapter_hash = execution.get("adapter_sha256", "")
    require(isinstance(adapter_hash, str) and SHA256.fullmatch(adapter_hash) is not None,
            f"{case_id}: adapter SHA-256 is required")
    actual_adapter_hash = hashlib.sha256(adapter_path.read_bytes()).hexdigest()
    require(adapter_hash == actual_adapter_hash,
            f"{case_id}: adapter SHA-256 does not match the executable file")
    require(execution.get("runtime") == "Rscript", f"{case_id}: only Rscript adapters are supported")
    require(isinstance(execution.get("args"), list) and execution["args"],
            f"{case_id}: execution args are required")
    require(isinstance(execution.get("timeout_seconds"), int) and execution["timeout_seconds"] > 0,
            f"{case_id}: positive timeout_seconds is required")
    enabled = execution.get("enabled", True)
    require(isinstance(enabled, bool), f"{case_id}: execution.enabled must be boolean")
    if not enabled:
        require(case["verification_status"] == "blocked",
                f"{case_id}: disabled execution is only valid for a blocked case")
        require(isinstance(execution.get("blocked_reason"), str) and execution["blocked_reason"],
                f"{case_id}: disabled execution requires blocked_reason")
    if case["verification_status"] == "blocked":
        require(not enabled, f"{case_id}: blocked cases must disable execution")
    input_tokens = {"{" + name + "}" for name in input_names}
    arg_tokens = {value for value in execution["args"] if isinstance(value, str) and value.startswith("{")}
    require("{output}" in arg_tokens, f"{case_id}: execution args must declare {{output}}")
    require(arg_tokens - {"{output}"} <= input_tokens,
            f"{case_id}: execution args reference an undeclared input")

    oracle = case.get("oracle")
    require(isinstance(oracle, dict), f"{case_id}: numerical oracle is required")
    require(oracle.get("evidence_kind") in {
        "publication_numeric",
        "author_code_and_publication_numeric",
        "author_code_numeric_and_publication_direction",
    }, f"{case_id}: oracle evidence_kind is required")
    require(oracle.get("analysis_scale") in {"log", "log_response_ratio"},
            f"{case_id}: oracle analysis scale is required")
    require(isinstance(oracle.get("source_locator"), str) and oracle["source_locator"],
            f"{case_id}: oracle source locator is required")
    assertions = oracle.get("assertions")
    require(isinstance(assertions, list) and len(assertions) >= 3,
            f"{case_id}: at least three numerical assertions are required")
    assertion_paths: set[str] = set()
    for assertion in assertions:
        require(isinstance(assertion, dict), f"{case_id}: oracle assertions must be objects")
        validate_assertion(case_id, assertion, assertion_paths)

    verification = case.get("verification")
    require(isinstance(verification, dict), f"{case_id}: verification record is required")
    if case["verification_status"] == "verified":
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(verification.get("verified_on", ""))) is not None,
                f"{case_id}: verified_on is required for verified cases")
        require(isinstance(verification.get("environment"), dict) and verification["environment"],
                f"{case_id}: verified environment is required")
        require(verification.get("result") == "pass",
                f"{case_id}: verified cases must record result=pass")
        output_hash = verification.get("frozen_output_sha256", "")
        require(isinstance(output_hash, str) and SHA256.fullmatch(output_hash) is not None,
                f"{case_id}: verified cases require a frozen output SHA-256")
    if case["classification"] == "targeted_reproduction":
        limitations = case.get("limitations")
        require(isinstance(limitations, list) and limitations,
                f"{case_id}: targeted reproduction must disclose limitations")


def validate_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == "1.0", "schema_version must be 1.0")
    require(payload.get("asset_root_env") == "EASYMETA_SOURCE_REPRO_ROOT",
            "asset_root_env must be EASYMETA_SOURCE_REPRO_ROOT")
    cases = payload.get("cases")
    require(isinstance(cases, list) and cases, "cases must be a non-empty array")
    seen_ids: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), "each case must be an object")
        validate_case(case, seen_ids)
    verified = sum(
        case["verification_status"] == "verified"
        and case["classification"] in {"exact_reproduction", "targeted_reproduction"}
        for case in cases
    )
    blocked = sum(case["verification_status"] == "blocked" for case in cases)
    classifications: dict[str, int] = {}
    for case in cases:
        key = case["classification"]
        classifications[key] = classifications.get(key, 0) + 1
    return {
        "schema_version": payload["schema_version"],
        "case_count": len(cases),
        "verified_source_reproductions": verified,
        "blocked_source_cases": blocked,
        "classifications": classifications,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = validate_manifest(payload)
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
