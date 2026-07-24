# AGENTS.md — TimeSheetAlgo

## Critical Commands (Agents often miss these specifics)

**Install development dependencies** (required for local work):
```bash
python -m pip install -e .[dev]
```

**Activate virtual environment when switching branches** (critical for config):
```bash
git checkout <branch-name>
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
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

## Critical Project Structure (Agents often miss these paths)

- **Main package**: `src_timesheetalgo/`
  - `TimeSheetAlgo.py` - entrypoint
  - `config.yaml` - configuration file
  - `naming_validation.py` - naming convention rules

- **Test structure**:
  - `tests/unit/` - Unit tests (79 tests)
  - `tests/integration/` - Integration tests (17 tests)
  - `tests/system/` - System tests (7 tests, requires real data)
  - All test files use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.system`

- **Documentation**:
  - `doc/ARCHITECTURE.md` - System architecture diagrams
  - `doc/CONTRIBUTING.md` - Contributing guidelines
  - `doc/TESTING.md` - Testing documentation
  - `tests/boundary_equivalence_analysis.md` - Boundary analysis

## Configuration Structure (`src_timesheetalgo/config.yaml`)

```yaml
file_paths:
  timelog_path: "FDTech_timelog.csv"
  timesheet_path: "2025_FDTech_Dennis_Hartel.xlsm"
```
- Paths are **relative to project root**, not script location
- Default environment: `development` (use `production` for live data)

## Testing Requirements

- 103 total tests (79 unit, 17 integration, 7 system, 1 xfail)
- ~99% branch/line coverage (CI gate: 90%)
- System tests require real data files: `sup/2025_extract.csv` and `src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm`

## Gotchas Agents Commonly Miss

1. **Virtual Environment Activation**: Must reactivate after branch switching - failure results in "ModuleNotFoundError" for local packages

2. **System Test Data Requirements**: System tests require real CSV/Excel files committed to repo - local runs fail without sample data

3. **Configuration Path Resolution**: Paths in `config.yaml` are relative to project root, not script location - working directory must be repository root

4. **Branch Strategy Flow**:
   - Feature branches → PR to master (tests required) → merge
   - Master → release/vX.Y.Z branches
   - Release tags → production deployment
   - Never deploy directly from master

5. **Testing Hierarchy**:
   - Unit: Isolated function/method testing
   - Integration: `TimeSheetProcessor` pipeline on memory workbook
   - System: Black-box real-file testing (skipped if data missing)

## Critical Conventions

- **Branch naming**: `feature/PRO-123-description` format
- **Commit messages**: Must follow conventional Commits spec (fe-review required)
- **PR validation**: Full test suite required for master merges
- **Release process**: Only deploy from version tags (`vX.Y.Z`)
- **Environment management**: Always activate venv when switching branches

> **Note**: All paths are relative to repository root, not script execution directory. Working directory must be project root for configuration loading.