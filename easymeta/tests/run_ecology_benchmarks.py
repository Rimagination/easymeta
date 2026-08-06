#!/usr/bin/env python3
"""Executable conceptual benchmarks anchored to the ecology casebook."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

import run_contract_tests as contracts
import run_p1_tests as p1
import run_tests as core


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "tests" / "ecology_benchmark_scenarios.json"
VALIDATOR = ROOT / "scripts" / "validate_ecology_benchmarks.py"
BIODIVERSITY_VALIDATOR = ROOT / "scripts" / "validate_biodiversity_contract.py"


class BenchmarkFailure(RuntimeError):
    pass


CASE_FUNCTIONS: dict[str, Callable[[Path], None]] = {}


def register(case_id: str) -> Callable[[Callable[[Path], None]], Callable[[Path], None]]:
    def decorator(function: Callable[[Path], None]) -> Callable[[Path], None]:
        if case_id in CASE_FUNCTIONS:
            raise RuntimeError(f"duplicate ecology benchmark function: {case_id}")
        CASE_FUNCTIONS[case_id] = function
        return function

    return decorator


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ecology_route() -> dict[str, Any]:
    payload = core.route_payload()
    payload["task"]["domain"] = "ecology"
    payload["task"]["topic_tags"] = ["biodiversity"]
    return payload


def assert_invalid_field(result: dict[str, Any], field: str) -> None:
    if result.get("error") != "invalid_input" or not any(
        issue.get("field") == field for issue in result.get("issues", [])
    ):
        raise BenchmarkFailure(f"expected invalid field {field!r}, got {result}")


def run_biodiversity_contract(
    payload: dict[str, Any], work: Path, *, expected: int = 0, contains: str | None = None
) -> None:
    path = work / "ecology-contract.json"
    write_json(path, payload)
    result = core.run([core.PYTHON, BIODIVERSITY_VALIDATOR, path], expected=expected)
    if contains and contains not in result.stderr:
        raise BenchmarkFailure(f"expected {contains!r} in contract rejection: {result.stderr}")


def raw_cvr_row() -> tuple[list[str], dict[str, str]]:
    seed_path = core.FIXTURES / "raw_rr_independent.csv"
    headers = list(core.read_csv(seed_path)[0])
    row = dict(core.read_csv(seed_path)[0])
    row.update(
        {
            "study_id": "ECO-CVR-01",
            "report_id": "ECO-CVR-R01",
            "effect_id": "ECO-CVR-01__variability",
            "citation": "synthetic conceptual benchmark",
            "study_design": "controlled_ecology_experiment",
            "population": "plant plots",
            "exposure_intervention": "restoration",
            "comparator": "degraded control",
            "outcome": "plant biomass variability",
            "outcome_definition": "coefficient of variation",
            "effect_measure": "CVR",
            "effect_scale": "natural_summary_statistics",
            "effect_estimate": "",
            "ci_lower": "",
            "ci_upper": "",
            "ci_level": "",
            "n_total": "42",
            "n_intervention": "20",
            "n_comparator": "22",
            "mean_intervention": "10",
            "sd_intervention": "2",
            "mean_comparator": "8",
            "sd_comparator": "1.2",
            "direction": "higher_means_more_variable_relative_to_mean",
            "dependency_cluster": "ECO-CVR-01",
            "source_locator": "synthetic fixture specification",
            "notes": "conceptual reimplementation; not source-data reproduction",
        }
    )
    return headers, row


def run_cvr(
    work: Path, *, mean_intervention: str = "10", include_correction: bool = True, expected: int = 0
) -> tuple[Any, Path]:
    headers, row = raw_cvr_row()
    row["mean_intervention"] = mean_intervention
    input_path = work / "raw-cvr.csv"
    output_path = work / "cvr-effects.csv"
    core.write_csv(input_path, headers, [row])
    command: list[str | Path] = [
        core.R_SCRIPT,
        core.SCRIPTS / "calculate_effect_sizes.R",
        "--input",
        input_path,
        "--output",
        output_path,
        "--measure",
        "CVR",
        "--m1i-col",
        "mean_intervention",
        "--m2i-col",
        "mean_comparator",
        "--sd1i-col",
        "sd_intervention",
        "--sd2i-col",
        "sd_comparator",
        "--n1i-col",
        "n_intervention",
        "--n2i-col",
        "n_comparator",
        "--vtype",
        "LS",
        "--overwrite",
        "yes",
    ]
    if include_correction:
        command.extend(["--bias-correction", "yes"])
    return core.run(command, expected=expected), output_path


@register("bench_atkinson_cvr_pass")
def atkinson_cvr_pass(work: Path) -> None:
    _, output = run_cvr(work)
    rows = core.read_csv(output)
    if len(rows) != 1 or rows[0]["measure"] != "CVR" or rows[0]["analysis_scale"] != "log":
        raise BenchmarkFailure(f"unexpected CVR output contract: {rows}")
    core.assert_close(rows[0]["yi"], 0.28969970175230497, "CVR yi")
    core.assert_close(rows[0]["vi"], 0.053148040555935291, "CVR vi")


@register("bench_atkinson_cvr_nonpositive_mean_reject")
def atkinson_cvr_nonpositive_mean_reject(work: Path) -> None:
    result, _ = run_cvr(work, mean_intervention="0", expected=2)
    if "CVR requires strictly positive means" not in result.stderr:
        raise BenchmarkFailure(f"non-positive CVR mean was not localized: {result.stderr}")


@register("bench_atkinson_cvr_missing_correction_reject")
def atkinson_cvr_missing_correction_reject(work: Path) -> None:
    result, _ = run_cvr(work, include_correction=False, expected=2)
    if "--bias-correction" not in result.stderr:
        raise BenchmarkFailure(f"missing CVR correction was not rejected: {result.stderr}")


def shared_control_route() -> dict[str, Any]:
    payload = ecology_route()
    payload["data"].update(
        {
            "effect_structure": "dependent",
            "dependence_topology": "nested",
            "dependency_sources": ["shared_control"],
            "sampling_covariance_status": "derived_exact",
            "sampling_v_path": "derived/shared-control-V.csv",
        }
    )
    return payload


@register("bench_cheng_shared_control_route_pass")
def cheng_shared_control_route_pass(work: Path) -> None:
    result = core.invoke_route(shared_control_route(), pass_reference_gate=True)
    if result["route"] != "dependent_effect_meta" or not result["runner_allowed"]:
        raise BenchmarkFailure(f"shared-control route did not become executable: {result}")
    if "references/complex-design-effects.md" not in result["required_references"]:
        raise BenchmarkFailure("shared-control route omitted complex-design guidance")


@register("bench_cheng_missing_v_reject")
def cheng_missing_v_reject(work: Path) -> None:
    payload = shared_control_route()
    payload["data"]["sampling_covariance_status"] = "unavailable"
    payload["data"]["sampling_v_path"] = None
    result = core.invoke_route(payload)
    if result["required_handoff"] != ["sampling_covariance_specialist"]:
        raise BenchmarkFailure(f"missing shared-control V did not stop the runner: {result}")


@register("bench_cheng_claimed_v_without_path_reject")
def cheng_claimed_v_without_path_reject(work: Path) -> None:
    payload = shared_control_route()
    payload["data"]["sampling_covariance_status"] = "provided_validated"
    payload["data"]["sampling_v_path"] = None
    result = core.invoke_route(payload, expected=1)
    assert_invalid_field(result, "data.sampling_v_path")


@register("bench_goncalves_alpha_contract_pass")
def goncalves_alpha_contract_pass(work: Path) -> None:
    run_biodiversity_contract(contracts.completed_contract(), work)


@register("bench_goncalves_missing_grain_reject")
def goncalves_missing_grain_reject(work: Path) -> None:
    payload = contracts.completed_contract()
    payload["scale_and_completeness"]["grain_area"] = None
    run_biodiversity_contract(payload, work, expected=1, contains="grain_area")


@register("bench_goncalves_raw_level_without_trigger_reject")
def goncalves_raw_level_without_trigger_reject(work: Path) -> None:
    payload = ecology_route()
    payload["data"]["level"] = "raw_community_matrix"
    payload["data"]["independent_cluster_count"] = None
    result = core.invoke_route(payload, expected=1)
    assert_invalid_field(result, "data.level")


def multifunction_contract() -> dict[str, Any]:
    payload = contracts.completed_contract()
    payload["route_type"] = "multifunctionality"
    payload["outcome"].update(
        {
            "diversity_component": "not_applicable",
            "diversity_dimension": "not_applicable",
            "measure_family": "multifunctionality",
            "metric_name": "effective multifunctionality",
            "hill_q": None,
            "input_data_type": "function_matrix",
            "reported_form": "index",
            "analysis_form": "index",
            "observed_or_estimated": "not_applicable",
        }
    )
    payload["scale_and_completeness"].update(
        {
            "grain_area": None,
            "grain_unit": "",
            "spatial_extent": None,
            "extent_unit": "",
            "n_sampling_units": None,
            "sampling_effort_definition": "",
            "standardization_method": "none",
            "observed_coverage": None,
            "target_coverage": None,
        }
    )
    payload["multifunctionality"].update(
        {
            "applicable": True,
            "function_registry_path": "functions.csv",
            "construction": "hill_number",
            "hill_q": 1,
            "thresholds": [],
            "weights_declared": True,
            "function_set_sensitivity": True,
        }
    )
    return payload


def factorial_contract() -> dict[str, Any]:
    payload = multifunction_contract()
    payload["route_type"] = "factorial_interaction"
    payload["outcome"]["measure_family"] = "interaction"
    payload["outcome"]["metric_name"] = "four-cell additive interaction"
    payload["outcome"]["input_data_type"] = "factorial_cells"
    payload["multifunctionality"]["applicable"] = False
    payload["factorial_interaction"].update(
        {
            "applicable": True,
            "interaction_scale": "additive",
            "cell_order": ["Y00", "Y10", "Y01", "Y11"],
            "contrast_coefficients": [1, -1, -1, 1],
            "cell_statistics_path": "cells.csv",
            "cell_covariance_status": "derived_exact",
            "cell_covariance_path": "cell-V.csv",
            "nonlinearity_and_confounding_check": "prespecified diagnostic",
        }
    )
    return payload


@register("bench_hong_factorial_contract_pass")
def hong_factorial_contract_pass(work: Path) -> None:
    run_biodiversity_contract(factorial_contract(), work)


@register("bench_hong_missing_factorial_cell_reject")
def hong_missing_factorial_cell_reject(work: Path) -> None:
    payload = factorial_contract()
    payload["factorial_interaction"]["cell_order"] = ["Y00", "Y10", "Y11"]
    run_biodiversity_contract(payload, work, expected=1, contains="cell_order")


@register("bench_hong_wrong_contrast_reject")
def hong_wrong_contrast_reject(work: Path) -> None:
    payload = factorial_contract()
    payload["factorial_interaction"]["contrast_coefficients"] = [1, 1, -1, -1]
    run_biodiversity_contract(payload, work, expected=1, contains="contrast_coefficients")


@register("bench_lefcheck_multifunction_contract_pass")
def lefcheck_multifunction_contract_pass(work: Path) -> None:
    run_biodiversity_contract(multifunction_contract(), work)


@register("bench_lefcheck_missing_hill_q_reject")
def lefcheck_missing_hill_q_reject(work: Path) -> None:
    payload = multifunction_contract()
    payload["multifunctionality"]["hill_q"] = None
    run_biodiversity_contract(payload, work, expected=1, contains="hill_q")


@register("bench_lefcheck_empty_thresholds_reject")
def lefcheck_empty_thresholds_reject(work: Path) -> None:
    payload = multifunction_contract()
    payload["multifunctionality"].update(
        {"construction": "multi_threshold", "hill_q": None, "thresholds": []}
    )
    run_biodiversity_contract(payload, work, expected=1, contains="thresholds")


def longitudinal_contract() -> dict[str, Any]:
    payload = multifunction_contract()
    payload["route_type"] = "longitudinal_recovery"
    payload["outcome"]["measure_family"] = "recovery"
    payload["outcome"]["metric_name"] = "resistance and persistence"
    payload["outcome"]["input_data_type"] = "time_series"
    payload["multifunctionality"]["applicable"] = False
    payload["recovery"].update(
        {
            "applicable": True,
            "comparator_type": "baseline",
            "reference_model_source": "baseline-and-event-window.md",
            "target_dimensions": ["completeness", "persistence"],
            "n_timepoints": 3,
            "time_covariance_status": "derived_exact",
            "persistence_window": "5 years",
        }
    )
    return payload


@register("bench_isbell_longitudinal_contract_pass")
def isbell_longitudinal_contract_pass(work: Path) -> None:
    run_biodiversity_contract(longitudinal_contract(), work)
    payload = ecology_route()
    payload["specialist_triggers"]["one_stage_longitudinal"] = True
    payload["data"]["ecology_contract_path"] = "contracts/isbell-longitudinal.json"
    result = core.invoke_route(payload)
    if result["required_handoff"] != ["one_stage_longitudinal_model_specialist"]:
        raise BenchmarkFailure(f"longitudinal ecology route did not hand off: {result}")


@register("bench_isbell_one_timepoint_reject")
def isbell_one_timepoint_reject(work: Path) -> None:
    payload = longitudinal_contract()
    payload["recovery"]["n_timepoints"] = 1
    run_biodiversity_contract(payload, work, expected=1, contains="n_timepoints")


@register("bench_isbell_missing_ecology_contract_reject")
def isbell_missing_ecology_contract_reject(work: Path) -> None:
    payload = ecology_route()
    payload["specialist_triggers"]["one_stage_longitudinal"] = True
    result = core.invoke_route(payload, expected=1)
    assert_invalid_field(result, "data.ecology_contract_path")


@register("bench_hooper_second_order_route_pass")
def hooper_second_order_route_pass(work: Path) -> None:
    payload = ecology_route()
    payload["task"]["product_type"] = "umbrella_review"
    payload["data"]["level"] = "meta_level"
    payload["data"]["independent_cluster_count"] = None
    payload["specialist_triggers"]["second_order_meta"] = True
    result = core.invoke_route(payload)
    if result["required_handoff"] != ["second_order_evidence_synthesis_specialist"]:
        raise BenchmarkFailure(f"second-order evidence was misrouted: {result}")
    if "references/second-order-meta.md" not in result["required_references"]:
        raise BenchmarkFailure("second-order route omitted its generic contract")


@register("bench_hooper_meta_level_without_trigger_reject")
def hooper_meta_level_without_trigger_reject(work: Path) -> None:
    payload = ecology_route()
    payload["data"]["level"] = "meta_level"
    payload["data"]["independent_cluster_count"] = None
    result = core.invoke_route(payload, expected=1)
    assert_invalid_field(result, "data.level")


@register("bench_hooper_trigger_with_aggregate_level_reject")
def hooper_trigger_with_aggregate_level_reject(work: Path) -> None:
    payload = ecology_route()
    payload["specialist_triggers"]["second_order_meta"] = True
    result = core.invoke_route(payload, expected=1)
    assert_invalid_field(result, "data.level")


def main() -> int:
    core.run([core.PYTHON, VALIDATOR, SCENARIOS])
    payload = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = payload["cases"]
    declared_local = {case["id"] for case in scenarios if case["executor"] == "ecology_case"}
    if declared_local != set(CASE_FUNCTIONS):
        raise BenchmarkFailure(
            f"ecology case registry mismatch; missing={sorted(declared_local - set(CASE_FUNCTIONS))}, "
            f"extra={sorted(set(CASE_FUNCTIONS) - declared_local)}"
        )

    versions = p1.preflight()
    results: list[tuple[str, str | None]] = []
    with tempfile.TemporaryDirectory(prefix="easymeta-ecology-benchmarks-") as temporary:
        suite_root = Path(temporary)
        for index, scenario in enumerate(scenarios, start=1):
            case_id = scenario["id"]
            work = suite_root / f"case-{index:02d}"
            work.mkdir()
            try:
                if scenario["executor"] == "ecology_case":
                    CASE_FUNCTIONS[case_id](work)
                else:
                    delegate_id = scenario["delegate_id"]
                    if delegate_id not in p1.CASE_FUNCTIONS:
                        raise BenchmarkFailure(f"unknown P1 delegate: {delegate_id}")
                    p1.CASE_FUNCTIONS[delegate_id](work)
            except Exception as exc:
                results.append((case_id, str(exc)))
            else:
                results.append((case_id, None))

    for case_id, error in results:
        if error is None:
            print(f"[PASS] {case_id}")
        else:
            print(f"[FAIL] {case_id}\n  {error}")
    failures = [case_id for case_id, error in results if error is not None]
    if failures:
        print(f"FAIL: {len(failures)}/{len(results)} ecology benchmark cases failed", file=core.sys.stderr)
        return 1
    families = {case["family"] for case in scenarios}
    print(
        f"PASS: {len(results)} executable conceptual ecology benchmarks across "
        f"{len(families)} families; R packages={versions}; source replications remain separately gated"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BenchmarkFailure, core.TestFailure, contracts.Failure, p1.TestFailure) as exc:
        print(f"FAIL: {exc}", file=core.sys.stderr)
        raise SystemExit(1)
