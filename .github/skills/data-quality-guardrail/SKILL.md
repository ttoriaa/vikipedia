---
name: data-quality-guardrail
description: "Validate pipeline inputs/outputs against required schema, null thresholds, and anomaly rules before report publish. Use when you need data gate checks, schema drift detection, or publish blocking by quality."
argument-hint: "optional args: input=<path>, profile=<name>, date=YYYY-MM-DD, block_on_warn=true|false"
user-invocable: true
disable-model-invocation: false
---

# Data Quality Guardrail

## Purpose
Prevent bad data from entering daily reports by enforcing deterministic quality gates before downstream generation and publishing.

## Trigger Conditions
- A daily pipeline run is about to generate report artifacts.
- Upstream source has changed schema/field names.
- Unexpected KPI spike/drop requires anomaly confirmation.

## Inputs
- input (required): CSV or JSON file path to validate.
- profile (optional): Rule profile name. Default: `dongchedi_daily_default`.
- date (optional): Business date used for baseline comparison.
- block_on_warn (optional, default true): Treat warning-level checks as blocking.

## Output Contract
Each run must return:
- run_id
- input path and profile
- check summary: pass_count, warn_count, fail_count
- failed checks with row/field evidence
- decision: pass | warn | block
- next_action list

## Evaluation Metrics
- schema_coverage: required fields present ratio.
- null_rate_by_field: null ratio per critical field.
- duplicate_key_rate: duplicates over business key.
- range_violation_rate: percentage outside allowed bounds.
- anomaly_zscore_max: largest standardized deviation vs baseline.
- freshness_hours: data staleness from expected timestamp.

## Failure Handling
- Missing input file:
  - Stop and return `ERR_INPUT_NOT_FOUND`.
- Unsupported format:
  - Stop and return `ERR_UNSUPPORTED_FORMAT` with accepted formats.
- Missing profile:
  - Fallback to default profile and emit warning.
- Baseline unavailable:
  - Skip anomaly checks and mark as `warn`.
- Blocking failures found:
  - Return `decision=block` and a remediation checklist.

## Procedure
1. Load input data and validation profile.
2. Validate schema and required fields.
3. Run content checks: nulls, duplicates, ranges, enum domain.
4. Run baseline anomaly checks when historical data exists.
5. Score severity and compute final decision.
6. Emit machine-readable result for pipeline gates.

## Minimum Runnable Example
### Profile example (`reports/quality/profiles/dongchedi_daily_default.json`)
```json
{
  "required_fields": ["car_model", "price", "range_km", "charge_time_min"],
  "key_fields": ["car_model", "config_id"],
  "ranges": {
    "price": [50000, 2000000],
    "range_km": [50, 1200],
    "charge_time_min": [5, 1000]
  },
  "null_threshold": {
    "price": 0.01,
    "range_km": 0.05
  }
}
```

### Run command example
```powershell
./.venv/Scripts/python.exe ./scripts/quality/run_quality_gate.py --input reports/dongchedi_daily/2026-07-07/merged.csv --profile dongchedi_daily_default --date 2026-07-07
```

### Expected minimal output example
```json
{
  "run_id": "dq-20260707-001",
  "summary": {"pass": 18, "warn": 1, "fail": 0},
  "decision": "pass",
  "failed_checks": []
}
```

## Safety Notes
- Block publish when critical fields fail threshold.
- Keep rule profiles versioned and auditable.
- Record every override with reason and operator.
