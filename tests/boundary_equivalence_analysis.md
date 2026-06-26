# Boundary Value & Equivalence Class Analysis (PRO-262)

This document records the **equivalence-class partitioning (ECP)** and
**boundary-value analysis (BVA)** performed on `src_timesheetalgo/TimeSheetAlgo.py`,
the additional test cases derived from it, and the findings worth a follow-up
decision. It complements [`TESTING.md`](TESTING.md) (which describes the test
*layout*); this file explains *why* the test vector is shaped the way it is.

## Method

For every input and output of the program we:

1. partition each domain into **equivalence classes** (valid + each distinct
   invalid kind) and keep one representative per class, then
2. add the **boundaries** between adjacent classes (just-inside / on / just-
   outside), where defects cluster.

Each derived case is placed at the level whose boundary it exercises (unit =
one function, integration = the `TimeSheetProcessor` pipeline on the in-memory
workbook, system = real-file copies).

## Input / output inventory

| # | Input / output | Where validated |
|---|----------------|-----------------|
| I1 | User date string (`parse_date`, `request_date_input`) | unit |
| I2 | Date range filter `start <= date <= end` (`select_timelog_data`) | unit / integration |
| I3 | Timelog CSV rows (`check_file_existence`, `store_data`) | unit / integration / system |
| I4 | Timesheet workbook cells (`store_data`, `set_default_start_date`, `check_year_consistency`) | unit / integration |
| I5 | Overwrite decision (`_prompt_overwrite_decision`, `confirm_overwrite`) | unit / integration |
| I6 | Configuration (`load_config`) | unit |
| O1 | Written cell: sheet `month-1`, row `ROW_OFFSET+day`, cols E/F | integration / system |

## I1 — User date string

### Equivalence classes

| Class | Representative | Result | Test |
|-------|----------------|--------|------|
| Valid format + valid calendar date | `15.03.2025` | parsed | `test_parse_date_valid` (existing) |
| Malformed format | `invalid` | retry → `ValueError` | `test_parse_date_retries_exhausted` (existing) |
| **Format-valid but calendar-invalid** | `32.01.2025`, `30.02.2025`, `31.04.2025` | `ValueError` | **`test_parse_date_calendar_invalid_is_rejected`** (new) |
| Empty string | `""` | default date | `test_request_date_input_empty_uses_defaults` (existing) |
| EOF | — | default date | `test_request_date_input_eof_uses_defaults` (existing) |

### Boundaries

| Boundary | Cases | Test |
|----------|-------|------|
| Retry budget | 0 / exhausted / recover-on-last | `test_parse_date_retries_zero`, `..._retries_exhausted`, `..._invalid_then_valid` (existing) |
| **Leap day** | `29.02.2024` valid · `29.02.2025` invalid | **`test_parse_date_leap_day_valid`**, **`..._non_leap_year_rejected`** (new) |

## I2 — Date range filter (`select_timelog_data`)

The filter is inclusive on both ends. Boundary partition around `[start, end]`:

| Partition | Representative (range 10.03–18.03) | Kept? | Test |
|-----------|-----------------------------------|-------|------|
| Just before start | `09.03` | no | **`test_select_timelog_data_range_inclusive_both_ends`** (new) |
| On start | `10.03` | yes | same |
| On end | `18.03` | yes | same |
| Just after end | `19.03` | no | same |
| Single-day range (`start == end`) | `15.03`, range 15–15 | yes | **`test_select_timelog_data_single_day_range`** (new) |
| Inverted range (`start > end`) | range 20→10 | none → `ValueError` | **`test_select_timelog_data_inverted_range_raises`** (new) |
| Empty timelog (header-only CSV) | `[]` | none → `ValueError` | **`test_select_timelog_data_empty_timelog_raises`** (new) |
| Cross-year exclusion | `30.12.2024` vs `15.01.2025` | only in-year | `test_cross_year_entries_excluded` (existing, integration) |

## I3 — Timelog CSV rows

| Class / boundary | Representative | Behaviour | Test |
|------------------|----------------|-----------|------|
| 3-column row | `date,start,end` | stored | existing pipeline tests |
| **4-column row (with Remark)** | `…,Project A` | loaded intact; Remark ignored on write | **`test_csv_preserves_remark_column`** (unit) + **`test_pipeline_ignores_remark_column`** (integration) — both new |
| **Malformed date in a row** | `not-a-date,…` | parsing `ValueError` aborts selection | **`test_select_timelog_data_malformed_row_propagates`** (new) — see Finding F3 |
| Time as `HH:MM` / `HH:MM:SS` | `09:00:00` | written verbatim (pass-through) | covered by pass-through; low risk, no dedicated test |

## I4 — Timesheet workbook cells

| Boundary | Representative | Test |
|----------|----------------|------|
| First day of month | day 1 → row `ROW_OFFSET+1` | `test_first_day_of_month` (existing) |
| Last day of month (write) | day 31 → row `ROW_OFFSET+31` | `test_last_day_of_month` (existing) + **`test_december_31_routes_to_last_sheet`** (new) |
| Month boundary | 31 Jan → 01 Feb | `test_month_boundary_routes_to_two_sheets` (existing) |
| **Default-start scan, day 31** | worked day on the 31st | **`test_set_default_start_date_day_31_boundary`** (new, `xfail`) — see Finding F1 |
| Year cell `Januar!B3` | date / text / mismatch / empty | `test_consistency.py` (existing) |

## I5 — Overwrite decision

`_prompt_overwrite_decision` / `confirm_overwrite` equivalence classes
(`y`/`yes`/`""` → overwrite, `s`/`skip` → skip, `n`/other → abort, EOF →
overwrite) are fully covered in `test_overwrite.py`. The new cases cover how
`store_data` *acts* when occupied and free days are **mixed** in one run:

| Boundary | Test |
|----------|------|
| skip_all with one occupied + one free day | **`test_skip_all_keeps_conflict_but_writes_free_day`** (new) |
| abort after an earlier free day was written | **`test_abort_is_not_atomic_for_earlier_free_days`** (new) — see Finding F2 |

## O1 — Written cell (month/sheet mapping)

| Boundary | Test |
|----------|------|
| First month (Jan → index 0) | existing pipeline/boundary tests |
| **Last month (Dec → index 11)** | **`test_december_31_routes_to_last_sheet`** (new) |
| Distribution across months | `test_pipeline_distributes_across_months` (existing) |

## Findings (for human review)

> These were surfaced by the analysis. No production code was changed under this
> ticket; each is captured by a test that **documents current behaviour** so the
> reviewer can decide whether to fix it (likely a separate ticket).

- **F1 — `set_default_start_date` misses day 31 (latent bug).**
  The scan `range(ROW_OFFSET + 30, ROW_OFFSET, -1)` covers days 30…1, so a
  worked day on the **31st is never detected** and the default start silently
  falls back to an earlier day or to 1 Jan. Captured by the **strict `xfail`**
  `test_set_default_start_date_day_31_boundary`. Proposed one-line fix:
  `range(ROW_OFFSET + 31, ROW_OFFSET, -1)`. When applied, remove the `xfail`
  marker — the test then asserts the correct behaviour.

- **F2 — `abort` is not atomic.**
  Because `store_data` computes the decision up front and then writes in
  timelog order, a non-conflicting day processed *before* the first conflict is
  written and not rolled back on `abort`. Documented by
  `test_abort_is_not_atomic_for_earlier_free_days`. Decide whether abort should
  be all-or-nothing.

- **F3 — No per-row timelog validation.**
  A single corrupt date in the CSV raises a parsing `ValueError` that aborts the
  entire selection (`select_timelog_data`). Documented by
  `test_select_timelog_data_malformed_row_propagates`. Consider skipping +
  logging bad rows instead of failing the run.

## Recommendation

Land the new tests as-is (suite stays green; the one `xfail` is an *expected*
failure, not a regression). Then triage F1–F3 as separate fix tickets; F1 in
particular is a small, well-understood correctness fix.
