# Implementation Plan PRO-375: Refactor CI Timing Measurement Pipeline — JSON Output & Data Validation

**Status:** ✅ Done  
**Epic Link:** PRO-259  
**Parent:** PRO-259 (In Arbeit)  
**Fix Version:** v4.4.0  
**Priority:** Medium  
**Story Points:** 8  

---

## Background

PRO-368 (Optimize Python CI Workflow Performance and Maintainability) implemented CI optimization foundation and identified O8 — Continuous CI timing benchmark. PRO-369 (Implement Continuous CI Timing Measurement and Historical Aggregation) completed the collection and aggregation pipeline, producing `ci-timings.csv` on the orphan `ci-metrics` branch and `CI_TIMING_REPORT.md`.

PRO-379 (dashboard) and PRO-380 (statistics) depend on structured JSON data — CSV-only output limits consumer flexibility. This ticket refactors the pipeline to produce machine-readable JSON alongside CSV, stores data in a top-level `data/` folder on master as the sole source of truth, and preserves all data perspectives (job, PR, branch).

**Architecture:** See `doc/03_Architecture_PRO-375.md` for detailed technical design.

## Goal

Refactor the CI timing data collection pipeline to produce structured JSON:

1. `data/runtimes.json` — raw per-run timing data alongside CSV
2. `data/metrics.json` — aggregated statistics with ready/withheld buckets
3. `data/` on master = final and sole source of truth
4. All data perspectives preserved: job, PR, branch
5. Maintain non-gating invariant (never fails CI, never writes to PR branch)
6. Three-phase migration: parallel → verify → decommission ci-metrics branch

## Scope

### In Scope

- Add `write_json()` to `collect_ci_timings.py` — emit `data/runtimes.json` with `schema_version: "v1.0"`
- Add `write_metrics()` to `aggregate_ci_timings.py` — emit `data/metrics.json` with statistics
- Add schema validation (`validate_json()`) using stdlib
- Add `branch` field to all timing records for branch perspective
- Update `ci-timing.yml` to commit both CSV + JSON files to ci-metrics branch AND data/ folder on master
- Migrate existing ci-metrics branch CSV data to `data/` on master
- Add unit tests for JSON output, schema validation, and migration
- Three-phase migration strategy (parallel → verify → decommission)

### Out of Scope

- Phase 3 decommission of ci-metrics branch (follow-up PR after Phase 2 verification)
- Dashboard/visualization (that's PRO-379)
- Rolling statistics, Bollinger bands, or distribution curves (that's PRO-380)
- GitHub Pages deployment
- Modifying `aggregate_ci_timings.py` existing `aggregate()` logic (only add JSON output)

## Implementation Plan

### Phase 1: Scripts + Tests + JSON Output (Rollout Step 1)

**Files:**
- `.github/scripts/collect_ci_timings.py` — Add `write_json()` method
- `.github/scripts/aggregate_ci_timings.py` — Add `write_metrics()` method
- `.github/scripts/validator.py` — NEW: `validate_json()` function for schema validation
- `.github/tests/ci-pipeline/test_collect_ci_timings.py` — Add JSON output tests
- `.github/tests/ci-pipeline/test_aggregate_ci_timings.py` — Add metrics JSON tests
- `.github/tests/ci-pipeline/test_validator.py` — NEW: schema validation tests

**Changes:**
1. Add `write_json(rows, run_meta, path)` to `collect_ci_timings.py`:
   - Read existing `data/runtimes.json` if exists
   - Append new run data (deduplicate by run_id + job + step)
   - Write back with `schema_version: "v1.0"` wrapper
2. Add `write_metrics(agg_data, path)` to `aggregate_ci_timings.py`:
   - Call existing `aggregate()` function
   - Format output with ready/withheld buckets
   - Write JSON with `schema_version: "v1.0"` wrapper
3. Create `validator.py` with `validate_json(data: dict) -> list[str]`:
   - Required root keys: `schema_version, generated_at, runs`
   - Required run keys: `run_id, run_attempt, pr_number, job_name, step_name, step_number, duration_s, conclusion`
   - Type checks: `duration_s` numeric, `schema_version` == `"v1.0"`
4. Add `branch` field to all timing records in `extract_rows()`
5. Add unit tests for all new functions

**Gate:** All unit tests pass (`.github/tests/ci-pipeline/` gate), ruff + black + pydocstyle clean, ≥90% coverage on new functions.

### Phase 2: Workflow + Dual Storage (Rollout Step 2)

**Files:**
- `.github/workflows/ci-timing.yml` — Update to write to both ci-metrics branch AND data/ folder on master
- `.github/scripts/backfill_ci_timings.py` — Add migration capability
- `data/` — NEW: top-level folder with `runtimes.json` and `metrics.json` on master branch

**Changes:**
1. Update `ci-timing.yml`:
   - Continuous trigger (`workflow_run`) writes to ci-metrics branch only (safety)
   - `workflow_dispatch` with `update_data=true` writes to both ci-metrics AND data/ on master
   - Separate commit step for master data/ folder
   - Safety gate prevents runaway loops
2. Add migration step to `backfill_ci_timings.py`:
    - Read existing `ci-timings.csv` from ci-metrics branch
    - Convert to `data/runtimes.json` format
    - Validate row counts match, no data loss
    - Extract feature branch info from historical runs via GitHub API
    - Support `--since-run-id` and `--since-date` to start from a specific starting point
3. Create `data/` folder structure on master branch

**Gate:** Workflow YAML valid, `workflow_dispatch` writes to both branches, data/ folder populated, validation passes.

### Phase 3: Verification & Migration (Rollout Step 3)

**Gate:** Backfill ci-metrics CSV → data/runtimes.json, validate row counts match, no data loss. User/PO confirms data integrity. Comparison report generated.

**Verification items:**
- Row counts: ci-metrics CSV rows == data/runtimes.json entries
- Field completeness: all CSV fields present in JSON
- No data loss during migration
- `data/metrics.json` matches `CI_TIMING_REPORT.md` statistics
- Backward compatibility: CSV consumers unaffected

### Phase 4: Documentation (Rollout Step 4)

**Files:**
- `AGENTS.md` — Document data/ folder location, non-gating invariant, no-loop invariants
- `doc/CONTRIBUTING.md` — Document data/ folder structure, migration path
- `doc/ARCHITECTURE.md` — Add data storage architecture section
- `doc/REQUIREMENTS.md` — Add FR-XX, QR-XX traceability entries

---

## Data Schema

### `data/runtimes.json` — Raw Per-Run Data

```json
{
  "schema_version": "v1.0",
  "generated_at": "2026-09-14T20:57:40Z",
  "runs": [
    {
      "run_id": 12345,
      "run_attempt": 1,
      "pr_number": 42,
      "head_sha": "abc123",
      "workflow_sha": "def456",
      "branch": "feature/PRO-375",
      "created_at": "2026-09-14T20:00:00Z",
      "job_name": "check",
      "step_name": "Run lint tools",
      "step_number": 2,
      "duration_s": 15.0,
      "conclusion": "success",
      "cache_state": "miss"
    }
  ]
}
```

- **One flat array** with one entry per successful step
- **All CSV fields preserved** plus `branch` added for branch perspective
- **Append-only**, deduplicated by `(run_id, job_name, step_number)`
- **Latest attempt wins** for deduplication

### `data/metrics.json` — Aggregated Statistics

```json
{
  "schema_version": "v1.0",
  "generated_at": "2026-09-14T20:57:40Z",
  "ready": {
    "check / Run lint tools": {
      "n": 128,
      "mean": 12.5,
      "stddev": 2.3,
      "median": 12.1,
      "p95": 18.2,
      "min": 8.1,
      "max": 25.4,
      "last": 14.2
    }
  },
  "withheld": {
    "test / Slow step": {
      "n": 2,
      "reason": "insufficient_samples",
      "min_samples": 3
    }
  }
}
```

- **Keys:** `n, mean, stddev, median, p95, min, max, last` per `(job_name, step_name)`
- **`ready`** = keys with ≥3 samples
- **`withheld`** = keys below threshold with reason
- **Recomputed from full dataset** on every update (no drift)

### Data Perspectives Preserved

| Perspective | Fields | Example |
|-------------|--------|---------|
| **Per Job** | job_name, step_name, step_number, duration_s | `check / Run lint tools` |
| **Per PR** | run_id, pr_number, head_sha, created_at | `run_id=12345, pr_number=42` |
| **Per Branch** | branch | `branch=feature/PRO-375` |

---

## Migration Strategy (Three Phases)

### Phase 1: Parallel
- `collect_ci_timings.py` writes both CSV (ci-metrics branch) AND JSON (data/ on master)
- `aggregate_ci_timings.py` writes both `data/metrics.json` AND `CI_TIMING_REPORT.md` (ci-metrics)
- Both storage locations active simultaneously
- No breaking changes

### Phase 2: Verification
- Backfill ci-metrics CSV → `data/runtimes.json`
- Validate: row counts match, no data loss
- Generate comparison report
- User/PO confirms data integrity

### Phase 3: Decommission (Follow-up PR)
- Remove CSV writes from `collect_ci_timings.py`
- Remove `CI_TIMING_REPORT.md` from ci-metrics workflow
- Archive ci-metrics branch (read-only)
- `data/` on master = sole source of truth

**Rollback:** ci-metrics branch remains fully functional (Phase 1 design).

---

## Function Specifications

### `write_json(rows, run_meta, path)` — in `collect_ci_timings.py`

```python
def write_json(rows: list[dict], run_meta: dict, path: Path) -> None:
    """Append run data to data/runtimes.json with schema_version v1.0 wrapper."""
    # Read existing JSON if exists
    # Append new runs
    # Deduplicate by (run_id, job_name, step_number)
    # Write back with schema_version: "v1.0" and generated_at
```

### `write_metrics(agg_data, path)` — in `aggregate_ci_timings.py`

```python
def write_metrics(agg_data: dict, path: Path) -> None:
    """Write data/metrics.json with ready/withheld buckets."""
    # Call existing aggregate() function
    # Format output with schema_version: "v1.0" and generated_at
    # Write JSON to path
```

### `validate_json(data: dict) -> list[str]` — in `validator.py`

```python
def validate_json(data: dict) -> list[str]:
    """Validate JSON structure. Returns list of errors (empty = valid)."""
    errors = []
    for key in REQUIRED_ROOT:
        if key not in data:
            errors.append(f"missing root key: {key}")
    if data.get("schema_version") != "v1.0":
        errors.append(f"unsupported schema_version: {data.get('schema_version')}")
    for i, run in enumerate(data.get("runs", [])):
        for key in REQUIRED_RUN:
            if key not in run:
                errors.append(f"run[{i}] missing key: {key}")
        if not isinstance(run.get("duration_s"), (int, float)):
            errors.append(f"run[{i}] duration_s not numeric")
    return errors
```

---

## Validation Rules

- **Required root keys:** `schema_version`, `generated_at`, `runs`
- **Required run keys:** `run_id`, `run_attempt`, `pr_number`, `job_name`, `step_name`, `step_number`, `duration_s`, `conclusion`
- **Type checks:** `duration_s` must be numeric, `schema_version` must be `"v1.0"`
- **Called before writing to disk**, returns list of errors
- **Unit tested** with malformed inputs

---

## Workflow Updates (ci-timing.yml)

- **Continuous trigger (`workflow_run`):** Writes to ci-metrics branch only
- **`workflow_dispatch` with `update_data=true`:** Writes to both ci-metrics AND data/ on master
- **Separate commit step** for master data/ folder
- **Safety gate** prevents runaway loops

---

## Backward Compatibility

- CSV on ci-metrics branch remains unchanged during Phase 1-2
- `aggregate_ci_timings.py` still produces `CI_TIMING_REPORT.md` from CSV
- New JSON outputs are additive, not replacing anything
- Deprecation timeline: 2 releases before CSV deprecation, 3 before removal
- Consumers get 6-month notice before Phase 3 decommission

---

## Testing Strategy

### Unit Tests

- `test_write_json` — JSON output validation, schema compliance
- `test_write_metrics` — metrics.json generation, ready/withheld buckets
- `test_validate_json` — schema validation with malformed inputs
- `test_round_trip` — JSON round-trip integrity
- `test_statistics_computation` — verify n, mean, stddev, median, p95, min, max, last
- `test_branch_field` — branch perspective preserved in all records
- `test_migration` — ci-metrics CSV → data/runtimes.json migration

### Integration Tests

- Full pipeline: collect → aggregate → both CSV + JSON outputs
- Data/ folder populated correctly on master branch
- Both ci-metrics and data/ contain consistent data

### CI Self-Tests

- Extended `.github/tests/ci-pipeline/` gate
- `test_ci_timing_does_not_retrigger_python_ci` — no-loop invariant
- `test_ci_timing_only_writes_to_ci_metrics_branch` — safety gate

---

## Verification Definition

### Phase 1 Gate (Rollout Step 1)
- All unit tests pass
- ruff + black + pydocstyle clean
- ≥90% coverage on new functions
- `validate_json()` catches all malformed inputs

### Phase 2 Gate (Rollout Step 2)
- Workflow YAML valid
- `workflow_dispatch` writes to both branches
- `data/` folder populated with `runtimes.json` and `metrics.json`
- No CI loops introduced

### Phase 3 Gate (Rollout Step 3)
- Row counts match: ci-metrics CSV == data/runtimes.json
- No data loss during migration
- `data/metrics.json` matches `CI_TIMING_REPORT.md` statistics
- User/PO confirms data integrity

### Phase 4 Gate (Rollout Step 4)
- Documentation updated in AGENTS.md, CONTRIBUTING.md, ARCHITECTURE.md
- Traceability entries added to REQUIREMENTS.md, ARCHITECTURE.md

---

## Final Status

**Status:** ✅ Done — all phases complete

- **Phase 1 (Scripts + Tests):** ✅ Done — JSON output, schema validation, and unit tests implemented
- **Phase 2 (Workflow + Dual Storage):** ✅ Done — `ci-timing.yml` generates both CSV and JSON; `data/` folder populated on master
- **Phase 3 (Verification & Migration):** ✅ Done — two-step migration completed; 2,755 CSV rows match JSON exactly; 26 qualifying runs backfilled from GitHub API with branch data
- **Phase 4 (Documentation):** ✅ Done — AGENTS.md, CONTRIBUTING.md, ARCHITECTURE.md, and REQUIREMENTS.md updated

### Acceptance Criteria

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | `collect_ci_timings.py` outputs valid JSON to `data/runtimes.json` alongside CSV | ✅ Complete |
| AC-2 | `aggregate_ci_timings.py` outputs valid `data/metrics.json` with stats per (job, step) | ✅ Complete |
| AC-3 | JSON schema documented with `schema_version: "v1.0"` at root level | ✅ Complete |
| AC-4 | Existing CSV consumers remain unaffected (backward compatibility confirmed) | ✅ Complete |
| AC-5 | Unit tests cover all new JSON output functions with ≥90% coverage | ✅ Complete |
| AC-6 | `ci-timing.yml` generates both CSV and JSON without errors | ✅ Complete |
| AC-7 | Data validation catches malformed or missing fields in output | ✅ Complete |
| AC-8 | Data stored in top-level `data/` folder on master branch | ✅ Complete |
| AC-9 | All data perspectives preserved (job, PR, branch) and usable | ✅ Complete |
| AC-10 | Existing ci-metrics branch CSV data migrated to `data/` on master | ✅ Complete |

### Definition of Done

- [x] All ACs checkmarked
- [x] Story Points: 8 assigned
- [x] PR #117 prepared for merge to master
- [x] CI self-tests: 139 passed
- [x] Application tests: 150 passed (99.71% coverage)
- [x] Lint checks: ruff, black, pydocstyle, radon
- [x] Traceability: 100%
- [x] JIRA PRO-375 prepared for transition to Fertig

### Test Results

- Application tests: 150 passed (99.71% coverage, gate: 90%)
- CI self-tests: 139 passed (100%)
- Traceability: 100%
- Lint: ruff, black, pydocstyle all clean
- Data validation: 0 errors in `data/runtimes.json` and `data/metrics.json`
- Migration: 2,755 CSV rows == 2,755 JSON rows (exact match)

---

## References

- [PRO-368](https://mainhatten.atlassian.net/browse/PRO-368): Optimize Python CI Workflow Performance and Maintainability
- [PRO-369](https://mainhatten.atlassian.net/browse/PRO-369): Implement Continuous CI Timing Measurement and Historical Aggregation
- [PRO-379](https://mainhatten.atlassian.net/browse/PRO-379): Dashboard (depends on this)
- [PRO-380](https://mainhatten.atlassian.net/browse/PRO-380): Statistics (depends on this)
- [PRO-259](https://mainhatten.atlassian.net/browse/PRO-259): Setup Timesheet

Refs: PRO-259
