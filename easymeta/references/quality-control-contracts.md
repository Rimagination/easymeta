# P1-4/P1-5 quality-control contracts

These contracts turn study identity, double extraction, risk of bias, and certainty into blocking, auditable data gates. They are deliberately generic: they do not reproduce any tool's signalling questions, and the scripts never make scientific judgements.

## 1. Shared rules

- Use UTF-8 CSV. Inputs may contain a UTF-8 BOM; generated CSV and JSON are UTF-8 without a BOM.
- Keep identifiers stable. Do not trim or silently repair `effect_id`, `study_id`, `report_id`, `result_id`, or `evidence_body_id` after publication.
- Treat every output path as new. The scripts publish complete files atomically and refuse to replace an existing path.
- Interpret exit `0` as a passed gate, `1` as a data/contract failure, and `2` as a usage, encoding, CSV, path, or output failure. `reconcile_extractions.py` additionally returns `3` after writing a comparison with unresolved substantive differences.
- An automated check may expose omissions and contradictions. It may not select a final extracted value, assign a risk-of-bias judgement, calculate a quality score, or upgrade/downgrade certainty.

## 2. Double extraction and adjudication

Start with two genuinely independent extraction CSVs. Each must contain exactly one row per nonblank `effect_id`; all other columns are compared. The comparator uses the union of both header sets, so a field omitted by one reviewer remains visible.

Run:

```bash
python scripts/reconcile_extractions.py reviewer-a.csv reviewer-b.csv \
  --output extraction-comparison.csv
```

The output contains one row per `effect_id + field`, preserving both literal values. If an entire effect appears on only one side, the reserved field `__record_presence__` records that omission.

Difference types are:

| Type | Meaning | Substantive? |
|---|---|---|
| `exact_match` | Literal values are identical | no |
| `format_difference` | Numeric values are equal despite representation, or normalized text differs only in case/spacing/Unicode form | no |
| `missing_difference` | One side is blank or an effect row is absent | yes |
| `numeric_difference` | Both values are finite numbers and differ | yes |
| `text_difference` | Other literal disagreement; the script does not claim whether meanings differ | yes |

The script never chooses a winner. When substantive differences exist it writes the comparison and exits `3`.

### Resolution ledger

Copy the generated comparison to a new ledger path and preserve every row and all source columns. For each substantive row only:

1. change `resolution_status` from `unresolved` to `resolved`;
2. enter `final_value` (`__MISSING__` means a human intentionally adjudicated an absent value);
3. enter precise `evidence`, such as report/table/figure/page/cell or author-response location;
4. enter the human `adjudicator` and canonical `adjudication_date` (`YYYY-MM-DD`).

Keep exact and format-only rows as `not_required` with blank resolution fields. Validate the completed ledger against the current two extractions and write a separate audit output:

```bash
python scripts/reconcile_extractions.py reviewer-a.csv reviewer-b.csv \
  --resolution-ledger extraction-resolution.csv \
  --output extraction-comparison-validated.csv
```

The ledger must contain every current comparison cell exactly once. Reviewer values, difference type, identifiers, and difference ID must match literally; this prevents a stale ledger from resolving changed input. A valid ledger is an audit record, not a curated effect table. Apply final values to curated data in a separate, reviewed transformation.

Use `assets/extraction_adjudication_template.csv` as the header contract. In practice the first comparison output is the safest ledger starting point because it already contains all required cells.

## 3. Study-report map

Use `assets/study_report_map_template.csv` before extraction. One row maps one `report_id` to one `study_id`.

Run:

```bash
python scripts/validate_study_map.py study-report-map.csv \
  --json-report study-report-map-validation.json
```

Required gates:

- Each row identifies a source through both `source_type` and `source_locator`, and explains the mapping in `mapping_evidence`.
- Each study has exactly one row with `is_primary_report=yes` and `report_role=primary`.
- A `report_id` mapped to multiple studies has the same nonblank `multi_study_reason` on every mapping row. This supports one article that explicitly reports multiple distinct experiments; it is not permission to split an overlapping cohort without evidence.
- `overlap_status=unresolved` always fails.
- `resolved_same_study` and `resolved_distinct_studies` require semicolon-separated `overlap_with_report_ids`, evidence, a resolution, and an adjudicator. Referenced reports must exist in the map, and the declared same/distinct relation must agree with their study mappings.
- `overlap_status=none` requires blank overlap-detail fields.
- `reviewer_1` and `reviewer_2` identify different humans; `decision_date` is a non-future ISO date.

The validator does not infer study identity from author names, dates, sample sizes, sites, registrations, or titles. Ambiguity remains unresolved until humans document it.

## 4. Risk-of-bias ledger

Use `assets/risk_of_bias_template.csv`. The unit is a specific `result_id`, not an article or study as a whole. Store one row per generic appraisal domain.

```bash
python scripts/validate_appraisal.py risk-of-bias risk-of-bias.csv \
  --json-report risk-of-bias-validation.json
```

Every domain row requires:

- `study_id`, `result_id`, generic `domain_id`/`domain_label`, and selected `tool_name`, `tool_version`, and optional `tool_variant`;
- an auditable `supporting_source_id`, `supporting_locator`, and short evidence excerpt/paraphrase;
- two different reviewers, each with an independent named judgement and rationale;
- `adjudication_status=agreement` when judgements match, or `adjudicated` plus adjudicator/date/rationale when they differ;
- a human-final domain judgement and rationale;
- one consistent result-level `overall_judgement` and `overall_rationale` across all domains;
- `human_final_confirmed=yes`, a final human decider, and final decision date.

The schema records domain evidence but contains no tool signalling questions. Open and complete the current licensed/official tool separately; keep that source artifact under its applicable licence.

## 5. Certainty ledger

Use `assets/certainty_template.csv`. The unit is an `evidence_body_id` defined by population, comparison/exposure, outcome, time horizon, and estimand. Store one row per generic certainty domain.

```bash
python scripts/validate_appraisal.py certainty certainty.csv \
  --json-report certainty-validation.json
```

The same evidence-body identity, tool/framework version, starting certainty, final certainty, final rationale, and final human decision metadata must repeat consistently across its domain rows. Each domain requires localized support, two independent judgements and rationales, adjudication when they differ, and a human-final domain judgement.

The validator does not calculate the final certainty from domain rows. It does not infer a starting level, count downgrades, apply upgrade rules, or reconcile double counting. Those are documented human decisions made under the selected current framework.

## 6. Forbidden automation and scoring

Both appraisal schemas reject score/point/quality-weight columns and numeric-only judgements. Columns that copy signalling questions are also rejected. Do not convert domain categories to numbers, sum them, weight Meta-analysis by a quality score, or define arbitrary cutoffs.

Record `automation_used=no, automation_role=none` when no automation assisted. If automation helped locate text or flag contradictions, record `automation_used=yes, automation_role=support_only`. Any other automation role fails. `human_final_confirmed=yes` is mandatory but remains an auditable assertion; accountable reviewers must verify it.

JSON validation reports are optional. When requested, they are written even for a contract failure, provided the output target is new and writable. Existing reports are never replaced.
