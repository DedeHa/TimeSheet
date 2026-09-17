# Architecture PRO-375: Refactor CI Timing Measurement Pipeline — JSON Output & Data Validation

**Status:** Draft  
**Epic Link:** PRO-259  
**Parent:** PRO-369 (Fertig)  
**Fix Version:** v4.4.0  
**Priority:** Medium  
**Story Points:** 8  

---

## 1. Design Decisions

### 1.1 JSON Structure

Both `runtimes.json` and `metrics.json` follow a shared wrapper pattern:

```json
{
  "schema_version": "v1.0",
  "generated_at": "2026-09-14T20:57:40Z",
  "runs": [ ... ]          // runtimes.json only
}
```

- `schema_version` is a **string literal** `"v1.0"` — not a semver range, not an integer.
- `generated_at` is an ISO-8601 UTC timestamp produced at write time.
- `runs` is a flat array of timing records (runtimes) or a dict of ready/withheld buckets (metrics).

**Decision:** Flat array for runtimes (one entry per successful step) preserves the CSV row semantics and keeps dedup key `(run_id, job_name, step_number)` simple.

### 1.2 Data Perspectives Preserved

| Perspective | Fields | Source |
|-------------|--------|--------|
| **Per Job** | job_name, step_name, step_number, duration_s | `extract_rows()` |
| **Per PR** | run_id, pr_number, head_sha, created_at | `run_meta` |
| **Per Branch** | branch | `run_meta['branch']` (new) |

The `branch` field is added to `run_meta` in `collect_ci_timings.py` and propagated into every row by `extract_rows()`. This is the only new field added to the timing record — all existing CSV fields remain unchanged.

### 1.3 Validation Strategy

`validate_json(data: dict) -> list[str]` is called **before writing to disk** in both `write_json()` and `write_metrics()`. Validation is a pure function with no side effects — it returns a list of error strings (empty = valid). This follows the existing pattern of pure, testable functions in the codebase (cf. `extract_rows()`, `aggregate()`).

**Decision:** Return `list[str]` rather than raising exceptions, so callers can decide how to handle validation failures (log warning, skip write, etc.). This maintains the non-gating invariant — validation failure does not fail CI.

### 1.4 Migration Strategy

Three phases, each with explicit gates:

| Phase | Activity | Gate |
|-------|----------|------|
| **1: Parallel** | Both CSV and JSON active simultaneously | All unit tests pass, JSON validates |
| **2: Verification** | Backfill ci-metrics CSV → data/runtimes.json, validate no data loss | Row counts match, field completeness, user/PO confirmation |
| **3: Decommission** | Remove CSV writes, archive ci-metrics (follow-up PR) | 6-month deprecation notice, data/ is sole source of truth |

**Decision:** Phase 3 is out of scope for this PR (follow-up PRO-376). Phase 1-2 are in scope. The ci-metrics branch remains fully functional during Phase 1-2 — no breaking changes.

### 1.5 Workflow Safety

The `ci-timing.yml` workflow must never re-trigger itself. The existing invariant (`python-ci.yml` does not trigger on `ci-metrics` push) is preserved. The new `data/` folder on master is written via a separate commit step that does not trigger `Python CI` (the workflow's `on:` does not include push to `data/`).

**Decision:** `workflow_run` (continuous trigger) writes to ci-metrics only. `workflow_dispatch` with `update_data=true` writes to both ci-metrics AND data/ on master. This prevents runaway loops while allowing manual data synchronization.

---

## 2. File Structure

```text
data/                          # NEW: top-level folder on master branch
├── runtimes.json              # Raw per-run timing data (append-only)
└── metrics.json               # Aggregated statistics with ready/withheld buckets

.github/scripts/
├── collect_ci_timings.py      # MODIFY: add write_json(), branch field
├── aggregate_ci_timings.py    # MODIFY: add write_metrics()
├── validator.py               # NEW: validate_json() function
└── backfill_ci_timings.py     # MODIFY: add JSON migration support (Phase 2)

.github/workflows/
└── ci-timing.yml              # MODIFY: dual-branch write logic

.github/tests/ci-pipeline/
├── test_collect_ci_timings.py # MODIFY: add JSON output tests
├── test_aggregate_ci_timings.py # MODIFY: add metrics JSON tests
├── test_backfill_ci_timings.py # MODIFY: add migration tests
└── test_validator.py          # NEW: schema validation tests
```

---

## 3. Function Specifications

### 3.1 `write_json(rows, run_meta, path)` — in `collect_ci_timings.py`

```python
def write_json(rows: list[dict], run_meta: dict, path: Path) -> None:
    """Append run data to data/runtimes.json with schema_version v1.0 wrapper.
    
    Reads existing JSON if present, appends new run data, deduplicates by
    (run_id, job_name, step_number), and writes back with schema wrapper.
    Validates before writing; logs warnings on validation failure.
    """
```

**Behavior:**
1. Read existing `data/runtimes.json` if it exists (empty `{"schema_version": "v1.0", "generated_at": "", "runs": []}` if absent)
2. Append new run data from `rows`
3. Deduplicate by `(run_id, job_name, step_number)` — latest attempt wins
4. Validate the combined dataset using `validate_json()`
5. Write back with `schema_version: "v1.0"` and `generated_at` timestamp

**Dependencies:** `validate_json()` from `validator.py`, `dedup_latest_attempt()` from same module

### 3.2 `write_metrics(agg_data, path)` — in `aggregate_ci_timings.py`

```python
def write_metrics(agg_data: dict, path: Path) -> None:
    """Write data/metrics.json with ready/withheld buckets.
    
    Formats aggregate output with schema_version v1.0 wrapper and
    generated_at timestamp. Validates before writing.
    """
```

**Behavior:**
1. Call existing `aggregate()` function to compute stats
2. Format output with `schema_version: "v1.0"`, `generated_at`, `ready`, `withheld`
3. Validate using `validate_json()` (metrics schema validation)
4. Write JSON to `path`

**Dependencies:** `aggregate()` from same module, `validate_json()` from `validator.py`

### 3.3 `validate_json(data: dict, schema: str = "runtimes") -> list[str]` — in `validator.py`

```python
def validate_json(data: dict, schema: str = "runtimes") -> list[str]:
    """Validate JSON structure against schema. Returns list of errors (empty = valid).
    
    Schemas:
      - "runtimes": validates data/runtimes.json structure
      - "metrics": validates data/metrics.json structure
    
    Called before writing to disk. Never raises — returns error list.
    """
```

**Validation Rules:**

**Root keys (both schemas):**
- `schema_version` must be present and equal to `"v1.0"`
- `generated_at` must be present (ISO-8601 format, not validated for exact format)
- `runs` must be present (runtimes schema) OR `ready`/`withheld` must be present (metrics schema)

**Run keys (runtimes schema):**
- `run_id` — present, numeric
- `run_attempt` — present, numeric
- `pr_number` — present (can be empty string)
- `job_name` — present, non-empty string
- `step_name` — present, non-empty string
- `step_number` — present, numeric
- `duration_s` — present, numeric (int or float)
- `conclusion` — present, string

**Metrics keys (metrics schema):**
- `ready` — dict with `(job_name, step_name)` keys and stat dicts
- `withheld` — dict with `(job_name, step_name)` keys and stat dicts with `n` and `reason`

**Type checks:**
- `duration_s` must be `int` or `float`
- `schema_version` must be `"v1.0"`
- `step_number` must be `int`
- `run_id` must be `int` or `str` (numeric)

---

## 4. JSON Schema Specifications

### 4.1 `data/runtimes.json` — Raw Per-Run Data

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

**Constraints:**
- One flat array with one entry per successful step
- All CSV fields preserved plus `branch` added for branch perspective
- Append-only, deduplicated by `(run_id, job_name, step_number)`
- Latest attempt wins for deduplication

### 4.2 `data/metrics.json` — Aggregated Statistics

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

**Constraints:**
- Keys: `n, mean, stddev, median, p95, min, max, last` per `(job_name, step_name)`
- `ready` = keys with ≥3 samples
- `withheld` = keys below threshold with reason
- Recomputed from full dataset on every update (no drift)

---

## 5. Workflow Changes (`ci-timing.yml`)

### 5.1 Trigger Logic

| Trigger | ci-metrics Branch | data/ on Master |
|---------|-------------------|-----------------|
| `workflow_run` (continuous) | ✅ Write CSV + JSON | ❌ Write JSON only |
| `workflow_dispatch` (default) | ✅ Write CSV + JSON | ❌ Write JSON only |
| `workflow_dispatch` with `update_data=true` | ✅ Write CSV + JSON | ✅ Write JSON only |

**Decision:** Continuous trigger writes to ci-metrics only (safety). `workflow_dispatch` with `update_data=true` writes to both branches. This prevents runaway loops while allowing manual data synchronization.

### 5.2 Safety Gates

1. **No-loop invariant:** `python-ci.yml` does not trigger on push to `ci-metrics` or `data/` — preserved from PRO-369.
2. **Concurrency group:** `ci-timing` prevents racing on the same branch when two backfills are dispatched — preserved.
3. **Validation gate:** `validate_json()` called before writing to disk — new. If validation fails, log warning and skip write (non-gating).
4. **Separate commit step:** Data/ folder commit is separate from ci-metrics commit — new. Prevents mixing unrelated changes.

### 5.3 New Environment Variables

```yaml
env:
  UPDATE_DATA: ${{ inputs.update_data || 'false' }}
```

### 5.4 New Workflow Steps

```yaml
- name: Write data/ to master (conditional)
  if: env.UPDATE_DATA == 'true'
  run: |
    # Commit data/runtimes.json and data/metrics.json to master branch
    # Separate commit from ci-metrics to prevent loop
```

---

## 6. Test Structure

### 6.1 Unit Tests (`.github/tests/ci-pipeline/`)

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_validator.py` | 5-7 tests | Schema validation with malformed inputs, missing keys, type errors |
| `test_collect_ci_timings.py` | +3 tests | `write_json()` output, schema compliance, branch field |
| `test_aggregate_ci_timings.py` | +2 tests | `write_metrics()` output, ready/withheld buckets |
| `test_backfill_ci_timings.py` | +2 tests | Migration CSV → JSON, row count validation |

### 6.2 Test Cases

**`test_validator.py`:**
- `test_validate_json_valid_runtimes` — valid runtimes JSON passes
- `test_validate_json_valid_metrics` — valid metrics JSON passes
- `test_validate_json_missing_root_keys` — missing `schema_version`, `generated_at`, `runs`
- `test_validate_json_missing_run_keys` — missing required run fields
- `test_validate_json_invalid_duration_type` — `duration_s` is string, not numeric
- `test_validate_json_invalid_schema_version` — `schema_version` is not `"v1.0"`
- `test_validate_json_empty_runs` — empty runs array is valid

**`test_collect_ci_timings.py` (additions):**
- `test_write_json_creates_file` — `write_json()` creates `data/runtimes.json`
- `test_write_json_deduplicates` — duplicate `(run_id, job_name, step_number)` is deduplicated
- `test_write_json_schema_version` — output has `schema_version: "v1.0"`
- `test_extract_rows_includes_branch` — `branch` field present in all rows

**`test_aggregate_ci_timings.py` (additions):**
- `test_write_metrics_creates_file` — `write_metrics()` creates `data/metrics.json`
- `test_write_metrics_ready_withheld` — output has `ready` and `withheld` buckets

**`test_backfill_ci_timings.py` (additions):**
- `test_backfill_csv_to_json` — migration from CSV to JSON preserves row count
- `test_backfill_json_validation` — migrated JSON passes validation

### 6.3 Integration Tests

- Full pipeline: collect → aggregate → both CSV + JSON outputs
- Data/ folder populated correctly on master branch
- Both ci-metrics and data/ contain consistent data

### 6.4 CI Self-Tests

- `test_ci_timing_does_not_retrigger_python_ci` — no-loop invariant
- `test_ci_timing_only_writes_to_ci_metrics_branch` — safety gate

---

## 7. Migration Details

### 7.1 Phase 1: Parallel (In Scope)

**Changes:**
1. `collect_ci_timings.py` writes both CSV (ci-metrics) AND JSON (data/ on master)
2. `aggregate_ci_timings.py` writes both `data/metrics.json` AND `CI_TIMING_REPORT.md` (ci-metrics)
3. Both storage locations active simultaneously
4. No breaking changes

**Gate:** All unit tests pass, JSON validates, CSV unchanged.

### 7.2 Phase 2: Verification (In Scope)

**Changes:**
1. Backfill ci-metrics CSV → `data/runtimes.json`
2. Validate: row counts match, no data loss
3. Generate comparison report
4. User/PO confirms data integrity

**Gate:** Row counts match, field completeness, user/PO confirmation.

### 7.3 Phase 3: Decommission (Out of Scope — Follow-up PRO-376)

**Changes:**
1. Remove CSV writes from `collect_ci_timings.py`
2. Remove `CI_TIMING_REPORT.md` from ci-metrics workflow
3. Archive ci-metrics branch (read-only)
4. `data/` on master = sole source of truth

**Rollback:** ci-metrics branch remains fully functional (Phase 1 design).

---

## 8. Backward Compatibility

| Aspect | Phase 1-2 | Phase 3 |
|--------|-----------|---------|
| CSV on ci-metrics | ✅ Unchanged | ❌ Removed (6-month notice) |
| `CI_TIMING_REPORT.md` | ✅ Unchanged | ❌ Removed (6-month notice) |
| JSON outputs | ✅ Additive | ✅ Sole source of truth |
| `aggregate()` logic | ✅ Unchanged | ✅ Unchanged |
| `extract_rows()` | ✅ Branch field added | ✅ Branch field present |

**Deprecation timeline:** 2 releases before CSV deprecation, 3 before removal. Consumers get 6-month notice before Phase 3 decommission.

---

## 9. Alignment Verification

### 9.1 ARCHITECTURE.md Patterns

- ✅ **Configuration flow:** YAML-driven, environment auto-detection — not applicable (CI scripts use env vars)
- ✅ **Error handling:** Configuration errors raise `ConfigError`, file I/O errors log warnings — validation returns error list, logs warnings
- ✅ **Pure functions:** `extract_rows()`, `dedup_latest_attempt()`, `aggregate()`, `stats_for()` are pure — `write_json()`, `write_metrics()` have side effects but are isolated
- ✅ **Standard library only:** All CI scripts use stdlib — `validator.py` uses stdlib only

### 9.2 CONTRIBUTING.md Conventions

- ✅ **Conventional Commits:** `feat(ci-timing): add JSON output and data validation`
- ✅ **Branch naming:** `feature/PRO-375-json-output-data-validation`
- ✅ **PR title:** `[feat][PRO-375] Add JSON output and data validation`
- ✅ **PR body:** `## Summary`, `## Testing`, `Refs: PRO-375`

### 9.3 TESTING.md Strategy

- ✅ **Unit tests:** Individual functions in isolation with tmp_path or mocks
- ✅ **Integration tests:** Full pipeline on in-memory data
- ✅ **System tests:** Real-file copies (skipped when absent)
- ✅ **Coverage gate:** ≥90% combined across all levels

---

## 10. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| JSON write fails mid-operation (corrupt file) | High | Low | Write to temp file, then rename (atomic). Validate before write. |
| CI loop from data/ push to master | High | Low | `python-ci.yml` does not trigger on push to `data/`. Separate commit step. |
| Data loss during migration (Phase 2) | High | Low | Row count validation, field completeness check, user/PO confirmation before decommission. |
| Schema version mismatch | Medium | Low | `validate_json()` checks `schema_version == "v1.0"`. Rejects unknown versions. |
| Branch field not populated | Medium | Low | `extract_rows()` adds `branch` from `run_meta`. Tested with `test_extract_rows_includes_branch`. |
| Backward compatibility break | Medium | Low | CSV outputs unchanged in Phase 1-2. JSON is additive. Deprecation timeline documented. |
| `workflow_dispatch` with `update_data=true` not triggered | Medium | Low | Manual trigger with explicit input. Documented in workflow comments. |

---

## 11. Assumptions

1. **Branch field source:** `branch` is available in `run_meta` from GitHub Actions API or environment variable `GITHUB_HEAD_REF` / `GITHUB_REF_NAME`.
2. **Python version:** CI scripts run on `ubuntu-latest` with Python 3.x (stdlib only, no version constraints).
3. **Data/ folder location:** `data/` is at repository root, committed to master branch.
4. **Schema evolution:** `schema_version` allows future versions (v1.1, v2.0) — validation only checks current version.
5. **Metrics computation:** `aggregate()` logic unchanged — only output format changes (CSV → JSON).
6. **No external dependencies:** All scripts use stdlib only (json, csv, pathlib, statistics, etc.).
7. **Non-gating invariant:** Validation failures log warnings but do not fail CI.

---

## 12. Documentation Updates

- [ ] `AGENTS.md`: Document `data/` folder location, non-gating invariant, no-loop invariants
- [ ] `doc/CONTRIBUTING.md`: Document `data/` folder structure, migration path
- [ ] `doc/ARCHITECTURE.md`: Add data storage architecture section
- [ ] `doc/REQUIREMENTS.md`: Add FR-XX, QR-XX traceability entries

---

## 13. Traceability

| Requirement ID | Architectural concern | Implementation reference |
|----------------|----------------------|--------------------------|
| FR-XX | JSON output | `collect_ci_timings.py` - `write_json()`, `aggregate_ci_timings.py` - `write_metrics()` |
| FR-XX | Data validation | `validator.py` - `validate_json()` |
| FR-XX | Branch perspective | `collect_ci_timings.py` - `extract_rows()` branch field |
| FR-XX | Dual storage | `ci-timing.yml` - workflow_dispatch `update_data=true` |
| QR-XX | Data integrity | `validator.py` - schema validation before write |
| QR-XX | No data loss | Phase 2 backfill validation |
| QR-XX | Non-gating invariant | Validation failures log warnings, never fail CI |

Refs: PRO-259, PRO-368, PRO-369, PRO-379, PRO-380
