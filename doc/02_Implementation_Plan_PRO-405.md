# Implementation Plan: PRO-405 - Clean up and standardize TimeSheetAlgo project structure to resolve inconsistencies

**Status:** Draft  
**Epic Link:** [Not set - no TimeSheet epic exists]  
**Parent:** PRO-405 (this is the top-level ticket)  
**Priority:** Medium  
**Story Points:** 5  

---

## 1. Design Decisions

### 1.1 Problem Summary

The TimeSheetAlgo project structure contains several inconsistencies that violate established project conventions and create technical debt:

* `src_azesheetalgo/` directory is NOT packaged and NOT tested per AGENTS.md conventions
* `ci/scripts/` location is inconsistent with `.github/scripts/` convention for CI pipeline scripts
* Data files (`metrics.json`, `runtimes.json`, `runtimes_backfill.json`) have ambiguous names that should be more explicit
* Documentation and test references are scattered and inconsistent

### 1.2 Data Storage Requirements

* `src_azesheetalgo/` must be removed entirely (no packaged functionality)
* CI scripts must be moved from `ci/scripts/` to `.github/scripts/`
* Data files must be renamed with clear, explicit names:
  * `data/metrics.json` → `ci_metrics.json`
  * `data/runtimes.json` → `ci_runtimes.json`
  * `data/runtimes_backfill.json` → `ci_runtimes_migration.csv`
* All references across documentation, tests, and code must be updated

### 1.3 Problem Decomposition

The issue is a systematic cleanup of project structure inconsistencies. The root cause is deviation from established conventions in AGENTS.md and the project architecture. This requires:

1. **Directory cleanup**: Remove `src_azesheetalgo/` (old AZE tool)
2. **Script relocation**: Move CI scripts to standard location
3. **Data file renaming**: Make data file names explicit and consistent
4. **Reference updates**: Update all documentation, tests, and code references
5. **Documentation updates**: Update AGENTS.md and other project documentation
6. **Configuration updates**: Update `.gitignore` for explicit Python cache

### 1.4 Solution Strategy

1. **Remove obsolete directory**: Delete `src_azesheetalgo/` entirely
2. **Relocate scripts**: Move `ci/scripts/validate_pr_merge.py` and `ci/scripts/validate_filesystem.py` to `.github/scripts/`
3. **Rename data files**: Apply new naming convention to all three data files
4. **Update references**: Systematically update all references in documentation, tests, and code
5. **Update documentation**: Update AGENTS.md and other project docs to reflect new structure
6. **Update configuration**: Add explicit Python cache directories to `.gitignore`

### 1.5 Implementation Plan

| Phase | Activity | Files Modified | Tests |
|-------|----------|----------------|-------|
| **1: Cleanup** | Remove `src_azesheetalgo/` directory | `src_azesheetalgo/` | Unit tests (remove imports) |
| **2: Relocate** | Move CI scripts from `ci/scripts/` to `.github/scripts/` | `ci/scripts/validate_pr_merge.py`, `ci/scripts/validate_filesystem.py` | Unit tests (update imports) |
| **3: Rename** | Rename data files with new naming convention | `data/metrics.json`, `data/runtimes.json`, `data/runtimes_backfill.json` | Integration tests (verify data integrity) |
| **4: Update** | Update all references in documentation, tests, and code | All project files referencing old paths | System tests (verify reference integrity) |
| **5: Document** | Update AGENTS.md and other project documentation | `AGENTS.md`, other project docs | Documentation validation |
| **6: Configure** | Update `.gitignore` for explicit Python cache | `.gitignore` | No specific tests |

### 1.6 Testing Strategy

**Unit Tests:**
- Test validation scripts (`validate_pr_merge.py`, `validate_filesystem.py`) import from new locations
- Test file operations and cache management in updated scripts
- Test CI pipeline script functionality after relocation

**Integration Tests:**
- Test cross-file references after refactoring
- Test script location changes in CI pipeline
- Test data file renaming and migration paths

**System Tests:**
- Test complete CI pipeline with updated script locations
- Test end-to-end workflow with new file structure
- Test project build and deployment processes

### 1.7 Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Script import errors in tests | High | Medium | Comprehensive test updates across all test files |
| Documentation inconsistency | Medium | Low | Systematic reference updates across all documentation |
| Data file corruption during rename | High | Low | Verify data integrity and content preservation |
| CI pipeline breakage | High | Medium | Update CI configuration and test all pipeline stages |
| Reference missed in updates | Medium | Medium | Systematic grep-based reference verification |

---

## 2. Implementation Plan

### 2.1 Files to Create/Modify/Delete

| File | Change | Description |
|------|--------|-------------|
| `src_azesheetalgo/` | **DELETE** | Remove obsolete AZE tool directory (NOT packaged, NOT tested) |
| `ci/scripts/validate_pr_merge.py` | **MOVE** | Move to `.github/scripts/validate_pr_merge.py` |
| `ci/scripts/validate_filesystem.py` | **MOVE** | Move to `.github/scripts/validate_filesystem.py` |
| `data/metrics.json` | **RENAME** | Rename to `ci_metrics.json` (preserve content) |
| `data/runtimes.json` | **RENAME** | Rename to `ci_runtimes.json` (preserve content) |
| `data/runtimes_backfill.json` | **RENAME** | Rename to `ci_runtimes_migration.csv` (convert JSON to CSV) |
| `AGENTS.md` | **UPDATE** | Update file structure documentation and conventions |
| `.github/workflows/*` | **UPDATE** | Update script path references in CI workflows |
| `.github/scripts/*` | **UPDATE** | Add new validation scripts and update existing ones |
| `tests/**` | **UPDATE** | Update all test imports and file path references |
| `doc/**` | **UPDATE** | Update documentation references to new file locations |
| `.gitignore` | **UPDATE** | Add explicit Python cache directories |

### 2.2 Rollout Steps

**Step 1: Directory Cleanup (High Priority)**
- Remove `src_azesheetalgo/` directory entirely
- Update any references in project documentation
- Verify no remaining imports or references to the directory

**Step 2: Script Relocation (High Priority)**
- Move `ci/scripts/validate_pr_merge.py` → `.github/scripts/validate_pr_merge.py`
- Move `ci/scripts/validate_filesystem.py` → `.github/scripts/validate_filesystem.py`
- Update script content if they contain hardcoded path references
- Update CI workflows to reference new script locations

**Step 3: Data File Renaming (Medium Priority)**
- Rename `data/metrics.json` → `ci_metrics.json`
- Rename `data/runtimes.json` → `ci_runtimes.json`
- Rename `data/runtimes_backfill.json` → `ci_runtimes_migration.csv` (convert JSON to CSV format)
- Update scripts that read/write these files to use new names

**Step 4: Reference Updates (Medium Priority)**
- Update all documentation files to reference new file paths
- Update all test files to import from new locations
- Update code files that reference the moved/renamed files
- Use grep-based systematic search to ensure no references are missed

**Step 5: Documentation Updates (Low Priority)**
- Update AGENTS.md to reflect new file structure and conventions
- Update any other project documentation that references file locations
- Ensure all documentation is consistent with new structure

**Step 6: Configuration Updates (Low Priority)**
- Update `.gitignore` to include explicit Python cache directories
- Ensure Python cache directories are properly ignored

### 2.3 Non-Goals

* Remove any other directories or files not explicitly listed in the clean-up plan
* Modify the actual functionality of validation scripts or CI pipeline logic
* Change the core application code or business logic
* Update external dependencies or configuration files beyond the scope
* Convert data files to different formats beyond JSON→CSV conversion for runtimes_backfill.json
* Update any files outside the project root

---

## 3. Verification Definition

### 3.1 Acceptance Criteria Verification

**AC-1: `src_azesheetalgo/` directory removed from project root**
- [ ] Directory `src_azesheetalgo/` does not exist
- [ ] No files or references remain in the project
- [ ] Build system does not attempt to package the directory

**AC-2: `ci/scripts/validate_pr_merge.py` moved to `.github/scripts/validate_pr_merge.py`**
- [ ] File exists at `.github/scripts/validate_pr_merge.py`
- [ ] Original file `ci/scripts/validate_pr_merge.py` does not exist
- [ ] Script content is preserved (functionality unchanged)

**AC-3: `ci/scripts/validate_filesystem.py` moved to `.github/scripts/validate_filesystem.py`**
- [ ] File exists at `.github/scripts/validate_filesystem.py`
- [ ] Original file `ci/scripts/validate_filesystem.py` does not exist
- [ ] Script content is preserved (functionality unchanged)

**AC-4: `data/metrics.json` renamed to `ci_metrics.json` with same content**
- [ ] File `ci_metrics.json` exists with same content as original `metrics.json`
- [ ] Original `data/metrics.json` does not exist
- [ ] Scripts reading this file have been updated

**AC-5: `data/runtimes.json` renamed to `ci_runtimes.json` with same content**
- [ ] File `ci_runtimes.json` exists with same content as original `runtimes.json`
- [ ] Original `data/runtimes.json` does not exist
- [ ] Scripts reading this file have been updated

**AC-6: `data/runtimes_backfill.json` renamed to `ci_runtimes_migration.csv`**
- [ ] File `ci_runtimes_migration.csv` exists (converted from JSON)
- [ ] Original `data/runtimes_backfill.json` does not exist
- [ ] Data conversion preserves all original data
- [ ] Scripts reading this file have been updated

**AC-7: All documentation files updated with new file paths and references**
- [ ] All `.md` files in project root and `doc/` updated
- [ ] All references to old file paths are updated
- [ ] Documentation is consistent with new structure

**AC-8: All test files updated to import from new locations**
- [ ] All test files reference new file locations
- [ ] Test imports are updated to use new paths
- [ ] Test functionality is preserved

**AC-9: AGENTS.md updated to reflect new file structure and conventions**
- [ ] AGENTS.md updated with new file structure documentation
- [ ] All conventions and references are current
- [ ] Project documentation is consistent

**AC-10: .gitignore updated to include explicit Python cache directories**
- [ ] `.gitignore` contains explicit Python cache directory entries
- [ ] Python cache directories are properly ignored
- [ ] No unintended files are ignored

### 3.2 Definition of Done

- [ ] All 10 acceptance criteria are checkmarked
- [ ] All tests pass (unit, integration, system)
- [ ] CI pipeline runs successfully
- [ ] Lint checks pass (ruff, black, pydocstyle, radon)
- [ ] Traceability matrix updated
- [ ] Implementation plan file deleted after completion
- [ ] JIRA ticket closed (Fertig)
- [ ] Story Points assigned (5)
- [ ] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md
- [ ] CI self-tests: All tests passing
- [ ] Application tests: All tests passing (≥90% coverage)
- [ ] Implementation plan updated and deleted
- [ ] JIRA description fully checkmarked

### 3.3 Verification Commands

**File Existence Verification:**
```bash
# Check that old files are gone
find . -name "src_azesheetalgo" -type d 2>/dev/null
find . -path "./ci/scripts/*.py" -type f 2>/dev/null
find . -path "./data/*.json" -type f 2>/dev/null

# Check that new files exist
find . -name "ci_metrics.json" -o -name "ci_runtimes.json" -o -name "ci_runtimes_migration.csv" -type f 2>/dev/null
find . -path "./.github/scripts/*.py" -type f 2>/dev/null
```

**Reference Verification:**
```bash
# Check for remaining references to old paths
grep -rn "ci/scripts/" . --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" 2>/dev/null | grep -v ".git/" | grep -v ".venv/"

grep -rn "data/metrics.json\|data/runtimes.json\|data/runtimes_backfill.json" . --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" 2>/dev/null | grep -v ".git/" | grep -v ".venv/"
```

**Test Verification:**
```bash
# Run unit tests
python -m pytest tests/ -m unit -q

# Run integration tests  
python -m pytest tests/ -m integration -q

# Run system tests (if resources available)
python -m pytest tests/ -m system -q
```

**CI Self-Test Verification:**
```bash
# Run CI pipeline self-tests
python -m pytest tests/ci-pipeline/ -q
```

**Lint Verification:**
```bash
# Run lint checks
ruff check src_timesheetalgo tests .github
black --check src_timesheetalgo tests .github
pydocstyle src_timesheetalgo tests .github
radon cc src_timesheetalgo -a
```

**Traceability Verification:**
```bash
# Generate and verify traceability matrix
python .github/scripts/generate_traceability_matrix.py
```

---

**Plan Status:** Ready for implementation  
**Next Step:** Begin Phase 4 rollout (Script Relocation)
