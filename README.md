# TimeSheetAlgo

Automated timesheet data extraction, documentation, and AZE sheet creation tool.

## Table of Contents

- [Description](#description)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Documentation](#documentation)
- [Development](#development)

## Description

TimeSheetAlgo automates the manual process of:
- Extracting time data from CSV timelogs
- Processing and validating time entries
- Populating Excel timesheet templates

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd TimeSheet

# Install dependencies
python -m pip install -e .[dev]

# Run the application
python src_timesheetalgo/TimeSheetAlgo.py
```

## Installation

### Prerequisites

- Python 3.12+
- pip (Python package manager)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd TimeSheet
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   # Development install with dev dependencies
   python -m pip install -e .[dev]
   # For a production install without dev extras:
   # python -m pip install .
   ```

4. **Configure the application:**
   - Copy or edit `src_timesheetalgo/config.yaml`
   - Set appropriate file paths for your environment

## Configuration

The application uses YAML-based configuration located at [`src_timesheetalgo/config.yaml`](src_timesheetalgo/config.yaml).

### Environments

| Environment | Description | Log Level |
|-------------|-------------|-----------|
| `development` | Local development and testing | INFO |
| `production` | Production deployment | WARNING |

### Configuration Options

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

**Configuration Key Points:**
- `year`: (Required, root level) - Work year for timesheet (e.g., `2025`)
- `environments`: Contains development and production configurations
- `file_paths`: Paths to timelog CSV and timesheet Excel files
- `logging`: Log level and format for each environment
- `default_environment`: Default environment to use when not specified

See [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) for detailed configuration flow diagrams and validation logic.

## Usage

### Basic Usage

```bash
python src_timesheetalgo/TimeSheetAlgo.py
```

The application will:
1. Load configuration from `config.yaml`
2. Prompt for start and end dates (format: DD.MM.YYYY)
3. Extract matching time entries from the CSV timelog
4. Populate the Excel timesheet with the extracted data

### Input Files

- **Timelog CSV:** Time entries exported from time tracking system
- **Timesheet Excel:** Template Excel file with VBA macros (.xlsm)

## Documentation

| Document | Description |
|----------|-------------|
| [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) | System architecture, configuration flow, and class diagrams |
| [`doc/CONTRIBUTING.md`](doc/CONTRIBUTING.md) | Contributing guidelines and naming conventions |
| [`tests/TESTING.md`](tests/TESTING.md) | Testing documentation and test structure |

## Development

### Development Workflow

Our development process follows a **Feature → Master → Release → Deployment** strategy:

```
feature/PRO-123  →  PR + Tests  →  master  →  release/vX.Y.Z  →  Deployment (v tags)
  (development)    (required)    (stable)    (release branch)     (production only)
```

**Key Points:**
1. **Feature Development:** Create feature branches from `master` with direct push allowed
2. **Quality Gate to Master:** PRs to `master` **require** full test suite to pass (Lint + Unit Tests + Code Coverage)
3. **Master is Always Stable:** Only tested, reviewed code merges to `master`
4. **Release Process:** Create `release/vX.Y.Z` branches from `master` for version releases
5. **Production Deployment:** Deploy **only** from release tags (`vX.Y.Z`), never directly from master

**Testing Requirements:**
- Feature branches: Optional linting on push
- Master PRs: ✅ **Tests required** (Lint + Unit Tests + Code Coverage)
- Release branches: Inherit tests from master (already verified)

**Deployment:**
- Development: No deployment
- Master: No deployment
- Release tags: ✅ **Production deployment only**

### Switching Between Branches

When switching between Git branches, **always reactivate the virtual environment**:

```bash
git checkout feature/PRO-123-description
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows
```

For detailed instructions on branch switching, shell aliases, and environment management, see [`doc/CONTRIBUTING.md#phase-1a-switching-between-branches--environment-management`](doc/CONTRIBUTING.md#phase-1a-switching-between-branches--environment-management).

### Running Tests

```bash
# All tests with coverage
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing

# One level (by path or marker)
python -m pytest tests/unit          # or: -m unit
python -m pytest tests/integration   # or: -m integration
python -m pytest tests/system        # or: -m system

# Fast set (no real resources) — what PR CI runs
python -m pytest -m "not system"
```

### Test Coverage

- **103 tests** across three levels (unit 79 · integration 17 · system 7; 1 `xfail`), ~99% branch+line coverage of `src_timesheetalgo` (CI gate: 90%)
- Unit: individual functions/methods in isolation
- Integration: the `TimeSheetProcessor` pipeline on an in-memory workbook
- System: black-box runs against real-file copies (skipped when data is absent)
- Boundary-value & equivalence-class rationale: [`tests/boundary_equivalence_analysis.md`](tests/boundary_equivalence_analysis.md)

See [`tests/TESTING.md`](tests/TESTING.md) for detailed testing documentation.

### Project Structure

```
TimeSheet/
├── src_timesheetalgo/       # Main application source
│   ├── TimeSheetAlgo.py     # Main application module
│   └── config.yaml          # Configuration file
├── tests/                   # Test suite (one folder per level)
│   ├── TESTING.md           # Test docs: layout, levels, fixtures, configuration
│   ├── conftest.py          # Shared fixtures
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── system/              # System tests (real resources)
├── doc/                     # Documentation and diagrams
│   ├── ARCHITECTURE.md      # Architecture documentation
│   └── CONTRIBUTING.md      # Contributing guidelines
├── sup/                     # Support files and test data
└── pyproject.toml          # Project metadata, deps, and all tool config (pytest, coverage, black, ruff)
```

See [`doc/CONTRIBUTING.md`](doc/CONTRIBUTING.md) for complete guidelines including branch naming, commit standards, pull request format, JIRA requirements, and Git workflow details.
