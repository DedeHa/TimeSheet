# PRO-368 — CI Optimization: Completeness Evaluation & Optimization Backlog

Companion to [00_Implementation_Plan_PRO-368.md](00_Implementation_Plan_PRO-368.md)
and [../PRO-368_IMPLEMENTATION_STATUS.md](../PRO-368_IMPLEMENTATION_STATUS.md).
This document records where the CI-optimization feature stands and which
optimizations remain, with a benefit assessment for each.

## 1. Completeness of the feature

### Requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-16 | pip dependency caching keyed on `pyproject.toml` | ✅ Done | composite action `cache: pip` |
| FR-17 | Reusable environment setup (composite action) | ✅ Done | `.github/actions/setup-python-deps` used by all jobs |
| QR-08 | CI performance (no redundant work) | 🟡 Mostly | pip cache, one setup action, no Node; `check`∥`test` now parallel; venv still reinstalled per job |
| QR-09 | CI maintainability (single point of change) | ✅ Done | composite action + `scripts`/`tests`/`workflows` split + CI self-tests + Dependabot |

### Acceptance Criteria

| AC | Description | Status | Notes |
|----|-------------|--------|-------|
| AC1 | Dependency caching via `setup-python` | ✅ Done | pip download cache |
| AC2 | Reusable environment setup | ✅ Done | composite action |
| AC3 | Remove unnecessary `setup-node` | ✅ Done | pure-Python lint |
| AC4 | Cache venv across jobs | 🟡 Partial | pip download cache only; `pip install -e .[dev]` re-runs each job (see O2) |
| AC5 | Parallelize independent validation | 🟡 Partial | `check`∥`test` run in parallel (O1 done); PR-metadata validators still sequential steps (see O4) |
| AC6 | Reuse build artifacts in deploy | ❌ Not done | deploy is a stub (`pip install build`) |
| AC7 | Extract common logic for maintainability | ✅ Done | composite action + scripts/tests structure |

### Verdict

Core goals (FR-16/17, QR-09, AC1–AC3, AC7) are **complete and shippable**. Open
gaps: **AC4** (venv reuse), **AC5** (validator consolidation), **AC6** (deploy).
The plan's "30–50% runtime reduction" headline was a **target, never measured**
(no baseline captured); see O8.

### Delivered beyond the original plan

Combined 4-section PR quality-gate summary (overview table + Traceability /
Testing / Coverage / Artifacts), traceability split into a generator-script gate,
a dedicated always-run `publish` job (comment on every run + per-run status
line), the `environment: "false"` root-cause fix, `benchmark.yml`, the CI
self-test suite now gating in `check`, and `.github/dependabot.yml`.

## 2. Optimization backlog (benefit vs. effort)

| # | Optimization | Benefit | Effort | Risk | Status |
|---|--------------|---------|--------|------|--------|
| O1 | Run `check` and `test` in parallel | High (~40% wall time) | Low | Low | ✅ Done |
| O5 | Run `.github/tests/` in CI (gate workflow/script regressions) | Med | Low | Low | ✅ Done |
| O3 | Dependabot for actions + Node-20 deprecation handling | Med | Low | Low | ✅ Done |
| O2 | Cache the installed venv/site-packages (AC4) | Med (~10–15s/job) | Med | Med (stale env) | ⬜ Backlog |
| O4 | Consolidate PR validators into one `validate_pr.py` (AC5) | Low–Med | Med | Low | ⬜ Backlog |
| O6 | Remove unused `flake8` from `[dev]` | Low | Trivial | None | ⬜ Backlog |
| O7 | Implement deploy (AC6): `python -m build` + artifact reuse | High (feature) | High | Med | ⬜ Separate ticket |
| O8 | Capture a runtime baseline to substantiate/close the 30–50% metric | Low | Low | None | ⬜ Backlog |
| O9 | Aggregate lint failures (run all four tools, collect) | Low (DX) | Low | Low | ⬜ Backlog |
| O10 | Python version matrix | Low (single target) | Med | Low | ❌ Out of scope |

**Highest remaining ROI:** O2 (venv cache → advances AC4/QR-08) and O8 (measure
runtime to close the DoD honestly). O7 completes AC6 but is a feature in its own
right and should be a separate ticket.

## 3. PR reporting model (implemented)

- **Job graph:** `check` ∥ `test` → `deploy`, `publish`.
- **`publish` job** (`if: always()`) posts on **every** run, even when `check`
  fails and `test` is skipped.
- **Two comments per run (Option C):** a **sticky** full report updated in place
  (with an `_Updated: … UTC_` timestamp), plus a compact **per-run comment**
  (`<!-- pro-337-ci-run-line -->`) — overall result + the overview table — for a
  per-run trail. The full report opens with the overall result + an (un-numbered)
  status-overview table, then the sections Traceability → Testing → Code Coverage
  → Artifacts. The **Testing** section includes a **CI Self-Tests** level
  (`.github/tests`), so the CI self-tests are counted in the test totals.
- **Steps overview:** the GitHub Actions run page relies on the job-summary
  render (same content as the comment) for the human-readable overview; per-level
  test steps stay separate for attributable failures.

### Possible further reporting tweaks (not implemented)

- Collapse the PR-metadata validators into one step (O4) to shorten the `check`
  step list.
- Prune historical standalone bot comments on PR #95 (pre-Option-C clutter).
