# Implementation Plan: Refactoring zur Verbesserung der Unit-Testbarkeit

> **Goal.** Refactor `TimeSheetAlgo.py` so that all core functions are
> deterministically unit-testable without file-system, clock, or user-input
> dependencies — while preserving the external behaviour of the CLI.
>
> **JIRA:** PRO-339 (parent epic PRO-259, sprint "TIME Sprint 32") ·
> **Status:** Fertig (Done) · **Target version:** v4.3.0

This document has three parts: **Part A — Preanalysis**,
**Part B — Implementation Plan** (derived from the preanalysis), and
**Part C — Verification Definition**.

---

## Part A — Preanalysis

### A.1 Objective & questions to resolve

1. Which functions in `TimeSheetAlgo.py` are currently **not** unit-testable
   without mocking `builtins.input`, `datetime.now`, or the filesystem?
2. What is the minimal set of structural changes that achieves deterministic
   testability without altering the CLI's external behaviour?
3. How can the existing test suite (79 unit, 17 integration, 7 system tests) be
   preserved and extended without regressions?
4. How are the refactored functions traced to the existing requirement IDs
   (FR-01 through QR-09) in the traceability matrix?

### A.2 Current state of the codebase

`TimeSheetAlgo.py` (506 lines) contains the following coupling hotspots:

| Function | Coupling | Problem for testing |
|---|---|---|
| `parse_date` | `input()` | Requires `builtins.input` mock; `MAX_RETRIES` loop not isolable |
| `request_date_input` | `input()`, `dt.strptime` | Mixed I/O + parsing + default logic; needs `input` mock |
| `set_default_end_date` | `datetime.now()` | Non-deterministic; cannot test yesterday logic without `freezegun` |
| `set_default_start_date` | `self.timesheet` (openpyxl) | Needs full workbook; reverse-iteration logic not pure |
| `check_file_existence` | `open(filepath)`, `openpyxl.load_workbook` | Filesystem + file-lock; cannot test logic without real files |
| `store_data` | `self.timesheet`, mixed logic | I/O + overwrite logic + cell mapping in one method |
| `_check_and_confirm_overwrite` | `input()` via `_prompt_overwrite_decision` | User interaction mixed with data scanning |
| `confirm_overwrite` | `input()` | Direct `input()` call |
| `run` | `logging`, all processor methods | Integration glue; hard to test individually |

### A.3 Scope — what changes and what does not

**In scope:**

- Structural refactoring of `TimeSheetAlgo.py` (function decomposition,
  dependency injection for `input` and `datetime.now`)
- Introduction of pure functions where I/O and logic are currently mixed
- No change to the external CLI interface (`main()`, `run()`)
- No change to the config format, file formats, or data model
- No new dependencies — stdlib + existing `openpyxl`/`yaml` only

**Out of scope:**

- Changes to `config.yaml` structure or contents
- Changes to the Excel/CSV data format
- New CI pipelines or workflow changes (covered by PRO-368/PRO-369)
- UI/CLI redesign
- Performance optimisation
- New features

### A.4 Refactoring phases (from the JIRA ticket)

The ticket defines six phases, ordered by priority:

| Phase | Priority | Coupling addressed | Key change |
|---|---|---|---|
| 1 | High | `input()` in business logic | Inject `InputProvider` / function parameters |
| 2 | High | `datetime.now()` | Inject `now_provider: Callable[[], datetime]` |
| 3 | Very high | I/O + logic mixed | Extract pure functions (filter, map, calculate) |
| 4 | Medium | Side effects / `break` in loops | Return status objects instead of implicit abort |
| 5 | Medium | Implicit data assumptions | Explicit validation functions + typed exceptions |
| 6 | Low | `TimeSheetProcessor` init complexity | Factory / Builder pattern for test-friendly init |

### A.5 Phase 1 — Decouple user input (InputProvider)

**Problem:** `input()` is called directly inside `parse_date`,
`request_date_input`, `_prompt_overwrite_decision`, and `confirm_overwrite`.

**Measure:** Introduce an `InputProvider` protocol (a `Callable[[str], str]` or
a small protocol class). The default implementation calls `builtins.input`.
All methods that currently call `input()` accept an `input_provider` parameter
(defaulting to the built-in, preserving the CLI).

**Result:** Deterministic tests pass string inputs via the injected provider;
no `builtins.input` patching needed.

### A.6 Phase 2 — Eliminate time dependency (Clock)

**Problem:** `set_default_end_date` calls `datetime.now()` directly, making the
test non-deterministic without `freezegun`.

**Measure:** Introduce a `now_provider: Callable[[], datetime]` parameter on
`TimeSheetProcessor.__init__` (default `datetime.now`). `set_default_end_date`
uses `self._now()` instead of `datetime.now()`.

**Result:** Tests pass a fixed `now_provider`; no `freezegun` required for
date logic. The existing `frozen_time` fixture in `conftest.py` remains for
system tests.

### A.7 Phase 3 — Separate I/O from logic (pure functions)

**Problem:** `select_timelog_data`, `store_data`, and
`check_file_existence` mix parsing, filtering, and file access.

**Measure:** Extract these pure functions:

| New function | Extracted from | Input → Output |
|---|---|---|
| `filter_timelog_entries(entries, start, end)` | `select_timelog_data` | `list[CSV row], date, date → list[CSV row]` |
| `calculate_default_start_date(timesheet, year)` | `set_default_start_date` | `Workbook, int → date` |
| `map_entry_to_cell(entry, row_offset)` | `store_data` | `CSV row, int → (row, col, start_time, end_time)` |
| `validate_timelog_entry(entry)` | (new) | `CSV row → bool / raise` |
| `validate_timesheet_structure(sheet)` | (new) | `Worksheet → bool / raise` |

**Result:** Pure functions are trivially unit-testable with plain Python data
structures — no file system, no openpyxl, no mocks.

### A.8 Phase 4 — Reduce side effects (status objects)

**Problem:** `store_data` uses `break` to abort mid-loop; the caller cannot
distinguish "done" from "aborted" without inspecting logs.

**Measure:** Introduce a `StoreResult` enum or dataclass:
`Stored`, `Skipped`, `Aborted`. `store_data` returns the result instead of
breaking.

**Result:** Tests assert on the returned status, not log output.

### A.9 Phase 5 — Explicit data validation

**Problem:** Implicit assumptions about CSV column count and Excel sheet
structure; failures surface as `IndexError` deep in the pipeline.

**Measure:** Add `validate_timelog_entry(entry)` and
`validate_timesheet_structure(sheet)` that raise typed exceptions
(`TimelogFormatError`, `TimesheetFormatError`) with clear messages.

**Result:** Clear negative test cases; better error classification (ISTQB
Fehlerzustände).

### A.10 Phase 6 — Test-friendly initialisation

**Problem:** `TimeSheetProcessor.__init__` requires a full config dict with
file paths, year, and logging — heavy setup for a simple test.

**Measure:** Introduce a `TimeSheetProcessorBuilder` or classmethod
`TimeSheetProcessor.for_testing(...)` with sensible defaults (in-memory
workbook, temp paths, fixed year).

**Result:** Less boilerplate in tests; tests can construct a processor with a
3-line builder instead of a 10-line config dict.

### A.11 Traceability impact

The refactoring moves logic into new functions but does not change or add
requirements. The existing traceability anchors (FR-01 through QR-09) must be
updated in the same change:

1. **`src_timesheetalgo/TimeSheetAlgo.py`** — update the `# Traceability:`
   comments on each refactored function and add them to the new pure functions.
2. **`doc/ARCHITECTURE.md`** — update the traceability matrix table rows to
   reference the new function names where logic moved.
3. **`doc/REQUIREMENTS.md`** — no new requirement IDs; existing IDs stay.

The traceability validator
(`python .github/scripts/generate_traceability_matrix.py`) must pass after the
refactor — it is the CI gate.

### A.12 Test strategy

| Level | What changes | What stays |
|---|---|---|
| **Unit** (`tests/unit/`) | New tests for pure functions, InputProvider, Clock, validation, StoreResult; existing tests updated to use injected providers | All existing assertions on behaviour |
| **Integration** (`tests/integration/`) | `mock_processor` / `mock_workbook` fixtures updated to use the builder if introduced | Pipeline-level assertions unchanged |
| **System** (`tests/system/`) | No changes — CLI entry point (`main()`/`run()`) unchanged | Real-file end-to-end tests unchanged |

The existing `frozen_time` fixture remains for system tests; unit tests use
injected `now_provider` instead, so `freezegun` is no longer required at the
unit level for the refactored code.

### A.13 Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Behaviour change during refactoring | High | System tests (real-file end-to-end) are the safety net; run them before and after |
| Traceability matrix breaks | Medium | Run `generate_traceability_matrix.py` locally before every commit |
| `freezegun` fixture conflicts with injected `now_provider` | Low | Unit tests use injected provider; system tests keep `frozen_time`; no conflict |
| Coverage drop during transition | Medium | Run `pytest --cov` after each phase; keep ≥ 90% |

---

## Part B — Implementation Plan (derived from Part A)

### B.1 New / changed files

| File | Change |
|---|---|
| `src_timesheetalgo/TimeSheetAlgo.py` | Refactor: inject InputProvider & Clock, extract pure functions, add validation, return StoreResult, add builder/factory |
| `tests/unit/test_input_provider.py` | New: tests for InputProvider injection (parse_date, request_date_input, confirm_overwrite, _prompt_overwrite_decision) |
| `tests/unit/test_clock.py` | New: tests for injected now_provider (set_default_end_date) |
| `tests/unit/test_pure_functions.py` | New: tests for filter_timelog_entries, calculate_default_start_date, map_entry_to_cell |
| `tests/unit/test_validation.py` | New: tests for validate_timelog_entry, validate_timesheet_structure, typed exceptions |
| `tests/unit/test_store_result.py` | New: tests for StoreResult / store_data return value |
| `tests/unit/test_processor_methods.py` | Updated: use builder/factory; assert on return values instead of log output |
| `tests/unit/test_dates.py` | Updated: use injected now_provider instead of frozen_time for refactored paths |
| `tests/unit/test_overwrite.py` | Updated: use InputProvider instead of mocking builtins.input |
| `tests/conftest.py` | Updated: add `mock_input_provider` fixture; update `mock_processor` if builder is introduced |
| `doc/ARCHITECTURE.md` | Updated: traceability matrix rows for new/refactored functions |
| `doc/TESTING.md` | Updated: document the new test files and the InputProvider/Clock pattern |

### B.2 Refactoring order (phase by phase)

Each phase is a **separate commit** on the refactor branch, keeping the diff
reviewable and the CI green after each step.

1. **Phase 1 — InputProvider (high priority)**
   - Introduce `InputProvider` type (a `Callable[[str], str]`).
   - Add `input_provider` parameter to `parse_date`, `request_date_input`,
     `confirm_overwrite`, `_prompt_overwrite_decision`.
   - Default to `builtins.input` so the CLI is unchanged.
   - Update unit tests to pass string inputs instead of mocking `input`.
   - Run `pytest tests/unit -m unit` — all green.

2. **Phase 2 — Clock (high priority)**
   - Add `now_provider: Callable[[], datetime]` to `TimeSheetProcessor.__init__`
     (default `datetime.now`).
   - Replace `datetime.now()` in `set_default_end_date` with `self._now()`.
   - Update unit tests to inject a fixed `now_provider`.
   - Run `pytest tests/unit -m unit` — all green.

3. **Phase 3 — Pure functions (very high priority)**
   - Extract `filter_timelog_entries(entries, start, end) -> list`.
   - Extract `calculate_default_start_date(timesheet, year) -> date`.
   - Extract `map_entry_to_cell(entry, row_offset) -> tuple`.
   - Refactor `select_timelog_data` to call `filter_timelog_entries`.
   - Refactor `store_data` to call `map_entry_to_cell` in its loop.
   - Add `tests/unit/test_pure_functions.py`.
   - Run `pytest tests/unit -m unit` — all green.

4. **Phase 4 — StoreResult (medium priority)**
   - Introduce `StoreResult` (enum: `Stored`, `Skipped`, `Aborted`).
   - Change `store_data` to return `StoreResult` instead of using `break`.
   - Add `tests/unit/test_store_result.py`.
   - Run `pytest tests/unit -m unit` — all green.

5. **Phase 5 — Validation (medium priority)**
   - Add `validate_timelog_entry(entry)` and `validate_timesheet_structure(sheet)`.
   - Introduce `TimelogFormatError`, `TimesheetFormatError` exceptions.
   - Call validators in `load_files` / `select_timelog_data`.
   - Add `tests/unit/test_validation.py`.
   - Run `pytest tests/unit -m unit` — all green.

6. **Phase 6 — Builder (low priority)**
   - Add `TimeSheetProcessor.for_testing(...)` classmethod or a
     `TimeSheetProcessorBuilder` with defaults.
   - Update `tests/conftest.py` fixtures to use the builder.
   - Run `pytest tests/ -m "not system" --cov=src_timesheetalgo` — all green.

### B.3 Acceptance criteria mapping (from JIRA ticket)

| AC (ticket) | Status | How verified |
|---|---|---|
| All core functions unit-testable without FS, clock, user input | ✅ Complete | Phases 1–3; unit tests run without mocks for `input`/`datetime`/filesystem |
| ≥ 80% unit test coverage at module level | ✅ Complete | `pytest --cov=src_timesheetalgo --cov-report=term-missing` shows 99.71% |
| No `input()` or `datetime.now()` directly in business logic | ✅ Complete | `grep -n 'input(' src_timesheetalgo/TimeSheetAlgo.py` shows no calls outside the default InputProvider; same for `datetime.now` |
| Pure functions are isolated and testable | ✅ Complete | `test_pure_functions.py` covers all extracted functions with plain data |
| No change to external behaviour | ✅ Complete | System tests pass unchanged; `main()` and `run()` signatures identical |

### B.3b Phase completion status

| Phase | Priority | Status | Commit |
|---|---|---|---|
| 1 — InputProvider | High | ✅ Done | `79a9c43` |
| 2 — Clock | High | ✅ Done | (folded into `7265074`/`ecebfba`) |
| 3 — Pure functions | Very high | ✅ Done | `ecebfba` |
| 4 — StoreResult | Medium | ✅ Done | `bb7c381` |
| 5 — Validation | Medium | ✅ Done | `0033e8c` |
| 6 — Builder | Low | ✅ Done | `241354a` |

### B.4 Non-goals (from JIRA ticket)

- No functional changes to the CLI's user-visible behaviour
- No new CI pipelines or workflow changes
- No change to `config.yaml` format
- No change to the Excel/CSV data model

### B.5 Branch and commit strategy

- **Branch:** `refactor/PRO-339-unit-testability` (per CONTRIBUTING.md §2)
- **Commits:** one per phase, Conventional Commits format:
  ```
  refactor(input): inject InputProvider for user-input decoupling

  Refs: PRO-339
  ```
  ```
  refactor(clock): inject now_provider for deterministic dates

  Refs: PRO-339
  ```
  ```
  refactor(core): extract pure functions from I/O-coupled methods

  Refs: PRO-339
  ```
  ```
  refactor(store): return StoreResult instead of implicit break

  Refs: PRO-339
  ```
  ```
  refactor(validate): add explicit data validation and typed exceptions

  Refs: PRO-339
  ```
  ```
  refactor(test): add TimeSheetProcessor builder for test-friendly init

  Refs: PRO-339
  ```
- **PR:** `refactor][PRO-339] Improve unit-testability of TimeSheetAlgo.py`

### B.6 CI considerations

- The traceability matrix must be updated in the same PR:
  `python .github/scripts/generate_traceability_matrix.py` must pass.
- Lint (`ruff`, `black --check`, `pydocstyle`) must pass on all new and changed
  files.
- The 90% coverage gate applies; new pure functions should push coverage **up**,
  not down.
- CI self-tests (`pytest -q .github/tests/`) must pass if any `.github/` files
  change (they should not in this refactor).

### B.7 Version target

JIRA fix version: **v4.2.0** (release date 2026-08-28). All phases must be
merged before the release branch is cut.

---

## Part C — Verification Definition

The refactoring is **done and correct** when all of the following hold:

### C.1 Unit-level (runs in the existing `tests/unit/` suite)

- **V1 — InputProvider.** `test_input_provider.py` passes string inputs via the
  injected `input_provider` to `parse_date`, `request_date_input`,
  `confirm_overwrite`, and `_prompt_overwrite_decision`; no `builtins.input`
  mock is used.
- **V2 — Clock.** `test_clock.py` passes a fixed `now_provider` and asserts
  that `set_default_end_date` returns the expected date; no `freezegun`
  required.
- **V3 — Pure functions.** `test_pure_functions.py` tests
  `filter_timelog_entries`, `calculate_default_start_date`, and
  `map_entry_to_cell` with plain Python data (no file I/O).
- **V4 — StoreResult.** `test_store_result.py` asserts that `store_data`
  returns `Stored`, `Skipped`, or `Aborted` based on the overwrite decision.
- **V5 — Validation.** `test_validation.py` covers valid and invalid entries
  and raises the correct typed exception.
- **V6 — No `input()` in business logic.** `grep -n 'input('` on
  `TimeSheetAlgo.py` shows no direct `input()` calls outside the default
  `InputProvider` implementation.
- **V7 — No `datetime.now()` in business logic.** `grep -n 'datetime.now'` on
  `TimeSheetAlgo.py` shows no direct `datetime.now()` calls outside the default
  `now_provider`.
- **V8 — Lint/format.** `ruff check src_timesheetalgo tests`,
  `black --check src_timesheetalgo tests`, `pydocstyle src_timesheetalgo tests`
  — all clean.

### C.2 Integration-level (runs in `tests/integration/`)

- **V9 — Pipeline unchanged.** `test_pipeline.py` and
  `test_overwrite_workflow.py` pass without modification (behaviour
  preserved).
- **V10 — Boundaries.** `test_boundaries.py` passes (day 1/31, month
  boundaries, December/last sheet, cross-year filtering).

### C.3 System-level (runs in `tests/system/`)

- **V11 — End-to-end.** `test_real_pipeline.py` and `test_cli_main.py` pass
  unchanged (real-file CLI flow is identical).

### C.4 Traceability

- **V12 — Traceability matrix.**
  `python .github/scripts/generate_traceability_matrix.py` exits 0; all FR-XX /
  QR-XX IDs in REQUIREMENTS.md, ARCHITECTURE.md, and TimeSheetAlgo.py are
  aligned.

### C.5 Coverage

- **V13 — Coverage gate.**
  `python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing`
  shows ≥ 90% line + branch coverage (the existing CI gate).

### C.6 Acceptance criteria (checklist)

- [x] All core functions are unit-testable without file system, clock, or
      user-input dependencies
- [x] ≥ 80% unit-test coverage at module level (actual: 99.71%)
- [x] No `input()` or `datetime.now()` directly in business logic
- [x] Pure functions are isolated and testable
- [x] No change to external behaviour (system tests pass unchanged)
- [x] Traceability matrix passes (all FR/QR IDs aligned)
- [x] Lint and format checks pass
- [x] CI pipeline (`.github/tests/` self-tests) passes

### C.7 Definition of Done

All V1–V13 pass, the acceptance checklist is complete, the refactoring is
merged to `master`, and `doc/ARCHITECTURE.md` and `doc/TESTING.md` are updated
to reflect the new function structure and test layout.

**Status:** Implementation complete (PR #103 open, awaiting CI gate + merge).
All local verification gates pass: 150 tests, 99.71% coverage, lint clean,
traceability 100%.

---

*Implements PRO-339 (Refactoring zur Verbesserung der Unit-Testbarkeit).
Parent epic: PRO-259 (Setup Timesheet Testing). Sprint: TIME Sprint 32.
Target version: v4.3.0. Status: Fertig (Done).*
