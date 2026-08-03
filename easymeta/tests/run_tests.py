#!/usr/bin/env python3
"""End-to-end golden and rejection tests for the meta-analysis skill.

Set META_TEST_R_LIBRARY to an R library containing metafor and clubSandwich.
Set R_SCRIPT only when Rscript is not available on PATH.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
GOLDEN = json.loads((SKILL_ROOT / "tests" / "golden" / "expected.json").read_text(encoding="utf-8"))
R_SCRIPT = Path(os.environ.get("R_SCRIPT") or shutil.which("Rscript") or "Rscript")
PYTHON = Path(sys.executable)
SCRIPTS = SKILL_ROOT / "scripts"
TOLERANCE = float(GOLDEN["tolerance"])


class TestFailure(RuntimeError):
    pass


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    test_library = env.get("META_TEST_R_LIBRARY", "").strip()
    if test_library:
        existing = env.get("R_LIBS_USER", "").strip()
        env["R_LIBS_USER"] = test_library if not existing else test_library + os.pathsep + existing
    return env


def run(
    command: Sequence[str | Path],
    *,
    expected: int = 0,
    stdin: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    rendered = [str(item) for item in command]
    result = subprocess.run(
        rendered,
        input=stdin,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd or SKILL_ROOT),
        env=command_env(),
        check=False,
    )
    if result.returncode != expected:
        raise TestFailure(
            "unexpected exit code\n"
            f"command: {rendered!r}\nexpected: {expected}\nactual: {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def assert_close(actual: float | str, expected: float, label: str) -> None:
    value = float(actual)
    if not math.isclose(value, expected, rel_tol=TOLERANCE, abs_tol=TOLERANCE):
        raise TestFailure(f"{label}: expected {expected:.15g}, got {value:.15g}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_fixture(path: Path, stage: str, *, allow_warnings: bool = False) -> None:
    command: list[str | Path] = [PYTHON, SCRIPTS / "validate_extraction.py", path, "--stage", stage]
    if allow_warnings:
        command.append("--allow-warnings")
    run(command)


def calculate_gen_rr(raw_path: Path, output_path: Path) -> None:
    run(
        [
            R_SCRIPT,
            SCRIPTS / "calculate_effect_sizes.R",
            "--input",
            raw_path,
            "--output",
            output_path,
            "--measure",
            "GEN",
            "--yi-col",
            "effect_estimate",
            "--uncertainty",
            "ci",
            "--ci-lb-col",
            "ci_lower",
            "--ci-ub-col",
            "ci_upper",
            "--input-scale",
            "ratio",
            "--ci-level",
            "95",
            "--ci-distribution",
            "normal",
            "--study-id-col",
            "study_id",
            "--overwrite",
            "yes",
        ]
    )


def expand_dependent_raw(source: Path, destination: Path, clusters: int = 12) -> None:
    source_rows = read_csv(source)
    if len(source_rows) != 8:
        raise TestFailure("dependent seed fixture must contain four two-effect studies")
    expanded: list[dict[str, str]] = []
    for index in range(clusters):
        pair = source_rows[(index % 4) * 2 : (index % 4) * 2 + 2]
        study_id = f"L{index + 1:02d}"
        for seed in pair:
            row = dict(seed)
            row["study_id"] = study_id
            row["report_id"] = f"LR{index + 1:02d}"
            row["effect_id"] = f"{study_id}__{row['outcome']}__12m"
            row["citation"] = f"LOO Study {index + 1:02d}"
            row["dependency_cluster"] = study_id
            row["notes"] = "generated deterministic multilevel LOO fixture"
            expanded.append(row)
    write_csv(destination, source_rows[0].keys(), expanded)


def runner_base(effects: Path, output_dir: Path, model: str, scale: str) -> list[str | Path]:
    return [
        R_SCRIPT,
        SCRIPTS / "run_meta_analysis.R",
        "--route-contract",
        FIXTURES / "passed_reference_route.json",
        "--input",
        effects,
        "--output-dir",
        output_dir,
        "--model",
        model,
        "--yi-col",
        "yi",
        "--vi-col",
        "vi",
        "--independent-cluster-col",
        "study_id",
        "--analysis-scale",
        scale,
    ]


def test_r_packages() -> None:
    result = run(
        [
            R_SCRIPT,
            "-e",
            "stopifnot(requireNamespace('metafor', quietly=TRUE)); "
            "stopifnot(requireNamespace('clubSandwich', quietly=TRUE)); "
            "stopifnot(requireNamespace('jsonlite', quietly=TRUE)); "
            "cat(as.character(packageVersion('metafor')), as.character(packageVersion('clubSandwich')), "
            "as.character(packageVersion('jsonlite')), sep='|')",
        ]
    )
    if result.stdout.count("|") != 2:
        raise TestFailure("R package version probe did not return all three versions")


def test_two_stage_and_models(work: Path) -> None:
    raw = FIXTURES / "raw_rr_independent.csv"
    validate_fixture(raw, "raw")
    effects = work / "effects_independent.csv"
    calculate_gen_rr(raw, effects)
    validate_fixture(effects, "analysis")

    effect_rows = read_csv(effects)
    if {row["data_stage"] for row in effect_rows} != {"analysis_effect"}:
        raise TestFailure("calculator did not emit analysis_effect stage")
    if {row["analysis_scale"] for row in effect_rows} != {"log"}:
        raise TestFailure("RR calculator output did not use one log scale")
    for row in effect_rows:
        assert_close(float(row["sei"]) ** 2, float(row["vi"]), f"vi/sei contract {row['effect_id']}")

    missing_route = runner_base(effects, work / "reject_missing_route", "common", "log")
    route_index = missing_route.index("--route-contract")
    del missing_route[route_index : route_index + 2]
    run(missing_route + ["--prediction", "no", "--overwrite", "yes"], expected=2)

    pending_route = json.loads((FIXTURES / "passed_reference_route.json").read_text(encoding="utf-8"))
    pending_route["runner_allowed"] = False
    pending_route["reference_gate"]["status"] = "pending"
    pending_route["reference_gate"]["issues"] = [{
        "code": "missing_reference_receipt",
        "field": "reference_receipt",
        "message": "test pending gate",
    }]
    pending_path = work / "pending-reference-route.json"
    pending_path.write_text(json.dumps(pending_route), encoding="utf-8")
    pending_command = runner_base(effects, work / "reject_pending_route", "common", "log")
    pending_command[pending_command.index("--route-contract") + 1] = pending_path
    run(pending_command + ["--prediction", "no", "--overwrite", "yes"], expected=2)

    common_dir = work / "common"
    run(runner_base(effects, common_dir, "common", "log") + ["--prediction", "no", "--overwrite", "yes"])
    common = read_csv(common_dir / "coefficients.csv")[0]
    assert_close(common["estimate"], GOLDEN["common_rr"]["estimate"], "common RR estimate")
    assert_close(common["display_estimate"], GOLDEN["common_rr"]["display_estimate"], "common RR display")
    common_manifest = (common_dir / "analysis_manifest.txt").read_text(encoding="utf-8")
    for token in ("reference_gate_status=passed", "route_plan_sha256=" + "a" * 64):
        if token not in common_manifest:
            raise TestFailure(f"ordinary runner manifest omitted route-gate provenance: {token}")

    random_dir = work / "random"
    run(
        runner_base(effects, random_dir, "random", "log")
        + [
            "--tau-method",
            "REML",
            "--test",
            "knha",
            "--prediction",
            "yes",
            "--sensitivity-tau",
            "REML,PM,DL",
            "--sensitivity-test",
            "knha,z",
            "--leave-one-out",
            "yes",
            "--overwrite",
            "yes",
        ]
    )
    random = read_csv(random_dir / "coefficients.csv")[0]
    prediction = read_csv(random_dir / "predictions.csv")[0]
    leave_one = read_csv(random_dir / "leave_one_cluster_out.csv")
    assert_close(random["estimate"], GOLDEN["random_rr"]["estimate"], "random RR estimate")
    assert_close(random["display_estimate"], GOLDEN["random_rr"]["display_estimate"], "random RR display")
    assert_close(prediction["display_pi_lower"], GOLDEN["random_rr"]["display_pi_lower"], "random RR PI lower")
    assert_close(prediction["display_pi_upper"], GOLDEN["random_rr"]["display_pi_upper"], "random RR PI upper")
    if len(leave_one) != GOLDEN["random_rr"]["leave_one_cluster_rows"]:
        raise TestFailure("leave-one-cluster-out did not produce one row per independent cluster")
    if len({row["omitted_cluster"] for row in leave_one}) != len(leave_one):
        raise TestFailure("leave-one-cluster-out repeated a cluster")

    missing_cluster = [item for item in runner_base(effects, work / "reject_missing_cluster", "common", "log") if item not in {"--independent-cluster-col", "study_id"}]
    # Remove the flag/value as a pair; the set-based comprehension above is safe for this fixed command.
    run(missing_cluster + ["--prediction", "no", "--overwrite", "yes"], expected=2)
    run(runner_base(effects, work / "reject_scale", "common", "identity") + ["--prediction", "no", "--overwrite", "yes"], expected=2)
    run(
        runner_base(effects, work / "reject_egger", "random", "log")
        + [
            "--tau-method",
            "REML",
            "--test",
            "knha",
            "--prediction",
            "no",
            "--small-study-test",
            "egger",
            "--overwrite",
            "yes",
        ],
        expected=2,
    )


def test_dependent_v_and_cr2(work: Path) -> None:
    raw = FIXTURES / "raw_rr_dependent.csv"
    validate_fixture(raw, "raw", allow_warnings=True)
    effects = work / "effects_dependent.csv"
    calculate_gen_rr(raw, effects)
    validate_fixture(effects, "analysis", allow_warnings=True)
    v_path = work / "V.csv"
    run(
        [
            R_SCRIPT,
            SCRIPTS / "build_sampling_v.R",
            "--input",
            effects,
            "--output-v",
            v_path,
            "--vi-col",
            "vi",
            "--id-col",
            "effect_id",
            "--cluster-col",
            "study_id",
            "--obs-col",
            "outcome",
            "--rho",
            "0.5",
            "--scenario-label",
            "rho_0.5",
            "--overwrite",
            "yes",
        ]
    )
    model_dir = work / "multilevel_cr2"
    run(
        runner_base(effects, model_dir, "multilevel", "log")
        + [
            "--id-col",
            "effect_id",
            "--v-matrix",
            v_path,
            "--random",
            "~ 1 | study_id/effect_id",
            "--mv-method",
            "REML",
            "--test",
            "t",
            "--dfs",
            "residual",
            "--prediction",
            "no",
            "--robust-cluster",
            "study_id",
            "--robust-method",
            "CR2",
            "--dependence-topology",
            "nested",
            "--overwrite",
            "yes",
        ]
    )
    coefficient = read_csv(model_dir / "coefficients.csv")[0]
    metrics = {row["metric"]: row["value"] for row in read_csv(model_dir / "heterogeneity.csv")}
    if coefficient["inference"] != "CR2":
        raise TestFailure("multilevel inference did not use CR2")
    assert_close(coefficient["estimate"], GOLDEN["multilevel_cr2"]["estimate"], "CR2 estimate")
    assert_close(coefficient["display_estimate"], GOLDEN["multilevel_cr2"]["display_estimate"], "CR2 display")
    assert_close(metrics["independent_clusters"], GOLDEN["multilevel_cr2"]["independent_clusters"], "CR2 cluster count")
    assert_close(metrics["effect_rows_per_independent_cluster"], GOLDEN["multilevel_cr2"]["effect_rows_per_cluster"], "CR2 effects/cluster")
    manifest_text = (model_dir / "analysis_manifest.txt").read_text(encoding="utf-8")
    for token in ("dependence_topology=nested", "robust_method=CR2", "robust_min_coefficient_df="):
        if token not in manifest_text:
            raise TestFailure(f"CR2 manifest did not record {token}")

    run(
        runner_base(effects, work / "multilevel_prediction_missing_target", "multilevel", "log")
        + [
            "--id-col", "effect_id", "--v-matrix", v_path,
            "--random", "~ 1 | study_id/effect_id", "--mv-method", "REML",
            "--test", "t", "--dfs", "residual", "--prediction", "yes",
            "--overwrite", "yes",
        ],
        expected=2,
    )
    prediction_dir = work / "multilevel_prediction_targeted"
    run(
        runner_base(effects, prediction_dir, "multilevel", "log")
        + [
            "--id-col", "effect_id", "--v-matrix", v_path,
            "--random", "~ 1 | study_id/effect_id", "--mv-method", "REML",
            "--test", "t", "--dfs", "residual", "--prediction", "yes",
            "--prediction-target", "new_study_new_effect",
            "--prediction-components", "study,effect", "--overwrite", "yes",
        ]
    )
    prediction_rows = read_csv(prediction_dir / "predictions.csv")
    if not prediction_rows or {row["prediction_target"] for row in prediction_rows} != {"new_study_new_effect"}:
        raise TestFailure("multilevel predictions did not preserve prediction target")
    if {row["prediction_components"] for row in prediction_rows} != {"study,effect"}:
        raise TestFailure("multilevel predictions did not preserve included variance components")
    run(
        runner_base(effects, work / "multilevel_crossed_cr2_reject", "multilevel", "log")
        + [
            "--id-col", "effect_id", "--v-matrix", v_path,
            "--random", "~ 1 | study_id/effect_id", "--mv-method", "REML",
            "--test", "t", "--dfs", "residual", "--prediction", "no",
            "--robust-cluster", "study_id", "--robust-method", "CR2",
            "--dependence-topology", "crossed", "--overwrite", "yes",
        ],
        expected=2,
    )

    loo_raw = work / "raw_dependent_12.csv"
    expand_dependent_raw(raw, loo_raw, clusters=12)
    validate_fixture(loo_raw, "raw", allow_warnings=True)
    loo_effects = work / "effects_dependent_12.csv"
    calculate_gen_rr(loo_raw, loo_effects)
    validate_fixture(loo_effects, "analysis", allow_warnings=True)
    loo_v = work / "V_12.csv"
    run(
        [
            R_SCRIPT,
            SCRIPTS / "build_sampling_v.R",
            "--input",
            loo_effects,
            "--output-v",
            loo_v,
            "--vi-col",
            "vi",
            "--id-col",
            "effect_id",
            "--cluster-col",
            "study_id",
            "--obs-col",
            "outcome",
            "--rho",
            "0.5",
            "--scenario-label",
            "rho_0.5_multilevel_loo",
            "--overwrite",
            "yes",
        ]
    )
    loo_dir = work / "multilevel_cr2_loo"
    run(
        runner_base(loo_effects, loo_dir, "multilevel", "log")
        + [
            "--id-col",
            "effect_id",
            "--v-matrix",
            loo_v,
            "--random",
            "~ 1 | study_id/effect_id",
            "--mv-method",
            "REML",
            "--test",
            "t",
            "--dfs",
            "residual",
            "--prediction",
            "no",
            "--robust-cluster",
            "study_id",
            "--robust-method",
            "CR2",
            "--dependence-topology",
            "nested",
            "--leave-one-out",
            "yes",
            "--overwrite",
            "yes",
        ]
    )
    leave_one = read_csv(loo_dir / "leave_one_cluster_out.csv")
    if len(leave_one) != 12:
        raise TestFailure("multilevel leave-one-cluster-out did not produce one row per cluster")
    if {row["inference"] for row in leave_one} != {"CR2"}:
        raise TestFailure("multilevel leave-one-cluster-out did not preserve CR2 inference")
    if {row["v_subset"] for row in leave_one} != {"row_and_column_subset"}:
        raise TestFailure("multilevel leave-one-cluster-out did not subset the full V by rows and columns")
    if {row["rows_omitted"] for row in leave_one} != {"2"}:
        raise TestFailure("multilevel leave-one-cluster-out omitted the wrong number of effects")


def test_logit_scale(work: Path) -> None:
    raw = FIXTURES / "raw_proportion.csv"
    validate_fixture(raw, "raw")
    effects = work / "effects_proportion.csv"
    run(
        [
            R_SCRIPT,
            SCRIPTS / "calculate_effect_sizes.R",
            "--input",
            raw,
            "--output",
            effects,
            "--measure",
            "PLO",
            "--xi-col",
            "events_intervention",
            "--ni-col",
            "n_total",
            "--zero-policy",
            "none",
            "--overwrite",
            "yes",
        ]
    )
    validate_fixture(effects, "analysis")
    if {row["analysis_scale"] for row in read_csv(effects)} != {"logit"}:
        raise TestFailure("PLO did not emit logit scale")
    output = work / "proportion_common"
    run(runner_base(effects, output, "common", "logit") + ["--prediction", "no", "--overwrite", "yes"])
    coefficient = read_csv(output / "coefficients.csv")[0]
    assert_close(coefficient["estimate"], GOLDEN["common_proportion"]["estimate"], "PLO estimate")
    assert_close(coefficient["display_estimate"], GOLDEN["common_proportion"]["display_estimate"], "PLO display")


def route_payload() -> dict[str, Any]:
    payload = json.loads((SKILL_ROOT / "assets" / "synthesis_route_template.json").read_text(encoding="utf-8"))
    payload["task"]["as_of_date"] = "2026-08-03"
    return payload


def make_reference_receipt(payload: Mapping[str, Any], pending: Mapping[str, Any]) -> dict[str, Any]:
    rule_id = pending["matched_reference_rules"][0]
    references = []
    for relative in pending["required_references"]:
        path = SKILL_ROOT / relative
        heading = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("#"))
        references.append({
            "path": relative,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sections_used": [heading],
            "decision_mapping": [{"decision_id": rule_id, "applied_rule": "test decision mapping"}],
        })
    sources = [{
        "source_id": source_id,
        "version_used": "test-version",
        "accessed_at": payload["task"]["as_of_date"],
        "checked_at_milestone": payload["task"]["stage"],
        "adoption_decision": "adopted",
        "change_summary": "test update check",
    } for source_id in pending["required_source_ids"]]
    return {
        "schema_version": "1.0",
        "plan_sha256": pending["reference_gate"]["plan_sha256"],
        "task_stage": payload["task"]["stage"],
        "attested_by": "test-runner",
        "attested_at": payload["task"]["as_of_date"],
        "reference_files": references,
        "source_records": sources,
    }


def invoke_route(
    payload: Mapping[str, Any], *, expected: int = 0, pass_reference_gate: bool = False
) -> dict[str, Any]:
    command: list[str | Path] = [PYTHON, SCRIPTS / "route_synthesis.py", "-"]
    if pass_reference_gate and expected == 0:
        pending = invoke_route(payload)
        with tempfile.TemporaryDirectory(prefix="reference-receipt-") as temporary:
            receipt_path = Path(temporary) / "receipt.json"
            receipt_path.write_text(
                json.dumps(make_reference_receipt(payload, pending)), encoding="utf-8"
            )
            command.extend(["--reference-receipt", receipt_path])
            result = run(command, stdin=json.dumps(payload), expected=expected)
    else:
        result = run(command, stdin=json.dumps(payload), expected=expected)
    stream = result.stdout if expected == 0 else result.stderr
    return json.loads(stream)


def test_router() -> None:
    payload = route_payload()
    pending = invoke_route(payload)
    if pending["runner_allowed"] or pending["provisional_runner_allowed"] is not True:
        raise TestFailure("aggregate route bypassed the missing-reference-receipt gate")
    if pending["reference_gate"]["status"] != "pending":
        raise TestFailure(f"unexpected pending reference gate: {pending}")
    expected_health_refs = {
        "references/medical-review.md",
        "references/effect-size-and-models.md",
        "references/r-metafor-workflows.md",
    }
    if set(pending["required_references"]) != expected_health_refs:
        raise TestFailure(f"ordinary health task received the wrong reference set: {pending}")
    aggregate = invoke_route(payload, pass_reference_gate=True)
    if aggregate["route"] != "aggregate_effect_meta" or not aggregate["runner_allowed"]:
        raise TestFailure(f"valid receipt did not release aggregate route: {aggregate}")
    if aggregate["reference_gate"]["status"] != "passed" or aggregate["stop_reason"] is not None:
        raise TestFailure(f"passed reference gate retained a stop condition: {aggregate}")

    dependent_payload = route_payload()
    dependent_payload["data"]["effect_structure"] = "dependent"
    dependent_payload["data"]["dependence_topology"] = "nested"
    dependent_payload["data"]["dependency_sources"] = ["shared_control"]
    dependent_payload["data"]["sampling_covariance_status"] = "derived_exact"
    dependent_payload["data"]["sampling_v_path"] = "derived/shared-control-V.csv"
    dependent = invoke_route(dependent_payload, pass_reference_gate=True)
    if dependent["route"] != "dependent_effect_meta" or not dependent["runner_allowed"]:
        raise TestFailure("dependent aggregate data were not routed to dependent_effect_meta")
    if "references/complex-design-effects.md" not in dependent["required_references"]:
        raise TestFailure("shared-control dependence did not route to the complex-design reference")
    if "references/specialist-medical-models.md" in dependent["required_references"]:
        raise TestFailure("shared-control dependence loaded an unrelated specialist medical reference")
    if "CLUBSANDWICH-DOCS" not in dependent["required_source_ids"]:
        raise TestFailure("dependent R implementation omitted clubSandwich version guidance")

    diagnostic_payload = route_payload()
    diagnostic_payload["specialist_triggers"]["diagnostic"] = True
    diagnostic = invoke_route(diagnostic_payload)
    if not {
        "references/medical-review.md",
        "references/specialist-medical-models.md",
        "references/bias-and-certainty.md",
    }.issubset(diagnostic["required_references"]):
        raise TestFailure("diagnostic route omitted its medical, model, or appraisal reference")
    if not {"COCHRANE-DTA-HB-2.0", "QUADAS-3-LIVING"}.issubset(
        diagnostic["required_source_ids"]
    ):
        raise TestFailure("diagnostic route omitted Cochrane DTA or QUADAS-3")
    if "references/ecology-review.md" in diagnostic["required_references"]:
        raise TestFailure("diagnostic route loaded an unrelated ecology reference")

    missing_v_payload = route_payload()
    missing_v_payload["data"]["effect_structure"] = "dependent"
    missing_v_payload["data"]["dependence_topology"] = "nested"
    missing_v_payload["data"]["dependency_sources"] = ["shared_control"]
    missing_v_payload["data"]["sampling_covariance_status"] = "unavailable"
    missing_v = invoke_route(missing_v_payload)
    if missing_v["runner_allowed"] or missing_v["required_handoff"] != ["sampling_covariance_specialist"]:
        raise TestFailure("dependent shared-control effects without V were not blocked")

    claimed_v_without_path_payload = route_payload()
    claimed_v_without_path_payload["data"]["effect_structure"] = "dependent"
    claimed_v_without_path_payload["data"]["dependence_topology"] = "nested"
    claimed_v_without_path_payload["data"]["dependency_sources"] = ["multiple_outcomes"]
    claimed_v_without_path_payload["data"]["sampling_covariance_status"] = "provided_validated"
    invalid_claim = invoke_route(claimed_v_without_path_payload, expected=1)
    if invalid_claim.get("error") != "invalid_input":
        raise TestFailure("dependent effects could claim a validated V without a locator")

    life_cycle_payload = route_payload()
    life_cycle_payload["specialist_triggers"]["life_cycle_assessment"] = True
    life_cycle = invoke_route(life_cycle_payload)
    if life_cycle["runner_allowed"] or life_cycle["required_handoff"] != ["life_cycle_assessment_data_fusion_specialist"]:
        raise TestFailure("life-cycle assessment was not hard-routed away from ordinary Meta")

    ecology_handoffs = {
        "raw_community_matrix": "community_ecology_raw_data_specialist",
        "community_composition": "community_composition_specialist",
        "multidimensional_biodiversity": "multivariate_biodiversity_specialist",
        "variability_effect": "variability_meta_analysis_specialist",
        "factorial_interaction": "factorial_interaction_meta_specialist",
        "ecosystem_multifunctionality": "ecosystem_multifunctionality_specialist",
        "one_stage_longitudinal": "one_stage_longitudinal_model_specialist",
        "derived_recovery_stability": "derived_recovery_stability_specialist",
        "second_order_meta": "second_order_evidence_synthesis_specialist",
    }
    for trigger, expected_handoff in ecology_handoffs.items():
        ecology_payload = route_payload()
        ecology_payload["task"]["domain"] = "ecology"
        ecology_payload["task"]["topic_tags"] = ["biodiversity"]
        ecology_payload["specialist_triggers"][trigger] = True
        if trigger in {
            "raw_community_matrix",
            "community_composition",
            "multidimensional_biodiversity",
            "variability_effect",
            "factorial_interaction",
            "ecosystem_multifunctionality",
            "derived_recovery_stability",
        }:
            ecology_payload["data"]["ecology_contract_path"] = "contracts/ecology-outcome.json"
        if trigger == "raw_community_matrix":
            ecology_payload["data"]["level"] = "raw_community_matrix"
        if trigger == "second_order_meta":
            ecology_payload["data"]["level"] = "meta_level"
        ecology_route = invoke_route(ecology_payload)
        if ecology_route["runner_allowed"] or ecology_route["required_handoff"] != [expected_handoff]:
            raise TestFailure(f"{trigger} was not hard-routed to {expected_handoff}")
        if trigger == "raw_community_matrix":
            if not {
                "references/ecology-review.md",
                "references/plant-biodiversity-specialist-routes.md",
            }.issubset(ecology_route["required_references"]):
                raise TestFailure("raw community data omitted ecology/biodiversity references")
            if "references/medical-review.md" in ecology_route["required_references"]:
                raise TestFailure("raw community data loaded an unrelated medical reference")
            if "references/r-metafor-workflows.md" in ecology_route["required_references"]:
                raise TestFailure("raw community data loaded the ordinary yi/vi R workflow before estimand generation")

    raw_level_without_trigger = route_payload()
    raw_level_without_trigger["data"]["level"] = "raw_community_matrix"
    invalid_raw_level = invoke_route(raw_level_without_trigger, expected=1)
    if invalid_raw_level.get("error") != "invalid_input":
        raise TestFailure("raw community data level was accepted without its specialist trigger")

    ambiguous = route_payload()
    ambiguous["specialist_triggers"]["lca"] = True
    invalid = invoke_route(ambiguous, expected=1)
    if invalid.get("error") != "invalid_input":
        raise TestFailure("ambiguous lca field was not rejected")

    no_pooling_payload = route_payload()
    no_pooling_payload["pooling"] = {
        "eligible": False,
        "ineligibility_reason": "estimands are not exchangeable",
    }
    no_pooling = invoke_route(no_pooling_payload)
    if no_pooling["route"] != "no_pooling" or no_pooling["runner_allowed"]:
        raise TestFailure("incoherent pooling plan did not stop the runner")

    with tempfile.TemporaryDirectory(prefix="route-file-test-") as temporary:
        route_dir = Path(temporary)
        input_path = route_dir / "input.json"
        output_path = route_dir / "output.json"
        input_path.write_text(json.dumps(route_payload()), encoding="utf-8")
        run([PYTHON, SCRIPTS / "route_synthesis.py", input_path, "--output", output_path])
        raw = output_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise TestFailure("route output unexpectedly contains a UTF-8 BOM")
        if json.loads(raw.decode("utf-8"))["route"] != "aggregate_effect_meta":
            raise TestFailure("route --output file is not valid UTF-8 route JSON")
        run([PYTHON, SCRIPTS / "route_synthesis.py", input_path, "--output", output_path], expected=2)
        run(
            [
                PYTHON,
                SCRIPTS / "route_synthesis.py",
                input_path,
                "--output",
                output_path,
                "--overwrite",
                "yes",
            ]
        )


def test_plant_biodiversity_knowledge_assets() -> None:
    casebook = (SKILL_ROOT / "references" / "plant-biodiversity-benchmark-casebook.md").read_text(encoding="utf-8")
    route_guide = (SKILL_ROOT / "references" / "plant-biodiversity-specialist-routes.md").read_text(encoding="utf-8")
    benchmark_ids = {
        "BENCH-CHEN-2025",
        "BENCH-KECK-2025",
        "BENCH-SHAW-2025",
        "BENCH-CHENG-2024",
        "BENCH-LI-2025",
        "BENCH-GONCALVES-2025",
        "BENCH-ATKINSON-2022",
        "BENCH-HONG-2022",
        "BENCH-CROUZEILLES-2016",
        "BENCH-MORENO-2017",
        "BENCH-MORI-2020",
        "BENCH-LEFCHECK-2015",
        "BENCH-ISBELL-2015",
        "BENCH-HOOPER-2012",
        "BENCH-CARDINALE-2006",
        "BENCH-DUFFY-2017",
        "BENCH-WAN-2020",
        "BENCH-DAINESE-2019",
        "BENCH-VELLEND-2013",
    }
    missing_benchmarks = sorted(item for item in benchmark_ids if item not in casebook)
    if missing_benchmarks:
        raise TestFailure(f"benchmark casebook is missing: {', '.join(missing_benchmarks)}")

    required_routes = {
        "raw_community_matrix",
        "community_composition",
        "multidimensional_biodiversity",
        "variability_effect",
        "factorial_interaction",
        "ecosystem_multifunctionality",
        "one_stage_longitudinal",
        "derived_recovery_stability",
        "second_order_meta",
        "sampling_covariance_status",
        "biodiversity_contract_template.json",
        "validate_biodiversity_contract.py",
    }
    missing_routes = sorted(item for item in required_routes if item not in route_guide)
    if missing_routes:
        raise TestFailure(f"plant-biodiversity route guide is missing: {', '.join(missing_routes)}")


def test_integrity_and_lineage(work: Path) -> None:
    run([PYTHON, SCRIPTS / "validate_integrity.py", SKILL_ROOT / "assets" / "publication_integrity_template.csv"])

    headers = [
        "object_type",
        "object_id",
        "checked_at",
        "status",
        "source",
        "disposition",
        "sensitivity_analysis",
        "notes",
    ]
    resolved = work / "integrity_resolved.csv"
    write_csv(
        resolved,
        headers,
        [
            {
                "object_type": "paper",
                "object_id": "PAPER-1",
                "checked_at": "2026-08-02",
                "status": "correction",
                "source": "publisher correction page",
                "disposition": "corrected values used",
                "sensitivity_analysis": "uncorrected values excluded by protocol",
                "notes": "test",
            }
        ],
    )
    run([PYTHON, SCRIPTS / "validate_integrity.py", resolved])

    unresolved = work / "integrity_unresolved.csv"
    write_csv(
        unresolved,
        headers,
        [
            {
                "object_type": "data",
                "object_id": "DATA-1",
                "checked_at": "2026-08-02",
                "status": "expression_of_concern",
                "source": "repository status page",
                "disposition": "pending",
                "sensitivity_analysis": "pending",
                "notes": "test",
            }
        ],
    )
    run([PYTHON, SCRIPTS / "validate_integrity.py", unresolved], expected=1)

    source = work / "lineage_input.csv"
    output = work / "lineage_output.csv"
    source.write_text("source_id,value\nA,2\n", encoding="utf-8")
    output.write_text("effect_id,yi\nA,0.6931471805599453\n", encoding="utf-8")
    lineage = work / "field_lineage.csv"
    write_csv(
        lineage,
        ["output_file", "output_field", "source_fields", "transform", "formula_or_code", "notes"],
        [
            {
                "output_file": output.name,
                "output_field": "effect_id",
                "source_fields": f"{source.name}:source_id",
                "transform": "identity",
                "formula_or_code": "effect_id = source_id",
                "notes": "test",
            },
            {
                "output_file": output.name,
                "output_field": "yi",
                "source_fields": f"{source.name}:value",
                "transform": "natural log",
                "formula_or_code": "yi = log(value)",
                "notes": "test",
            },
        ],
    )
    manifest_one = work / "lineage_one.json"
    artifact = work / "model.rds"
    artifact.write_bytes(b"RDX-test-artifact\x00\x01")
    first = run(
        [
            PYTHON,
            SCRIPTS / "build_lineage_manifest.py",
            "--lineage",
            lineage,
            "--input",
            source,
            "--script",
            SCRIPTS / "calculate_effect_sizes.R",
            "--output",
            output,
            "--artifact",
            artifact,
            "--seed",
            "not_applicable",
            "--manifest",
            manifest_one,
        ],
        cwd=work,
    )
    first_payload = json.loads(first.stdout)
    if first_payload["inputs"][0]["sha256"] != sha256(source):
        raise TestFailure("lineage manifest input hash is incorrect")
    if first_payload["artifacts"][0]["sha256"] != sha256(artifact):
        raise TestFailure("lineage manifest artifact hash is incorrect")
    first_hash = first_payload["inputs"][0]["sha256"]
    source.write_text("source_id,value\nA,3\n", encoding="utf-8")
    second = run(
        [
            PYTHON,
            SCRIPTS / "build_lineage_manifest.py",
            "--lineage",
            lineage,
            "--input",
            source,
            "--script",
            SCRIPTS / "calculate_effect_sizes.R",
            "--output",
            output,
            "--artifact",
            artifact,
            "--seed",
            "not_applicable",
        ],
        cwd=work,
    )
    second_hash = json.loads(second.stdout)["inputs"][0]["sha256"]
    if first_hash == second_hash:
        raise TestFailure("lineage SHA-256 did not change after an input-byte change")

    incomplete = work / "field_lineage_incomplete.csv"
    write_csv(
        incomplete,
        ["output_file", "output_field", "source_fields", "transform", "formula_or_code"],
        [
            {
                "output_file": output.name,
                "output_field": "effect_id",
                "source_fields": f"{source.name}:source_id",
                "transform": "identity",
                "formula_or_code": "effect_id = source_id",
            }
        ],
    )
    run(
        [
            PYTHON,
            SCRIPTS / "build_lineage_manifest.py",
            "--lineage",
            incomplete,
            "--input",
            source,
            "--script",
            SCRIPTS / "calculate_effect_sizes.R",
            "--output",
            output,
            "--seed",
            "not_applicable",
        ],
        cwd=work,
        expected=1,
    )


def main() -> int:
    if not R_SCRIPT.is_file():
        raise TestFailure(f"Rscript was not found: {R_SCRIPT}")
    test_r_packages()
    with tempfile.TemporaryDirectory(prefix="easymeta-tests-") as temporary:
        work = Path(temporary)
        test_two_stage_and_models(work)
        test_dependent_v_and_cr2(work)
        test_logit_scale(work)
        test_router()
        test_plant_biodiversity_knowledge_assets()
        test_integrity_and_lineage(work)
    print("PASS: P0-1 through P0-6 end-to-end golden and rejection tests")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TestFailure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
