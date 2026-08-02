#!/usr/bin/env python3
"""Repeatable end-to-end tests for every case registered in p1_scenarios.json.

The suite creates all mutable inputs and outputs under the system temporary
directory, or under META_TEST_SCRATCH when that environment variable names an
existing directory. Set META_TEST_R_LIBRARY to an R library containing metafor;
an existing R_LIBS_USER is retained after it on the R library search path.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
SCRIPTS = SKILL_ROOT / "scripts"
SCENARIOS_PATH = SKILL_ROOT / "tests" / "p1_scenarios.json"
R_SCRIPT = Path(os.environ.get("R_SCRIPT") or shutil.which("Rscript") or "Rscript")
PYTHON = Path(sys.executable)
SCRATCH_ROOT = Path(os.environ["META_TEST_SCRATCH"]).expanduser() if os.environ.get("META_TEST_SCRATCH") else None
CASE_FUNCTIONS: dict[str, Callable[[Path], None]] = {}
CURRENT_COMMANDS: list[tuple[list[str], str, int, str, str]] = []


class TestFailure(RuntimeError):
    pass


def register(case_id: str) -> Callable[[Callable[[Path], None]], Callable[[Path], None]]:
    def decorator(function: Callable[[Path], None]) -> Callable[[Path], None]:
        if case_id in CASE_FUNCTIONS:
            raise RuntimeError(f"duplicate test registration: {case_id}")
        CASE_FUNCTIONS[case_id] = function
        return function

    return decorator


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    test_library = env.get("META_TEST_R_LIBRARY", "").strip()
    existing_library = env.get("R_LIBS_USER", "").strip()
    if test_library:
        env["R_LIBS_USER"] = (
            test_library
            if not existing_library
            else test_library + os.pathsep + existing_library
        )
    return env


def run(
    command: Sequence[str | Path],
    *,
    expected: int = 0,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    rendered = [str(item) for item in command]
    working_directory = str(cwd or SKILL_ROOT)
    result = subprocess.run(
        rendered,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=working_directory,
        env=command_env(),
        check=False,
    )
    CURRENT_COMMANDS.append(
        (rendered, working_directory, result.returncode, result.stdout, result.stderr)
    )
    if result.returncode != expected:
        raise TestFailure(
            f"unexpected exit code: expected {expected}, got {result.returncode}"
        )
    return result


def command_trace() -> str:
    if not CURRENT_COMMANDS:
        return "commands: none"
    blocks: list[str] = []
    for index, (command, cwd, returncode, stdout, stderr) in enumerate(
        CURRENT_COMMANDS, start=1
    ):
        blocks.append(
            "\n".join(
                [
                    f"command[{index}]: {subprocess.list2cmdline(command)}",
                    f"cwd[{index}]: {cwd}",
                    f"exit[{index}]: {returncode}",
                    f"stdout[{index}]:\n{stdout.rstrip() or '<empty>'}",
                    f"stderr[{index}]:\n{stderr.rstrip() or '<empty>'}",
                ]
            )
        )
    return "\n\n".join(blocks)


def assert_contains(result: subprocess.CompletedProcess[str], *needles: str) -> None:
    combined = (result.stdout + "\n" + result.stderr).casefold()
    if not any(needle.casefold() in combined for needle in needles):
        raise TestFailure(f"expected one of these messages: {needles!r}")


def assert_close(actual: float | str, expected: float, label: str) -> None:
    value = float(actual)
    if not math.isclose(value, expected, rel_tol=1e-8, abs_tol=1e-10):
        raise TestFailure(f"{label}: expected {expected:.15g}, got {value:.15g}")


def assert_file_set(directory: Path, expected: Iterable[str]) -> None:
    actual = {path.name for path in directory.iterdir()}
    expected_set = set(expected)
    if actual != expected_set:
        raise TestFailure(
            f"unexpected output set in {directory}: expected {sorted(expected_set)}, "
            f"got {sorted(actual)}"
        )


def read_csv_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise TestFailure(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def read_csv(path: Path) -> list[dict[str, str]]:
    return read_csv_table(path)[1]


def write_csv(
    path: Path,
    headers: Iterable[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(headers), lineterminator="\n", extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_matrix(
    path: Path,
    id_header: str,
    ids: Sequence[str],
    values: Sequence[Sequence[float]],
) -> None:
    if len(values) != len(ids) or any(len(row) != len(ids) for row in values):
        raise TestFailure(f"matrix dimensions do not match IDs for {path}")
    rows = [
        {id_header: row_id, **dict(zip(ids, row_values))}
        for row_id, row_values in zip(ids, values)
    ]
    write_csv(path, [id_header, *ids], rows)


def yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def asset_table(name: str) -> tuple[list[str], list[dict[str, str]]]:
    return read_csv_table(ASSETS / name)


def template_row(name: str, field: str, value: str) -> tuple[list[str], dict[str, str]]:
    headers, rows = asset_table(name)
    matches = [dict(row) for row in rows if row.get(field) == value]
    if len(matches) != 1:
        raise TestFailure(
            f"expected exactly one {name} row with {field}={value!r}, got {len(matches)}"
        )
    return headers, matches[0]


def validate_analysis(path: Path) -> None:
    run(
        [
            PYTHON,
            SCRIPTS / "validate_extraction.py",
            path,
            "--stage",
            "analysis",
            "--allow-warnings",
        ]
    )


def run_complex_pass(
    work: Path,
    row: Mapping[str, str],
    *,
    expected_yi: float,
    expected_vi: float,
) -> None:
    headers, _ = asset_table("complex_effect_input_template.csv")
    source = work / "complex-input.csv"
    output = work / "complex-effects.csv"
    write_csv(source, headers, [row])
    run(
        [
            R_SCRIPT,
            SCRIPTS / "calculate_complex_effects.R",
            "--input",
            source,
            "--output",
            output,
        ]
    )
    validate_analysis(output)
    output_rows = read_csv(output)
    if len(output_rows) != 1:
        raise TestFailure("complex calculator did not preserve one-row cardinality")
    result = output_rows[0]
    assert_close(result["yi"], expected_yi, "complex yi")
    assert_close(result["vi"], expected_vi, "complex vi")
    assert_close(float(result["sei"]) ** 2, expected_vi, "complex sei^2")
    if result["analysis_scale"] != "identity":
        raise TestFailure("complex MD fixture did not remain on identity scale")
    for field in (
        "calculation_method",
        "design_formula",
        "uncertainty_route",
        "effect_orientation",
    ):
        if not result[field].strip():
            raise TestFailure(f"complex output audit field is blank: {field}")
    manifest = work / "complex-effects.manifest.txt"
    if not manifest.is_file():
        raise TestFailure("complex calculator did not write its manifest")


def run_complex_reject(
    work: Path, row: Mapping[str, str], *messages: str
) -> None:
    headers, _ = asset_table("complex_effect_input_template.csv")
    source = work / "complex-reject.csv"
    output = work / "must-not-exist.csv"
    write_csv(source, headers, [row])
    result = run(
        [
            R_SCRIPT,
            SCRIPTS / "calculate_complex_effects.R",
            "--input",
            source,
            "--output",
            output,
        ],
        expected=2,
    )
    assert_contains(result, *messages)
    if output.exists() or (work / "must-not-exist.manifest.txt").exists():
        raise TestFailure("rejected complex input published an output")


@register("complex_paired_direct_pass")
def complex_paired_direct_pass(work: Path) -> None:
    _, row = template_row(
        "complex_effect_input_template.csv", "complex_design", "paired_continuous_md"
    )
    run_complex_pass(work, row, expected_yi=-2.0, expected_vi=16.0 / 28.0)


def derived_paired_row() -> dict[str, str]:
    _, row = template_row(
        "complex_effect_input_template.csv",
        "complex_design",
        "crossover_continuous_md",
    )
    row["complex_design"] = "paired_continuous_md"
    row["study_design"] = "paired_measurements"
    row["carryover_cleared"] = "not_applicable"
    row["carryover_assessment_source"] = ""
    return row


@register("complex_paired_derived_pass")
def complex_paired_derived_pass(work: Path) -> None:
    row = derived_paired_row()
    expected_variance = (3.0**2 + 3.5**2 - 2 * 0.6 * 3.0 * 3.5) / 22.0
    run_complex_pass(work, row, expected_yi=-2.0, expected_vi=expected_variance)


@register("complex_missing_correlation_reject")
def complex_missing_correlation_reject(work: Path) -> None:
    row = derived_paired_row()
    row["paired_correlation"] = ""
    run_complex_reject(work, row, "paired_correlation", "explicit correlation")


@register("complex_carryover_reject")
def complex_carryover_reject(work: Path) -> None:
    _, row = template_row(
        "complex_effect_input_template.csv",
        "complex_design",
        "crossover_continuous_md",
    )
    row["carryover_cleared"] = "no"
    run_complex_reject(work, row, "carryover_cleared=yes", "carryover blocks")


@register("complex_two_group_change_pass")
def complex_two_group_change_pass(work: Path) -> None:
    _, row = template_row(
        "complex_effect_input_template.csv", "complex_design", "two_group_change_md"
    )
    run_complex_pass(work, row, expected_yi=-3.0, expected_vi=36.0 / 40.0 + 25.0 / 40.0)


@register("complex_baci_additive_pass")
def complex_baci_additive_pass(work: Path) -> None:
    _, row = template_row(
        "complex_effect_input_template.csv", "complex_design", "baci_additive_md"
    )
    intervention_variance = 2.5**2 + 2.8**2 - 2 * 0.5 * 2.5 * 2.8
    comparator_variance = 2.4**2 + 2.6**2 - 2 * 0.5 * 2.4 * 2.6
    run_complex_pass(
        work,
        row,
        expected_yi=2.5,
        expected_vi=intervention_variance / 20.0 + comparator_variance / 20.0,
    )


@register("complex_cluster_adjusted_generic_pass")
def complex_cluster_adjusted_generic_pass(work: Path) -> None:
    _, row = template_row(
        "complex_effect_input_template.csv",
        "complex_design",
        "cluster_adjusted_generic",
    )
    run_complex_pass(work, row, expected_yi=-1.2, expected_vi=0.4**2)


@register("complex_effective_sample_only_reject")
def complex_effective_sample_only_reject(work: Path) -> None:
    _, row = template_row(
        "complex_effect_input_template.csv",
        "complex_design",
        "cluster_adjusted_generic",
    )
    row["cluster_adjusted_estimate"] = "no"
    row["effect_estimate"] = ""
    row["se"] = ""
    row["uncertainty_type"] = ""
    run_complex_reject(
        work,
        row,
        "already reported design-adjusted estimate",
        "effective sample size alone is forbidden",
    )


def diagnostic_command(source: Path, output: Path) -> list[str | Path]:
    return [
        R_SCRIPT,
        SCRIPTS / "run_diagnostic_meta.R",
        "--input",
        source,
        "--output-dir",
        output,
    ]


@register("diagnostic_single_threshold_pass")
def diagnostic_single_threshold_pass(work: Path) -> None:
    headers, rows = asset_table("diagnostic_meta_template.csv")
    source = work / "diagnostic.csv"
    output = work / "diagnostic-output"
    write_csv(source, headers, rows)
    run(
        diagnostic_command(source, output)
        + ["--zero-strategy", "continuity", "--continuity-correction", "0.5"]
    )
    assert_file_set(
        output,
        {
            "analysis_manifest.txt",
            "data_used.csv",
            "long_effects.csv",
            "summary_measures.csv",
            "random_effects.csv",
            "model.rds",
            "session_info.txt",
        },
    )
    if {row["outcome"] for row in read_csv(output / "summary_measures.csv")} != {
        "sensitivity",
        "specificity",
    }:
        raise TestFailure("diagnostic summary did not contain sensitivity and specificity")
    manifest = (output / "analysis_manifest.txt").read_text(encoding="utf-8")
    if "zero_strategy=continuity" not in manifest or "zero_corrected_studies=1" not in manifest:
        raise TestFailure("diagnostic manifest did not audit the explicit zero-cell policy")


@register("diagnostic_multiple_thresholds_reject")
def diagnostic_multiple_thresholds_reject(work: Path) -> None:
    headers, rows = asset_table("diagnostic_meta_template.csv")
    repeated = dict(rows[0])
    repeated["threshold_id"] = "T2"
    source = work / "diagnostic-multiple-thresholds.csv"
    output = work / "must-not-exist"
    write_csv(source, headers, [*rows, repeated])
    result = run(
        diagnostic_command(source, output)
        + ["--zero-strategy", "continuity", "--continuity-correction", "0.5"],
        expected=2,
    )
    assert_contains(result, "multiple/repeated threshold", "repeated study_id")
    if output.exists():
        raise TestFailure("rejected diagnostic input published an output directory")


@register("diagnostic_implicit_zero_policy_reject")
def diagnostic_implicit_zero_policy_reject(work: Path) -> None:
    headers, rows = asset_table("diagnostic_meta_template.csv")
    source = work / "diagnostic-zero.csv"
    output = work / "must-not-exist"
    write_csv(source, headers, rows)
    result = run(diagnostic_command(source, output), expected=2)
    assert_contains(result, "missing required option '--zero-strategy'")
    if output.exists():
        raise TestFailure("missing diagnostic zero policy published an output directory")


def dose_v(rows: Sequence[Mapping[str, str]]) -> list[list[float]]:
    matrix = [[0.0 for _ in rows] for _ in rows]
    for i, left in enumerate(rows):
        matrix[i][i] = 0.04 + 0.005 * (i % 2)
        for j in range(i):
            if left["study"] == rows[j]["study"]:
                matrix[i][j] = matrix[j][i] = 0.01
    return matrix


def dose_command(source: Path, v_path: Path, output: Path) -> list[str | Path]:
    return [
        R_SCRIPT,
        SCRIPTS / "run_dose_response.R",
        "--input",
        source,
        "--v-matrix",
        v_path,
        "--output-dir",
        output,
    ]


@register("dose_linear_gls_pass")
def dose_linear_gls_pass(work: Path) -> None:
    headers, rows = asset_table("dose_response_template.csv")
    source = work / "dose.csv"
    v_path = work / "dose-V.csv"
    output = work / "dose-output"
    write_csv(source, headers, rows)
    ids = [row["effect_id"] for row in rows]
    write_matrix(v_path, "effect_id", ids, dose_v(rows))
    run(dose_command(source, v_path, output))
    assert_file_set(
        output,
        {
            "analysis_manifest.txt",
            "data_used.csv",
            "study_slopes.csv",
            "pooled_slope.csv",
            "heterogeneity.csv",
            "model.rds",
            "session_info.txt",
        },
    )
    slopes = read_csv(output / "study_slopes.csv")
    if len(slopes) != 3 or {row["effects"] for row in slopes} != {"2"}:
        raise TestFailure("dose-response runner did not fit three two-level study slopes")
    pooled = read_csv(output / "pooled_slope.csv")
    if len(pooled) != 1 or not math.isfinite(float(pooled[0]["estimate"])):
        raise TestFailure("dose-response runner did not produce one finite pooled slope")


@register("dose_missing_v_reject")
def dose_missing_v_reject(work: Path) -> None:
    headers, rows = asset_table("dose_response_template.csv")
    source = work / "dose.csv"
    output = work / "must-not-exist"
    write_csv(source, headers, rows)
    result = run(
        [
            R_SCRIPT,
            SCRIPTS / "run_dose_response.R",
            "--input",
            source,
            "--output-dir",
            output,
        ],
        expected=2,
    )
    assert_contains(result, "missing required option '--v-matrix'")
    if output.exists():
        raise TestFailure("dose-response run without V published output")


@register("dose_one_nonreference_level_reject")
def dose_one_nonreference_level_reject(work: Path) -> None:
    headers, rows = asset_table("dose_response_template.csv")
    rows = [dict(row) for row in rows]
    rows[1]["dose_difference"] = rows[0]["dose_difference"]
    source = work / "dose-one-level.csv"
    v_path = work / "dose-V.csv"
    output = work / "must-not-exist"
    write_csv(source, headers, rows)
    ids = [row["effect_id"] for row in rows]
    write_matrix(v_path, "effect_id", ids, dose_v(rows))
    result = run(dose_command(source, v_path, output), expected=2)
    assert_contains(result, "at least two distinct non-reference dose differences")
    if output.exists():
        raise TestFailure("one-level dose input published output")


def network_v(rows: Sequence[Mapping[str, str]]) -> list[list[float]]:
    matrix = [[0.0 for _ in rows] for _ in rows]
    for i, left in enumerate(rows):
        matrix[i][i] = float(left["vi"])
        for j in range(i):
            if left["study"] == rows[j]["study"]:
                matrix[i][j] = matrix[j][i] = 0.01
    return matrix


def network_command(source: Path, output: Path) -> list[str | Path]:
    return [
        R_SCRIPT,
        SCRIPTS / "run_network_meta.R",
        "--input",
        source,
        "--output-dir",
        output,
        "--reference-treatment",
        "A",
    ]


@register("network_connected_pass")
def network_connected_pass(work: Path) -> None:
    headers, rows = asset_table("network_meta_template.csv")
    source = work / "network.csv"
    v_path = work / "network-V.csv"
    output = work / "network-output"
    write_csv(source, headers, rows)
    ids = [row["effect_id"] for row in rows]
    write_matrix(v_path, "effect_id", ids, network_v(rows))
    run(network_command(source, output) + ["--v-matrix", v_path])
    assert_file_set(
        output,
        {
            "analysis_manifest.txt",
            "data_used.csv",
            "basic_parameters.csv",
            "all_comparisons.csv",
            "model_fit.csv",
            "model.rds",
            "session_info.txt",
        },
    )
    if len(read_csv(output / "basic_parameters.csv")) != 2:
        raise TestFailure("three-treatment network did not produce two basic parameters")
    comparisons = read_csv(output / "all_comparisons.csv")
    if len(comparisons) != 3 or {row["direction"] for row in comparisons} != {
        "treatment_b_minus_treatment_a"
    }:
        raise TestFailure("network did not produce all three directed pairwise contrasts")


@register("network_disconnected_reject")
def network_disconnected_reject(work: Path) -> None:
    headers, seed_rows = asset_table("network_meta_template.csv")
    rows: list[dict[str, str]] = []
    for index, (study, a, b) in enumerate(
        (("S1", "A", "B"), ("S2", "A", "B"), ("S3", "C", "D"), ("S4", "C", "D")),
        start=1,
    ):
        row = dict(seed_rows[0])
        row.update(
            effect_id=f"E{index}",
            study=study,
            treatment_a=a,
            treatment_b=b,
            yi=str(-0.1 * index),
            vi="0.04",
        )
        rows.append(row)
    source = work / "network-disconnected.csv"
    output = work / "must-not-exist"
    write_csv(source, headers, rows)
    result = run(network_command(source, output), expected=2)
    assert_contains(result, "treatment network is disconnected")
    if output.exists():
        raise TestFailure("disconnected network published output")


@register("network_multiarm_without_v_reject")
def network_multiarm_without_v_reject(work: Path) -> None:
    headers, rows = asset_table("network_meta_template.csv")
    source = work / "network-multiarm.csv"
    output = work / "must-not-exist"
    write_csv(source, headers, rows)
    result = run(network_command(source, output), expected=2)
    assert_contains(result, "complete --v-matrix is mandatory for multi-arm")
    if output.exists():
        raise TestFailure("multi-arm network without V published output")


def structure_data(work: Path) -> tuple[Path, list[str], list[str], list[str]]:
    species = ["sp1", "sp2", "sp3"]
    sites = ["site1", "site2", "site3"]
    effects = ["e1", "e2", "e3"]
    rows = [
        {
            "effect_id": effect,
            "species_id": species[index],
            "site_id": sites[index],
            "vi": variance,
            "analysis_scale": "identity",
        }
        for index, (effect, variance) in enumerate(
            zip(effects, ("0.04", "0.05", "0.06"))
        )
    ]
    data_path = work / "structure-data.csv"
    write_csv(data_path, rows[0].keys(), rows)
    return data_path, species, sites, effects


def validate_matrix_command(
    matrix: Path,
    matrix_type: str,
    data: Path,
    id_col: str,
    report: Path | None = None,
) -> list[str | Path]:
    command: list[str | Path] = [
        PYTHON,
        SCRIPTS / "validate_structure_matrix.py",
        matrix,
        "--type",
        matrix_type,
        "--data",
        data,
        "--id-col",
        id_col,
    ]
    if matrix_type == "sampling_v":
        command += ["--vi-col", "vi"]
    if matrix_type == "distance":
        command += [
            "--distance-unit",
            "km",
            "--distance-method",
            "synthetic_linear_coordinates",
        ]
    if report is not None:
        command += ["--report", report]
    return command


@register("structure_correlation_pass")
def structure_correlation_pass(work: Path) -> None:
    data, species, sites, effects = structure_data(work)
    correlation = work / "correlation.csv"
    distance = work / "distance.csv"
    sampling = work / "sampling-V.csv"
    write_matrix(
        correlation,
        "id",
        species,
        [[1.0, 0.3, 0.1], [0.3, 1.0, 0.2], [0.1, 0.2, 1.0]],
    )
    write_matrix(
        distance,
        "id",
        sites,
        [[0.0, 3.0, 7.0], [3.0, 0.0, 4.0], [7.0, 4.0, 0.0]],
    )
    write_matrix(
        sampling,
        "effect_id",
        effects,
        [[0.04, 0.01, 0.005], [0.01, 0.05, 0.0], [0.005, 0.0, 0.06]],
    )
    commands = (
        (correlation, "correlation", "species_id"),
        (distance, "distance", "site_id"),
        (sampling, "sampling_v", "effect_id"),
    )
    for matrix, matrix_type, id_col in commands:
        report = work / f"{matrix_type}.validation.json"
        result = run(
            validate_matrix_command(matrix, matrix_type, data, id_col, report)
        )
        payload = json.loads(result.stdout)
        if payload["status"] != "valid" or payload["matrix_type"] != matrix_type:
            raise TestFailure(f"{matrix_type} matrix did not validate as its declared type")
        if payload["repair_applied"] or payload["near_pd_applied"]:
            raise TestFailure(f"{matrix_type} validator reported an implicit matrix repair")
        if json.loads(report.read_text(encoding="utf-8"))["status"] != "valid":
            raise TestFailure(f"{matrix_type} JSON report is not valid")


@register("structure_asymmetry_reject")
def structure_asymmetry_reject(work: Path) -> None:
    data, species, _, _ = structure_data(work)
    matrix = work / "asymmetric.csv"
    write_matrix(
        matrix,
        "id",
        species,
        [[1.0, 0.2, 0.1], [0.4, 1.0, 0.2], [0.1, 0.2, 1.0]],
    )
    result = run(
        validate_matrix_command(matrix, "correlation", data, "species_id"),
        expected=2,
    )
    assert_contains(result, "matrix is not symmetric")


@register("structure_nonpositive_definite_reject")
def structure_nonpositive_definite_reject(work: Path) -> None:
    data, species, _, _ = structure_data(work)
    matrix = work / "non-pd.csv"
    write_matrix(
        matrix,
        "id",
        species,
        [[1.0, 0.9, 0.9], [0.9, 1.0, -0.9], [0.9, -0.9, 1.0]],
    )
    result = run(
        validate_matrix_command(matrix, "correlation", data, "species_id"),
        expected=2,
    )
    assert_contains(result, "not strictly positive definite", "cholesky pivot")


@register("structure_sampling_diagonal_mismatch_reject")
def structure_sampling_diagonal_mismatch_reject(work: Path) -> None:
    data, _, _, effects = structure_data(work)
    matrix = work / "sampling-mismatch.csv"
    write_matrix(
        matrix,
        "effect_id",
        effects,
        [[0.041, 0.0, 0.0], [0.0, 0.05, 0.0], [0.0, 0.0, 0.06]],
    )
    result = run(
        validate_matrix_command(matrix, "sampling_v", data, "effect_id"),
        expected=2,
    )
    assert_contains(result, "but data variance is", "diagonal")


@register("ecoevo_phylogenetic_fit_pass")
def ecoevo_phylogenetic_fit_pass(work: Path) -> None:
    species = [f"sp{index:02d}" for index in range(1, 13)]
    yi_values = [-1.4, -1.1, -0.8, -0.55, -0.3, -0.05, 0.2, 0.45, 0.75, 1.0, 1.25, 1.55]
    rows = [
        {
            "effect_id": f"e{index:02d}",
            "study_id": f"study{index:02d}",
            "species_id": species[index - 1],
            "yi": yi_values[index - 1],
            "vi": 0.02,
            "analysis_scale": "identity",
            "data_stage": "analysis_effect",
        }
        for index in range(1, 13)
    ]
    data_path = work / "ecoevo-effects.csv"
    matrix_path = work / "phylogeny.csv"
    output = work / "ecoevo-output"
    spec_path = work / "ecoevo-spec.json"
    write_csv(data_path, rows[0].keys(), rows)
    identity = [
        [1.0 if i == j else 0.0 for j in range(len(species))]
        for i in range(len(species))
    ]
    write_matrix(matrix_path, "id", species, identity)
    spec = {
        "schema_version": "1.1.0",
        "structure_type": "phylogenetic",
        "input_csv": data_path.name,
        "output_dir": output.name,
        "analysis_scale": "identity",
        "columns": {
            "effect_id": "effect_id",
            "study_id": "study_id",
            "species_id": "species_id",
            "yi": "yi",
            "vi": "vi",
        },
        "phylogeny": {
            "correlation_matrix": matrix_path.name,
            "source": "deterministic synthetic test phylogeny",
            "version": "p1-test-v1",
            "branch_length_method": "identity correlation for runner contract test",
            "pruning_rule": "exact pre-matched species IDs; no pruning",
        },
        "sampling_v_matrix": None,
        "moderators": "~ 1",
        "method": "REML",
        "test": "t",
        "dfs": "contain",
        "level": 95,
        "model_role": "sensitivity",
        "species_iid_exception_reason": "nonidentifiable",
        "random_effects": {
            "study": False,
            "phylogenetic_species": True,
            "species_iid": False,
            "effect": False,
        },
        "hessian_policy": "require_positive_definite",
        "variance_boundary_tolerance": 1e-10,
        "overwrite": False,
    }
    write_json(spec_path, spec)
    run([R_SCRIPT, SCRIPTS / "run_ecoevo_meta_analysis.R", "--spec", spec_path])
    assert_file_set(
        output,
        {"coefficients.csv", "variance_components.csv", "analysis_manifest.json", "model.rds"},
    )
    manifest = json.loads((output / "analysis_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "success" or manifest["structure_type"] != "phylogenetic":
        raise TestFailure("ecoevo runner manifest did not record a phylogenetic success")
    if manifest["repair_applied"] or manifest["near_pd_applied"]:
        raise TestFailure("ecoevo runner reported a matrix repair")
    components = read_csv(output / "variance_components.csv")
    if len(components) != 1 or components[0]["component"] != "phylogenetic_species":
        raise TestFailure("ecoevo runner did not fit the frozen phylogenetic component")
    if float(components[0]["estimate"]) <= 1e-10:
        raise TestFailure("ecoevo phylogenetic variance landed on the forbidden boundary")

    invalid_primary = dict(spec)
    invalid_primary["model_role"] = "primary"
    invalid_primary["species_iid_exception_reason"] = "prespecified_sensitivity"
    invalid_primary["output_dir"] = "ecoevo-invalid-primary"
    invalid_path = work / "ecoevo-invalid-primary.json"
    write_json(invalid_path, invalid_primary)
    run([R_SCRIPT, SCRIPTS / "run_ecoevo_meta_analysis.R", "--spec", invalid_path], expected=2)


def extraction_pair(work: Path) -> tuple[Path, Path]:
    headers = ["effect_id", "yi", "outcome"]
    reviewer_a = work / "reviewer-a.csv"
    reviewer_b = work / "reviewer-b.csv"
    write_csv(
        reviewer_a,
        headers,
        [{"effect_id": "E1", "yi": "0.20", "outcome": "mortality"}],
    )
    write_csv(
        reviewer_b,
        headers,
        [{"effect_id": "E1", "yi": "0.25", "outcome": "mortality"}],
    )
    return reviewer_a, reviewer_b


def reconcile_command(
    reviewer_a: Path,
    reviewer_b: Path,
    output: Path,
    ledger: Path | None = None,
) -> list[str | Path]:
    command: list[str | Path] = [
        PYTHON,
        SCRIPTS / "reconcile_extractions.py",
        reviewer_a,
        reviewer_b,
        "--output",
        output,
    ]
    if ledger is not None:
        command += ["--resolution-ledger", ledger]
    return command


@register("reconcile_difference_detected")
def reconcile_difference_detected(work: Path) -> None:
    reviewer_a, reviewer_b = extraction_pair(work)
    output = work / "comparison.csv"
    result = run(reconcile_command(reviewer_a, reviewer_b, output), expected=3)
    payload = json.loads(result.stderr)
    if payload["substantive_differences"] != 1 or payload["unresolved_substantive_differences"] != 1:
        raise TestFailure("reconciler did not expose exactly one unresolved substantive difference")
    differences = [row for row in read_csv(output) if row["is_substantive"] == "yes"]
    if len(differences) != 1 or differences[0]["difference_type"] != "numeric_difference":
        raise TestFailure("reconciler did not classify the numeric extraction difference")


@register("reconcile_missing_adjudication_reject")
def reconcile_missing_adjudication_reject(work: Path) -> None:
    reviewer_a, reviewer_b = extraction_pair(work)
    ledger = work / "unresolved-ledger.csv"
    run(reconcile_command(reviewer_a, reviewer_b, ledger), expected=3)
    output = work / "must-not-exist.csv"
    result = run(
        reconcile_command(reviewer_a, reviewer_b, output, ledger), expected=1
    )
    assert_contains(result, "UNRESOLVED_DIFFERENCE", "resolution_status=resolved")
    if output.exists():
        raise TestFailure("invalid adjudication ledger published a validated comparison")


@register("reconcile_complete_adjudication_pass")
def reconcile_complete_adjudication_pass(work: Path) -> None:
    reviewer_a, reviewer_b = extraction_pair(work)
    comparison = work / "comparison.csv"
    run(reconcile_command(reviewer_a, reviewer_b, comparison), expected=3)
    headers, rows = read_csv_table(comparison)
    for row in rows:
        if row["is_substantive"] == "yes":
            row["resolution_status"] = "resolved"
            row["final_value"] = row["reviewer_a_value"] or "__MISSING__"
            row["evidence"] = "Table 2, row E1, independently checked"
            row["adjudicator"] = "Reviewer C"
            row["adjudication_date"] = yesterday()
    ledger = work / "resolved-ledger.csv"
    write_csv(ledger, headers, rows)
    output = work / "validated-comparison.csv"
    result = run(reconcile_command(reviewer_a, reviewer_b, output, ledger))
    payload = json.loads(result.stdout)
    if not payload["resolution_ledger_validated"] or payload["unresolved_substantive_differences"] != 0:
        raise TestFailure("completed human adjudication was not validated")
    unresolved = [
        row
        for row in read_csv(output)
        if row["is_substantive"] == "yes" and row["resolution_status"] != "resolved"
    ]
    if unresolved:
        raise TestFailure("validated comparison retained unresolved substantive differences")


def study_map_row(study_id: str, report_id: str) -> dict[str, str]:
    return {
        "schema_version": "1.0.0",
        "study_id": study_id,
        "report_id": report_id,
        "report_role": "primary",
        "is_primary_report": "yes",
        "source_type": "journal_article",
        "source_locator": f"doi:10.0000/{report_id.lower()}",
        "mapping_evidence": "Unique registry and site identifiers match",
        "multi_study_reason": "",
        "overlap_status": "none",
        "overlap_with_report_ids": "",
        "overlap_evidence": "",
        "overlap_resolution": "",
        "reviewer_1": "Reviewer A",
        "reviewer_2": "Reviewer B",
        "adjudicator": "",
        "decision_date": yesterday(),
        "notes": "",
    }


@register("study_map_valid_pass")
def study_map_valid_pass(work: Path) -> None:
    headers, _ = asset_table("study_report_map_template.csv")
    source = work / "study-map.csv"
    report = work / "study-map.validation.json"
    write_csv(source, headers, [study_map_row("S1", "R1"), study_map_row("S2", "R2")])
    result = run(
        [
            PYTHON,
            SCRIPTS / "validate_study_map.py",
            source,
            "--json-report",
            report,
        ]
    )
    payload = json.loads(result.stdout)
    if payload["status"] != "ok" or payload["studies"] != 2 or payload["reports"] != 2:
        raise TestFailure("valid study-report map returned an unexpected summary")
    if json.loads(report.read_text(encoding="utf-8"))["summary"]["errors"] != 0:
        raise TestFailure("valid study-report JSON report contains errors")


@register("study_map_unresolved_overlap_reject")
def study_map_unresolved_overlap_reject(work: Path) -> None:
    headers, _ = asset_table("study_report_map_template.csv")
    row = study_map_row("S1", "R1")
    row["overlap_status"] = "unresolved"
    source = work / "study-map-unresolved.csv"
    write_csv(source, headers, [row])
    result = run([PYTHON, SCRIPTS / "validate_study_map.py", source], expected=1)
    assert_contains(result, "UNRESOLVED_OVERLAP", "blocks synthesis")


@register("study_map_report_multimap_reject")
def study_map_report_multimap_reject(work: Path) -> None:
    headers, _ = asset_table("study_report_map_template.csv")
    first = study_map_row("S1", "R1")
    second = study_map_row("S2", "R1")
    second["source_locator"] = first["source_locator"]
    source = work / "study-map-multimap.csv"
    write_csv(source, headers, [first, second])
    result = run([PYTHON, SCRIPTS / "validate_study_map.py", source], expected=1)
    assert_contains(result, "UNEXPLAINED_MULTI_STUDY_REPORT", "reason on every mapping row")


def risk_of_bias_row() -> dict[str, str]:
    return {
        "schema_version": "1.0.0",
        "appraisal_type": "risk_of_bias",
        "study_id": "S1",
        "result_id": "S1__mortality__12m",
        "domain_id": "D1",
        "domain_label": "Randomization process",
        "tool_name": "RoB 2",
        "tool_version": "22 Aug 2019",
        "tool_variant": "individual parallel trial",
        "supporting_source_id": "R1",
        "supporting_locator": "Protocol page 4 and report page 7",
        "supporting_evidence": "Sequence generation and allocation concealment were documented",
        "reviewer_1": "Reviewer A",
        "judgement_1": "low risk",
        "rationale_1": "Documented sequence and concealment support the judgement",
        "reviewer_2": "Reviewer B",
        "judgement_2": "low risk",
        "rationale_2": "Independent review found the same documented safeguards",
        "adjudication_status": "agreement",
        "adjudicator": "",
        "adjudication_date": "",
        "adjudication_rationale": "",
        "final_domain_judgement": "low risk",
        "final_domain_rationale": "Both reviewers confirmed the source evidence",
        "overall_judgement": "low risk",
        "overall_rationale": "All assessed domains were human-confirmed as low risk",
        "human_final_confirmed": "yes",
        "final_decider": "Reviewer C",
        "final_decision_date": yesterday(),
        "automation_used": "no",
        "automation_role": "none",
        "notes": "",
    }


@register("risk_of_bias_complete_pass")
def risk_of_bias_complete_pass(work: Path) -> None:
    headers, _ = asset_table("risk_of_bias_template.csv")
    source = work / "risk-of-bias.csv"
    report = work / "risk-of-bias.validation.json"
    write_csv(source, headers, [risk_of_bias_row()])
    result = run(
        [
            PYTHON,
            SCRIPTS / "validate_appraisal.py",
            "risk-of-bias",
            source,
            "--json-report",
            report,
        ]
    )
    payload = json.loads(result.stdout)
    if payload["status"] != "ok" or payload["automatic_final_judgements"]:
        raise TestFailure("complete human-final risk-of-bias ledger did not validate")


@register("risk_of_bias_score_reject")
def risk_of_bias_score_reject(work: Path) -> None:
    headers, _ = asset_table("risk_of_bias_template.csv")
    row = risk_of_bias_row()
    row["quality_score"] = "5"
    source = work / "risk-of-bias-score.csv"
    write_csv(source, [*headers, "quality_score"], [row])
    result = run(
        [PYTHON, SCRIPTS / "validate_appraisal.py", "risk-of-bias", source],
        expected=1,
    )
    assert_contains(result, "SCORING_COLUMN_FORBIDDEN", "quality_score")


def certainty_row() -> dict[str, str]:
    return {
        "schema_version": "1.0.0",
        "appraisal_type": "certainty",
        "evidence_body_id": "EB1",
        "population": "Adults with the target condition",
        "comparison": "Intervention versus comparator",
        "outcome": "Mortality",
        "time_horizon": "12 months",
        "estimand": "Risk ratio for assignment effect",
        "domain_id": "risk_of_bias",
        "domain_label": "Risk of bias",
        "tool_name": "GRADE",
        "tool_version": "GRADE Book accessed 2026-08-02",
        "tool_variant": "intervention effects",
        "supporting_source_id": "EB1-RoB-summary",
        "supporting_locator": "Evidence profile, risk-of-bias footnote 1",
        "supporting_evidence": "Most weight came from human-confirmed low-risk results",
        "reviewer_1": "Reviewer A",
        "judgement_1": "not serious",
        "rationale_1": "Sensitivity analysis did not cross the decision threshold",
        "reviewer_2": "Reviewer B",
        "judgement_2": "not serious",
        "rationale_2": "Independent assessment reached the same threshold judgement",
        "adjudication_status": "agreement",
        "adjudicator": "",
        "adjudication_date": "",
        "adjudication_rationale": "",
        "final_domain_judgement": "not serious",
        "final_domain_rationale": "Both reviewers agreed using the cited evidence profile",
        "starting_certainty": "high",
        "final_certainty": "moderate",
        "final_certainty_rationale": "One prespecified downgrade in another domain was human-confirmed",
        "human_final_confirmed": "yes",
        "final_decider": "Reviewer C",
        "final_decision_date": yesterday(),
        "automation_used": "no",
        "automation_role": "none",
        "notes": "",
    }


@register("certainty_missing_rationale_reject")
def certainty_missing_rationale_reject(work: Path) -> None:
    headers, _ = asset_table("certainty_template.csv")
    valid = work / "certainty-valid.csv"
    valid_report = work / "certainty-valid.validation.json"
    write_csv(valid, headers, [certainty_row()])
    valid_result = run(
        [
            PYTHON,
            SCRIPTS / "validate_appraisal.py",
            "certainty",
            valid,
            "--json-report",
            valid_report,
        ]
    )
    if json.loads(valid_result.stdout)["status"] != "ok":
        raise TestFailure("valid certainty baseline did not pass before the negative test")

    invalid_row = certainty_row()
    invalid_row["final_certainty_rationale"] = ""
    invalid = work / "certainty-missing-rationale.csv"
    write_csv(invalid, headers, [invalid_row])
    result = run(
        [PYTHON, SCRIPTS / "validate_appraisal.py", "certainty", invalid],
        expected=1,
    )
    assert_contains(result, "final_certainty_rationale", "MISSING_VALUE")


def load_scenarios() -> list[dict[str, str]]:
    payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if payload.get("schema_version") != "1.0" or not isinstance(cases, list):
        raise TestFailure("p1_scenarios.json does not match schema version 1.0")
    if len(cases) != 31:
        raise TestFailure(f"expected 31 registered P1 scenarios, found {len(cases)}")
    ids = [item.get("id") for item in cases]
    if any(not isinstance(case_id, str) or not case_id for case_id in ids):
        raise TestFailure("every P1 scenario must have a non-empty string id")
    if len(set(ids)) != len(ids):
        raise TestFailure("p1_scenarios.json contains duplicate case ids")
    for item in cases:
        if item.get("expected") not in {"pass", "reject"}:
            raise TestFailure(f"invalid expected value for {item.get('id')}")
        if not isinstance(item.get("module"), str) or not item["module"]:
            raise TestFailure(f"invalid module for {item.get('id')}")
    registered = set(CASE_FUNCTIONS)
    declared = set(ids)
    if registered != declared:
        raise TestFailure(
            "case registration mismatch: "
            f"missing implementations={sorted(declared - registered)}, "
            f"unregistered implementations={sorted(registered - declared)}"
        )
    return cases


def preflight() -> str:
    if not R_SCRIPT.is_file():
        raise TestFailure(f"Rscript was not found: {R_SCRIPT}")
    result = run(
        [
            R_SCRIPT,
            "-e",
            "stopifnot(requireNamespace('metafor', quietly=TRUE)); "
            "stopifnot(packageVersion('metafor') >= '5.0.1'); "
            "stopifnot(requireNamespace('jsonlite', quietly=TRUE)); "
            "cat(as.character(packageVersion('metafor')), "
            "as.character(packageVersion('jsonlite')), sep='|')",
        ]
    )
    versions = result.stdout.strip()
    if "|" not in versions:
        raise TestFailure("R dependency probe did not return metafor and jsonlite versions")
    return versions


def main() -> int:
    scenarios = load_scenarios()
    temporary_parent = SCRATCH_ROOT if SCRATCH_ROOT is not None and SCRATCH_ROOT.is_dir() else None
    with tempfile.TemporaryDirectory(
        prefix="easymeta-p1-tests-",
        dir=str(temporary_parent) if temporary_parent is not None else None,
    ) as temporary:
        suite_root = Path(temporary)
        CURRENT_COMMANDS.clear()
        versions = preflight()
        results: list[tuple[str, str | None]] = []
        recorded: set[str] = set()
        for index, scenario in enumerate(scenarios, start=1):
            case_id = scenario["id"]
            if case_id in recorded:
                raise TestFailure(f"case id would be recorded more than once: {case_id}")
            recorded.add(case_id)
            case_work = suite_root / f"case-{index:02d}"
            case_work.mkdir()
            CURRENT_COMMANDS.clear()
            try:
                CASE_FUNCTIONS[case_id](case_work)
            except Exception as exc:  # continue so every declared case is recorded exactly once
                results.append((case_id, f"{exc}\n{command_trace()}"))
            else:
                results.append((case_id, None))

        if recorded != {scenario["id"] for scenario in scenarios} or len(results) != len(scenarios):
            raise TestFailure("internal error: not every JSON case id was recorded exactly once")

        for case_id, error in results:
            if error is None:
                print(f"[PASS] {case_id}")
            else:
                print(f"[FAIL] {case_id}")
                print("\n".join(f"  {line}" for line in error.splitlines()))

        failures = [case_id for case_id, error in results if error is not None]
        if failures:
            print(
                f"FAIL: {len(failures)}/31 P1 cases failed; R packages={versions}",
                file=sys.stderr,
            )
            return 1

        location = str(temporary_parent) if temporary_parent is not None else "system temp"
        print(
            f"PASS: all 31 P1 end-to-end cases; R packages={versions}; "
            f"temporary workspace={location} (cleaned automatically)"
        )
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TestFailure as exc:
        print(f"FAIL: {exc}\n{command_trace()}", file=sys.stderr)
        raise SystemExit(1)
