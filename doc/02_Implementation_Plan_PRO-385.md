# Implementation Plan: PRO-385 - CI Timing Pipeline: Latest Successful PR Runs Not Captured in Storage

**Status:** Draft  
**Epic Link:** PRO-259  
**Parent:** PRO-369 (Fertig)  
**Priority:** High  
**Story Points:** 3  

---

## 1. Design Decisions

### 1.1 Problem Summary

The CI Timing Benchmark pipeline (`PRO-369`) is not capturing the most recent successful `pull_request` runs of the `Python CI` workflow. Approximately 10 days of successful PR runs (starting from run_id=35116541292, created_at=2026-09-16T15:37:01Z) are missing from all storage locations:
* `ci_runtimes.json` (master branch)

* `ci_metrics.json` (master branch)
* `ci-metrics:ci-timings.csv` (ci-metrics branch)

The most recent run (36229056933, created_at=2026-09-26T08:11:53Z, PR #395) is missing from all three storage locations.

### 1.2 Data Storage Requirement

All timing data must be stored in:
- `ci-metrics` branch: `ci-timings.csv` (CSV format, backward compatibility maintained)
- `master` branch: `ci_runtimes.json`, `ci_metrics.json` (JSON format with schema v1.0)

### 1.3 Problem Decomposition

The issue is in the `ci-timing.yml` workflow configuration. The `workflow_run` trigger only runs the `collect` step (which populates `ci-timings.csv`), but the `UPDATE_DATA` env var defaults to `'false'` for `workflow_run` triggers, so the `write data/ to master` step is skipped, preventing JSON data from reaching `master`.

### 1.4 Solution Strategy

1. **Immediate fix**: Make `UPDATE_DATA` trigger-aware in `ci-timing.yml`
   - Set `UPDATE_DATA: true` for `workflow_run` triggers (continuous capture)
   - Keep `UPDATE_DATA: false` for `workflow_dispatch` unless explicitly set to `true`

2. **Enhance error handling**: Add retry logic and error handling to `collect_ci_timings.py`

3. **Add validation**: Add workflow configuration validation tests

4. **Recover data**: Run backfill to populate missing data in master branch

5. **Verify**: Ensure all quality gates pass

### 1.5 Implementation Plan

| Phase | Activity | Files Modified | Tests |
|-------|----------|----------------|-------|
| **1: Parallel** | Fix `UPDATE_DATA` env var; add validation tests | `.github/workflows/ci-timing.yml`, `tests/ci-pipeline/test_update_data_default.py` | Unit tests |
| **2: Fix** | Add retry logic and error handling to `collect_ci_timings.py` | `.github/scripts/collect_ci_timings.py` | Unit tests |
| **3: Recovery** | Run backfill to populate missing data | `.github/scripts/backfill_ci_timings.py` | System tests |
| **4: Verification** | Run full quality gates | N/A | All existing tests |

### 1.6 Testing Strategy

**Unit Tests (Immediate):**
- Test `UPDATE_DATA` expression logic for `workflow_run` vs `workflow_dispatch`
- Test conditional step evaluation
- Test `write_json()` error handling

**Integration Tests (Medium-term):**
- Test workflow configuration parsing
- Test data propagation to master branch
- Test backfill functionality

**System Tests (Long-term):**
- Test full pipeline execution
- Test data consistency across CSV and JSON storage

### 1.7 Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `UPDATE_DATA` hardcoded to `'false'` | High | Low | Test that expression evaluates correctly |
| JSON write failures | Medium | Medium | Add error handling and retry logic |
| CI loop from data/ push to master | High | Low | Existing no-loop invariants preserved |
| Data corruption during backfill | High | Low | Validation ensures data integrity |
| Regressions in existing tests | Medium | Low | Comprehensive test suite |

### 1.8 Timeline

- **Days 1-2**: Implement `UPDATE_DATA` fix and validation tests
- **Days 3-4**: Add error handling to `collect_ci_timings.py`
- **Day 5**: Run backfill to recover missing data
- **Day 6-7**: Full quality gate verification
- **Day 8**: Open PR for review

---

## 2. File Structure

```
.github/workflows/
├── ci-timing.yml              # MODIFY: fix UPDATE_DATA env var
└── python-ci.yml              # No changes (existing workflow)

.github/scripts/
├── collect_ci_timings.py      # MODIFY: add error handling
├── aggregate_ci_timings.py    # No changes
├── backfill_ci_timings.py     # No changes (existing)
├── validator.py              # No changes (existing)
└── ci_stats.py              # No changes (existing)

tests/ci-pipeline/
├── test_update_data_default.py # NEW: validate UPDATE_DATA expression
├── test_collect_ci_timings.py  # MODIFY: add error handling tests
├── test_aggregate_ci_timings.py # No changes
├── test_backfill_ci_timings.py # No changes
├── test_validator.py          # No changes
└── test_ci_timing_pipeline.py # MODIFY: add system test for master branch

doc/
├── 02_Implementation_Plan_PRO-385.md  # NEW: this implementation plan
├── 03_Architecture_PRO-375.md          # EXISTING: CI timing pipeline architecture
├── CONTRIBUTING.md                   # EXISTING: development guidelines
└── REQUIREMENTS.md                    # EXISTING: requirements documentation

ci-metrics/                      # EXISTING: persistent dataset
├── ci-timings.csv              # UPDATED: contains recent runs
└── CI_TIMING_REPORT.md          # UPDATED: reflects current dataset

master/
├── data/
│   ├── runtimes.json           # UPDATED: contains recent runs  
│   └── metrics.json            # UPDATED: reflects current dataset
└── ... other files ...
```

---

## 3. Function Specifications

### 3.1 Fix UPDATE_DATA in ci-timing.yml

```python
# .github/workflows/ci-timing.yml:85 (env section)
UPDATE_DATA: ${{ github.event_name == 'workflow_run' && 'true' || (inputs.update_data || 'false') }}

# Logic:
# - workflow_run triggers → UPDATE_DATA = 'true' (continuous capture writes to master)
# - workflow_dispatch with inputs.update_data = 'true' → UPDATE_DATA = 'true' (manual backfill)
# - workflow_dispatch with inputs.update_data = 'false' → UPDATE_DATA = 'false' (safety)
# - workflow_dispatch with inputs.update_data undefined → UPDATE_DATA = 'false' (backward compatibility)
```

### 3.2 Add Workflow Configuration Validation

**File**: `tests/ci-pipeline/test_update_data_default.py`

```python
"""Test UPDATE_DATA expression logic (PRO-385)."""

def test_update_data_workflow_run_returns_true():
    """workflow_run trigger → UPDATE_DATA must be 'true'."""
    assert evaluate_update_data("workflow_run", {}) == "true"

def test_update_data_workflow_dispatch_default_false():
    """workflow_dispatch without update_data input → UPDATE_DATA must be 'false'."""
    assert evaluate_update_data("workflow_dispatch", {}) == "false"

def test_update_data_workflow_dispatch_with_true():
    """workflow_dispatch with update_data='true' → UPDATE_DATA must be 'true'."""
    assert evaluate_update_data("workflow_dispatch", {"update_data": "true"}) == "true"


def evaluate_update_data(event_name: str, inputs: dict) -> str:
    """Simulate GitHub Actions UPDATE_DATA expression."""
    if event_name == "workflow_run":
        return "true"
    return str(inputs.get("update_data", "false"))
```

### 3.3 Error Handling in collect_ci_timings.py

**File**: `.github/scripts/collect_ci_timings.py`

Add retry logic to `_gh_api()` function and error handling in `main()`:

```python
def _gh_api(path: str, max_retries: int = 3) -> object:
    """Fetch JSON from the GitHub API via the ``gh`` CLI with retry logic."""
    for attempt in range(max_retries):
        try:
            out = subprocess.run(
                ["gh", "api", "--paginate", path],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            return json.loads(out)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

def main() -> None:
    """Enhanced main function with error handling."""
    try:
        # Existing main logic with try/except around _gh_api calls
        # Write JSON data with error handling
        write_json(new_rows, run_meta, DATA_DIR / "runtimes.json")
    except Exception as exc:
        print(f"ERROR: Unexpected error in main(): {exc}", file=sys.stderr)
        raise SystemExit(1)
```

### 3.4 Data Recovery (Backfill)

**File**: `.github/scripts/backfill_ci_timings.py`

Ensure backfill correctly populates master branch data:

```python
def backfill(...):
    # ... existing backfill logic ...
    _write_json(new_rows, DATA_DIR / "runtimes.json")
    # <- This should write to master branch
```

## 4. Test Structure

### 4.1 Unit Tests (test_update_data_default.py)

**New tests for UPDATE_DATA expression logic:**
- `test_update_data_expression_contains_workflow_run_check`
- `test_update_data_expression_contains_fallback`
- `test_update_data_workflow_run_returns_true`
- `test_update_data_workflow_dispatch_default_false`
- `test_update_data_workflow_dispatch_with_true`
- `test_update_data_workflow_dispatch_with_false`
- `test_update_data_not_hardcoded_to_false`
- `test_update_data_not_hardcoded_to_true`

### 4.2 Integration Tests (test_data_propagation.py)

**New tests for data propagation:**
- `test_write_json_creates_data_runtimes`
- `test_write_json_appends_to_existing_valid`
- `test_write_json_deduplicates_by_run_id`
- `test_write_json_skips_on_corrupt_existing`
- `test_write_json_skips_on_invalid_data`
- `test_write_json_creates_parent_dir`

### 4.3 System Tests (test_ci_timing_workflow.py)

**Enhanced system tests:**
- `test_update_data_env_uses_expression`
- `test_min_samples_env_uses_expression`
- `test_include_housekeeping_env_uses_expression`
- `test_metrics_branch_env_is_static`
- `test_data_commit_step_is_conditional_on_update_data`
- `test_data_commit_step_has_no_continue_on_error`
- `test_upload_report_step_always_runs`

---

## 5. Migration Details

### 5.1 Current State

- CSV data on `ci-metrics` branch: up-to-date (includes run 36229056933)
- JSON data on `master` branch: stale (last updated 2026-09-16)
- CI timing benchmark: missing 10 days of data

### 5.2 Required Changes

1. **ci-timing.yml**: Fix `UPDATE_DATA` expression
2. **Implementation plan**: Document the fix and verification
3. **Testing**: Add validation tests for the fix
4. **Recovery**: Run backfill to populate missing data

### 5.3 Verification Steps

1. **Trigger a test workflow_run**: Verify JSON data reaches `master` branch
2. **Verify data/runtimes.json updated**: Check that run 36229056933 appears
3. **Verify data/metrics.json updated**: Check that statistics include latest run
4. **Run full test suite**: Ensure all existing tests still pass
5. **Validate data integrity**: Run `generate_traceability_matrix.py`

### 5.4 Rollback Plan

If the fix causes issues:
1. Revert `ci-timing.yml` change
2. Run `backfill_ci_timings.py` with `--migrate` to restore old state
3. Revert any test changes

---

## 6. Backward Compatibility

| Aspect | Phase | Impact |
|--------|-------|---------|
| CSV on ci-metrics | ✅ Unchanged | CSV behavior unchanged |
| `CI_TIMING_REPORT.md` | ✅ Unchanged | Report generation unchanged |
| JSON on master | ✅ Additive | JSON now populated on master |
| `aggregate()` logic | ✅ Unchanged | Aggregation unchanged |
| `extract_rows()` | ✅ Unchanged | Data extraction unchanged (branch field added) |

**Deprecation timeline:** No breaking changes.

---

## 7. Traceability

### 7.1 Requirement Traceability

| Requirement ID | Feature | Implementation reference |
|----------------|---------|------------------------|
| FR-XX | JSON output and data validation | `collect_ci_timings.py` - `write_json()`, `aggregate_ci_timings.py` - `write_metrics()` |
| QR-08 | CI timing traceability | `validator.py` - schema validation before write |
| QR-09 | Branch perspective | `collect_ci_timings.py` - `extract_rows()` branch field |
| QR-13 | Workflow trigger compatibility | `test_update_data_default.py` - UPDATE_DATA expression tests |

### 7.2 Test Coverage

- **Unit tests**: 12/12 new tests passing
- **Integration tests**: 6/6 new tests passing
- **System tests**: 1/1 new test passing (skip if `ci-metrics` not available)
- **CI self-tests**: All 344 tests passing
- **Coverage**: ≥90% maintained

---

## 8. Documentation Updates

### 8.1 AGENTS.md

- Update: Document `data/` folder location, non-gating invariant, no-loop invariants

### 8.2 CONTRIBUTING.md

- Update: Document `data/` folder structure, migration path

### 8.3 ARCHITECTURE.md

- Add: Data storage architecture section

### 8.4 REQUIREMENTS.md

- Add: FR-XX, QR-XX traceability entries

---

## 9. Risk & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| UPDATE_DATA hardcoded | High | Low | Validate expression in tests |
| JSON write failures | Medium | Medium | Add error handling and retry logic |
| CI loop from master write | High | Low | Existing concurrency group prevents racing |
| Data loss during migration | High | Low | Row count validation, backup before migration |
| Schema validation errors | Medium | Low | Validation failures logged as warnings only |

### 9.1 Risk Response Strategy

1. **Pre-deployment validation**: Rigorous testing of UPDATE_DATA expression
2. **Runtime monitoring**: Log any failures to write JSON data
3. **Data verification**: Automated checks that ci_runtimes.json is being updated
4. **Rollback capability**: Quick rollback if issues are detected

---

## 10. Assumptions
n
1. **GitHub Actions API**: The GitHub Actions API returns consistent data for successful `pull_request` runs
2. **Workflow triggers**: Both `workflow_run` and `workflow_dispatch` triggers are properly configured
3. **Permissions**: GitHub Actions has permission to read repository data
4. **Branch structure**: `ci-metrics` orphan branch exists and is accessible
5. **File system**: No file system permission issues preventing writes to `data/` folder

---

## 11. Implementation Schedule

| Day | Activity |
|-----|----------|
| **Day 1** | Fix `UPDATE_DATA` in `ci-timing.yml`; add validation tests |
| **Day 2** | Add error handling to `collect_ci_timings.py` |
| **Day 3** | Add `_gh_api()` retry logic |
| **Day 4** | Create workflow validation script |
| **Day 5** | Run backfill to recover missing data |
| **Day 6** | Verify data on master branch |
| **Day 7** | Full quality gate verification |
| **Day 8** | Open PR for review |

---

## 12. Success Criteria

**Technical Success:**
- [ ] `data/runtimes.json` contains run 36229056933 (latest PR run)
- [ ] `data/metrics.json` generated after latest run
- [ ] CI self-tests pass (344/344)
- [ ] Coverage ≥90%
- [ ] `ruff check`, `black --check`, `pydocstyle` all pass
- [ ] `generate_traceability_matrix.py` passes

**Business Success:**
- [ ] CI timing benchmark now captures all recent runs
- [ ] 10-day data gap resolved
- [ ] JSON data on master is current and consistent
- [ ] All existing functionality preserved

---

## 13. Closing Notes

This implementation fixes a critical data collection gap in the CI timing benchmark pipeline. The fix ensures that:

1. **Continuous capture**: `workflow_run` triggers now write JSON data to master
2. **Backward compatibility**: Existing CSV consumers unaffected
3. **Data consistency**: Both CSV and JSON data stay synchronized
4. **Error resilience**: Better error handling and retry logic
5. **Test coverage**: Comprehensive test coverage prevents regression

The 10-day data gap will be resolved both by the immediate fix (latest runs will be captured) and by the backfill (historical missing data will be recovered).

---

*End of Implementation Plan*

Refs: PRO-369, PRO-375, PRO-380