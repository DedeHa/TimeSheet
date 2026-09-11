# Implementation Plan PRO-369: Implement Continuous CI Timing Measurement and Historical Aggregation

**Status:** In Progress
**Epic Link:** PRO-259
**Parent:** PRO-368 (Fertig)
**Fix Version:** v4.3.0
**Priority:** Medium

---

## Background

PRO-368 (Optimize Python CI Workflow Performance and Maintainability) implemented
CI optimization foundation (dependency caching, reusable environment setup,
parallel job execution, CI self-tests) and identified O8 — Capture a runtime
baseline / continuous timing benchmark as the remaining optimization item.

The existing `.github/workflows/benchmark.yml` provides on-demand setup
micro-benchmarking but is not a replacement for continuous measurement of the
complete CI pipeline. This ticket implements that continuous measurement.

## Goal

Continuously collect and aggregate timing data from successful Python CI runs
to establish a historical baseline for measuring future optimization effects.

## Scope

### In Scope

- Continuous collection of per-job/per-step execution times from GitHub Actions API
- Historical aggregation with persistent dataset on orphan `ci-metrics` branch
- Human-readable `CI_TIMING_REPORT.md` with statistics (mean, stddev, median, p95, n, min, max, last, delta)
- `workflow_run` trigger on `Python CI` completion for automatic capture
- `workflow_dispatch` with `backfill` input for historical seeding
- Idempotent operations (dedup by `run_id` + `run_attempt`)
- Exclusion of failed/cancelled/timed-out runs, skipped steps, housekeeping steps

### Out of Scope

- Modifying Python CI workflow quality gates
- Optimizing the CI workflow itself
- External dashboards or databases
- Application performance benchmarking
- Replacing `.github/workflows/benchmark.yml`
- Comparison against master/baseline in v1

## Implementation Plan

### Phase 1: Scripts + Unit Tests (Rollout Step 1)

**Files:**
- `.github/scripts/collect_ci_timings.py` — Fetch job/step timings via GitHub Actions API, apply exclusion rules, emit CSV rows
- `.github/scripts/aggregate_ci_timings.py` — Read CSV, compute per-(job,step) stats, render `CI_TIMING_REPORT.md`
- `.github/tests/ci-pipeline/test_collect_ci_timings.py` — Unit-test exclusion rules + row extraction
- `.github/tests/ci-pipeline/test_aggregate_ci_timings.py` — Unit-test statistics, drift handling, edge inputs
- `.github/tests/ci-pipeline/test_backfill_ci_timings.py` — Unit-test backfill idempotency and exclusion

**Gate:** All unit tests pass (`.github/tests/ci-pipeline/` gate), ruff + black clean.

### Phase 2: Workflow + Orphan Branch Seed (Rollout Step 2)

**Files:**
- `.github/workflows/ci-timing.yml` — `workflow_run` + `workflow_dispatch` trigger; orchestrates capture → aggregate → publish
- `ci-metrics` branch → `ci-timings.csv`, `CI_TIMING_REPORT.md`, `README.md` — Persistent dataset + generated report

**Gate:** Workflow YAML valid, `workflow_dispatch` backfill runs successfully, `ci-metrics` branch created with data.

### Phase 3: Enable Continuous Trigger + Docs (Rollout Step 3)

**Gate:** `workflow_run` trigger enabled, next real `Python CI` run appends rows correctly, no CI loop introduced, docs updated.

### Phase 4: Documentation (Rollout Step 4)

**Files:**
- `AGENTS.md` — Where the artefact lives, that it is non-gating, what the no-loop invariants are
- `doc/CONTRIBUTING.md` — Where to find the report, non-gating documentation

## Data Schema

`ci-timings.csv` columns:
```
run_id, run_attempt, pr_number, head_sha, workflow_sha, created_at,
job_name, step_name, step_number, duration_s, conclusion, cache_state
```

One row per successful step; job-level totals stored with `step_name = "<job total>"`.
Dedup key: `(run_id, run_attempt, job_name, step_number)`.

## Configuration Knobs

- `MIN_SAMPLES` (default 3) — minimum samples before a key appears in main tables
- `INCLUDE_HOUSEKEEPING_STEPS` (default false) — include GitHub synthetic steps
- `WARM_ONLY` (default true) — exclude cold-cache measurements from main stats

## Rollout Steps (from plan)

1. ✅ Scripts + unit tests (pure code, no workflow)
2. ✅ Workflow + orphan branch seed + manual backfill
3. ✅ Continuous trigger enabled + docs
4. ✅ Documentation in AGENTS.md

## Non-Goals

Not a quality gate (never fails a PR); does not change `python-ci.yml`'s timing;
does not measure queue time; does not compare against `master`/baseline in v1;
no external dashboards or databases; does not replace `.github/workflows/benchmark.yml`;
does not perform application performance benchmarking.

## Acceptance Criteria

- [x] AC-1: Continuous collection active — `workflow_run` trigger fires on `Python CI` completion
- [x] AC-2: Per-job and per-step execution times captured from GitHub Actions timing data
- [x] AC-3: Per-job and per-step mean and standard deviation continuously updated
- [x] AC-4: Median, p95, sample count, latest value, and delta vs previous mean available
- [x] AC-5: Failed, cancelled, timed-out, skipped, and invalid runs/steps excluded
- [x] AC-6: Re-runs do not result in duplicate measurements (dedup by run_id + run_attempt)
- [x] AC-7: Historical measurements persist across CI runs (ci-metrics branch)
- [x] AC-8: Active-PR measurements continuously updated for qualifying runs
- [x] AC-9: Historical backfill available and idempotent
- [x] AC-10: Workflow/step changes do not incorrectly mix incompatible measurements (keyed on step names)
- [x] AC-11: Report clearly communicates runner variance and minimum-sample limitations
- [x] AC-12: Implementation does not modify CI timing or quality gates (non-gating)
- [x] AC-13: PR branch never modified by metrics collection (only ci-metrics)
- [x] AC-14: Metrics update does not trigger unintended CI loops (python-ci.yml doesn't trigger on ci-metrics push)
- [x] AC-15: Unit tests cover all collection, filtering, and statistical functions
- [x] AC-16: Integration tests verify backfill, deduplication, and persistence
- [x] AC-17: All tests pass through existing CI self-test mechanism

## Definition of Done

- [x] Continuous collection is active (workflow_run trigger)
- [x] Historical data has been seeded through a backfill
- [x] Active PR measurements update automatically after successful CI runs
- [x] Overall historical statistics update automatically
- [x] Generated reports are available and accessible
- [x] All exclusion and deduplication rules are verified
- [x] All relevant tests pass
- [x] Documentation explains metric location and usage
- [x] Mechanism is demonstrably non-gating
- [x] No CI trigger loop is introduced

## Verification Summary

### Unit Tests
- `test_collect_ci_timings.py` — 5 tests (exclusion rules, duration parsing, dedup, failed runs, housekeeping flag)
- `test_aggregate_ci_timings.py` — 6 tests (stats, percentile, min-samples withholding, report rendering, empty dataset)
- `test_backfill_ci_timings.py` — 4 tests (idempotency, attempt supersedes, non-success skipping)

### Lint/Format
- ruff check: pass
- black format: pass

### Tests Run
- All `.github/tests/ci-pipeline/` tests pass
- Application tests pass with ≥90% coverage

## References

- PRO-368: Optimize Python CI Workflow Performance and Maintainability
- PRO-259: Setup Timesheet Testing
- `.github/workflows/python-ci.yml`: Python CI workflow
- `.github/workflows/benchmark.yml`: Existing setup micro-benchmark
- `doc/01_Implementation_Plan_CI_Timing_Benchmark.md`: Original plan (older format, kept for reference)

Refs: PRO-259
