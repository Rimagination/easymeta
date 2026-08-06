#!/usr/bin/env python3
"""Run frozen-data ecology reproductions and compare numerical oracles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from materialize_source_reproductions import default_asset_root, materialize  # noqa: E402
from validate_source_reproductions import DEFAULT_MANIFEST, ManifestError, validate_manifest  # noqa: E402


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def resolve_pointer(payload: Any, pointer: str) -> Any:
    current = payload
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def r_environment() -> dict[str, str]:
    env = os.environ.copy()
    test_library = env.get("META_TEST_R_LIBRARY", "").strip()
    existing = env.get("R_LIBS_USER", "").strip()
    if test_library:
        env["R_LIBS_USER"] = test_library if not existing else test_library + os.pathsep + existing
    return env


def run_case(
    case: dict[str, Any],
    asset_root: Path,
    output_dir: Path,
    r_script: str,
    require_frozen_output: bool,
) -> dict[str, Any]:
    adapter = ROOT / Path(case["execution"]["adapter"])
    actual_adapter_hash = file_sha256(adapter)
    expected_adapter_hash = case["execution"]["adapter_sha256"]
    if actual_adapter_hash != expected_adapter_hash:
        return {
            "id": case["id"],
            "status": "FAIL",
            "reason": "adapter_sha256_mismatch",
            "expected": expected_adapter_hash,
            "actual": actual_adapter_hash,
        }
    inputs = {item["name"]: asset_root / Path(item["path"]) for item in case["inputs"]}
    output = output_dir / f"{case['id']}.json"
    substitutions = {"{" + name + "}": str(path) for name, path in inputs.items()}
    substitutions["{output}"] = str(output)
    command = [r_script, str(adapter)]
    command.extend(substitutions.get(str(value), str(value)) for value in case["execution"]["args"])
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=r_environment(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=case["execution"]["timeout_seconds"],
        check=False,
    )
    if completed.returncode != 0:
        return {
            "id": case["id"],
            "status": "FAIL",
            "reason": "adapter_failed",
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"id": case["id"], "status": "FAIL", "reason": f"invalid_output:{exc}"}

    checks: list[dict[str, Any]] = []
    failed = False
    for assertion in case["oracle"]["assertions"]:
        try:
            actual = resolve_pointer(payload, assertion["path"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            checks.append({"path": assertion["path"], "status": "FAIL", "error": str(exc)})
            failed = True
            continue
        expected = assertion["expected"]
        if isinstance(expected, bool):
            passed = isinstance(actual, bool) and actual is expected
        else:
            passed = (
                isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and math.isfinite(float(actual))
                and math.isclose(
                    float(actual),
                    float(expected),
                    rel_tol=float(assertion["rel_tol"]),
                    abs_tol=float(assertion["abs_tol"]),
                )
            )
        checks.append({
            "path": assertion["path"],
            "expected": expected,
            "actual": actual,
            "abs_tol": assertion["abs_tol"],
            "rel_tol": assertion["rel_tol"],
            "status": "PASS" if passed else "FAIL",
        })
        failed = failed or not passed
    output_hash = file_sha256(output)
    frozen_hash = case["verification"].get("frozen_output_sha256")
    output_matches = output_hash == frozen_hash
    failed = failed or (require_frozen_output and not output_matches)
    return {
        "id": case["id"],
        "classification": case["classification"],
        "status": "FAIL" if failed else "PASS",
        "assertions_passed": sum(item["status"] == "PASS" for item in checks),
        "assertion_count": len(checks),
        "checks": checks,
        "output": str(output),
        "output_sha256": output_hash,
        "frozen_output_sha256": frozen_hash,
        "matches_frozen_output": output_matches,
        "output_identity_status": "MATCH" if output_matches else "DRIFT",
        "verification_scope": (
            "frozen_output_identity" if output_matches else "numeric_oracle_only"
        ),
        "require_frozen_output": require_frozen_output,
        "adapter_sha256": actual_adapter_hash,
        "adapter_stderr": completed.stderr[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--require-all", action="store_true")
    identity_group = parser.add_mutually_exclusive_group()
    identity_group.add_argument(
        "--require-frozen-output",
        dest="require_frozen_output",
        action="store_true",
        help="require byte-identical output (default)",
    )
    identity_group.add_argument(
        "--allow-output-drift",
        dest="require_frozen_output",
        action="store_false",
        help="allow numerical-oracle PASS with an explicit numeric_oracle_only label",
    )
    parser.set_defaults(require_frozen_output=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_manifest(manifest)
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    selected = manifest["cases"]
    if args.case_ids:
        wanted = set(args.case_ids)
        selected = [case for case in selected if case["id"] in wanted]
        missing_ids = wanted - {case["id"] for case in selected}
        if missing_ids:
            print(f"FAIL: unknown case ids: {', '.join(sorted(missing_ids))}", file=sys.stderr)
            return 1
    selected_manifest = dict(manifest)
    selected_manifest["cases"] = selected

    asset_root = (args.root or default_asset_root()).resolve()
    output_dir = (args.output_dir or (ROOT.parent / ".local" / "source-reproductions" / "outputs")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        source_report = materialize(selected_manifest, asset_root, allow_download=args.download)
    except (OSError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    source_status = {case["id"]: case["status"] for case in source_report["cases"]}
    configured_r = os.environ.get("R_SCRIPT", "").strip()
    r_script = configured_r or shutil.which("Rscript") or ""
    results: list[dict[str, Any]] = []
    for case in selected:
        if not case["execution"].get("enabled", True):
            results.append({
                "id": case["id"],
                "status": "BLOCKED",
                "reason": case["execution"]["blocked_reason"],
            })
        elif source_status[case["id"]] != "verified":
            results.append({"id": case["id"], "status": "NOT_RUN", "reason": "source_assets_missing"})
        elif not r_script:
            results.append({"id": case["id"], "status": "NOT_RUN", "reason": "Rscript_not_found"})
        else:
            try:
                results.append(run_case(
                    case,
                    asset_root,
                    output_dir,
                    r_script,
                    args.require_frozen_output,
                ))
            except subprocess.TimeoutExpired:
                results.append({"id": case["id"], "status": "FAIL", "reason": "timeout"})
            except OSError as exc:
                results.append({"id": case["id"], "status": "FAIL", "reason": str(exc)})

    report = {
        "schema_version": "1.0",
        "manifest": str(args.manifest.resolve()),
        "asset_root": str(asset_root),
        "results": results,
        "passed": sum(item["status"] == "PASS" for item in results),
        "blocked": sum(item["status"] == "BLOCKED" for item in results),
        "not_run": sum(item["status"] == "NOT_RUN" for item in results),
        "failed": sum(item["status"] == "FAIL" for item in results),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        return 1
    if args.require_all and report["not_run"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
