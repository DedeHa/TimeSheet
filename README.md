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
- [Naming Conventions](#naming-conventions)

## Description

TimeSheetAlgo automates the manual process of:
- Extracting time data from CSV timelogs
- Processing and validating time entries
- Populating Excel timesheet templates
- Creating AZE (Arbeitszeiterfassung) documentation

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
| [`tests/TESTING.md`](tests/TESTING.md) | Testing documentation, test structure, and verification reports |
| [`sup/naming_conventions.md`](sup/naming_conventions.md) | Contributing guidelines and naming conventions |

### Architecture Diagrams

The [`doc/`](doc/) directory contains:
- System architecture overview (Mermaid diagrams)
- Analysis diagrams (BDD, IBD, Use Cases)
- Activity diagrams for detailed workflows
- Configuration loading flow diagrams

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

### Running Tests

```bash
# All tests with coverage
python -m pytest tests/ -v --cov=src_timesheetalgo --cov-report=term-missing

# Unit tests only
python -m pytest tests/test_unittest_timesheetalgo.py -v

# System verification tests
python tests/test_systemverification_timesheetalgo.py
```

### Test Coverage

- **51 tests** with **97% code coverage**
- Unit tests for all functions and classes
- System verification tests with real data

See [`tests/TESTING.md`](tests/TESTING.md) for detailed testing documentation.

### Project Structure

```
TimeSheet/
├── src_timesheetalgo/       # Main application source
│   ├── TimeSheetAlgo.py     # Main application module
│   └── config.yaml          # Configuration file
├── src_azesheetalgo/        # AZE sheet module (future)
├── tests/                   # Test suite
│   ├── TESTING.md           # Testing documentation
│   └── verification_report_*.md  # Test verification reports
├── doc/                     # Documentation and diagrams
├── sup/                     # Support files and test data
├── pyproject.toml          # Project metadata & dependencies (PEP 621) - replaces requirements.txt
└── pytest.ini               # Pytest configuration
```

## Naming Conventions

Quick reference for contributing to this project:

### Branch Naming
| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/PRO-123-description` | `feature/PRO-123-login-api` |
| Bugfix | `bugfix/PRO-123-description` | `bugfix/PRO-123-scan-timeout` |
| Hotfix | `hotfix/PRO-123-description` | `hotfix/PRO-123-security-patch` |
| Refactor | `refactor/PRO-123-description` | `refactor/PRO-296-codebase` |
| Docs | `docs/PRO-123-description` | `docs/PRO-123-api-guide` |
| Release | `release/vX.Y.Z` | `release/v4.1.2` |

### Commit Format (Conventional Commits)
```
type(scope): description

Optional body explaining changes in more detail.

Refs: PRO-123
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `ci`, `build`

### Pull Request Format
- **Title:** `[Type][PRO-123] Clear description of changes`
- **Example:** `[feat][PRO-123] Add dashboard UI with user authentication`

### Release Versioning (Semantic Versioning)
- **Format:** `vX.Y.Z` (X=MAJOR, Y=MINOR, Z=PATCH)
- **Examples:** `v1.2.3`, `v2.0.0`, `v4.1.2`

### Branch Protection Policy
- **Protected (require PR + review):** `master`, `release/*`
- **Open (direct push allowed):** `feature/*`, `bugfix/*`, `hotfix/*`, `refactor/*`, `docs/*`, `test/*`

---

For complete guidelines including JIRA requirements, Git compatibility rules, and detailed workflow steps, see [`sup/naming_conventions.md`](sup/naming_conventions.md).
