# PRO-368 — Optimize Python CI Workflow: Plan, Status & Evaluation

> **Single source of truth.** This document consolidates what were previously three
> files — the original implementation plan, the delivered-status report, and the
> completeness/optimization evaluation. Sections 1–7 describe the **actual**
> delivered state; Section 8 records post-implementation addenda; Section 9
> archives the original (aspirational) phased plan for history.

**JIRA:** PRO-368 · **Parent epic:** PRO-259 · **Fix version:** v4.2.0 ·
**Branch:** `feature/PRO-368-optimize-ci`

---

## 1. Feature summary & requirements

Optimize the GitHub Actions CI workflow for the Python TimeSheet project —
eliminate redundant work, reuse dependencies, and improve maintainability — while
preserving all existing quality gates, branch strategy and deployment patterns.
The original "30–50% runtime reduction" figure was a planning **target**, never a
measured result (no baseline was captured; see the optimization backlog O8 and the
separate CI-timing-benchmark plan).

**Functional requirements**
- **FR-16** CI dependency caching (pip download cache keyed on `pyproject.toml`).
- **FR-17** CI reusable environment setup (single composite action).

**Quality requirements**
- **QR-08** CI performance (avoid redundant work: caching, one setup action, no unconditional Node.js).
- **QR-09** CI maintainability (single point of change for environment setup).

FR-16, FR-17, QR-08, QR-09 are recorded in `doc/REQUIREMENTS.md`,
`doc/ARCHITECTURE.md`, and the anchor comment in
`src_timesheetalgo/TimeSheetAlgo.py`; the traceability gate
(`python .github/scripts/generate_traceability_matrix.py`) keeps all three in sync.

## 2. Delivered pipeline (actual)

Four jobs. `check` and `test` run **in parallel** (no `needs` between them);
`deploy` and `publish` depend on both.

- **`check`** — composite setup → PR/commit/Jira validators (PR events only,
  exempt for `dependabot[bot]`) → lint (ruff, black, pydocstyle, radon).
  Environment: `development` (static).
- **`test`** — composite setup → traceability generate+gate →
  unit/integration/system (accumulated branch coverage → 90 % gate) → CI
  self-tests (`.github/tests`, reported as a separate **CI-Pipeline** test group,
  no coverage) → upload reports artifact. Environment: `staging` (static).
- **`deploy`** — release tags only, gated on `check` + `test`; installs the
  `build` frontend (stub — packaging/deploy not yet implemented, see AC6).
  Environment: `production`.
- **`publish`** — `if: always()`, depends on the gating jobs; downloads the reports
  artifact and publishes the consolidated quality-gate summary (see Section 6).

CI maintenance: `.github/dependabot.yml` bumps GitHub Actions weekly. Environments
are **static** — a previous dynamic `environment:` expression coerced to the
boolean `false` and auto-created a junk environment named "false" (removed).

## 3. Files (actual)

| File | Purpose |
|------|---------|
| `.github/workflows/python-ci.yml` | The CI pipeline (check / test / deploy / publish) |
| `.github/actions/setup-python-deps/action.yml` | Composite action: Python setup + pip cache + `pip install -e .[dev]` (checkout stays in each job) |
| `.github/scripts/generate_pr_summary.py` | Quality-gate summary generator (sticky + per-run comment + job summary) |
| `.github/scripts/generate_traceability_matrix.py` | Traceability matrix generator + completeness gate (exits non-zero if untraced) |
| `.github/tests/test_verify_ci_workflow.py` | Structural + regression workflow assertions |
| `.github/tests/test_generate_pr_summary.py` | Unit tests for the summary generator |
| `.github/tests/test_generate_traceability_matrix.py` | Unit tests for the traceability generator |
| `.github/workflows/benchmark.yml` | On-demand composite-vs-inline **setup** benchmark (Addendum B) |
| `.github/dependabot.yml` | Weekly GitHub-Actions version bumps |

**Removed as dead/ineffective:** `.github/workflows/validate_naming.py` (never
invoked) and `.github/scripts/performance_validation.py` (always skipped; its
assertions duplicated `test_verify_ci_workflow.py`).

## 4. Acceptance-criteria traceability

| AC | Description | Status | Notes |
|----|-------------|--------|-------|
| AC1 | Dependency caching via `actions/setup-python` | ✅ Done | pip download cache keyed on `pyproject.toml` |
| AC2 | Reusable environment setup via composite action | ✅ Done | `setup-python-deps` used by all jobs |
| AC3 | Remove unnecessary `actions/setup-node` | ✅ Done | pure-Python lint; JS actions use `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` |
| AC4 | Cache the virtual environment across jobs | 🟡 Partial | pip download cache only; `pip install -e .[dev]` re-runs each job (backlog O2) |
| AC5 | Parallelize independent validation | 🟡 Partial | `check` ∥ `test` (O1 done); PR-metadata validators still sequential steps (backlog O4) |
| AC6 | Reuse build artifacts in deploy | ❌ Not done | deploy is a stub (backlog O7 / separate ticket) |
| AC7 | Extract common logic for maintainability | ✅ Done | composite action + scripts/tests/workflows split |

## 5. Completeness evaluation & verdict

Core goals (FR-16/17, QR-09, AC1–AC3, AC7) are **complete and shippable**. Open
gaps: **AC4** (venv reuse), **AC5** (validator consolidation), **AC6** (deploy).
QR-08 is **mostly** met (pip cache, one setup action, no Node, `check` ∥ `test`) —
the remaining lever is venv reuse. The 30–50 % runtime claim remains **unmeasured**;
the CI-timing-benchmark plan (separate document) is how it is closed.

**Delivered beyond the original plan:** the combined 4-section PR quality-gate
summary, the traceability generator-gate split, the always-run `publish` job
(comment on every run + per-run comment), the `environment: "false"` root-cause
fix, `benchmark.yml`, the CI self-test suite gating in CI, and Dependabot.

## 6. PR reporting model (implemented)

- **Publisher:** the `publish` job (`if: always()`) posts on **every** run — even
  when `check` fails and `test` is skipped (degrades gracefully). Non-gating.
- **Two comments per run (Option C):** a **sticky** full report updated in place
  (with an `_Updated: … UTC_` timestamp), plus a compact **per-run comment**
  (overall result + overview table) posted fresh each run for a per-run trail.
- **Structure (un-numbered):** overall result + a status-overview table (Lint +
  the steps), then sections **Traceability** → **Testing** → **Code Coverage** →
  **Artifacts**. The **job summary** ("PR Run") uses the same renderer and embeds
  the full traceability matrix; the comment links to it instead.
- **Testing is split** into two independent groups, each with its own status,
  pass rate and per-level total: **Application Tests** (unit/integration/system)
  and **CI-Pipeline Tests** (`.github/tests`).

## 7. Optimization backlog (benefit vs. effort)

| # | Optimization | Benefit | Effort | Risk | Status |
|---|--------------|---------|--------|------|--------|
| O1 | Run `check` and `test` in parallel | High (~40 % wall time) | Low | Low | ✅ Done |
| O5 | Run `.github/tests/` in CI (gate workflow/script regressions) | Med | Low | Low | ✅ Done |
| O3 | Dependabot for actions + Node-20 deprecation handling | Med | Low | Low | ✅ Done |
| O2 | Cache the installed venv/site-packages (AC4) | Med (~10–15 s/job) | Med | Med (stale env) | ⬜ Backlog |
| O4 | Consolidate PR validators into one `validate_pr.py` (AC5) | Low–Med | Med | Low | ⬜ Backlog |
| O6 | Remove unused `flake8` from `[dev]` | Low | Trivial | None | ⬜ Backlog |
| O7 | Implement deploy (AC6): `python -m build` + artifact reuse | High (feature) | High | Med | ⬜ Separate ticket |
| O8 | Capture a runtime baseline / continuous timing benchmark | Med | Med | Low | ⬜ See CI-timing plan |
| O9 | Aggregate lint failures (run all four tools, collect) | Low (DX) | Low | Low | ⬜ Backlog |
| O10 | Python version matrix | Low (single target) | Med | Low | ❌ Out of scope |

**Highest remaining ROI:** O2 (venv cache → AC4/QR-08) and O8 (measure runtime).
O7 completes AC6 but is a feature in its own right.

## 8. Post-implementation addenda

### A. Composite-action checkout fix

Every run initially failed at the first `check` step: *"Can't find 'action.yml' …
Did you forget to run actions/checkout before running your local action?"* Root
cause: a local (`./`) composite action can only be resolved once the repo is
checked out, but the refactor had placed `actions/checkout` **inside** the
composite action (chicken-and-egg). Fix: hoist `actions/checkout@v5`
(`fetch-depth: 0`) into each job before the composite action; the composite action
keeps Python setup + pip cache + install. `fetch-depth: 0` is required by the
Jira-reference commit-range check (`base.sha..head.sha`).

### B. Composite-vs-inline **setup** benchmark (`benchmark.yml`)

On-demand (`workflow_dispatch`) benchmark that compares the composite action
against the same steps inlined, to demonstrate the maintainability win (QR-09)
carries no runtime penalty. A `warmup` job primes the shared pip cache; two 8-run
matrix jobs time the warm-cache setup window with `date +%s.%N`; a `summary` job
reports mean/median/stddev per variant. Expectation: within run-to-run noise.
This measures **setup only** — see the separate *CI-timing benchmark* plan for
measuring the whole pipeline continuously.

### C. Environment "false" fix & reporting evolution

The dynamic `environment:` expression created junk environments (`false`, `dev`,
`develope`); replaced with static labels and the junk environment deleted. The PR
summary evolved from two separate comments → one combined sticky → sticky + per-run
comment (Option C), with un-numbered sections and split Application/CI-Pipeline
testing.

## 9. Original phased plan (archived, superseded)

The original plan proposed six phases: (1) dependency caching, (2) reusable
composite action, (3) remove Node.js, (4) parallelize validation, (5) deployment
artifact reuse, (6) maintainability/shared templates — on a 10-week timeline with
a 30–50 % runtime-reduction target and >80 % cache-hit / 100 % stability metrics.
Phases 1–3 and 6 landed (AC1–AC3, AC7); phase 4 landed partially as job-level
parallelism (AC5 partial); phase 5 (AC6) was deferred. The week-by-week timeline
and the unmeasured runtime target are retained here only for historical context —
the authoritative status is Sections 2–7 above.

## 10. Risks, out-of-scope, definition of done

**Key risks & mitigations:** stale caches (hash-keyed on `pyproject.toml`);
composite action breaking jobs (covered by `test_verify_ci_workflow.py`);
artifact-reuse skipping rebuilds (AC6 deferred, so not yet a risk); unmeasured
runtime target (addressed by the CI-timing benchmark).

**Out of scope:** matrix testing, splitting tests into parallel jobs, branch- or
deployment-strategy changes, quality-gate threshold changes, CI-platform migration.

**Definition of done (delivered subset):** AC1–AC3 + AC7 done; quality gates,
branch strategy, deployment strategy and the 90 % coverage gate unchanged;
`.github/tests` green; documentation updated (this file, `AGENTS.md`,
`doc/CONTRIBUTING.md`, `doc/TESTING.md`, `README.md`). Deferred: AC4, AC5 (full),
AC6, and the measured runtime target.

---
*Consolidated from the former `00_Implementation_Plan_PRO-368.md`,
`PRO-368_IMPLEMENTATION_STATUS.md` and `doc/PRO-368_CI_Evaluation.md`.*
