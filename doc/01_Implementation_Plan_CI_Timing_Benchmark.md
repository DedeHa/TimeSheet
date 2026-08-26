# Implementation Plan: Continuous CI-Pipeline Timing Benchmark

> **Goal.** Continuously measure the execution time of the real `Python CI`
> pipeline across the runs of the **active PR**, maintain a running **mean** and
> **standard deviation** per pipeline step (and per job), **exclude failed / edge-case
> runs**, and keep a generated report updated automatically on every new run.
>
> This is distinct from `.github/workflows/benchmark.yml`, which is a one-off,
> manually-dispatched **setup** micro-benchmark (composite vs. inline). Here we
> measure the **whole pipeline over time**.
>
> **JIRA:** PRO-369 (child of PRO-368, optimization O8; parent epic PRO-259) · **Status:** New (JIRA "Zu erledigen") — not yet implemented

This document has three parts, as requested: **Part A — Preanalysis**,
**Part B — Implementation Plan** (derived from the preanalysis), and
**Part C — Verification Definition**.

---

## Part A — Preanalysis

### A.1 Objective & questions to resolve

1. Where does per-step timing come from, reliably?
2. Which runs count (scope), and how do we exclude failed/edge-case runs?
3. How is the accumulating dataset **persisted** across runs without polluting the
   PR branch or re-triggering CI?
4. How is it **triggered continuously**?
5. What statistics, at what **granularity**, and how are they kept stable while the
   workflow itself changes?
6. What are the accuracy limits (runner variance) and the security/permission needs?

### A.2 Data source — GitHub Actions API, not shell timestamps

The Actions REST API already exposes authoritative timing:
`GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` returns, for every job,
`started_at`, `completed_at`, `conclusion`, and a `steps[]` array with each step's
`number`, `name`, `status`, `conclusion`, `started_at`, `completed_at`.

Consequences:
- **No workflow instrumentation is required** (unlike `benchmark.yml`, which used
  `date +%s.%N` because it timed a sub-step window). We read timings *after the
  fact* from the API — the measured pipeline stays untouched.
- Step duration = `completed_at − started_at`; job duration likewise. Queue/idle
  time before `started_at` is excluded (we measure execution, not wall-to-wall).
- Granularity available: **per job** and **per step**.

### A.3 Scope — the active PR's runs of `Python CI`

- Target workflow: `python-ci.yml` (name `Python CI`).
- Target runs: `event == pull_request`, head branch == the PR's branch. The "active
  PR" is resolved from the branch (`gh pr view --json number,headRefName`) or, in a
  `workflow_run` trigger, from the triggering run's `pull_requests[]`.
- Tag/`workflow_dispatch` runs are **out of scope** for the PR benchmark (different
  event profile); they may be captured separately later. (The `workflow_dispatch`
  **backfill** input is a separate, explicit, opt-in mechanism — see A.7 — and is
  not part of the continuous PR capture.)

#### Backfill starting point

The benchmark should be seeded from the point where the **complete naming-validation
pipeline** is in place on `master`. The relevant cut-off is:

| | |
|---|---|
| **Commit** | `92991ed` — `feat(ci): implement O2 venv caching and O4 consolidated PR validators` |
| **Merged via** | PR #101 (`feature/PRO-368-optimize-ci` → `master`) |
| **Merged at** | 2026-08-22T13:05:16Z |
| **Branches** | `master` + `release/**` |

This is the commit where all four naming checks (commit messages, JIRA reference,
PR title, PR body) were **consolidated from four separate `run:`/`uses:` steps into
the single `Validate PR` step** that calls `.github/scripts/validate_pr.py`. Before
this commit the `check` job had four separate steps (`Validate commit messages`
using `commitlint`, `Validate PR Title`, `Validate PR Body`, `Validate Jira
reference in commits`). The step names changed, so mixing runs from before and after
`92991ed` would trigger the workflow-drift rule (A.6) and produce misleading
comparisons.

The backfill sweep should start from **2026-08-22T13:05:16Z** (the merge time of
`92991ed`) to avoid capturing pre-consolidation step names that are no longer in the
workflow. The first `pull_request` run of `Python CI` on `master` after the merge
was run `32575534224` (branch `release/v4.2.0`, 2026-08-22T13:21:25Z).

### A.4 Exclusion rules (failed / edge-case runs) — precise definition

Applied at three levels:

| Level | Include only when | Rationale |
|-------|-------------------|-----------|
| **Run** | `conclusion == success` | Drops `failure`, `cancelled` (incl. concurrency-superseded), `timed_out`, `startup_failure`, `action_required`, `stale`, `null`/in-progress |
| **Job** | job `conclusion == success` | A run can be success overall while a job was skipped (e.g. `deploy` on a PR) — skipped jobs contribute no timing |
| **Step** | step `conclusion == success` and has both timestamps | Drops `skipped`/`cancelled` steps and GitHub's synthetic `Set up job` / `Post …` housekeeping if desired |

Additional edge-case handling:
- **Re-runs / attempts:** key the dataset by `run_id` **and** `run_attempt`; keep the
  **latest attempt** only (dedup) so a re-run supersedes its earlier attempt.
- **Cold-cache first run:** the first run after a `pyproject.toml` change repopulates
  the pip cache and is a legitimate outlier. Mark each sample with a
  `cache` flag (warm/cold) derived from whether the cache-restore step reported a
  hit, and compute stats over **warm** samples by default (cold shown separately).
- **Statistical outliers:** optionally drop samples beyond a median-absolute-deviation
  threshold (e.g. |x − median| > 3·MAD). Off by default; documented and configurable.
- **Workflow drift:** if the set of step names changed (workflow edited), older
  samples for a renamed/removed step must not be mixed with new ones — see A.6.

### A.5 Persistence — where the accumulating dataset lives

The data must survive across runs and **must not** (a) pollute the PR branch history
or (b) re-trigger `Python CI`. Options considered:

| Option | Durable? | Retriggers CI? | Notes |
|--------|----------|----------------|-------|
| Commit to the **PR branch** | ✅ | ❌ **yes** (loops) | Rejected — pushes would start new CI runs |
| **Orphan branch** `ci-metrics` | ✅ | No (not a CI trigger) | **Recommended** — durable, auditable, isolated |
| `actions/cache` | ⚠️ (evictable, 7 d / 10 GB) | No | Lightweight alt; risk of silent data loss |
| Run **artifacts** | ⚠️ (expire; awkward cross-run fetch) | No | Must fetch previous run's artifact via API |
| External store (Pages/DB) | ✅ | No | Overkill for this repo |

**Decision:** primary store is an **orphan `ci-metrics` branch** holding
`ci-timings.csv` (one row per run × job × step) and the generated
`CI_TIMING_REPORT.md`. Pushes to `ci-metrics` do not match `python-ci.yml`'s
triggers, so no loop. `actions/cache` is the documented fallback if a branch is
undesirable.

### A.6 Statistics & granularity

- **Key:** `(job_name, step_name)` for steps; `(job_name)` for jobs. Store the
  `workflow_sha`/content hash with each sample so drift is visible.
- **Per key, over the included samples:** `n`, `mean`, `stddev` (sample),
  `median`, `p95`, `min`, `max`, `last`, and `Δ vs previous mean`.
- **Update model:** **recompute from the full CSV** on every update (idempotent,
  no drift, trivial at PR scale of tens–hundreds of rows). Incremental Welford
  (persisted `count/mean/M2`) is the alternative if the dataset ever grows large;
  not needed initially.
- **Drift rule:** a step key is reported only if it has ≥ `MIN_SAMPLES` (e.g. 3)
  **warm, successful** samples; keys not present in the current workflow are marked
  *retired* and moved to an appendix rather than mixed in.

### A.7 Trigger — continuous capture

- **Primary:** a new workflow `ci-timing.yml` with
  `on: workflow_run: { workflows: ["Python CI"], types: [completed] }`. It fires
  once per completed `Python CI` run, reads that run's timings via the API, appends
  to the dataset on `ci-metrics`, recomputes stats, regenerates the report, and
  (optionally) updates a sticky PR comment. Event-driven = truly continuous.
- **Secondary:** `workflow_dispatch` with an optional `backfill` input that sweeps
  all historical successful PR runs and rebuilds the dataset from scratch
  (idempotent — dedup by `run_id`+`run_attempt`).

`workflow_run` executes in the **default-branch** context with repo secrets, which
is exactly what we need to write to `ci-metrics` and comment on the PR.

### A.8 Permissions & security

- `permissions: { actions: read, contents: write, pull-requests: write }`.
  `actions: read` → job/step timings; `contents: write` → push to `ci-metrics`;
  `pull-requests: write` → optional sticky comment.
- Only the built-in `GITHUB_TOKEN`; no PATs. The workflow treats API JSON as data.

### A.9 Accuracy caveats (must be stated in the report)

GitHub-hosted runners are shared and noisy; per-step times vary run-to-run
(often ±10–30 %). Therefore: report **stddev alongside mean** (never mean alone),
require `MIN_SAMPLES` before drawing conclusions, prefer **median/p95** for
decisions, and treat the numbers as **trend indicators**, not benchmarks of the
code itself. This is the same caveat that applies to `benchmark.yml`.

### A.10 Feasibility verdict

Feasible with standard GitHub features (Actions API + `workflow_run` + an orphan
branch), no external infrastructure, and the built-in token. Effort: **medium**.
Main risks are runner variance (mitigated by stddev + min-samples) and workflow
drift (mitigated by keying on step names + a retired-keys appendix).

---

## Part B — Implementation Plan (derived from Part A)

### B.1 New / changed files

| File | Purpose |
|------|---------|
| `.github/workflows/ci-timing.yml` | `workflow_run` + `workflow_dispatch` trigger; orchestrates capture → aggregate → publish |
| `.github/scripts/collect_ci_timings.py` | Fetch job/step timings for a run via the API; apply exclusion rules; emit CSV rows |
| `.github/scripts/aggregate_ci_timings.py` | Read the full CSV, compute per-(job,step) stats, render `CI_TIMING_REPORT.md` |
| `.github/tests/test_collect_ci_timings.py` | Unit-test exclusion rules + row extraction against sample API JSON |
| `.github/tests/test_aggregate_ci_timings.py` | Unit-test stats (mean/stddev/median/p95), drift handling, empty/edge inputs |
| `ci-metrics` branch → `ci-timings.csv`, `CI_TIMING_REPORT.md` | Persistent dataset + generated report |

Both scripts are **standard-library only** (`json`, `csv`, `statistics`,
`urllib`/`subprocess` for `gh api`), matching the existing CI-support scripts, and
are added to the `.github/tests` CI self-test group.

### B.2 Data schema (`ci-timings.csv`)

`run_id, run_attempt, pr_number, head_sha, workflow_sha, created_at, job_name,
step_name, step_number, duration_s, conclusion, cache_state`

One row per successful step; job-level totals derived at aggregation time (or
stored with `step_name = "<job total>"`). Dedup key: `(run_id, run_attempt,
job_name, step_number)`.

### B.3 Workflow logic (`ci-timing.yml`)

1. `on.workflow_run` (completed) **and** `on.workflow_dispatch` (input `backfill`).
2. Guard: proceed only if the triggering run's `event == pull_request` (or, for
   dispatch, sweep PR runs).
3. `actions/checkout` the `ci-metrics` branch (create it as an orphan on first run).
4. `collect_ci_timings.py` — for the triggering `run_id` (or, for backfill, every
   qualifying run) fetch jobs/steps, apply A.4 exclusions, append de-duplicated rows
   to `ci-timings.csv`.
5. `aggregate_ci_timings.py` — recompute stats, write `CI_TIMING_REPORT.md` (tables
   per job with per-step mean ± stddev, median, p95, n, Δ; a retired-keys appendix;
   the runner-variance caveat).
6. Commit & push `ci-metrics` (skip commit if nothing changed).
7. Optional: upsert a sticky **"CI Timing Benchmark"** PR comment (distinct marker
   from the quality-gate summary) with the top-line table + a link to the full
   report on `ci-metrics`.

### B.4 Report shape (`CI_TIMING_REPORT.md`)

- Header: PR number, sample window, total included/excluded runs, generation time,
  variance caveat.
- Per job: a table of steps — `Step | n | mean (s) | stddev | median | p95 | last | Δmean`.
- A **job-total** table (same columns) for check / test / publish.
- Appendix: retired/renamed step keys; excluded-run log (run_id, conclusion, reason).

### B.5 Configuration knobs (documented, in the workflow `env` or inputs)

`MIN_SAMPLES` (default 3), `WARM_ONLY` (default true), `MAD_OUTLIER_K`
(default off), `INCLUDE_HOUSEKEEPING_STEPS` (default false).

### B.6 Rollout steps

1. Land the two scripts + their unit tests (green in the existing `.github/tests`
   gate) — no workflow yet, so zero CI-behaviour change.
2. Add `ci-timing.yml` (initially `workflow_dispatch` only) and create the orphan
   `ci-metrics` branch; run `backfill` once to seed from history.
   - The orphan `ci-metrics` branch is created by the workflow on its first run.
     On GitHub it does not exist until the workflow runs for the first time.
   - The backfill should be seeded from commit `92991ed` (the merge of PR #101,
     2026-08-22T13:05:16Z — the point where the consolidated naming-validation
     pipeline was introduced on `master`). See A.3 "Backfill starting point" for
     the full rationale. The `workflow_dispatch` backfill sweeps all successful
     `pull_request` runs; the `workflow_run` continuous capture handles runs
     from this point forward automatically.
   - The `ci-metrics` orphan branch, once created, holds `ci-timings.csv`,
     `CI_TIMING_REPORT.md` and a `README.md` with usage instructions.
3. Verify the seeded report; then enable the `workflow_run` trigger for continuous
   capture.
4. Document in `AGENTS.md` / `doc/CONTRIBUTING.md` (where to find the report; that
   it is non-gating and never pushes to the PR branch).

### B.7 Explicit non-goals

Not a quality gate (never fails a PR); does not change `python-ci.yml`'s timing;
does not measure queue time; does not compare against `master`/baseline in v1
(possible later); no external dashboards or databases; does **not** replace
`.github/workflows/benchmark.yml`; does **not** perform application performance
benchmarking.

---

## Part C — Verification Definition

The feature is **done and correct** when all of the following hold:

### C.1 Unit-level (runs in the `.github/tests` CI gate)

- **V1 — Exclusion rules.** `test_collect_ci_timings.py` feeds sample API JSON
  containing success/failure/cancelled/skipped runs, a skipped `deploy` job, a
  re-run (two attempts), and housekeeping steps; asserts only success run + success
  job + success step rows survive, the latest attempt wins, and housekeeping is
  excluded by default.
- **V2 — Statistics.** `test_aggregate_ci_timings.py` feeds a known CSV and asserts
  exact `mean`, sample `stddev`, `median`, `p95`, `n`, and `Δ vs previous`; asserts
  a key with `< MIN_SAMPLES` is withheld (or appears in the retired appendix), and
  that empty input yields a valid "no data yet" report (no crash).
- **V3 — Idempotency.** Re-collecting the same `run_id`+`run_attempt` does not add a
  duplicate row (dedup verified).
- **V4 — Lint/format.** `ruff` + `black` clean on both scripts and tests.

### C.2 Integration-level (on the `ci-metrics` branch)

- **V5 — Backfill.** A `workflow_dispatch` backfill on a PR with ≥ 5 successful runs
  produces `ci-timings.csv` with the expected number of rows (successful steps only)
  and a `CI_TIMING_REPORT.md` whose per-job means are within a hand-checked tolerance
  of the same runs' durations read directly via `gh run view`.
- **V6 — Continuity.** After enabling `workflow_run`, the next real `Python CI` run
  appends exactly its rows and the report's `n` increments by one per included step;
  the PR branch receives **no** new commit (only `ci-metrics` does), and no new
  `Python CI` run is triggered by the metrics push (no loop).
- **V7 — Edge exclusion in the wild.** A deliberately failed `Python CI` run (e.g.
  a lint error) results in **zero** new timing rows and an entry in the excluded-run
  log with the correct reason.

### C.3 Acceptance criteria (checklist)

- [ ] Per-step and per-job **mean + stddev** (plus median/p95/n) are reported and
      update automatically on every new successful PR run.
- [ ] Failed, cancelled, timed-out, startup-failure and superseded runs are
      excluded; skipped jobs/steps and re-run earlier attempts are excluded.
- [ ] The dataset persists across runs on `ci-metrics`; the PR branch is never
      written to and CI is never re-triggered by the metrics workflow.
- [ ] The report states the runner-variance caveat and withholds under-sampled keys.
- [ ] Scripts are stdlib-only, unit-tested, and green in the `.github/tests` gate.
- [ ] The mechanism is non-gating (never fails a PR).

### C.4 Definition of Done

All V1–V7 pass, the acceptance checklist is complete, `CI_TIMING_REPORT.md` is
visible on `ci-metrics` (and/or as the sticky "CI Timing Benchmark" PR comment),
and `AGENTS.md` / `doc/CONTRIBUTING.md` document where to find it and that it is
non-gating.

---
*Companion to [00_Implementation_Plan_PRO-368.md](00_Implementation_Plan_PRO-368.md)
(optimization O8). Implements the "measure the whole pipeline continuously" goal
that `benchmark.yml` — a setup-only micro-benchmark — does not cover.*
