---
name: source-reliability-retry-orchestrator
description: "Coordinate multi-source fetch with tiered retries, fallback sources, and evidence reliability scoring. Use when you need resilient data collection, timeout recovery, or source failover orchestration."
argument-hint: "optional args: task=<name>, date=YYYY-MM-DD, retry_policy=<name>, max_retries=3, timeout_sec=30"
user-invocable: true
disable-model-invocation: false
---

# Source Reliability & Retry Orchestrator

## Purpose
Increase collection success rate with deterministic retries, fallback routing, and transparent reliability logs.

## Trigger Conditions
- Direct fetch failed due to timeout, 429, or transient 5xx.
- Daily collection must complete before report deadline.
- Multiple equivalent sources exist and need priority routing.

## Inputs
- task (required): Collection task id, for example `daily_market_news`.
- date (optional): Business date for output partition.
- retry_policy (optional): Policy name. Default: `standard_web_fetch_v1`.
- max_retries (optional, default 3): Retry attempts per source.
- timeout_sec (optional, default 30): Timeout per request.

## Output Contract
Each run must return:
- run_id
- source attempt timeline
- success/failure by source
- reliability scores by source
- final selected evidence set
- decision: complete | partial | failed
- next_action list

## Evaluation Metrics
- source_success_rate: successful sources over attempted sources.
- retry_recovery_rate: failures recovered via retry/fallback.
- median_fetch_latency_ms: median fetch latency.
- evidence_completeness: required topics covered ratio.
- reliability_weighted_score: confidence-weighted aggregate score.
- final_failure_count: unresolved source failures.

## Failure Handling
- All primary sources fail:
  - Route to fallback sources and mark confidence downgrade.
- Rate limit encountered:
  - Apply backoff and jitter; cap retries; preserve partial outputs.
- Parser failure for fetched content:
  - Store raw body for forensic trace and continue with other sources.
- No usable evidence after retries:
  - Return `decision=failed` with unresolved source list.
- Partial evidence only:
  - Return `decision=partial` and block publish if strict mode is enabled.

## Procedure
1. Load source registry and retry policy.
2. Attempt primary sources in priority order.
3. On retryable errors, apply backoff and retry until `max_retries`.
4. On hard failures, switch to fallback sources.
5. Normalize and score evidence reliability.
6. Aggregate results and determine final decision.
7. Emit artifacts: raw logs, normalized evidence, summary report.

## Minimum Runnable Example
### Retry policy example (`reports/fetch/policies/standard_web_fetch_v1.json`)
```json
{
  "retryable_status": [408, 425, 429, 500, 502, 503, 504],
  "backoff_seconds": [1, 3, 8],
  "source_priority": ["official_site", "exchange", "newswire", "backup_feed"],
  "strict_mode": false
}
```

### Run command example
```powershell
./.venv/Scripts/python.exe ./scripts/fetch/run_orchestrator.py --task daily_market_news --date 2026-07-07 --retry-policy standard_web_fetch_v1 --max-retries 3 --timeout-sec 30
```

### Expected minimal output example
```json
{
  "run_id": "src-20260707-001",
  "decision": "complete",
  "source_success_rate": 0.83,
  "retry_recovery_rate": 0.5,
  "final_failure_count": 1
}
```

## Safety Notes
- Keep raw failure logs for postmortem and tuning.
- Do not silently drop failed sources without trace.
- Mark confidence downgrade whenever fallback dominates.
