# TimeSheet Architecture

TimeSheet is a single-module Python CLI (`src_timesheetalgo/TimeSheetAlgo.py`)
that reads a CSV timelog, asks the user for a date range, writes the matching
start/end times into the correct month worksheet of an Excel `.xlsm` timesheet,
and saves it. Configuration is YAML-driven with folder-based environment
detection; there is no database or network dependency.

This document covers the system context, the runtime processing pipeline, the
data model, and the configuration subsystem.

Testing details, including the suite layout and the traceability validation workflow, are documented in [doc/TESTING.md](TESTING.md).

## Traceability Approach

The repository uses lightweight requirement identifiers in the form FR-XX and QR-XX. These IDs are used in [doc/REQUIREMENTS.md](REQUIREMENTS.md), the implementation in [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py), and the traceability entries below so that design, code, and tests remain aligned.

## Traceability Matrix

| Requirement ID | Architectural concern | Implementation reference |
| --- | --- | --- |
| FR-01 | Configuration loading | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `load_config()` and `configure_logging()` |
| FR-02 | Environment detection | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `detect_environment()` |
| FR-03 | Configuration validation | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `_read_yaml()` and `load_config()` |
| FR-04 | Input file loading | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `load_files()` and `check_file_existence()` |
| FR-05 | Input file validation | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `check_file_existence()`, `validate_timelog_entry()`, `validate_timesheet_structure()` |
| FR-06 | Timesheet consistency check | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `check_year_consistency()` |
| FR-07 | Date range determination | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `request_date_input()`, `parse_date()`, `set_default_start_date()`, `set_default_end_date()`, `calculate_default_start_date()` |
| FR-08 | Timelog filtering | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `select_timelog_data()`, `filter_timelog_entries()` |
| FR-09 | Mapping logic | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `store_data()`, `map_entry_to_cell()` |
| FR-10 | Existing data detection | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `_check_and_confirm_overwrite()` |
| FR-11 | Overwrite decision | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `_prompt_overwrite_decision()` |
| FR-12 | Data transfer | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `store_data()` (returns `StoreResult`) |
| FR-13 | Saving | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `save_timesheet()` |
| FR-14 | Error handling | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `run()` |
| FR-15 | Logging | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `configure_logging()` and `run()` |
| QR-01 | Reliability | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `check_year_consistency()` and `run()` |
| QR-02 | Data integrity | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `select_timelog_data()`, `filter_timelog_entries()` and `store_data()` |
| QR-03 | Consistency | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `check_year_consistency()` |
| QR-04 | Usability | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `request_date_input()`, `TimeSheetProcessor.for_testing()` |
| QR-05 | Robustness | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `check_file_existence()`, `parse_date()`, `validate_timelog_entry()`, `validate_timesheet_structure()` |
| QR-06 | Maintainability | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - `load_config()` and `configure_logging()` |
| QR-07 | Traceability | [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py) - this module and the traceability comments in each function |
| FR-16 | CI dependency caching | [python-ci.yml](../.github/workflows/python-ci.yml) - `actions/setup-python` `cache: pip` / `cache-dependency-path: pyproject.toml` in check, test and deploy jobs |
| FR-17 | CI reusable environment setup | [setup-python-deps/action.yml](../.github/actions/setup-python-deps/action.yml) - composite action used by check, test and deploy jobs |
| QR-08 | CI performance | [python-ci.yml](../.github/workflows/python-ci.yml) - pip download caching (keyed on `pyproject.toml`), removed `actions/setup-node`, single reusable composite action (no duplicated setup) |
| QR-09 | CI maintainability | [setup-python-deps/action.yml](../.github/actions/setup-python-deps/action.yml) - single composite action for Python setup, pip caching and dependency install (each job runs `actions/checkout` before it) |

## CI Setup Design Decision: Composite Action vs. Inlined Steps (QR-08, QR-09)

The Python environment setup (checkout → `actions/setup-python` with pip cache →
`pip install -e .[dev]`) is shared by all three CI jobs (`check`, `test`,
`deploy`). Two designs were considered:

- **Composite action** (chosen): the setup steps live once in
  [setup-python-deps/action.yml](../.github/actions/setup-python-deps/action.yml)
  and each job calls it with `uses: ./.github/actions/setup-python-deps`.
- **Inlined steps**: the same steps copied into each job.

**Decision:** use the composite action, for maintainability (QR-09) — a single
source of truth for the environment, one place to change the Python version,
cache key, or install command, and consistent setup across jobs.

**Constraint discovered:** a local (`./`) composite action cannot perform the
repository checkout itself, because it can only be resolved *after* the repo is
on the runner. Each job therefore runs `actions/checkout` before the composite
action; the action owns Python setup, pip caching and dependency install only.

**Performance validated (not assumed).** To confirm the `uses:` indirection
carries no runtime cost, a dispatch-only benchmark
([benchmark.yml](../.github/workflows/benchmark.yml)) measures warm-cache setup
time for both designs (8 runs each, identical pip cache warmed beforehand). One
run on `ubuntu-latest`, Python 3.14:

| Variant | Runs | Mean (s) | Median (s) | Std dev (s) | Min (s) | Max (s) |
| --- | --- | --- | --- | --- | --- | --- |
| composite | 8 | 9.972 | 10.013 | 1.006 | 8.491 | 11.722 |
| inline | 8 | 11.171 | 9.919 | 2.990 | 9.246 | 18.103 |

Medians are effectively identical (10.01 s vs. 9.92 s); the inline mean is
skewed upward by a single 18.1 s outlier. The mean delta (-1.2 s, -10.7 %) is
well within the largest per-variant standard deviation (2.99 s), so the two
designs are **statistically equivalent** in runtime. The composite action is
therefore adopted for its maintainability benefit at no measurable performance
cost. The benchmark is retained (manual `workflow_dispatch` only, outside the CI
pipeline) so the comparison can be re-run when the toolchain changes.

## System-Level Diagrams

### Stakeholder Diagram

```mermaid
graph TB
    subgraph "Stakeholders"
        USER["👤 End Users<br/>(Time Tracking Personnel)"]
        PM["👨‍💼 Project Manager<br/>(Dennis Hartel)"]
        DEV["👨‍💻 Developers<br/>(System Maintainers)"]
        ADMIN["🔧 System Administrator<br/>(Operations)"]
    end

    subgraph "Concerns"
        USER_CONCERNS["✓ Easy time entry<br/>✓ Accurate tracking<br/>✓ Quick report generation<br/>✓ Data integrity"]
        PM_CONCERNS["✓ Complete time records<br/>✓ Accurate billing<br/>✓ Team productivity<br/>✓ System reliability"]
        DEV_CONCERNS["✓ Clean code<br/>✓ Maintainability<br/>✓ Test coverage<br/>✓ Documentation"]
        ADMIN_CONCERNS["✓ System uptime<br/>✓ Data backup<br/>✓ Environment management<br/>✓ Configuration control"]
    end

    USER --> USER_CONCERNS
    PM --> PM_CONCERNS
    DEV --> DEV_CONCERNS
    ADMIN --> ADMIN_CONCERNS

    style USER fill:#e3f2fd
    style PM fill:#fff3e0
    style DEV fill:#f3e5f5
    style ADMIN fill:#e8f5e9
```

### System Context Diagram

```mermaid
graph TB
    subgraph "TimeSheet System"
        TS["TimeSheetAlgo System<br/>Time Tracking & Excel Export"]
    end

    subgraph "External Systems"
        JIRA["JIRA<br/>(Ticket Tracking)"]
        EXCEL["Excel / Spreadsheet<br/>(Data Output)"]
        CSV["CSV Files<br/>(Time Log Input)"]
        CONFIG["Configuration Files<br/>(YAML)"]
    end

    subgraph "Users"
        END_USER["End Users<br/>(Time Entry Personnel)"]
        DEV["Developers<br/>(Code Maintainers)"]
    end

    END_USER -->|Inputs time data| TS
    TS -->|Generates timesheet| EXCEL
    TS -->|Reads time log| CSV
    TS -->|Loads config| CONFIG
    JIRA -.->|References| TS
    TS -.->|Logs to| JIRA
    DEV -->|Maintains| TS
    DEV -->|Updates| CONFIG

    style TS fill:#e3f2fd
    style EXCEL fill:#fff3e0
    style CSV fill:#c8e6c9
    style CONFIG fill:#f3e5f5
    style JIRA fill:#ffebee
```

### Use Cases Diagram

```mermaid
graph TB
    USER["👤 User"]
    ADMIN["🔧 Administrator"]

    subgraph "TimeSheet System"
        UC1["Load Time Log<br/>(CSV File)"]
        UC2["Load Timesheet<br/>(Excel File)"]
        UC3["Select Date Range<br/>(Start/End Dates)"]
        UC4["Filter Time Data<br/>(By Date Range)"]
        UC5["Populate Timesheet<br/>(Write Data)"]
        UC6["Save Timesheet<br/>(Excel Export)"]
        UC7["Configure Environment<br/>(Dev/Prod)"]
        UC8["Manage Logging<br/>(Log Levels)"]
        UC9["Validate Configuration<br/>(YAML Structure)"]
    end

    USER -->|Initiates| UC1
    USER -->|Initiates| UC2
    USER -->|Inputs| UC3
    UC1 -.->|Enables| UC4
    UC4 -.->|Enables| UC5
    UC5 -.->|Enables| UC6
    USER -->|Triggers| UC6

    ADMIN -->|Configures| UC7
    ADMIN -->|Sets| UC8
    ADMIN -->|Validates| UC9
    UC9 -.->|Validates| UC7

    style USER fill:#e3f2fd
    style ADMIN fill:#e8f5e9
    style UC1 fill:#fff3e0
    style UC2 fill:#fff3e0
    style UC3 fill:#fff3e0
    style UC4 fill:#f3e5f5
    style UC5 fill:#f3e5f5
    style UC6 fill:#c8e6c9
    style UC7 fill:#ffebee
    style UC8 fill:#ffebee
    style UC9 fill:#ffebee
```

---

## Processing Pipeline

`main()` loads configuration and delegates to `run(config)`, which drives the
five-step pipeline on a `TimeSheetProcessor`. A failure in any step (for example
an empty selection) is logged and ends the run gracefully rather than crashing.

```mermaid
sequenceDiagram
    participant CLI as main()
    participant RUN as run(config)
    participant P as TimeSheetProcessor
    participant CSV as timelog.csv
    participant XLSM as timesheet.xlsm

    CLI->>CLI: load_config() + configure_logging()
    CLI->>RUN: run(config)
    RUN->>P: load_files()
    P->>CSV: read rows (skip header)
    P->>XLSM: load_workbook(keep_vba=True)
    RUN->>P: request_date_input()
    Note over P: prompt start/end (DD.MM.YYYY)<br/>otherwise defaults: start = last worked day,<br/>end = yesterday
    RUN->>P: select_timelog_data()
    Note over P: keep rows within (start, end);<br/>raise ValueError if none
    RUN->>P: store_data()
    Note over P: per entry → sheet[month-1],<br/>row ROW_OFFSET+day, cols E/F
    RUN->>P: save_timesheet()
    P->>XLSM: workbook.save()
```

### Overwrite Decision

When `store_data()` finds existing values in target cells it asks once how to
proceed; the answer drives a small state machine applied to every conflicting day.

```mermaid
flowchart TD
    START[store_data: any target cells already filled?]
    NONE[No conflicts → write all entries]
    PROMPT{Prompt: overwrite all / skip / abort}
    OW[overwrite_all: replace existing values]
    SK[skip_all: keep existing, skip those days]
    AB[abort: stop writing]

    START -->|none occupied| NONE
    START -->|some occupied| PROMPT
    PROMPT -->|y / empty / EOF| OW
    PROMPT -->|s| SK
    PROMPT -->|n| AB

    style NONE fill:#c8e6c9
    style OW fill:#e3f2fd
    style SK fill:#fff3e0
    style AB fill:#ffcdd2
```

---

## Data Model

### Timelog (CSV input)

A header line followed by rows of `Date,Start,End,Remark`:

- `Date` — `DD.MM.YYYY`
- `Start`, `End` — `HH:MM` (or `HH:MM:SS`)
- `Remark` — free text, **not** written to the timesheet

### Timesheet (Excel `.xlsm`)

- 12 month worksheets; worksheet **index = `date.month - 1`** (January = 0 … December = 11).
- A day's entry lives at **row = `ROW_OFFSET + day`** (`ROW_OFFSET = 4`, so day 1 → row 5, day 31 → row 35).
- **Column 5 (E)** = start time, **Column 6 (F)** = end time.
- The work year comes from configuration (and the year cell at row 3, column 2 of the first sheet).
- Loaded with `keep_vba=True` so embedded macros survive a save.

### Constants (`TimeSheetAlgo.py`)

| Constant | Value | Meaning |
|----------|-------|---------|
| `DATE_FORMAT` | `%d.%m.%Y` | date parsing/format |
| `ROW_OFFSET` | `4` | header rows above day 1 |
| `TIMESHEET_SHEETS` | `12` | month worksheets |
| `MAX_RETRIES` | `3` | date-input retry budget |

---

## Configuration Subsystem

### System Architecture Overview

```mermaid
graph TB
    subgraph "TimeSheetAlgo Application"
        TSA[TimeSheetAlgo.py]
        LCF[load_config function]
        CE[ConfigError Exception]
        CF[src_timesheetalgo/config.yaml]
    end

    subgraph "Configuration Sources"
        DEV[Development Config]
        PROD[Production Config]
        ROOT["Root Level Config: year"]
    end

    subgraph "External Dependencies"
        YAML[PyYAML Library]
        LOG[Python Logging]
        OS[os module]
    end

    TSA --> LCF
    LCF --> CF
    LCF --> YAML
    LCF --> LOG
    LCF --> OS
    LCF -.-> CE

    CF --> DEV
    CF --> PROD
    CF --> ROOT

    style TSA fill:#e1f5fe
    style LCF fill:#f3e5f5
    style CF fill:#fff3e0
    style CE fill:#ffcdd2
    style ROOT fill:#c8e6c9
```

### Configuration Loading Flow

```mermaid
sequenceDiagram
    participant TSA as TimeSheetAlgo.py
    participant LCF as load_config
    participant CF as config.yaml
    participant LOG as Logging System
    participant CE as ConfigError

    TSA->>LCF: Call load_config(config_path)
    LCF->>LCF: Determine config file path
    LCF->>LCF: Validate year exists at root level

    alt Config file not found
        LCF->>CE: Raise ConfigError
        CE-->>TSA: Configuration file not found
    else Config file exists
        LCF->>CF: Load YAML content with safe_load
        alt Invalid YAML
            LCF->>CE: Raise ConfigError
            CE-->>TSA: Invalid YAML format
        else Valid YAML
            LCF->>LCF: Validate config structure
            LCF->>LCF: Check year at root level (required)
            alt Year missing at root level
                LCF->>CE: Raise ConfigError
                CE-->>TSA: Missing required 'year' configuration
            else Year found
                LCF->>LCF: Validate environment exists
                alt Environment not found
                    LCF->>CE: Raise ConfigError
                    CE-->>TSA: Environment not found
                else Valid environment
                    LCF->>LCF: Extract file_paths
                    LCF->>LCF: Convert relative paths to absolute
                    LCF->>LOG: Configure logging from YAML
                    LCF->>LOG: Log configuration diagnostics (Work year, environment)
                    LCF-->>TSA: Return config dict with year
                end
            end
        end
    end

    Note over TSA: Year is required - no fallback to hardcoded defaults
```

### Environment Selection Logic

The environment is detected purely from the **folder structure** by
`detect_environment(base_dir)` — there is no environment parameter, and the
`default_environment` key present in `config.yaml` is **not** read by the loader.

```mermaid
flowchart TD
    START([load_config: base_dir = config.yaml directory])

    Q1{basename == 'src_timesheetalgo'?}
    DEV1[environment = development]
    Q2{'Timealarm/' subfolder exists?}
    PROD[environment = production]
    DEV2[environment = development fallback]

    VALIDATE{environment in config 'environments'?}
    LOAD_ENV[Load that environment's file_paths + logging]
    RAISE_ERROR[Raise ConfigError]

    END([Configuration Loaded])

    START --> Q1
    Q1 -->|Yes| DEV1
    Q1 -->|No| Q2
    Q2 -->|Yes| PROD
    Q2 -->|No| DEV2

    DEV1 --> VALIDATE
    PROD --> VALIDATE
    DEV2 --> VALIDATE

    VALIDATE -->|Yes| LOAD_ENV
    VALIDATE -->|No| RAISE_ERROR

    LOAD_ENV --> END

    style START fill:#e8f5e8
    style END fill:#e8f5e8
    style RAISE_ERROR fill:#ffcdd2
    style LOAD_ENV fill:#e3f2fd
    style PROD fill:#fff3e0
```

### Configuration Structure

```mermaid
graph LR
    subgraph "config.yaml Structure"
        ROOT[config.yaml]
        YEAR_ROOT["year: 2025"]

        subgraph "Environments Section"
            ENVS[environments]

            subgraph "Development"
                DEV_ENV[development]
                DEV_PATHS[file_paths]
                DEV_LOG[logging]
                DEV_TL["timelog_path: FDTech_timelog.csv"]
                DEV_TS["timesheet_path: 2025_FDTech_Dennis_Hartel.xlsm"]
                DEV_LVL["level: INFO"]
                DEV_FMT["format: asctime - levelname - message"]
            end

            subgraph "Production"
                PROD_ENV[production]
                PROD_PATHS[file_paths]
                PROD_LOG[logging]
                PROD_TL["timelog_path: Timealarm/FDTech_timelog.csv"]
                PROD_TS["timesheet_path: 2025_FDTech_Dennis_Hartel.xlsm"]
                PROD_LVL["level: WARNING"]
                PROD_FMT["format: asctime - levelname - message"]
            end
        end

        subgraph "Default Environment"
            DEFAULT["default_environment: development"]
        end
    end

    ROOT --> YEAR_ROOT
    ROOT --> ENVS
    ROOT --> DEFAULT

    ENVS --> DEV_ENV
    ENVS --> PROD_ENV

    DEV_ENV --> DEV_PATHS
    DEV_ENV --> DEV_LOG
    DEV_PATHS --> DEV_TL
    DEV_PATHS --> DEV_TS
    DEV_LOG --> DEV_LVL
    DEV_LOG --> DEV_FMT

    PROD_ENV --> PROD_PATHS
    PROD_ENV --> PROD_LOG
    PROD_PATHS --> PROD_TL
    PROD_PATHS --> PROD_TS
    PROD_LOG --> PROD_LVL
    PROD_LOG --> PROD_FMT

    style ROOT fill:#fff3e0
    style YEAR_ROOT fill:#c8e6c9
    style DEV_ENV fill:#e3f2fd
    style PROD_ENV fill:#ffebee
```

### Error Handling Flow

```mermaid
flowchart TD
    LOAD[Load Configuration]

    FILE_EXISTS{Config file exists?}
    YAML_VALID{Valid YAML?}
    YEAR_VALID{Year at root level?}
    ENV_VALID{Valid environment?}
    PATHS_VALID{Valid file_paths?}

    SUCCESS[Configuration Loaded Successfully]

    ERR_MISSING[Raise ConfigError: File not found]
    ERR_YAML[Raise ConfigError: Invalid YAML]
    ERR_YEAR[Raise ConfigError: Missing year at root]
    ERR_ENV[Raise ConfigError: Environment not found]
    ERR_PATHS[Raise ConfigError: Missing file_paths]

    LOAD --> FILE_EXISTS

    FILE_EXISTS -->|No| ERR_MISSING
    FILE_EXISTS -->|Yes| YAML_VALID

    YAML_VALID -->|No| ERR_YAML
    YAML_VALID -->|Yes| YEAR_VALID

    YEAR_VALID -->|No| ERR_YEAR
    YEAR_VALID -->|Yes| ENV_VALID

    ENV_VALID -->|No| ERR_ENV
    ENV_VALID -->|Yes| PATHS_VALID

    PATHS_VALID -->|No| ERR_PATHS
    PATHS_VALID -->|Yes| SUCCESS

    style SUCCESS fill:#e8f5e8
    style ERR_MISSING fill:#ffcdd2
    style ERR_YAML fill:#ffcdd2
    style ERR_YEAR fill:#ffcdd2
    style ERR_ENV fill:#ffcdd2
    style ERR_PATHS fill:#ffcdd2
```

### Class Relationship Diagram

```mermaid
classDiagram
    class ConfigError {
        <<Exception>>
        Custom exception for configuration errors
    }

    class TimeSheetAlgoModule {
        +DATE_FORMAT: str
        +MAX_RETRIES: int
        +ROW_OFFSET: int
        +TIMESHEET_SHEETS: int
        +load_config(config_path): Dict[str, Any]
        +parse_date(input_prompt, retries): datetime
        +check_file_existence(filepath, filetype): Any
        +run(config): None
        +main(): None
    }

    class TimeSheetProcessor {
        -timelog_path: str
        -timesheet_path: str
        -year: int
        -timelog: List
        -timedata: List
        -timesheet: Workbook
        -obj_date_startpoint: datetime
        -obj_date_endpoint: datetime

        +__init__(config: Dict[str, Any])
        +load_files(): None
        +request_date_input(): None
        +select_timelog_data(): None
        +store_data(): None
        +save_timesheet(): None
        +confirm_overwrite(): bool
        +set_default_start_date(): datetime
        +set_default_end_date(): datetime
        -_get_date(prompt, fallback): datetime
        -_check_and_confirm_overwrite(): str
        -_prompt_overwrite_decision(count): str
    }

    class PyYAML {
        <<External Library>>
        +safe_load(stream): Any
    }

    class PythonLogging {
        <<Standard Library>>
        +basicConfig()
        +warning()
        +info()
        +error()
    }

    class OSModule {
        <<Standard Library>>
        +path.dirname()
        +path.abspath()
        +path.join()
        +path.exists()
        +path.isabs()
    }

    TimeSheetAlgoModule --> ConfigError : raises
    TimeSheetAlgoModule --> TimeSheetProcessor : creates
    TimeSheetAlgoModule --> PyYAML : uses
    TimeSheetAlgoModule --> PythonLogging : configures
    TimeSheetAlgoModule --> OSModule : uses

    note for TimeSheetAlgoModule "Year required from config.yaml (no fallback)\nEnvironment auto-detected by folder (detect_environment)\nrun()/main() orchestrate the pipeline"
    note for TimeSheetProcessor "Year stored as instance attribute\nUsed for default date calculations"
```

### Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment (folder: src_timesheetalgo)"
        DEV_SCRIPT[TimeSheetAlgo.py]
        DEV_CONFIG[config.yaml]
        DEV_DATA[FDTech_timelog.csv<br/>2025_FDTech_Dennis_Hartel.xlsm]
        DEV_LOGS[Console Output - INFO level]
    end

    subgraph "Production Environment (folder contains Timealarm/)"
        PROD_SCRIPT[TimeSheetAlgo.py]
        PROD_CONFIG[config.yaml]
        PROD_DATA[Timealarm/FDTech_timelog.csv<br/>2025_FDTech_Dennis_Hartel.xlsm]
        PROD_LOGS[Console Output - WARNING level]
    end

    DEV_SCRIPT --> DEV_CONFIG
    DEV_CONFIG --> DEV_DATA
    DEV_SCRIPT --> DEV_LOGS

    PROD_SCRIPT --> PROD_CONFIG
    PROD_CONFIG --> PROD_DATA
    PROD_SCRIPT --> PROD_LOGS

    style DEV_SCRIPT fill:#e3f2fd
    style PROD_SCRIPT fill:#ffebee
```

> The end-to-end validation order is shown in **Error Handling Flow** above
> (file → YAML → year → environment → file_paths). There is **no** fallback to
> hardcoded defaults: any `ConfigError` propagates to `main()`, which logs it and
> exits with status 1.

---
