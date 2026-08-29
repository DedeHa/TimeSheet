# AGENTS.md — TimeSheetAlgo

## Critical Commands (Agents often miss these specifics)

**Install development dependencies** (required for local work):
```bash
python -m pip install -e .[dev]
```

**Activate virtual environment when switching branches** (critical for config):
```bash
git checkout <branch-name>
source /workspaces/TimeSheet/.venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

**Run complete test suite with coverage verification** (required for PRs to master):
```bash
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing
```
- Must achieve ≥90% branch+line coverage (CI gate)
- Output shows missing coverage areas

**Run specific test types** (use markers or folder paths):
```bash
python -m pytest tests/unit -m unit          # Unit tests only
python -m pytest tests/integration -m integration  # Integration tests only
python -m pytest tests/system -m system      # System tests (requires real data files)
python -m pytest -m "not system"             # Fast CI mode (skip system tests)
```

**Run full test suite locally** (verifies all checks):
```bash
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing -q
```

**Code quality checks** (required for PRs):
```bash
# Linting and formatting
ruff check src_timesheetalgo tests
black --check src_timesheetalgo tests
pydocstyle src_timesheetalgo tests
radon cc src_timesheetalgo -a

# Documentation traceability (generates the matrix; exits non-zero if incomplete)
python .github/scripts/generate_traceability_matrix.py
```

**Run the CI-pipeline tests before committing changes under `.github/`**
(scripts, tests, actions, or the workflow YAML). The `check` job runs these in
CI (`Run CI self-tests (.github/tests)`), so they now gate the pipeline —
running them locally first just avoids a red CI run:
```bash
pytest -q .github/tests/
```
- Covers `test_verify_ci_workflow.py` (workflow structure/regression),
  `test_generate_pr_summary.py`, and `test_generate_traceability_matrix.py`
- All must pass before you commit; treat a failure here exactly like a failing
  application test

## Critical Project Structure (Agents often miss these paths)

- **Main package**: `src_timesheetalgo/`
  - `TimeSheetAlgo.py` - entrypoint
  - `config.yaml` - configuration file

- **Test structure**:
  - `tests/unit/` - Unit tests (79 tests)
    - Test configuration loading, date parsing, file validation
    - All test files use `@pytest.mark.unit` marker
  - `tests/integration/` - Integration tests (17 tests)
    - Tests `TimeSheetProcessor` pipeline on in-memory workbook
    - All test files use `@pytest.mark.integration` marker
  - `tests/system/` - System tests (7 tests, requires real data)
    - Black-box tests against real Excel/CSV files
    - All test files use `@pytest.mark.system` marker
  - Shared `tests/conftest.py` with fixtures and frozen_time

- **Key artifacts**:
  - `src_timesheetalgo/TimeSheetAlgo.py` - Main application module
  - `src_timesheetalgo/config.yaml` - YAML configuration
  - `.github/workflows/python-ci.yml` - CI pipeline
  - `doc/ARCHITECTURE.md` - System architecture (600 lines)
  - `doc/TESTING.md` - Complete testing guide (222 lines)
  - `doc/CONTRIBUTING.md` - Development standards (539 lines)
  - `.github/agents/` - Agent definitions for different roles

## Configuration Structure (`src_timesheetalgo/config.yaml`)

```yaml
year: 2026

environments:
  development:
    file_paths:
      timelog_path: "FDTech_timelog.csv"
      timesheet_path: "2026_FDTech_Dennis_Hartel.xlsm"
    logging:
      level: "INFO"
      format: "%(asctime)s - %(levelname)s - %(message)s"

  production:
    file_paths:
      timelog_path: "Timealarm/FDTech_timelog.csv"
      timesheet_path: "2026_FDTech_Dennis_Hartel.xlsm"
    logging:
      level: "INFO"
      format: "%(asctime)s - %(levelname)s - %(message)s"

default_environment: "development"
```
- **Note**: Paths are **relative to project root**, not script location
- Environment auto-detection based on folder structure
- Year is required at root level - no fallback

## Environment & Branch Management

**Critical**: Virtual environment is `.venv/` (not `venv/`) and must be reactivated when switching branches:

```bash
# Switching branches requires venv reactivation
git checkout feature/PRO-123-description
source /workspaces/TimeSheet/.venv/bin/activate
echo "✅ venv activated: $VIRTUAL_ENV"  # Should show /.venv path
```

**Virtual Environment Notes**:
- `.venv/` is gitignored and works across all branches
- You don't reinstall packages when switching branches
- Failure to reactivate causes ModuleNotFoundError for local packages

## Testing Requirements

- **103 total tests** (79 unit + 17 integration + 7 system + 1 xfail)
- **~99% branch/line coverage** (CI gate: 90%)
- **System tests require real data**: 
  - `sup/2025_extract.csv` - 93 sample timelog entries
  - `src_timesheetalgo/2026_FDTech_Dennis_Hartel.xlsm` - 12-month workbook
- All tests have markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.system`
- `freezegun` provides frozen_time fixture for deterministic date handling

## Gotchas Agents Commonly Miss

1. **Virtual Environment Activation**: `.venv/` is gitignored. Must reactivate when switching branches.

2. **System Test Data**: Files are committed to repo but tests skip cleanly when missing.

3. **Configuration Path Resolution**: Working directory must be repository root.

4. **Environment Detection**: Auto-detected by folder structure, not config parameter.

5. **No Pre-tests on Development Branches**: Tests run on PRs (to master or release/**), on release tags, and via manual dispatch — not on direct branch pushes.

## Critical Conventions

**Git Branch Strategy** (Trunk-based Development):
- Feature: `feature/PRO-123-description` (direct pushes allowed)
- Bugfix: `bugfix/PRO-123-description` (direct pushes allowed)
- Hotfix: `hotfix/PRO-123-description` (direct pushes allowed)
- Refactor: `refactor/PRO-123-description` (direct pushes allowed)
- Docs: `docs/PRO-123-description` (direct pushes allowed)
- Test: `test/PRO-123-description` (direct pushes allowed)
- Release: `release/vX.Y.Z` (protected, PR required)
- Master: Always protected (PR + tests required)

**Commit Messages** (Conventional Commits):
- Format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `ci`, `build`
- Footer: `Refs: PRO-123` (JIRA ticket reference)
- Scope optional but recommended for specific modules

**Pull Requests**:
- Target: Always `master`
- Title: `[type][PRO-XXX] Description`
- Body: Required `## Summary` and `## Testing` sections
- No placeholder text (TODO, TBD, etc.)
- **CI will fail the PR** if any of these are missing — the naming validation job blocks merge

**Release Process**:
- Create `release/vX.Y.Z` from master
- Commit version bump: `chore(release): bump version to vX.Y.Z
  
  Refs: PRO-123`
- Tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
- Deploy only from tags

**Environment Management**:
- Environment detected by folder structure (`src_timesheetalgo/` = development, contains `Timealarm/` = production)
- `.venv/` works across branches but must be reactivated
- Configuration paths are relative to project root

## Testing Architecture

Three-level hierarchy matching runtime boundaries:

**Unit** (`tests/unit/`, marker `unit`):
- Configuration subsystem
- Date parsing logic (with calendar/leap-day BVA)
- File I/O (tmp files, mocks)
- Overwrite decision logic

**Integration** (`tests/integration/`, marker `integration`):
- `TimeSheetProcessor` pipeline on in-memory workbook
- Data model mapping (`date.month - 1`, `ROW_OFFSET + day`, cols E/F)
- Overwrite workflow

**System** (`tests/system/`, marker `system`):
- Real-file copies in `tmp_path`
- End-to-end CLI flow
- Skipped when real resources are absent (uses `real_resource_copy` fixture)

**Fixtures**:
- `frozen_time` - autouse, freezes to 2025-12-23 (degrades with warning if `freezegun` absent)
- `mock_workbook` - dummy 12-sheet workbook
- `mock_processor` - `TimeSheetProcessor` over mock files
- `real_resource_copy` - copies from `sup/` and `src_timesheetalgo/` or `None` if missing

## Quality Gate & CI

**GitHub Actions** (`.github/workflows/python-ci.yml`) — `check` and `test` run **in parallel** (no `needs` between them); `deploy` and `publish` depend on both:
- PRs to `master`: Full CI (Lint + Unit + Integration + System + Coverage)
- PRs to `release/**`: Full CI (same quality gate as master)
- Tags `vX.Y.Z`: Full CI (Lint + Tests + Coverage) re-run as a release gate, then Deployment — deploy only proceeds if `check` and `test` pass
- The **CI self-tests** (`pytest -q .github/tests/`) run in the `test` job and appear as a **CI Self-Tests** level in the summary; workflow/script regressions are a CI gate.
- **Environments** (GitHub deployment labels) are static: `check` → `development`, `test` → `staging`, `deploy` → `production`. Do **not** reintroduce a dynamic `environment:` expression — a previous one coerced to the boolean `false` and auto-created a junk environment named "false".
- **Dependabot** (`.github/dependabot.yml`) bumps action versions weekly; its PRs are exempt from the `PRO-XXX` naming validators via `github.actor != 'dependabot[bot]'` guards.

**Pull Request Quality-Gate Summary** (PRO-337):
- A dedicated `publish` job (`if: always()`, depends on the gating jobs) publishes it, so a comment is posted on **every** run — even when `check` fails and `test` is skipped (the summary degrades gracefully). It is non-gating.
- **Two comments per run (Option C):** one **sticky** comment (updated in place, carrying an "_Updated: … UTC_" timestamp) with the full report, plus a compact **per-run comment** (`<!-- pro-337-ci-run-line -->`) — the overall result + the status-overview table — posted fresh each run for a per-run trail.
- The full report opens with the overall result + a **status-overview table** (Lint + the steps, **un-numbered**), then sections: **Traceability** (0–100%; matrix embedded in the PR Run, linked in the comment) → **Testing** (split into **Application Tests** (unit/integration/system) and **CI-Pipeline Tests** (`.github/tests`), each with its own pass-rate %, status and per-level table) → **Code Coverage** (% + 90%-gate status) → **Artifacts** (run, matrix, JUnit/coverage, htmlcov)

**Traceability Validation**:
- `.github/scripts/generate_traceability_matrix.py` scans requirements and architecture
- The script is the gate: it exits non-zero if any requirement is untraced
- Publishes the matrix as an artifact; its summary is folded into the PR quality-gate comment above (rendered by `generate_pr_summary.py`)

## Development Workflow

**Phase 1: Feature Development** (Tests optional)
```bash
# Create feature branch
git checkout -b feature/PRO-123-description master

# Make changes, commit with PRO ticket
# No tests required on feature branch
```

**Phase 2: Integration to Master** (Tests REQUIRED)
```bash
# Open PR to master
gh pr create --base master --title "[feat][PRO-123] Description"

# Required CI checks:
# - Lint checks (Ruff, Black, Pydocstyle, Radon)
# - Unit tests
# - Code coverage ≥90%
# - At least one approval
```

**Phase 3: Release** (Production only)
```bash
# Create release branch
git checkout -b release/vX.Y.Z master

# Update version, create final commit
# Open PR to master, get approval
# After merge: git tag vX.Y.Z && git push origin vX.Y.Z

# Deployment to Production (automation or manual)
```

## CI Validation Steps

Complete validation on PRs to master:
1. **Dependencies**: `pip install -e .[dev]`
2. **Lint**: `ruff check src_timesheetalgo tests`, `black --check src_timesheetalgo tests`, etc.
3. **Documentation traceability**: `python .github/scripts/generate_traceability_matrix.py` (fails if any requirement is untraced)
4. **Test suite**: `pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing`
5. **Quality-gate summary**: Generated automatically

## CI Validation Checks (What Fails PRs)

The CI pipeline (`.github/workflows/python-ci.yml`) has a **Naming Conventions Check** job that runs first and blocks merge if any of these fail:

| Check | What's Validated | Failure Reason |
|-------|-----------------|----------------|
| Commit messages | Conventional Commits + `Refs: PRO-XXX` | Missing JIRA ref or wrong format |
| PR title | `[type][PRO-XXX] Description` | Wrong format or missing ticket |
| PR body | `## Summary` + `## Testing` + `Refs: PRO-XXX` + no TODO/TBD | Missing sections, missing ref, or placeholder text |

**Key rule**: All three checks must pass before lint/test jobs even run. A failure in any blocks the entire pipeline.

1. **Forget venv activation**: After `git checkout`, always `source .venv/bin/activate`

2. **System test failures**: When real files are missing, tests skip (not fail). Restore with `git checkout sup/2025_extract.csv src_timesheetalgo/2026_FDTech_Dennis_Hartel.xlsm`

3. **Configuration loading**: Must be in repository root, not script directory

4. **Coverage gate**: Must meet 90% target; CI publishes detailed missing coverage areas

5. **PR validation**: Tests run on PRs (master or release/**), release tags, and manual dispatch — not on direct branch pushes

## CI Workflow Optimizations (PRO-368)

The CI pipeline (`python-ci.yml`) has been optimized. An agent editing the workflow should know:

- **Reusable setup action**: All three jobs (`check`, `test`, `deploy`) now start with
  `uses: ./.github/actions/setup-python-deps` (FR-17, QR-09). Do **not** add a
  second `actions/checkout` + `actions/setup-python` + `pip install -e .[dev]`
  block — that is duplicated, obsolete setup logic.
- **Pip caching**: The composite action passes `cache: pip` /
  `cache-dependency-path: pyproject.toml` to `actions/setup-python` (FR-16).
  Cache keys are based on `pyproject.toml`, so dependency changes invalidate.
- **No Node.js in the check job**: `actions/setup-node` was removed (AC3).
  JavaScript actions (commitlint, github-script) run on the Node 24 runtime
  provided by `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`. Do not re-add
  `setup-node` unless a step actually needs a Node tool.
- **Validation steps are separate, independent steps** (AC5): `Validate commit
  messages`, `Validate Jira reference in commits`, `Validate PR Title`,
  `Validate PR Body`. Steps within a job run **sequentially** (GitHub Actions);
  "independent" means each is its own step so a failure is individually
  attributable — not that they run in parallel. The first uses
  `continue-on-error: true` (third-party action); the other three must keep
  `continue-on-error: false` or the gate silently degrades.
- **CI support-script tests live under `.github/tests/`** (not in `tests/`), so
  they do not count toward the 103-test suite or the 90% coverage gate. The
  `check` job runs them (`Run CI self-tests`), so they **gate** the pipeline:
  - `.github/tests/test_verify_ci_workflow.py`
  - `.github/tests/test_generate_pr_summary.py`
  - `.github/tests/test_generate_traceability_matrix.py`
  - **Run `pytest -q .github/tests/` locally before committing any change under
    `.github/`** so CI does not fail on a workflow/script regression.
- **CI support scripts live under `.github/scripts/`** (verb_subject naming):
  `generate_pr_summary.py`, `generate_traceability_matrix.py`. `.github/workflows/`
  holds workflow definitions only (no `.py`).
- **Traceability**: PRO-368 added `FR-16`, `FR-17`, `QR-08`, `QR-09` to
  `doc/REQUIREMENTS.md`, `doc/ARCHITECTURE.md`, and the anchor comment in
  `src_timesheetalgo/TimeSheetAlgo.py`. The traceability validator
  (`python .github/scripts/generate_traceability_matrix.py`) requires all
  three sources to list the same IDs — update all three together.
- **Composite setup action location**: The reusable setup action lives at
  `.github/actions/setup-python-deps/action.yml` and is referenced as
  `uses: ./.github/actions/setup-python-deps`. A local composite action must be
  referenced by its **directory**, never by the `action.yml` file path, and must
  **not** live under `.github/workflows/` (GitHub would try to parse it as a
  workflow). Every `run:` step in the composite action requires an explicit
  `shell:` line.

## CI Timing Benchmark (PRO-369)

A separate `ci-timing.yml` workflow continuously captures per-job / per-step
execution times from the GitHub Actions API for every successful PR run of
`python-ci.yml`, persists them on the orphan `ci-metrics` branch, and renders
`CI_TIMING_REPORT.md` with running statistics.

**Key facts agents must know:**

- **Non-gating**: this workflow never fails a PR. It is purely observational.
- **Location**: `ci-metrics` branch → `ci-timings.csv` (raw rows) and
  `CI_TIMING_REPORT.md` (aggregated stats). Report link in the PR quality-gate
  comment.
- **No CI loop**: `python-ci.yml` does not trigger on push to `ci-metrics`,
  so the metrics push never starts a new CI run.
  (`test_ci_timing_does_not_retrigger_python_ci` in
  `.github/tests/test_verify_ci_workflow.py` enforces this.)
- **Scope**: successful `pull_request` runs of `Python CI` only. Failed,
  cancelled, timed-out, skipped, and superseded runs are excluded automatically.
- **Data source**: authoritative API timing (`started_at` / `completed_at`) —
  no workflow instrumentation required.
- **Scripts** (stdlib-only, in `.github/scripts/`):
  `collect_ci_timings.py` (fetch + filter one run),
  `aggregate_ci_timings.py` (render stats + report),
  `backfill_ci_timings.py` (historical sweep).
- **Tests** (in `.github/tests/`): `test_collect_ci_timings.py`,
  `test_aggregate_ci_timings.py`, `test_backfill_ci_timings.py`.
- **Runner variance caveat**: GitHub-hosted runners are noisy (±10–30%).
  Always read stddev alongside mean; prefer median / p95 for decisions.
- **Drift handling**: a step key is withheld from the main tables until it has
  ≥ 3 warm, successful samples. Retired / renamed keys appear in an appendix.
- **Backfill**: `workflow_dispatch` with `backfill: true` sweeps all historical
  successful PR runs. The sweep is idempotent (re-running is a no-op).
- **Do not commit timing results** to the PR branch — they belong on `ci-metrics`.
- See `doc/01_Implementation_Plan_CI_Timing_Benchmark.md` for the full plan.

## JIRA Workflow Skills

Two skills support the end-to-end JIRA ticket lifecycle:

- **`.opencode/skills/plan-feature/`** — Canonical template for discovering, planning, and scoping new Story tickets. Based on analysis of PRO-370, PRO-369, PRO-368, PRO-367, PRO-366, PRO-365. Includes field definitions, description structure, AC/DoD formats, story points reference, and quick-start checklist.
- **`.opencode/skills/complete-feature/`** — Workflow for completing a feature: final verification, AC evaluation, story point assignment, JIRA closure, PR update, commit/push.

## ⛔ Agent-Team Closure Policy (CRITICAL)

> The agent-team **must NOT** autonomously close JIRA tickets or merge PRs.
> These are reserved for the user or Product-Owner.

| Operation | Agent-Team Allowed? | Who Decides |
|-----------|--------------------|--------------------|
| Prepare AC/DoD checkmarks in JIRA description | ✅ Yes | Agent |
| Post JIRA status comment | ✅ Yes | Agent |
| Assign story points (`customfield_10028`) | ✅ Yes | Agent |
| Update PR description (`gh pr edit`) | ✅ Yes | Agent |
| Push branch (`git push`) | ✅ Yes | Agent |
| **Transition JIRA to Fertig (`atlassian_transitionJiraIssue`)** | ❌ **No** | **User / PO** |
| **Merge PR (`gh pr merge`)** | ❌ **No** | **User / PO** |
| **Delete remote branch after merge** | ❌ **No** | **User / PO** |

**Rationale:** JIRA closure and PR merges are irreversible quality-gate
decisions. They require human review of the agent-team's work to catch
context the agent may have missed (acceptance-criteria drift, scope creep,
business priorities). The agent-team **prepares** the close; the user
**executes** it.

When the `complete-feature` skill reaches Step 3d (Transition to Done), it
must hand off to the user / PO instead of calling
`atlassian_transitionJiraIssue` directly. See
`.opencode/skills/complete-feature/SKILL.md` Step 3d for the exact
wording.

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> a70971c (docs: add agent-team workflow documentation to AGENTS.md)
## Agent-Team Workflow

The four agent definitions in `.github/agents/` form a coordinated pipeline. Each agent loads the relevant `.opencode/skills/` skill at its step.

### Key-Request → Agent → Skill Mapping

| Key-Request | Trigger | Agent Team Member | Skill Invoked |
|-------------|---------|-------------------|---------------|
| "plan a new feature" | User intent | **Product Owner** (`product-owner-agent`) | `plan-feature` |
| "plan a bug fix" | Bug report | **Product Owner** (`product-owner-agent`) | `plan-feature` |
| "start feature PRO-XXX" / "implement ticket PRO-XXX" / "work on PRO-XXX" | Existing JIRA ticket | **Architect** (`architect-agent`) → **Developer** (`developer-agent`) | `develop-feature` |
| "complete feature" / "finalise implementation" | PR ready | **Tester** (`tester-agent`) → `complete-feature` skill | `complete-feature` |
| "release" / "create a release vX.Y.Z" / "tag vX.Y.Z" | Release ready | **Release** (manual trigger) | `release-project` |

### Pipeline

```
Key-Request → Agent Team Member → Uses Skills
```

| Step | Key-Request | Agent | Skill | What It Does |
|------|-------------|-------|-------|--------------|
| 1 | "plan a new feature" | **Product Owner** | `plan-feature` | Analyze user intent, define stories with AC, create JIRA ticket (Phase 5), assign story points |
| 2 | "start feature PRO-XXX" | **Architect** | `develop-feature` | Translate stories into technical design, produce implementation plan (Part A/B/C format) |
| 3 | "start feature PRO-XXX" | **Developer** | `develop-feature` | Implement features per plan (Phases 3–7: branch, rollout, verification, PR) |
| 4 | "complete feature" | **Tester** | `complete-feature` | Validate AC, run tests, verify coverage ≥90% CI gate |
| 5 | "complete feature" | **Tester → complete-feature** | `complete-feature` | Assign story points, update JIRA description, checkmark ACs/DoD, update PR |
| 6 | *(release)* | *(manual)* | `release-project` | Tag vX.Y.Z, publish GitHub Release, Confluence release notes |

### Skill Invocation Rules

- Each agent **must** load its listed skill before executing its workflow
- Skills are loaded from `.opencode/skills/<skill-name>/SKILL.md`
- The `invoke` field controls when the skill loads: `always` (before any work), `after-testing` (after test approval), `after-approval` (after tester approves)
- The `phases` field lists the skill phases applicable to that agent step

### Handoff Protocol

1. **PO → Architect**: Pass complete User Story output with acceptance criteria
2. **Architect → Developer**: Pass implementation plan (Part A/B/C), file list, test strategy
3. **Developer → Tester**: Pass implementation output, acceptance criteria, coverage metrics
4. **Tester → complete-feature**: After PASSED decision, load `complete-feature` skill to prepare JIRA close (assign story points, checkmark ACs/DoD, update PR description)
5. **complete-feature → User/PO**: Hand off the prepared ticket. The user / Product-Owner calls `atlassian_transitionJiraIssue` and `gh pr merge` — the agent-team must not
6. **Release**: Trigger `release-project` skill manually when ready to publish

### How to Trigger the Agent Team

The agent team is triggered by **natural language key-requests**:

- **"plan a new feature"** → Product Owner → `plan-feature` skill → creates JIRA ticket
- **"plan a bug fix"** → Product Owner → `plan-feature` skill → creates JIRA ticket
- **"start feature PRO-XXX"** or **"implement ticket PRO-XXX"** → Architect → Developer → `develop-feature` skill → implements feature
- **"complete feature"** or **"finalise implementation"** → Tester → `complete-feature` skill → validates and prepares closure
- **"release vX.Y.Z"** → Manual trigger → `release-project` skill → publishes release

Each key-request maps to a specific agent team member who loads the matching skill. The user provides the key-request; the agent team executes the steps.

### Quality Gates (CI)

- **Coverage**: ≥90% branch+line (`AGENTS.md` CI gate)
- **Lint**: `ruff check`, `black --check`, `pydocstyle`, `radon cc`
- **Tests**: Unit + Integration + System (system tests skip when real data absent)
- **Traceability**: `python .github/scripts/generate_traceability_matrix.py` — exits non-zero if any requirement untraced
- **CI self-tests**: `pytest -q .github/tests/` — gates the pipeline

<<<<<<< HEAD
=======
>>>>>>> 441e55a (docs: add JIRA workflow skills section and story point assignment)
=======
>>>>>>> a70971c (docs: add agent-team workflow documentation to AGENTS.md)
## Additional Resources

- **Branch Protection**: GitHub Settings → Branches
- **Agent Types**: Check `.github/agents/` for specialized roles: `architect-agent`, `developer-agent`, `tester-agent`, `product-owner-agent`
- **Commit Messages**: `.github/workflows/python-ci.yml` validates Conventional Commits format
- **Documentation**: `doc/ARCHITECTURE.md` - `doc/CONTRIBUTING.md` - `doc/TESTING.md`

> **Critical**: All paths in this guide are relative to the repository root. The working directory must be `/workspaces/TimeSheet` for proper configuration and file access.