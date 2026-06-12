# TimeSheetAlgo Testing Documentation

**Before running tests:** install the dev dependencies with
`python -m pip install -e .[dev]` (provides `pytest`, `pytest-cov`,
`freezegun`, etc.).

This is the single reference for the test suite of
`src_timesheetalgo/TimeSheetAlgo.py` — its layout, the intent of each level, the
fixtures, and the configuration behind them.

## Layout

```text
tests/
  conftest.py                    # shared: frozen_time, sys.path, workbook/processor builders
  unit/
    conftest.py                  # clean_root_logger
    test_config.py               # load_config, _read_yaml, detect_environment, ConfigError
    test_logging.py              # configure_logging
    test_dates.py                # parse_date, _get_date, set_default_start/end_date
    test_files.py                # check_file_existence (csv/excel/lock/permission/not-found)
    test_processor_methods.py    # load_files, request_date_input, select_timelog_data, save_timesheet
    test_overwrite.py            # confirm_overwrite, _prompt_overwrite_decision, _check_and_confirm_overwrite
  integration/
    conftest.py                  # processor_with_timelog builder
    test_pipeline.py             # load→select→store→save (single + multi-month + week)
    test_overwrite_workflow.py   # store_data with overwrite_all / skip_all / abort / empty / EOF
    test_boundaries.py           # day 1 / day 31, month boundary, cross-year filtering
  system/
    conftest.py                  # real_resource_copy, cli_runner
    test_real_pipeline.py        # real copies → TimeSheetProcessor end-to-end, reload & assert cells
    test_cli_main.py             # run()/main() with stdin + tmp config
```

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
- `test_dates.py` — `parse_date` (valid / retries-exhausted / retries=0 / retry), `_get_date` (success + fallback), `set_default_start_date` (with data + no-data fallback), `set_default_end_date`.
- `test_files.py` — `check_file_existence` (csv/excel happy path, not-found, permission denied, lock warning).
- `test_processor_methods.py` — `load_files`, `request_date_input` (valid/invalid/empty/EOF/specific default), `select_timelog_data` (in-range + empty→ValueError), `save_timesheet`.
- `test_overwrite.py` — `confirm_overwrite`, `_prompt_overwrite_decision`, `_check_and_confirm_overwrite` (the decision logic, in isolation).

### 2. Integration (`tests/integration/`, marker `integration`)

The `TimeSheetProcessor` pipeline run across multiple steps on the in-memory
dummy 12-sheet workbook (no real `.xlsm`/`.csv`). Verifies the data model:
sheet index = `date.month - 1`, row = `ROW_OFFSET + day`, start in column 5,
end in column 6.

- `test_pipeline.py` — `select → store → save` for single entry, multiple months, and a realistic week.
- `test_overwrite_workflow.py` — how `store_data` *acts* on each decision (overwrite_all / skip_all / abort / empty / EOF).
- `test_boundaries.py` — day 1, day 31, month boundary, cross-year filtering.

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
- `real_resource_copy` (system) — copies `sup/2025_extract.csv` + `src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm` into `tmp_path`, or `None` when missing.
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
`src_timesheetalgo` package imports regardless of the invocation directory (no
`pythonpath` setting is needed).

### Coverage (`pyproject.toml`)

```toml
[tool.coverage.run]
source = ["src_timesheetalgo"]
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
python -m pytest --cov=src_timesheetalgo --cov-report=term-missing
```

CI (`.github/workflows/python-ci.yml`): PRs to `master` run the full suite with
coverage; all 83 tests (including 7 system tests) run because the real data files
are committed to the repo.

## Real test data files

The system tests rely on two real data files committed to the repository:

- **`sup/2025_extract.csv`** — 93 sample timelog entries from 2025 (dates, start/end times).
- **`src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm`** — real timesheet workbook (12 month sheets, VBA macros preserved).

These files **are committed to version control** (not gitignored) to ensure:

1. ✅ All 83 tests run on CI (including 7 system tests).
2. ✅ 100% code coverage is achieved and gated at 90%.
3. ✅ System tests verify the real end-to-end workflow.
4. ✅ System tests skip cleanly only if cloned without history or files are manually deleted.

### For local development

If you don't have the real files locally:

```bash
git lfs pull  # If the files are stored with Git LFS (unlikely)
# or
git checkout sup/2025_extract.csv src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm  # Restore from repo
```

If system tests skip with a message like `"Real resource files not available"`, you can:
1. Run unit + integration tests only: `pytest -m "not system"`
2. Run the full suite once you've restored the files: `git checkout <files>`

---

**Counts:** unit 63 · integration 13 · system 7 · total 83.
Branch+line coverage of `src_timesheetalgo` ≈ 99% (gate 90%).
