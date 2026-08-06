#!/usr/bin/env python3
"""Acquire or verify external source-reproduction artifacts without vendoring them."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from validate_source_reproductions import DEFAULT_MANIFEST, ManifestError, validate_manifest


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify_file(path: Path, *, size: int, checksums: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["missing"]
    actual_size = path.stat().st_size
    if actual_size != size:
        errors.append(f"size:{actual_size}!={size}")
    for algorithm, expected in checksums.items():
        actual = digest(path, algorithm)
        if actual.lower() != expected.lower():
            errors.append(f"{algorithm}:{actual}!={expected}")
    return errors


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "EasyMeta-source-reproduction/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def resolve_download(acquisition: dict[str, Any]) -> str:
    mode = acquisition["mode"]
    if mode == "direct":
        return str(acquisition["download_url"])
    metadata = fetch_json(str(acquisition["metadata_url"]))
    wanted = acquisition["file_name"]
    if mode == "figshare_version_file":
        for item in metadata.get("files", []):
            if item.get("name") == wanted:
                return str(item["download_url"])
    elif mode == "zenodo_record_file":
        for item in metadata.get("files", []):
            if item.get("key") == wanted:
                return str(item["links"]["content"])
    raise RuntimeError(f"source metadata did not contain frozen file: {wanted}")


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    if partial.exists():
        partial.unlink()
    request = urllib.request.Request(url, headers={"User-Agent": "EasyMeta-source-reproduction/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        partial.replace(target)
    finally:
        if partial.exists():
            partial.unlink()


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            member_path = Path(member.filename.replace("\\", "/"))
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"unsafe zip member: {member.filename}")
            resolved = (destination / member_path).resolve()
            if resolved != destination_root and destination_root not in resolved.parents:
                raise RuntimeError(f"zip member escapes extraction root: {member.filename}")
        bundle.extractall(destination)


def default_asset_root() -> Path:
    configured = os.environ.get("EASYMETA_SOURCE_REPRO_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (ROOT.parent / ".local" / "source-reproductions" / "raw").resolve()


def materialize(
    manifest: dict[str, Any],
    asset_root: Path,
    *,
    allow_download: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "asset_root": str(asset_root),
        "network_used": False,
        "cases": [],
    }
    for case in manifest["cases"]:
        case_report: dict[str, Any] = {"id": case["id"], "artifacts": [], "inputs": []}
        for artifact in case["artifacts"]:
            path = asset_root / Path(artifact["path"])
            errors = verify_file(path, size=artifact["size"], checksums=artifact["checksums"])
            downloaded = False
            if errors == ["missing"] and allow_download:
                url = resolve_download(artifact["acquisition"])
                report["network_used"] = True
                download(url, path)
                downloaded = True
                errors = verify_file(path, size=artifact["size"], checksums=artifact["checksums"])
            if errors and errors != ["missing"]:
                raise RuntimeError(
                    f"{case['id']}/{artifact['id']} failed integrity verification: {'; '.join(errors)}"
                )
            extracted = False
            if not errors and artifact.get("extract_to"):
                extraction_root = asset_root / Path(artifact["extract_to"])
                extraction_prefix = Path(artifact["extract_to"])
                related_inputs = [
                    item for item in case["inputs"]
                    if Path(item["path"]).is_relative_to(extraction_prefix)
                ]
                if any(not (asset_root / Path(item["path"])).is_file() for item in related_inputs):
                    safe_extract_zip(path, extraction_root)
                    extracted = True
            case_report["artifacts"].append({
                "id": artifact["id"],
                "status": "verified" if not errors else "missing",
                "downloaded": downloaded,
                "extracted": extracted,
                "path": str(path),
            })
        for item in case["inputs"]:
            path = asset_root / Path(item["path"])
            errors = verify_file(path, size=item["size"], checksums={"sha256": item["sha256"]})
            if errors and errors != ["missing"]:
                raise RuntimeError(
                    f"{case['id']}/{item['name']} failed input verification: {'; '.join(errors)}"
                )
            case_report["inputs"].append({
                "name": item["name"],
                "status": "verified" if not errors else "missing",
                "path": str(path),
            })
        statuses = [entry["status"] for entry in case_report["artifacts"] + case_report["inputs"]]
        case_report["status"] = "verified" if all(value == "verified" for value in statuses) else "not_run"
        report["cases"].append(case_report)
    report["verified_cases"] = sum(case["status"] == "verified" for case in report["cases"])
    report["not_run_cases"] = sum(case["status"] == "not_run" for case in report["cases"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--download", action="store_true", help="download only missing frozen artifacts")
    parser.add_argument("--require-all", action="store_true", help="fail when any artifact or input is missing")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_manifest(manifest)
        if args.case_ids:
            wanted = set(args.case_ids)
            selected = [case for case in manifest["cases"] if case["id"] in wanted]
            missing_ids = wanted - {case["id"] for case in selected}
            if missing_ids:
                raise ManifestError(f"unknown case ids: {', '.join(sorted(missing_ids))}")
            manifest = dict(manifest)
            manifest["cases"] = selected
        result = materialize(manifest, (args.root or default_asset_root()).resolve(), allow_download=args.download)
    except (OSError, json.JSONDecodeError, ManifestError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_all and result["not_run_cases"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
