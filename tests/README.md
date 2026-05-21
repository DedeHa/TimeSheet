# Test Structure Documentation

## Overview

This project uses a three-tier testing strategy to ensure code quality and reliability:
- **Unit Tests**: Test individual functions and methods in isolation
- **Integration Tests**: Test multiple components working together (end-to-end workflows)
- **System Tests**: Test the complete system with real resources (CSV and Excel files)

## Test Categories

### Unit Tests (`test_unit.py`)
**Purpose**: Verify individual components work correctly in isolation.

**Coverage**:
- Configuration loading and validation
- Date parsing and formatting
- File I/O operations
- TimeSheetProcessor methods
- Edge cases and error handling

**Run with**: `pytest tests/ -m unit` (69 tests)

**Key Features**:
- Uses mock files and fixtures
- No external file dependencies
- Fast execution (~2 seconds)
- Tests error conditions and edge cases

### Integration Tests (`test_integration.py`)
**Purpose**: Verify that multiple components work together correctly through complete workflows.

**Coverage**:
- End-to-end workflows (load → select → store → save)
- Multiple month handling
- Data overwrite scenarios
- Real resource loading (if available)
- Complex realistic scenarios

**Run with**: `pytest tests/ -m integration` (10 tests)

**Key Test Groups**:
1. **TestLoadRealResources**: Loading actual project files
2. **TestEndToEndWorkflow**: Complete workflows from load to save
3. **TestComplexScenarios**: Real-world use cases and edge cases
4. **TestRealResourceIntegration**: Full pipeline with actual data

### System Tests (`test_system.py`)
**Purpose**: Comprehensive verification of the complete system with real resources.

**Coverage**:
- Data loading verification
- Date parsing validation
- Worksheet mapping
- Row calculation correctness
- Column placement accuracy
- Data integrity with actual Excel operations

**Run with**: `pytest tests/ -m system` (1 test)

**Requirements**:
- Real CSV file: `sup/2025_extract.csv`
- Real Excel file: `src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm`
- Test creates backups before modifications

## Running Tests

### Run All Tests
```bash
pytest tests/
# or
python -m pytest tests/
```

### Run by Category
```bash
# Unit tests only
pytest tests/ -m unit

# Integration tests only
pytest tests/ -m integration

# System tests only
pytest tests/ -m system

# Unit + Integration (everything except system)
pytest tests/ -m "unit or integration"
```

### Run Specific Test File
```bash
pytest tests/test_unit.py
pytest tests/test_integration.py
pytest tests/test_system.py
```

### Run with Coverage
```bash
pytest tests/ --cov=src_timesheetalgo --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v
pytest tests/ -vv  # Very verbose
```

### Run with Logging
```bash
pytest tests/ --log-cli-level=DEBUG
```

## Test Configuration

The test environment is configured via:
- **`pytest.ini`**: Pytest markers, test discovery, and logging configuration
- **`tests/conftest.py`**: Shared fixtures and test setup

### Fixtures (from `conftest.py`)
- `mock_workbook`: Creates a dummy Excel workbook
- `mock_csv_file`: Creates a temporary CSV file with test data
- `mock_excel_file`: Creates a temporary Excel file
- `mock_processor`: Creates a TimeSheetProcessor with mock files
- `real_resource_copy`: Copies real project files to temp directory
- `frozen_time`: Freezes time for deterministic tests (2025-12-23)

## Integration Test Details

### TestEndToEndWorkflow
Tests the core workflow steps:
1. **test_e2e_load_and_select_data**: Load files and filter by date range
2. **test_e2e_load_select_and_store_single_entry**: Process single entry to Excel
3. **test_e2e_load_select_and_store_multiple_months**: Distribute entries across months
4. **test_e2e_full_workflow_with_save**: Complete pipeline including file save

### TestComplexScenarios
Tests real-world situations:
1. **test_scenario_week_of_entries_with_various_times**: Process variable work hours
2. **test_scenario_data_overwrite_workflow**: Handle data conflicts with user confirmation
3. **test_scenario_cross_year_boundary_not_supported**: Verify year boundary handling

### TestLoadRealResources
Tests actual project files:
1. **test_load_real_csv**: Load and validate real timelog CSV
2. **test_load_real_excel**: Load and validate real Excel workbook

## Writing New Tests

### For Unit Tests
```python
import pytest
from src_timesheetalgo.TimeSheetAlgo import function_to_test

pytestmark = pytest.mark.unit

def test_function_behavior(mock_processor):
    """Test that function does X when Y condition exists."""
    # Setup
    mock_processor.setup_data()
    
    # Execute
    result = mock_processor.do_something()
    
    # Verify
    assert result == expected_value
```

### For Integration Tests
```python
import pytest
from src_timesheetalgo.TimeSheetAlgo import TimeSheetProcessor

pytestmark = pytest.mark.integration

class TestMyWorkflow:
    """Test a complete workflow."""
    
    def test_workflow_scenario(self, mock_processor):
        """Test that workflow produces correct output."""
        # Load and configure
        mock_processor.timelog = [["15.03.2025", "09:00", "17:00"]]
        mock_processor.obj_date_startpoint = datetime(2025, 3, 15)
        
        # Execute workflow steps
        mock_processor.select_timelog_data()
        mock_processor.store_data()
        
        # Verify complete state
        assert mock_processor.timesheet.worksheets[2].cell(row=19, column=5).value == "09:00"
```

## Test Metrics

Current test coverage:
- **Unit Tests**: 69 tests - Fast, isolated tests of individual functions
- **Integration Tests**: 10 tests - Complete workflows and complex scenarios
- **System Tests**: 1 test - Full system with real resources
- **Total**: 80 tests

Expected execution time: ~4 seconds for full suite

## CI/CD Integration

Tests are run in CI/CD pipeline:
- **Development Branches** (`feature/*`, etc.): Lint checks
- **Master PRs**: Full test suite (Unit + Integration)
- **Release Tags**: Tests inherited from master (already passing)
- **System Tests**: Run manually when real resources are available

See `.github/workflows/python-ci.yml` for CI configuration.

## Troubleshooting

### Tests Fail with Import Errors
Ensure the repository root is on the Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:/workspaces/TimeSheet"
pytest tests/
```

### Tests Fail with "Module Not Found"
Verify package structure:
```bash
ls -la /workspaces/TimeSheet/src_timesheetalgo/
# Should contain: TimeSheetAlgo.py, __init__.py
```

### System Tests Skipped
System tests require real files to be present:
```bash
# Check if real files exist
ls -la sup/2025_extract.csv
ls -la src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm
```

If files don't exist, system tests will be skipped (expected behavior).

## Best Practices

1. **Use descriptive test names**: Should clearly state what is being tested
2. **Keep tests independent**: Each test should work in isolation
3. **Use fixtures for setup**: Reuse common setup through fixtures
4. **Mock external dependencies**: Don't rely on real files for unit tests
5. **Group related tests**: Use test classes to organize related tests
6. **Add docstrings**: Explain what each test verifies
7. **Avoid test interdependencies**: Tests should be runnable in any order

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest markers](https://docs.pytest.org/en/stable/how-to/mark.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
