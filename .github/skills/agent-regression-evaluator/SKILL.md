---
name: agent-regression-evaluator
description: "Evaluate prompt and agent quality with a fixed benchmark set, score deltas, and failure clustering. Use when you need prompt regression test, quality drift detection, or evaluation before deploy."
argument-hint: "optional args: benchmark=<path>, candidate=<id>, baseline=<id>, max_cases=50, fail_fast=true|false"
user-invocable: true
disable-model-invocation: false
---

# Agent Regression Evaluator

## Purpose
Run repeatable regression tests for agent/prompt changes and block low-quality releases with explicit score deltas.

## Trigger Conditions
- A prompt/skill/agent file changed and needs pre-release verification.
- A scheduled daily or weekly quality health check is required.
- User feedback indicates quality drift and you need reproducible evidence.

## Inputs
- benchmark (optional): Path to benchmark dataset. Default: `reports/evals/benchmarks/default_cases.jsonl`.
- candidate (required): Candidate prompt or agent version id.
- baseline (optional): Baseline version id. If omitted, use latest stable tag.
- max_cases (optional, default 50): Max samples to evaluate.
- fail_fast (optional, default false): Stop once blocking threshold is reached.

## Output Contract
Each run must return:
- run_id
- benchmark path and sample count
- candidate and baseline ids
- aggregate metrics with delta
- top failure clusters
- release_decision: pass | warn | block
- next_action list

## Evaluation Metrics
- pass_rate: fraction of cases that satisfy all required assertions.
- factuality_score: evidence-grounded correctness score (0-100).
- format_compliance: schema/structure compliance rate.
- latency_p95_ms: 95th percentile runtime.
- token_cost_per_case: average tokens per sample.
- regression_delta: candidate minus baseline for key metrics.

## Failure Handling
- Missing benchmark:
  - Stop and return `ERR_BENCHMARK_NOT_FOUND` with expected path.
- Candidate execution error:
  - Mark case as failed, collect stderr, continue unless `fail_fast=true`.
- Baseline unavailable:
  - Continue in single-version mode and set delta fields to `null`.
- Metric parser failure:
  - Return `ERR_METRIC_PARSE` and include offending sample id.
- Blocking regression:
  - Return `release_decision=block` and list top 3 actionable fixes.

## Procedure
1. Resolve candidate/baseline ids and benchmark path.
2. Validate benchmark readability and sample schema.
3. Execute candidate on sampled cases and collect raw outputs.
4. Execute baseline on same sampled cases when available.
5. Score outputs and compute aggregate metrics.
6. Compute metric deltas and identify failure clusters.
7. Apply gating thresholds and return release decision.

## Minimum Runnable Example
### Dataset example (`reports/evals/benchmarks/default_cases.jsonl`)
```json
{"id":"c1","input":"Summarize this note in 2 bullets","must_include":["action"],"forbidden":[]}
{"id":"c2","input":"Return JSON with fields title and score","schema":{"title":"string","score":"number"}}
```

### Run command example
```powershell
./.venv/Scripts/python.exe ./scripts/evals/run_regression.py --benchmark reports/evals/benchmarks/default_cases.jsonl --candidate prompt_v3 --baseline prompt_v2 --max-cases 20
```

### Expected minimal output example
```json
{
  "run_id": "eval-20260707-001",
  "sample_count": 20,
  "metrics": {
    "pass_rate": 0.9,
    "factuality_score": 88.0,
    "format_compliance": 0.95,
    "latency_p95_ms": 1800
  },
  "delta_vs_baseline": {
    "pass_rate": 0.05,
    "factuality_score": 2.0
  },
  "release_decision": "pass"
}
```

## Safety Notes
- Never replace baseline without an explicit changelog entry.
- Keep benchmark stable across runs when comparing deltas.
- Do not publish candidate if `release_decision=block`.
