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
# Unit tests only
python -m pytest tests/unit -m unit

# Integration tests only  
python -m pytest tests/integration -m integration

# System tests (requires real data files)
python -m pytest tests/system -m system
```

**Fast CI mode** (skip system tests when no real data):
```bash
python -m pytest -m "not system"
```

**Run full test suite locally** (verifies all checks):
```bash
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing -q
```

## Critical Project Structure (Agents often miss these paths)

- **Main package**: `src_timesheetalgo/` 
  - Contains `TimeSheetAlgo.py` (entrypoint)
  - Contains `config.yaml` (configuration file)
  - Contains `naming_validation.py` (naming convention rules)

- **Test structure** (mirror of code structure):
  - `tests/unit/` - Unit tests (80% of tests)
  - `tests/integration/` - Integration tests (17 tests)
  - `tests/system/` - System tests (7 tests, requires real data)
  - All test files use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.system`

- **Documentation structure**:
  - `doc/ARCHITECTURE.md` - System architecture diagrams
  - `doc/CONTRIBUTING.md` - Detailed contributing guidelines
  - `doc/TESTING.md` - Comprehensive testing documentation
  - `tests/boundary_equivalence_analysis.md` - Boundary analysis documentation

## Key Conventions Agents Often Miss

**Python Requirements**:
- Python ≥3.9 (currently 3.12 in README)
- Dependencies: `openpyxl==3.1.5`, `PyYAML==6.0.1` (exact versions pinned)

**Configuration Structure** (`src_timesheetalgo/config.yaml`):
```yaml
year: 2025
environments:
  development:
    file_paths:
      timelog_path: "FDTech_timelog.csv"
      timesheet_path: "2025_FDTech_Dennis_Hartel.xlsm"
    logging:
      level: "INFO"
      format: "%(asctime)s - %(levelname)s - %(message)s"
  production:
    file_paths:
      timelog_path: "Timealarm/FDTech_timelog.csv"
      timesheet_path: "2025_FDTech_Dennis_Hartel.xlsm"
    logging:
      level: "WARNING"
      format: "%(asctime)s - %(levelname)s - %(message)s"
default_environment: "development"
```

**Testing Requirements**:
- 103 total tests (79 unit, 17 integration, 7 system, 1 xfail)
- ~99% branch/line coverage (CI gate: 90%)
- Traceability between requirements/architecture/implementation validated in CI
- Boundary-value and equivalence-class testing documented in `tests/boundary_equivalence_analysis.md`

## Critical CI/CD Workflow Details

**.github/workflows/** naming conventions:
- `test-*.py` → Tests for workflow scripts (e.g., `test-docs-traceability.py`)
- `*-*.py` → Action implementation files (e.g., `pr-test-summary.py`, `naming-validation.py`)
- `*.yml` → Complete workflow definitions (e.g., `python-ci.yml`)

**Commit/PR Title Validation**:
- Enforced via GitHub Actions per `doc/CONTRIBUTING.md`
- Required format: `feat:`, `fix:`, `docs:`, etc. prefixes
- Automated validation prevents invalid titles from being merged

## Gotchas Agents Commonly Miss

1. **Virtual Environment Activation**:
   - Must reactivate after branch switching
   - Failure results in "ModuleNotFoundError" for local packages

2. **System Test Data Requirements**:
   - System tests require real CSV/Excel files
   - CI provides test data files - local runs may fail without sample data

3. **Configuration Path Resolution**:
   - Paths in `config.yaml` are relative to project root, not script location
   - Working directory must be repository root

4. **Branch Strategy Flow**:
   - Feature branches → PR to master (tests required) → merge to master
   - Master → release/vX.Y.Z branches (for versioning)
   - Release tags → production deployment
   - Never deploy directly from master

5. **Testing Hierarchy**:
   - Unit tests: Isolated function/method testing
   - Integration tests: `TimeSheetProcessor` pipeline on memory workbook
   - System tests: Black-box real-file testing (skipped if data missing)

## Critical Conventions

- **Branch naming**: `feature/PRO-123-description` format
- **Commit messages**: Must follow conventional Commits spec (fe-review required)
- **PR validation**: Full test suite required for master merges
- **Release process**: Only deploy from version tags (`vX.Y.Z`)
- **Environment management**: Always activate venv when switching branches

> **Note**: All paths are relative to repository root, not script execution directory.
> Working directory must be the project root for proper configuration loading.