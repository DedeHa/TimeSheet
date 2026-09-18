# Implementation Plan — PRO-380 Statistical Enhancement & Visualization Optimization

- **JIRA Key:** PRO-380
- **Parent Epic:** PRO-259 (Setup Timesheet)
- **Summary:** Statistical Enhancement & Visualization Optimization — Rolling Stats, Bollinger Bands, Normal Distribution
- **Current Status:** Implementation complete, verification passed
- **Story Points:** 8
- **Fix Version:** v4.3.0

---

## Part A — Preanalysis

### A.1 Data Source
- Source: `data/ci-timings.csv` on the orphan `ci-metrics` branch, collected by `collect_ci_timings.py` (PRO-369, Fertig)
- Aggregated to `data/metrics.json` by `aggregate_ci_timings.py` (PRO-368/PRO-375, Fertig)
- Schema wrapper: `schema_version: "v1.0"` + `generated_at` (PRO-375)

### A.2 Scope
- Add rolling statistics (20-run window), Bollinger bands (mean ± 2σ), and normal distribution parameters (μ, σ) per `(job, step)`
- Pure functions in `.github/scripts/ci_stats.py` using only the Python standard library (`statistics.stdev` for sample stddev)
- Extend `aggregate_ci_timings.py` to compute and embed these into `data/metrics.json`
- Extend `data/metrics.json` schema with `rolling` and `distribution` keys per key

### A.3 Exclusion Rules
- Only `ready` keys (≥ MIN_SAMPLES = 3 samples) are computed for rolling/distribution
- `withheld` keys (< MIN_SAMPLES) remain as-is with `reason: insufficient samples`
- Backward compatibility: existing `stats_for()` and `aggregate()` outputs unchanged

### A.4 Statistics Granularity
- Per `(job, step)` bucket, computed over the chronological `last n` samples
- Window default: 20 runs; Bollinger k default: 2
- Edge cases: empty list → `[]`; fewer than window samples → empty list

### A.5 Security/Permissions
- No network access, no external services, no credentials
- Standard library only; no numpy/pandas

### A.6 Feasibility Verdict
- **Feasible.** All data sources exist (PRO-375), statistical primitives are stdlib (`statistics`), and the metrics JSON write path is already established (`write_metrics()`). No architectural changes required.

---

## Part B — Implementation Plan

### B.1 New/Changed Files

| File | Change |
| --- | --- |
| `.github/scripts/ci_stats.py` | **NEW** — pure statistical functions (`compute_rolling_stats`, `compute_bollinger_bands`, `compute_normal_distribution`) |
| `.github/scripts/aggregate_ci_timings.py` | **CHANGED** — integrate `ci_stats.py`, extend `write_metrics()` payload |
| `.github/tests/ci-pipeline/test_ci_stats.py` | **NEW** — unit tests for all new functions (≥90% coverage) |
| `.github/tests/ci-pipeline/test_aggregate_ci_timings.py` | **CHANGED** — verify schema_version and backward compatibility |
| `.github/scripts/validator.py` | **CHANGED** — extend `STAT_KEYS`/schema validation for new fields |
| `data/metrics.json` | **CHANGED** — regenerated with `rolling` and `distribution` keys |
| `doc/REQUIREMENTS.md` | **CHANGED** — add FR-XX/QR-XX traceability |
| `doc/ARCHITECTURE.md` | **CHANGED** — add architecture traceability entry |
| `doc/02_Implementation_Plan_PRO-380.md` | **CHANGED** — status table updated per rollout step |

### B.2 Data Schema
`data/metrics.json` payload from `write_metrics()`:

```json
{
  "schema_version": "v1.0",
  "generated_at": "<ISO-8601>",
  "ready": {
    "<job / step>": {
      "n": 47,
      "mean": 17.2553,
      "stddev": 2.9301,
      "median": 17.0,
      "p95": 22.0,
      "min": 12.0,
      "max": 24.0,
      "last": 19.0,
      "rolling": {
        "window": 20,
        "values": [
          {"start": 1, "end": 20, "mean": 16.5, "stddev": 2.1, "upper": 20.7, "lower": 12.3},
          ...
        ]
      },
      "distribution": {
        "mean": 17.2553,
        "stddev": 2.9301,
        "curve": {"points": [{"x": 0, "y": 0.03}, {"x": 1, "y": 0.09}, ...]}
      }
    }
  },
  "withheld": { ... }
}
```

### B.3 Workflow / Module Logic (Numbered Steps)

1. **Implement `ci_stats.py`** — pure functions:
   - `compute_rolling_stats(values, window=20)` → list of dicts `{"start", "end", "mean", "stddev"}`
   - `compute_bollinger_bands(values, window=20, k=2)` → list of dicts `{"start", "end", "mean", "upper", "lower"}`
   - `compute_normal_distribution(values)` → dict `{"mean": μ, "stddev": σ, "curve": [{"x", "y"}]}`
   - All use `statistics.stdev` (sample stddev) for consistency with `stats_for()`

2. **Integrate into `aggregate_ci_timings.py`**:
   - Import `ci_stats` functions
   - Compute rolling/distribution per bucket in `write_metrics()`
   - Preserve existing `stats_for()` / `aggregate()` behavior unchanged

3. **Extend `data/metrics.json` schema**:
   - Add `rolling` and `distribution` keys to each `ready` entry
   - `schema_version` stays `"v1.0"` (backward compatible)

4. **Update `validator.py`**:
   - Extend `STAT_KEYS` to include `rolling`, `distribution`
   - Keep `validate_json()` non-gating

5. **Add unit tests** (`.github/tests/ci-pipeline/test_ci_stats.py`):
   - `test_rolling_mean_known_values` — 25 values with window 20 → 6 results
   - `test_rolling_mean_exactly_20_values` — returns 1 result
   - `test_rolling_mean_under_20_values` — returns empty list
   - `test_rolling_mean_empty` — returns empty list
   - `test_bollinger_constant_values` — all equal → upper = lower = mean
   - `test_bollinger_bounds_contain_mean` — lower ≤ mean ≤ upper
   - `test_normal_dist_params_known_dataset` — hand-calculated μ/σ oracle
   - `test_schema_version` — `metrics.json` has `schema_version: "v1.0"`

6. **Rollout plan**:
   - Step 1: Pure code + tests (no workflow changes)
   - Step 2: Integrate `aggregate_ci_timings.py`
   - Step 3: Regenerate `data/metrics.json`
   - Step 4: Update validator + docs
   - Step 5: Full verification (tests, lint, traceability)

### B.4 Configuration Knobs
- `MIN_SAMPLES = 3` (existing, unchanged)
- Rolling window default: 20 (ticket spec)
- Bollinger k: 2 (ticket spec)
- No new config flags required

### B.5 Non-Goals
- No dashboard rendering (PRO-379)
- No external monitoring services (Datadog, Grafana)
- No real-time computation (batch only)
- No numpy/pandas (stdlib only)
- No changes to `data/runtimes.json`

---

## Part C — Verification Definition

### V1. Unit-level (ci-pipeline tests)
- `pytest -q .github/tests/ci-pipeline/test_ci_stats.py` — all 14 tests pass, ≥90% coverage
- `pytest -q .github/tests/ci-pipeline/test_aggregate_ci_timings.py` — backward compatibility (10 tests)
- `pytest -q .github/tests/ci-pipeline/test_validator.py` — schema validation (17 tests)

### V2. Integration-level
- `pytest -q .github/tests/ci-pipeline/test_ci_timing_pipeline.py` — full pipeline still passes
- `python .github/scripts/aggregate_ci_timings.py data/ci-timings.csv /tmp/report.md` — generates valid metrics with new fields

### V3. Acceptance Criteria (JIRA AC-1…AC-9)
- [x] AC-1: `compute_rolling_stats()` returns correct rolling mean for 20-run window
- [x] AC-2: `compute_rolling_stats([1..25], 20)` → 6 results (windows: 1-20, 2-21, ..., 6-25)
- [x] AC-3: `compute_bollinger_bands()` returns correct upper/lower bounds
- [x] AC-4: `compute_normal_distribution()` returns correct μ and σ
- [x] AC-5: Edge cases handled (empty list → [], <20 values → [])
- [x] AC-6: `metrics.json` contains all new statistical fields (rolling, distribution)
- [x] AC-7: Unit tests cover all new functions with ≥90% coverage
- [x] AC-8: Statistical calculations use sample stddev (`statistics.stdev`) consistently
- [x] AC-9: `compute_rolling_stats([1..25], 20)` → 6 results confirmed

### V4. Definition of Done
- [ ] PR merged to master
- [ ] JIRA ticket closed (Fertig)
- [x] All 9 ACs checkmarked
- [x] Story Points: 8 assigned
- [x] Traceability: FR-19, QR-11, QR-12 added to `doc/REQUIREMENTS.md`, `doc/ARCHITECTURE.md`
- [x] CI self-tests: All statistical tests pass (154 passed)

### Review Findings

| Reviewer | Verdict | Notes |
| --- | --- | --- |
| **Developer** | ✅ Pass | Pure stdlib; stddev matches existing pattern; `[1..25]`→6 verified; backward compatible |
| **Architect** | ✅ Pass | Consistent with scripts pattern; additive schema v1.0; no infra; boundaries correct |
| **Tester** | ✅ Pass | All 9 ACs testable; ≥90% achievable; edge cases well-defined |

### Status Table

| Step | Status |
| --- | --- |
| Review: Developer | ✅ Passed |
| Review: Architect | ✅ Passed |
| Review: Tester | ✅ Passed |
| Review: Common (PO+Dev+Arch+Test) | ✅ Passed |
| 1. Pure code (ci_stats.py + tests) | ✅ Completed |
| 2. Integrate aggregate_ci_timings.py | ✅ Completed |
| 3. Regenerate metrics.json | ✅ Completed |
| 4. Update validator.py + docs | ✅ Completed |
| 5. Full verification | ✅ Completed |

---

*Plan drafted per the develop-feature skill. Status updates as rollout steps complete.*

### Rollout Status

#### Step 1: Pure code (ci_stats.py + tests) - ✅ COMPLETED
- **Files:** `.github/scripts/ci_stats.py`, `.github/tests/ci-pipeline/test_ci_stats.py`
- **Test results:** 24 unit tests passed (14 from ci_stats, 10 from aggregator)
- **Coverage:** ≥90% on ci_stats functions
- **Architecture:** Pure stdlib; consistent with existing patterns; backward compatible

#### Step 2: Integrate aggregate_ci_timings.py - ✅ COMPLETED
- **Changes:** Updated `aggregate()` to include `values` field; enhanced `write_metrics()` to compute rolling stats, Bollinger bands, and normal distribution per key
- **Backward compatibility:** All existing 10 aggregation tests pass unchanged
- **Metrics output:** `data/metrics.json` now contains `rolling`, `bollinger`, `distribution` keys in every ready entry

#### Step 3: Regenerate metrics.json - ✅ COMPLETED
- **Result:** `data/metrics.json` (25.5 KB → 29.5 KB) includes new statistical fields across 83 ready entries and 17 withheld entries
- **Validation:** Schema validator (extended STAT_KEYS) passes with no errors
- **Files updated:** `data/metrics.json` (regenerated), `doc/ARCHITECTURE.md`, `doc/REQUIREMENTS.md`

#### Step 4: Update validator.py + docs - ✅ COMPLETED
- **validator.py:** Extended STAT_KEYS to include `rolling`, `bollinger`, `distribution`; added new unit test `test_validate_json_ready_with_new_stat_keys`
- **docs:** Added FR-19, QR-11, QR-12; updated traceability matrix entries for ci_stats.py, aggregate_ci_timings.py, validator.py
- **test_validator.py:** Updated existing test case to include new stat keys; added new test for non-dict ready entries

#### Step 5: Full verification - ✅ COMPLETED
- **Tests:** All CI self-tests pass (154 passed)
- **Lint/format:** ruff, black, pydocstyle all pass
- **Traceability:** 100% architecture and code coverage
- **Pipeline state:** Ready for commit, PR, JIRA closure
