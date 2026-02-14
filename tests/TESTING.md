# TimeSheetAlgo.py Testing Documentation

## Overview
**Before running tests:** install the test dependencies: `python -m pip install -e .[dev]` (this provides `freezegun`, `pytest`, `openpyxl` etc.).
This document provides comprehensive testing information for the TimeSheetAlgo.py application, including unit tests, system verification tests, and configuration testing.

> **Note:** For detailed test execution results and verification reports, see [`verification_report_2025-11-21.md`](verification_report_2025-11-21.md).

## Test Structure and Organization

### 1. Unit Tests (`test_unit.py`)

**Purpose:** Test individual functions and methods in isolation with comprehensive error handling

**Marker:** `@pytest.mark.unit` (default tests for CI/PR checks)

**Test Categories:**
1. **Configuration Loading Tests (10 tests)** - Validate [`load_config()`](../src_timesheetalgo/TimeSheetAlgo.py:34) function
   - External YAML configuration parsing
   - Environment-specific configuration loading
   - Error handling for various config issues
   - Path resolution and validation
   
2. **Date Parsing Tests (2 tests)** - Validate [`parse_date()`](../src_timesheetalgo/TimeSheetAlgo.py:109) function
   - Valid date format parsing (DD.MM.YYYY)
   - Invalid date handling with retry logic

3. **File Handling Tests (6 tests)** - Test [`check_file_existence()`](../src_timesheetalgo/TimeSheetAlgo.py:131) function
   - CSV file loading and parsing
   - Excel file loading with VBA preservation
   - File not found error handling
   - Permission denied error handling

4. **TimeSheetProcessor Class Tests (15 tests)** - Test all methods of [`TimeSheetProcessor`](../src_timesheetalgo/TimeSheetAlgo.py:189)
   - Date input and validation
   - Timelog data selection and filtering
   - Data storage with overwrite handling
   - File operations (load/save)

**Key Features:**
- Uses pytest fixtures for mock data
- Parameterized tests for multiple input scenarios
- Monkeypatching for user input simulation
- Temporary file creation for testing
- Comprehensive exception testing
- 100% coverage of all exception handlers

### 2. Integration Tests (`test_integration.py`)

**Purpose:** Test loading of real data files (CSV and Excel)

**Marker:** `@pytest.mark.integration` (requires real files)

**Test Coverage:**
- Real CSV timelog loading (93 records from `sup/2025_extract.csv`)
- Real Excel workbook loading (structured with 12 monthly sheets)

### 3. System Verification Tests (`test_system.py`)

**Purpose:** End-to-end verification of the complete system functionality with real data

**Marker:** `@pytest.mark.system` (may be slow, excluded from default CI runs)

**Test Categories:**
1. **Data Loading Verification** - Real file loading tests
   - CSV parsing with real 2025 data (93 records)
   - Excel workbook structure validation
   
2. **Date Processing Verification** - Core algorithm validation
   - Date format parsing (05 different dates)
   - Month extraction and validation
   
3. **Worksheet Mapping Verification** - Component interaction
   - Date-to-worksheet indexing (4 different months)
   - Worksheet name verification
   
4. **Row Calculation Verification** - Algorithm validation
   - ROW_OFFSET application (3 different days)
   - Row indexing accuracy
   
5. **Column Placement Verification** - Target cell validation
   - Column E (5) for start times
   - Column F (6) for end times
   - Coordinate accuracy
   
6. **Data Integrity Verification** - Actual Excel manipulation
   - Data writing to cells
   - Data reading/verification
   - Original data restoration

**Key Features:**
- Uses real data files (2025_extract.csv, 2025_FDTech_Dennis_Hartel.xlsm)
- Creates backup files before testing
- Comprehensive logging to verification.log
- Restores original data after testing
- Non-destructive testing approach
- Detailed verification reports

### 4. Configuration Testing (Integrated)

**Coverage:**
- ✅ YAML file parsing and validation
- ✅ Environment-specific configuration selection
- ✅ File path resolution (absolute and relative)
- ✅ Logging configuration application
- ✅ Graceful fallback to defaults
- ✅ Comprehensive error handling with custom ConfigError exception

## Test Configuration

### pytest.ini Configuration
```ini
[pytest]
pythonpath = .
testpaths = tests
markers =
    unit: fast unit tests (no external I/O)
    integration: integration tests (require I/O)
    system: end-to-end verification (may be slow)
addopts = -q --disable-warnings -m "unit"
```

**Key Points:**
- **pythonpath = .** - Makes `src_timesheetalgo` package discoverable with correct imports
- **Default Mode** - Runs only unit tests (`-m "unit"`)
  - Fast feedback loop (< 1 second on PR checks)
  - No external file dependencies
  - No slow operations
- **Integration/System Mode** - Use `-m "not system"` or `-m "system"` explicitly
  - Include slower tests with real files
  - Useful for local development and release validation

### Dependencies (pyproject.toml)
Project dependencies and dev/extras are defined in `pyproject.toml` (PEP 621). Example key test/dev dependencies include:
- `pytest==8.3.4` - Testing framework
- `pytest-cov==5.0.0` - Coverage reporting
- `openpyxl==3.1.5` - Excel file handling
- Additional development tools (black, flake8, ruff, etc.)

## Running Tests

### Default (Unit Tests Only - Fast CI/PR Feedback)
```bash
python -m pytest
# or explicitly:
python -m pytest -m unit -q
```

### Unit Tests with Coverage
```bash
python -m pytest -m unit --cov=src_timesheetalgo --cov-report=term-missing
```

### Integration Tests Only
```bash
python -m pytest -m integration -q
```

### System Verification Tests
```bash
python -m pytest -m system -q
```

### All Tests (except System)
```bash
python -m pytest -m "not system" -v
```

### All Tests (including System)
```bash
python -m pytest tests/ -v --override-ini="addopts="
```

## Known Issues and Recommendations

### Current Issues:
1. **Fallback Configuration Handler:** Lines 128-131 only executed if config file missing
   - **Impact:** Minimal - graceful fallback in place
   - **Status:** Acceptable - fallback paths tested implicitly
   - **Note:** Difficult to test without removing config file

2. **Exception Re-raise Handlers:** Lines 69-70 in YAML error handling
   - **Impact:** None - error handling works correctly
   - **Status:** Acceptable - alternative paths tested

### Recommendations:
1. **Configuration Enhancement** - Add environment variable override support
2. **Extended Testing** - Add integration tests for complete workflow scenarios
3. **Performance Testing** - Consider performance testing with large datasets (500+ records)
4. **Documentation** - Add configuration setup guide for developers

## External Configuration System

### Configuration File Location
- **Primary Location:** `src_timesheetalgo/config.yaml`
- **Format:** YAML (human-readable and version-controllable)

### Supported Environments
1. **Development** - For local development and testing
   ```yaml
   development:
     file_paths:
       timelog_path: "FDTech_timelog.csv"
       timesheet_path: "2025_FDTech_Dennis_Hartel.xlsm"
     logging:
       level: "INFO"
   ```

2. **Production** - For production deployment
   ```yaml
   production:
     file_paths:
       timelog_path: "Timealarm/FDTech_timelog.csv"
       timesheet_path: "2025_FDTech_Dennis_Hartel.xlsm"
     logging:
       level: "WARNING"
   ```

### Configuration Validation
- ✅ Required keys validation (environments, file_paths)
- ✅ File path existence checking
- ✅ YAML syntax validation
- ✅ Environment selection validation
- ✅ Custom ConfigError exceptions with helpful messages

### Error Handling
The configuration system includes comprehensive error handling:
- Missing config file → Graceful fallback to hardcoded paths
- Invalid YAML → ConfigError with details
- Missing environments → Clear error message with available options
- Incomplete file paths → Validation with specific missing keys
- Invalid structure → Clear error about expected format

## Test Data Files

### Input Files:
- `sup/2025_extract.csv` - Real timelog data (93 records)
- `src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm` - Target Excel timesheet

### Generated Files:
- `test_system_timesheetalgo_verification.log` - Detailed test execution log
- `src_timesheetalgo/2025_FDTech_Dennis_Hartel_VERIFICATION_BACKUP.xlsm` - Backup file

## Verification Reports

Detailed verification reports documenting specific test runs are maintained separately:

| Report | Date | Status |
|--------|------|--------|
| [`verification_report_2025-12-23.md`](verification_report_2025-12-23.md) | 2025-12-23 | ✅ APPROVED |
| [`verification_report_2025-11-21.md`](verification_report_2025-11-21.md) | 2025-11-21 | ✅ APPROVED |

These reports serve as audit artifacts documenting production readiness verification.

---

**Last Updated:** 2025-12-23  
**Test Environment:** Linux, Python 3.12, pytest 8.3.4  
**Coverage Report:** HTML available in `tests/reports/htmlcov/index.html`
