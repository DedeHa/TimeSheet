# TimeSheetAlgo Testing Documentation

**Before running tests:** install the dev dependencies with
`python -m pip install -e .[dev]` (provides `pytest`, `pytest-cov`,
`freezegun`, etc.).

This is the single reference for the test suite of
`src/TimeSheetAlgo.py` — its layout, the intent of each level, the
fixtures, and the configuration behind them.

## Layout

```text
tests/
  conftest.py                    # shared: frozen_time, sys.path, workbook/processor builders
  boundary_equivalence_analysis.md  # ECP/BVA analysis, derived cases, findings
  @tests/unit/
    conftest.py                  # clean_root_logger
    test_config.py               # load_config, _read_yaml, detect_environment, ConfigError
    test_logging.py              # configure_logging
    test_dates.py                # parse_date (incl. calendar/leap-day BVA), _get_date, set_default_start/end_date
    test_input_provider.py       # InputProvider injection (no builtins.input mock)
    test_clock.py                # injected Clock (no freezegun required)
    test_pure_functions.py       # filter_timelog_entries, calculate_default_start_date, map_entry_to_cell
    test_store_result.py         # StoreResult enum + store_data return value
    test_validation.py           # validate_timelog_entry, validate_timesheet_structure
    test_builder.py              # TimeSheetProcessor.for_testing()
    test_files.py                # check_file_existence (csv/excel/lock/permission/not-found, remark column)
    test_processor_methods.py    # load_files, request_date_input, select_timelog_data (range BVA), save_timesheet
    test_overwrite.py            # confirm_overwrite, _prompt_overwrite_decision, _check_and_confirm_overwrite
    test_consistency.py          # check_year_consistency (config vs. timesheet year)
  integration/
    conftest.py                  # processor_with_timelog builder
    test_pipeline.py             # load→select→store→save (single + multi-month + week + remark column)
    test_overwrite_workflow.py   # store_data with overwrite_all / skip_all / abort / empty / EOF / mixed conflicts
    test_boundaries.py           # day 1 / day 31, month boundary, December/last sheet, cross-year filtering
  system/
    conftest.py                  # real_resource_copy, cli_runner
    test_real_pipeline.py        # real copies → TimeSheetProcessor end-to-end, reload & assert cells
    test_cli_main.py             # run()/main() with stdin + tmp config
```

Mapped each level to its folder and marker — unit lives under the `@tests/unit/` sub‑folder.
```

## Testing Architecture

Tests mirror the runtime boundaries described in [docs/ARCHITECTURE.md](ARCHITECTURE.md), in three levels — one folder and one marker each.

| Level | Folder | Exercises |
|-------|--------|-----------|
| unit | `tests/unit/` | one function/method in isolation — the configuration subsystem, date logic, file I/O, and the overwrite-decision logic |
| integration | `tests/integration/` | the processing pipeline on an in-memory dummy workbook — data-model mapping (`month-1`, `ROW_OFFSET+day`, columns E/F), the overwrite workflow, and date boundaries |
| system | `tests/system/` | the shipped `TimeSheetProcessor` / `run()` / `main()` against real-file copies (skipped when the real resources are absent) |

Mapping back to the architecture: the **configuration subsystem** is verified at the unit level (`tests/unit/test_config.py`), the **data model** and **overwrite decision** at the integration level, and the **processing pipeline** end-to-end at the system level. Coverage is gated at 90% (`[tool.coverage]` in `pyproject.toml`).

## Traceability Validation

Requirement-to-architecture-to-code traceability is generated and validated by [.github/scripts/generate_traceability_matrix.py](../.github/scripts/generate_traceability_matrix.py). The script scans [docs/REQUIREMENTS.md](REQUIREMENTS.md) for FR-XX / QR-XX identifiers, checks that each requirement appears in [docs/ARCHITECTURE.md](ARCHITECTURE.md), confirms implementation references in [src/TimeSheetAlgo.py](../src/TimeSheetAlgo.py), and exits non-zero (failing the build) when any requirement is missing a mapping — so the script is itself the CI quality gate. Its parsing/rendering logic is unit-tested by
[tests/ci-pipeline/test_generate_traceability_matrix.py](../tests/ci-pipeline/test_generate_traceability_matrix.py),
which the `check` job runs as part of the CI self-tests
(`pytest -q tests/ci-pipeline/`). The generated markdown matrix is published in the GitHub Actions job summary and stored as an artifact for pull requests.

## Agent-System Tests

The agent-team pipeline (4 agents + 5 skills) is validated by a dedicated `agents` CI job in
[.github/workflows/python-ci.yml](../.github/workflows/python-ci.yml) that runs
`pytest -q .opencode/tests/agents/` and uploads the JUnit report
(`tests/reports/agent-results.xml`) as an artifact. Agent tests live under
`.opencode/tests/agents/` (not in `tests/`), so they do not change the 103-test
application suite or the coverage gate.

### Layout

```text
.opencode/tests/agents/
├── test_orchestration.py     # Existing - structural tests (YAML frontmatter, file existence, path resolution)
├── test_handoffs.py         # Handoff protocol: placeholders, cycle counts, escalation triggers
├── test_constraints.py      # Agent boundary enforcement via constraints
├── test_agent_outputs.py    # Output format contracts (PO/Architect/Developer/Tester)
├── test_skill_workflows.py  # Skill phase execution order
├── test_pipeline_flow.py    # End-to-end pipeline simulation
├── test_pipeline_recovery.py    # PRO-407 AC-2: what-missed, check-stuck, dry-run, resume, history
├── test_pipeline_read_only.py   # PRO-407 FR-22: read-only commands create no state or history
├── test_pipeline_status.py      # PRO-407 status owned by the CLI; blocking; derived interruption
├── test_handoff_gate.py         # PRO-407 handoff status validation; continue needs a COMPLETED handoff
├── test_dor_gate.py             # PRO-407 AC-3: DoR checklist, waivers, develop gate
├── test_reconcile.py            # PRO-407 AC-4: living-document reconciliation gate
├── test_work_item_ref.py        # PRO-407 ticket Step 6: jira, github, and generic references
├── test_record_handoff.py       # PRO-407 AC-6: handoff recording and rendering
├── test_governance_docs.py      # PRO-407: governance docs, decision records, readiness review
├── test_pipeline_integration.py # PRO-407 integration: CLI flow through pipeline.main() (marker: integration)
├── test_isolation.py            # PRO-407: the suite runs under the isolated HOME
└── conftest.py                  # PRO-407 isolation guard: HOME on a temp dir; fails the session on real-home writes
```

### Test Categories

| File | Category | Exercises |
|------|----------|-----------|
| `test_orchestration.py` | Structural | YAML frontmatter parsing, file existence, path resolution, skill registry consistency |
| `test_handoffs.py` | Handoff protocol | Placeholder extraction, cycle tracking, escalation context, agent references |
| `test_constraints.py` | Constraint enforcement | PO/Architect/Developer/Tester boundary enforcement, cycle limit |
| `test_agent_outputs.py` | Output format | Required markdown sections for each agent's output template |
| `test_skill_workflows.py` | Skill workflow | Phase execution order for orchestrate/plan/develop/complete/release skills |
| `test_pipeline_flow.py` | Pipeline simulation | Full PO→Architect→Developer→Tester flow, cycle escalation, error propagation |
| `test_pipeline_recovery.py` | Recovery commands (FR-22) | Interruption from the clock (fake `now`), the `interrupt` marker, stuck detection, dry-run, forced resume, history |
| `test_pipeline_read_only.py` | Read-only guarantee (FR-22), fail-closed files | Every inspection command on an unknown ticket leaves the state and history files absent or byte-identical; corrupt state or history exits 1 with the bytes unchanged; atomic writes; no home directory created by reads |
| `test_pipeline_status.py` | State machine | CLI-set status, BLOCKED kept by IN_PROGRESS and cleared by COMPLETED or a forced continue, interruption from the clock, blocked resume |
| `test_handoff_gate.py` | Handoff gate | Status validation, `continue` refusal and acceptance, the latest-handoff rule with completed cycles (isolated from the zero-cycle rule), `--force` bypasses the handoff rule only and is recorded as `forced_advance` |
| `test_dor_gate.py` | DoR gate (AC-3) | `dor` and `waive` validation, D1 not waivable, develop gate pass, refuse, waiver, and that `--force` never bypasses the gate |
| `test_reconcile.py` | Reconciliation gate (AC-4) | Path-to-document mapping with an injected file list, and the git diff path in a temporary repository |
| `test_work_item_ref.py` | Work item references | Parametrised classification table, malformed tracker keys, one normaliser (`work_item_arg`) for every command, tracker in handoff history and comment |
| `test_record_handoff.py` | Handoff recording (AC-6) | Handoff schema, rendered comment sections, `handoff` CLI |
| `test_governance_docs.py` | Governance documents | DoR, reconciliation, handoff, decision records, readiness reviewer, traceability IDs |
| `test_pipeline_integration.py` | Integration (`integration` marker) | set-mode, dor, continue, BLOCKED, resume, read-only commands, exact history order, and the exit-code contract (0, 1, 2), all on `tmp_path` |
| `test_isolation.py` | Isolation | HOME is the session temp directory and pipeline paths resolve under it |
| `conftest.py` | Isolation guard | Sets HOME before any import; at session end fails if the original home's pipeline files changed |

**Isolation rule:** no agent test may write to the real `~/.opencode`. Tests redirect
`STATE_PATH` and `HISTORY_PATH` to `tmp_path`. The `conftest.py` guard enforces this for the
whole session and fails it with an `ISOLATION FAILURE` message if a write slips through.

### Running

```bash
# All agent tests
pytest -q .opencode/tests/agents/

# One category
pytest -q .opencode/tests/agents/test_handoffs.py
```

CI runs the agent tests as its own "Agent System Tests" level in the summary, in
parallel with the application test job (no `needs` dependency between them).

## Pull Request Quality-Gate Summary

Every Pull Request targeting `master` publishes one consolidated quality-gate summary, regenerated on every run, in the GitHub Actions **job summary** (the "PR Run" page) and as a **sticky PR comment** (updated in place, never duplicated, carrying an `_Updated: … UTC_` timestamp). A compact **per-run comment** is also posted fresh on every run (Option C) — the overall result plus the status-overview table — giving a per-run trail alongside the always-current sticky report.

The report opens with the **overall workflow result** and a **status-overview table** — one row each for Lint & Formatting and the steps (un-numbered), with status and a one-line summary — so the whole gate is readable at a glance. It then details each step (headings are un-numbered):

- **Traceability** — requirement→code traceability summary (0–100%) + status. The **PR Run** embeds the full traceability matrix table; the **PR comment** shows the percentage plus a link to the matrix artifact.
- **Testing** — split into two independent groups, each with its own pass rate, status and per-level table (executed / passed / failed / skipped + Total): **Application** (the script: Unit / Integration / System) and **CI Pipeline** (the `tests/ci-pipeline` suite). The status overview shows them as separate **Application Tests** and **CI-Pipeline Tests** rows.
- **Code Coverage** — split into two independent sections: **Application Code Coverage** (the script: Unit / Integration / System) and **CI Pipeline Coverage** (the `tests/ci-pipeline` suite). The status overview table shows the 90% quality-gate status on the application coverage.
- **Artifacts** — links covering all aspects: the workflow run, the traceability matrix (`.md` / `.html`), the JUnit reports (incl. `ci-results.xml`) and `coverage.json`, and the HTML coverage report — all inside the `test-results` artifact.

How it is produced:

1. In the `test` job, each level writes a JUnit report (`tests/reports/*-results.xml`, including `ci-results.xml` for the CI self-tests) and `tests/reports/coverage.json` is exported (`coverage json --fail-under=0`); the traceability matrix (`tests/reports/traceability-matrix.md` / `.html`) is written by the earlier traceability step. The CI self-tests are run with a separate coverage data file and exported to `tests/reports/ci-coverage.json`. All are uploaded as the `test-results` artifact.
2. A dedicated `publish` job (`if: always()`, depends on the gating jobs) downloads that artifact and runs [.github/scripts/generate_pr_summary.py](../.github/scripts/generate_pr_summary.py) with the upstream results (`LINT_RESULT=needs.check.result`, `TEST_RESULT=needs.test.result`). It writes the full **sticky** report to `tests/reports/test-summary.md`, the compact **per-run comment** (overview table) to `tests/reports/test-summary-line.md`, and appends the **job-summary** variant (with the matrix embedded) to `$GITHUB_STEP_SUMMARY`.
3. The same job publishes two comments via `actions/github-script`: it updates the **sticky** full report in place (found by a hidden marker), and posts the compact **per-run comment** fresh on every run (Option C) so the PR keeps a per-run trail.

Because the `publish` job runs with `if: always()` in its own job — **not** inside `test` — a PR receives an up-to-date comment on **every** run, including when `check` (lint/naming) fails and the `test` job is skipped (the summary then degrades gracefully, showing lint failed and tests skipped). Publication is non-gating: it only reports results; the merge is still gated by the `check` and `test` jobs.

The generator uses the standard library only and is covered by
[tests/ci-pipeline/test_generate_pr_summary.py](../tests/ci-pipeline/test_generate_pr_summary.py),
which the `test` job runs explicitly (it is outside `testpaths`, so it does
not change the application suite or the coverage gate).

## Test levels and their intent

The suite is split into three levels — one folder and one marker each. The
discriminator is **what the code under test touches**: tmp-file or mocked single
call → unit; `mock_processor` multi-step → integration; real-resource copy or
CLI flow → system. No test appears at two levels.

### 1. Unit (`tests/unit/`, marker `unit`)

One function or method, fully isolated. I/O is a `tmp_path` file or is
monkeypatched (`builtins.input`, `openpyxl.load_workbook`, `detect_environment`,
…). No real project resources, no multi-step pipeline. These pin behaviour and
exact error messages.

- `test_config.py` — `load_config`, `_read_yaml`, `detect_environment`, all `ConfigError`/`KeyError` paths, empty-YAML branch.
- `test_logging.py` — `configure_logging` (custom/default/invalid level, default format).
- `test_dates.py` — `parse_date` (valid / retries-exhausted / retries=0 / retry / calendar-invalid / leap-day BVA), `_get_date` (success + fallback), `set_default_start_date` (with data + no-data fallback + day-31 boundary `xfail`), `set_default_end_date`.
- `test_files.py` — `check_file_existence` (csv/excel happy path, not-found, permission denied, lock warning, 4-column/remark row).
- `test_processor_methods.py` — `load_files`, `request_date_input` (valid/invalid/empty/EOF/specific default), `select_timelog_data` (in-range, empty→ValueError, inclusive-range BVA, single-day, inverted range, empty timelog, malformed row), `save_timesheet`.
- `test_overwrite.py` — `confirm_overwrite`, `_prompt_overwrite_decision`, `_check_and_confirm_overwrite` (the decision logic, in isolation).
- `test_consistency.py` — `check_year_consistency` (year as date, year as text, mismatch → `ConsistencyError`, empty `B3`).

### 2. Integration (`tests/integration/`, marker `integration`)

The `TimeSheetProcessor` pipeline run across multiple steps on the in-memory
dummy 12-sheet workbook (no real `.xlsm`/`.csv`). Verifies the data model:
sheet index = `date.month - 1`, row = `ROW_OFFSET + day`, start in column 5,
end in column 6.

- `test_pipeline.py` — `select → store → save` for single entry, multiple months, a realistic week, and a 4-column row whose remark is ignored.
- `test_overwrite_workflow.py` — how `store_data` *acts* on each decision (overwrite_all / skip_all / abort / empty / EOF), plus mixed occupied+free days (skip keeps the conflict but writes the free day; abort is not atomic).
- `test_boundaries.py` — day 1, day 31, month boundary, December → last sheet, cross-year filtering.

For the equivalence-class and boundary-value rationale behind these cases — and
the findings they document (e.g. the day-31 default-start gap) — see
[`boundary_equivalence_analysis.md`](boundary_equivalence_analysis.md).

### 3. System (`tests/system/`, marker `system`)

Black-box against **real-file copies** in `tmp_path`, driving the shipped code
end-to-end. Skips cleanly (not failed) when the real resources are absent.

- `test_real_pipeline.py` — copies the real CSV + xlsm, runs `TimeSheetProcessor` for a January day, re-opens the saved workbook and asserts the value landed in the right cell. (This replaces the old `VerificationTester`, which re-implemented the algorithm instead of running it.)
- `test_cli_main.py` — exercises the CLI entry points `run()` and `main()` (config load → logging → pipeline) with monkeypatched stdin and a temporary `config.yaml`, including the missing-`year` → `SystemExit(1)` path.

## Fixtures

Defined in `tests/conftest.py` (shared) and cascading into each level's `conftest.py`.

- `frozen_time` — autouse; freezes the clock to 2025-12-23 (degrades to a no-op with a warning when `freezegun` is absent).
- `mock_workbook` / `mock_excel_file` / `mock_csv_file` — dummy 12-sheet workbook and temp files.
- `mock_processor` — a `TimeSheetProcessor` over the mock files, already loaded.
- `make_processor(timelog=…, timesheet_cells=…, year=2025)` — factory building a processor over a fresh dummy workbook with optional pre-populated cells.
- `clean_root_logger` (unit) — clears/restores root logging handlers so `configure_logging` is observable.
- `processor_with_timelog(timelog, start, end, …)` (integration) — `make_processor` plus parsed date boundaries.
- `real_resource_copy` (system) — copies `sup/2025_extract.csv` + `src/2025_FDTech_Dennis_Hartel.xlsm` into `tmp_path`, or `None` when missing.
- `cli_runner(answers)` (system) — drives `run()` in-process against the copies, feeding `answers` to `input()`.

## Configuration

### pytest (`pyproject.toml` → `[tool.pytest.ini_options]`)

All tooling configuration lives in `pyproject.toml` — there is no separate
`pytest.ini`, so pytest has exactly one config source.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --tb=short"
markers = [
    "unit: individual functions/methods in isolation (tmp files or mocks, no real resources)",
    "integration: TimeSheetProcessor pipeline on the in-memory dummy workbook",
    "system: real-resource copies + CLI flow, skipped when resources are missing",
]
```

The repository root is placed on `sys.path` by `tests/conftest.py`, so the
`src` package imports regardless of the invocation directory (no
`pythonpath` setting is needed).

### Coverage (`pyproject.toml`)

```toml
[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
show_missing = true
fail_under = 90
exclude_lines = ["pragma: no cover", "if __name__ == .__main__.:", "raise NotImplementedError"]
```

### Determinism

`set_default_end_date` uses `datetime.now() - 1 day`. The autouse `frozen_time`
fixture freezes the clock to 2025-12-23; with `freezegun` installed runs are
fully deterministic. Without it the fixture degrades to a no-op (with a warning)
and time-relative assertions are written relative to `now()`.

## Running

```bash
python -m pytest                          # full suite
python -m pytest tests/unit               # one level by path
python -m pytest -m unit                  # one level by marker
python -m pytest -m "not system"          # fast set (PR CI)
python -m pytest --cov=src --cov-report=term-missing
```

CI (`.github/workflows/python-ci.yml`): PRs to `master` run the full suite with
coverage; all 103 tests (including 7 system tests) run because the real data
files are committed to the repo.

## Real test data files

The system tests rely on two real data files committed to the repository:

- **`sup/2025_extract.csv`** — 93 sample timelog entries from 2025 (dates, start/end times).
- **`src/2025_FDTech_Dennis_Hartel.xlsm`** — real timesheet workbook (12 month sheets, VBA macros preserved).

These files **are committed to version control** (not gitignored) to ensure:

1. ✅ All 103 tests run on CI (including 7 system tests).
2. ✅ 100% code coverage is achieved and gated at 90%.
3. ✅ System tests verify the real end-to-end workflow.
4. ✅ System tests skip cleanly only if cloned without history or files are manually deleted.

### For local development

If you don't have the real files locally:

```bash
git lfs pull  # If the files are stored with Git LFS (unlikely)
# or
git checkout sup/2025_extract.csv src/2025_FDTech_Dennis_Hartel.xlsm  # Restore from repo
```

If system tests skip with a message like `"Real resource files not available"`, you can:
1. Run unit + integration tests only: `pytest -m "not system"`
2. Run the full suite once you've restored the files: `git checkout <files>`

---

**Counts:** unit 79 · integration 17 · system 7 · total 103 (1 `xfail`).
Branch+line coverage of `src` ≈ 99% (gate 90%).
