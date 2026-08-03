#!/usr/bin/env python3
"""Python-only contracts for ecology, P0-6 references, and living guidance."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class Failure(RuntimeError):
    pass


def run(args: list[object], expected: int = 0, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(value) for value in args], input=stdin, text=True,
        encoding="utf-8", capture_output=True, cwd=ROOT, check=False,
    )
    if result.returncode != expected:
        raise Failure(
            f"expected exit {expected}, got {result.returncode}: {' '.join(str(x) for x in args)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def completed_contract() -> dict:
    payload = json.loads((ROOT / "assets" / "biodiversity_contract_template.json").read_text(encoding="utf-8"))

    def replace(value: object) -> object:
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, str) and value.startswith("REPLACE_WITH_"):
            return "test-value"
        return value

    return replace(payload)  # type: ignore[return-value]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_biodiversity_contract(work: Path) -> None:
    validator = ROOT / "scripts" / "validate_biodiversity_contract.py"
    alpha = completed_contract()
    alpha_path = work / "alpha.json"
    write_json(alpha_path, alpha)
    run([PYTHON, validator, alpha_path])

    missing_scale = copy.deepcopy(alpha)
    missing_scale["scale_and_completeness"]["grain_area"] = None
    path = work / "missing-grain.json"
    write_json(path, missing_scale)
    result = run([PYTHON, validator, path], expected=1)
    if "grain_area" not in result.stderr:
        raise Failure("missing grain was not localized")

    entropy = copy.deepcopy(alpha)
    entropy["outcome"]["reported_form"] = "entropy"
    entropy["outcome"]["analysis_form"] = "effective_diversity"
    entropy["outcome"]["entropy_log_base"] = None
    path = work / "entropy-no-base.json"
    write_json(path, entropy)
    run([PYTHON, validator, path], expected=1)

    composition = copy.deepcopy(alpha)
    composition["route_type"] = "community_composition"
    composition["outcome"].update({
        "diversity_component": "composition", "measure_family": "dissimilarity",
        "metric_name": "Bray-Curtis", "hill_q": None, "input_data_type": "distance_matrix",
        "reported_form": "distance", "analysis_form": "distance",
        "composition_type": "bray_curtis",
    })
    composition["dependence"].update({
        "dependency_sources": ["pairwise_distances"],
        "sampling_covariance_status": "derived_exact",
        "sampling_v_path": "V-composition.csv",
    })
    path = work / "composition.json"
    write_json(path, composition)
    run([PYTHON, validator, path])

    multifunction = copy.deepcopy(alpha)
    multifunction["route_type"] = "multifunctionality"
    multifunction["outcome"].update({
        "diversity_component": "not_applicable", "diversity_dimension": "not_applicable",
        "measure_family": "multifunctionality", "metric_name": "effective multifunctionality",
        "hill_q": None, "input_data_type": "function_matrix", "reported_form": "index",
        "analysis_form": "index", "observed_or_estimated": "not_applicable",
    })
    multifunction["scale_and_completeness"].update({
        "grain_area": None, "grain_unit": "", "spatial_extent": None, "extent_unit": "",
        "n_sampling_units": None, "sampling_effort_definition": "",
        "standardization_method": "none", "observed_coverage": None,
        "target_coverage": None,
    })
    multifunction["multifunctionality"].update({
        "applicable": True, "function_registry_path": "functions.csv",
        "construction": "hill_number", "hill_q": 1,
        "weights_declared": True, "function_set_sensitivity": True,
    })
    path = work / "multifunction.json"
    write_json(path, multifunction)
    run([PYTHON, validator, path])
    multifunction["multifunctionality"]["hill_q"] = None
    write_json(path, multifunction)
    run([PYTHON, validator, path], expected=1)

    interaction = copy.deepcopy(multifunction)
    interaction["route_type"] = "factorial_interaction"
    interaction["outcome"]["measure_family"] = "interaction"
    interaction["multifunctionality"]["applicable"] = False
    interaction["factorial_interaction"].update({
        "applicable": True, "interaction_scale": "additive",
        "cell_order": ["Y00", "Y10", "Y01", "Y11"],
        "contrast_coefficients": [1, -1, -1, 1],
        "cell_statistics_path": "cells.csv", "cell_covariance_status": "derived_exact",
        "cell_covariance_path": "cell-V.csv",
        "nonlinearity_and_confounding_check": "prespecified diagnostic",
    })
    path = work / "interaction.json"
    write_json(path, interaction)
    run([PYTHON, validator, path])
    interaction["factorial_interaction"]["cell_order"] = ["Y00", "Y10", "Y11"]
    write_json(path, interaction)
    run([PYTHON, validator, path], expected=1)

    recovery = copy.deepcopy(multifunction)
    recovery["route_type"] = "restoration_comparison"
    recovery["outcome"]["measure_family"] = "recovery"
    recovery["multifunctionality"]["applicable"] = False
    recovery["recovery"].update({
        "applicable": True, "comparator_type": "reference",
        "reference_model_source": "reference-model.md",
        "target_dimensions": ["completeness", "persistence"], "n_timepoints": 3,
        "time_covariance_status": "derived_exact", "persistence_window": "5 years",
    })
    path = work / "recovery.json"
    write_json(path, recovery)
    run([PYTHON, validator, path])
    recovery["recovery"]["reference_model_source"] = None
    write_json(path, recovery)
    run([PYTHON, validator, path], expected=1)


def complete_route_task(route: dict, *, domain: str = "medical") -> dict:
    route["task"]["domain"] = domain
    route["task"]["as_of_date"] = "2026-08-03"
    return route


def build_receipt(route: dict, pending: dict) -> dict:
    decision_id = pending["matched_reference_rules"][0]
    references = []
    for relative in pending["required_references"]:
        path = ROOT / relative
        heading = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("#"))
        references.append({
            "path": relative,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sections_used": [heading],
            "decision_mapping": [{"decision_id": decision_id, "applied_rule": "contract-test mapping"}],
        })
    return {
        "schema_version": "1.0",
        "plan_sha256": pending["reference_gate"]["plan_sha256"],
        "task_stage": route["task"]["stage"],
        "attested_by": "contract-test",
        "attested_at": route["task"]["as_of_date"],
        "reference_files": references,
        "source_records": [{
            "source_id": source_id,
            "version_used": "test-version",
            "accessed_at": route["task"]["as_of_date"],
            "checked_at_milestone": route["task"]["stage"],
            "adoption_decision": "adopted",
            "change_summary": "checked for contract test",
        } for source_id in pending["required_source_ids"]],
    }


def test_route_contract_gate(work: Path) -> None:
    route = json.loads((ROOT / "assets" / "synthesis_route_template.json").read_text(encoding="utf-8"))
    complete_route_task(route)
    script = ROOT / "scripts" / "route_synthesis.py"
    pending = json.loads(run([PYTHON, script, "-"], stdin=json.dumps(route)).stdout)
    if pending["runner_allowed"] or pending["reference_gate"]["status"] != "pending":
        raise Failure("missing reference receipt did not block the ordinary runner")

    receipt = build_receipt(route, pending)
    route_path = work / "pending-route.json"
    receipt_path = work / "reference-receipt.json"
    write_json(route_path, pending)
    write_json(receipt_path, receipt)
    validator = ROOT / "scripts" / "validate_reference_receipt.py"
    run([PYTHON, validator, route_path, receipt_path])
    passed = json.loads(run(
        [PYTHON, script, "-", "--reference-receipt", receipt_path],
        stdin=json.dumps(route),
    ).stdout)
    if not passed["runner_allowed"] or passed["reference_gate"]["status"] != "passed":
        raise Failure("valid reference receipt did not release the ordinary runner")

    stale = copy.deepcopy(receipt)
    living_ids = set(pending["required_living_source_ids"])
    next(record for record in stale["source_records"] if record["source_id"] in living_ids)["accessed_at"] = "2026-08-02"
    write_json(receipt_path, stale)
    result = run([PYTHON, validator, route_path, receipt_path], expected=1)
    if "living_guidance_stale" not in result.stderr:
        raise Failure("stale living guidance was not rejected")

    wrong_hash = copy.deepcopy(receipt)
    wrong_hash["reference_files"][0]["sha256"] = "0" * 64
    write_json(receipt_path, wrong_hash)
    result = run([PYTHON, validator, route_path, receipt_path], expected=1)
    if "sha256_mismatch" not in result.stderr:
        raise Failure("incorrect local-reference hash was not rejected")

    traversal = copy.deepcopy(receipt)
    traversal["reference_files"][0]["path"] = "../SKILL.md"
    write_json(receipt_path, traversal)
    result = run([PYTHON, validator, route_path, receipt_path], expected=1)
    if "path_outside_allowed_root" not in result.stderr:
        raise Failure("reference receipt accepted a path traversal")

    complete_route_task(route, domain="ecology")
    route["specialist_triggers"]["community_composition"] = True
    result = run([PYTHON, script, "-"], expected=1, stdin=json.dumps(route))
    if "ecology_contract_path" not in result.stderr:
        raise Failure("community composition did not require an ecology contract")
    route["data"]["ecology_contract_path"] = "contracts/composition.json"
    routed = json.loads(run([PYTHON, script, "-"], stdin=json.dumps(route)).stdout)
    if routed["required_handoff"] != ["community_composition_specialist"]:
        raise Failure("community composition route is incorrect")

    unknown = complete_route_task(json.loads((ROOT / "assets" / "synthesis_route_template.json").read_text(encoding="utf-8")))
    unknown["data"].update({
        "effect_structure": "dependent", "dependence_topology": "unknown",
        "dependency_sources": ["other"], "sampling_covariance_status": "derived_exact",
        "sampling_v_path": "V.csv",
    })
    result = json.loads(run([PYTHON, script, "-"], stdin=json.dumps(unknown)).stdout)
    if result["required_handoff"] != ["dependence_structure_specialist"]:
        raise Failure("unknown dependence topology was not blocked")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_governance_contracts(work: Path) -> None:
    guidance_fields = next(csv.reader((ROOT / "assets" / "guidance_manifest_template.csv").open(encoding="utf-8")))
    guidance = {field: "" for field in guidance_fields}
    guidance.update({
        "source_id": "CEE-PUBBIAS-LIVING", "source_type": "standard",
        "title": "CEE Section 8.2.2", "owner": "CEE",
        "official_url": "https://environmentalevidence.org/information-for-authors/8-data-synthesis/",
        "version_used": "v5.1 living section", "published_or_updated": "2026-01-27",
        "accessed_at": "2026-08-03", "applicable_stage": "analysis",
        "authority": "conduct guidance", "living_source": "true",
        "checked_at_milestone": "analysis_lock", "update_signal": "official update record",
        "change_summary": "publication-bias section checked", "impact_class": "reporting",
        "adoption_decision": "adopted", "license_or_copyright": "CEE webpage",
        "reviewer": "tester",
    })
    guidance_path = work / "guidance.csv"
    write_csv(guidance_path, guidance_fields, [guidance])
    run([PYTHON, ROOT / "scripts" / "validate_guidance_manifest.py", guidance_path])
    guidance["change_summary"] = ""
    write_csv(guidance_path, guidance_fields, [guidance])
    run([PYTHON, ROOT / "scripts" / "validate_guidance_manifest.py", guidance_path], expected=1)

    fields = next(csv.reader((ROOT / "assets" / "review_level_appraisal_template.csv").open(encoding="utf-8")))
    base = {field: "" for field in fields}
    base.update({
        "appraisal_id": "A1", "review_id": "R1", "question_id": "Q1",
        "product_type": "evidence_review", "tool_id": "CEESAT_REVIEW",
        "tool_version": "2.2", "documents_examined": "paper;protocol;supplement",
        "item_id": "domain-1", "judgment": "Green", "support_locator": "paper p.4",
        "not_reported_does_not_prove_not_done": "true", "aggregation_forbidden": "true",
        "assessor": "tester", "assessed_at": "2026-08-03",
    })
    appraisal_path = work / "appraisal.csv"
    write_csv(appraisal_path, fields, [base])
    validator = ROOT / "scripts" / "validate_review_appraisal.py"
    run([PYTHON, validator, appraisal_path])

    mates = copy.deepcopy(base)
    mates.update({
        "appraisal_id": "M1", "question_id": "", "product_type": "environmental_meta_analysis",
        "tool_id": "MATES", "tool_version": "paper-2026", "model_id": "model-2",
        "target_selection_rule": "most_complete_model", "target_selection_deviation": "false",
        "item_id": "item-1",
    })
    write_csv(appraisal_path, fields, [mates])
    run([PYTHON, validator, appraisal_path], expected=1)
    mates.update({
        "model_id": "first-meta-analysis", "target_selection_rule": "first_meta_analysis_in_paper",
        "target_selection_deviation": "false",
    })
    write_csv(appraisal_path, fields, [mates])
    run([PYTHON, validator, appraisal_path])


def test_distilled_assets() -> None:
    registry = (ROOT / "references" / "source-registry.md").read_text(encoding="utf-8")
    reference_routes = json.loads((ROOT / "assets" / "reference_routes.json").read_text(encoding="utf-8"))
    casebook = (ROOT / "references" / "plant-biodiversity-benchmark-casebook.md").read_text(encoding="utf-8")
    plan = (ROOT / "assets" / "analysis_plan_template.yaml").read_text(encoding="utf-8")
    for token in (
        "CEESAT-2.2", "CEE-PUBBIAS-LIVING", "2041-210X.70156", "2041-210X.13760",
        "s11121-021-01246-3", "2041-210X.70155", "2041-210X.13682",
        "2041-210X.13714", "rec.70441",
    ):
        if token not in registry:
            raise Failure(f"source registry is missing {token}")
    for source_id in reference_routes["source_metadata"]:
        if f"`{source_id}`" not in registry:
            raise Failure(f"reference route source is not registered: {source_id}")
    for rule in reference_routes["rules"]:
        for relative in rule["required_reference_files"]:
            if not (ROOT / relative).is_file():
                raise Failure(f"reference route points to a missing file: {relative}")
    for token in ("BENCH-CHEN-2025", "BENCH-KECK-2025", "BENCH-SHAW-2025"):
        if token not in casebook:
            raise Failure(f"casebook is missing {token}")
    for token in (
        'schema_version: "1.3"', "community_composition", "ecology_contract_path",
        "assets/reference_routes.json", "reference_receipt_template.json",
        'version: "2.2"', "first_meta_analysis_in_paper", "ai_stage_run_id",
        "binary_publication_bias_verdict_forbidden",
    ):
        if token not in plan:
            raise Failure(f"analysis plan is missing {token}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="meta-contract-tests-") as temporary:
        work = Path(temporary)
        test_biodiversity_contract(work)
        test_route_contract_gate(work)
        test_governance_contracts(work)
        test_distilled_assets()
    print("PASS: ecology, reporting-governance, and living-source contract tests")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Failure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
