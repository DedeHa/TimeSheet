# YAML Configuration System Architecture Diagrams

## System Architecture Overview

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
        ROOT[Root Level Config (year)]
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

## Configuration Loading Flow

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

## Environment Selection Logic

```mermaid
flowchart TD
    START([Start Configuration Loading])
    
    CHECK_PARAM{Environment parameter provided?}
    USE_PARAM[Use provided environment]
    
    CHECK_DEFAULT{default_environment in config?}
    USE_DEFAULT[Use default_environment from config]
    USE_DEV[Use 'development' as fallback]
    
    VALIDATE{Environment exists in config?}
    LOAD_ENV[Load environment configuration]
    RAISE_ERROR[Raise ConfigError]
    
    END([Configuration Loaded])
    
    START --> CHECK_PARAM
    
    CHECK_PARAM -->|Yes| USE_PARAM
    CHECK_PARAM -->|No| CHECK_DEFAULT
    
    CHECK_DEFAULT -->|Yes| USE_DEFAULT
    CHECK_DEFAULT -->|No| USE_DEV
    
    USE_PARAM --> VALIDATE
    USE_DEFAULT --> VALIDATE
    USE_DEV --> VALIDATE
    
    VALIDATE -->|Yes| LOAD_ENV
    VALIDATE -->|No| RAISE_ERROR
    
    LOAD_ENV --> END
    
    style START fill:#e8f5e8
    style END fill:#e8f5e8
    style RAISE_ERROR fill:#ffcdd2
    style LOAD_ENV fill:#e3f2fd
    style USE_DEFAULT fill:#fff3e0
```

## Configuration Structure

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

## Error Handling Flow

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

## Class Relationship Diagram

```mermaid
classDiagram
    class ConfigError {
        <<Exception>>
        Custom exception for configuration errors
    }

    class TimeSheetAlgoModule {
        +CONFIG: Dict[str, Any]
        +DATE_FORMAT: str
        +MAX_RETRIES: int
        +ROW_OFFSET: int
        +TIMESHEET_SHEETS: int
        +load_config(config_path): Dict[str, Any]
        +parse_date(input_prompt, retries): datetime
        +check_file_existence(filepath, filetype): Any
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

    note for TimeSheetAlgoModule "Year loaded from config.yaml\nEnvironment auto-detected\nNo hardcoded fallbacks"
    note for TimeSheetProcessor "Year stored as instance attribute\nUsed for default date calculations"
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment (default_environment: development)"
        DEV_SCRIPT[TimeSheetAlgo.py]
        DEV_CONFIG[config.yaml]
        DEV_DATA[fdtech_timelog.csv<br/>2025_FDTech_Dennis_Hartel.xlsm]
        DEV_LOGS[Console Output - INFO level]
    end
    
    subgraph "Production Environment (set via parameter or config)"
        PROD_SCRIPT[TimeSheetAlgo.py]
        PROD_CONFIG[config.yaml]
        PROD_DATA[Timealarm/fdtech_timelog.csv<br/>2025_FDTech_Dennis_Hartel.xlsm]
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

## Configuration Validation Process

```mermaid
stateDiagram-v2
    [*] --> LoadingConfig
    
    LoadingConfig --> FileCheck
    FileCheck --> FileExists : file found
    FileCheck --> RaiseConfigError : file not found
    
    FileExists --> YAMLParsing
    YAMLParsing --> ValidYAML : parsing successful
    YAMLParsing --> RaiseConfigError : parsing failed
    
    ValidYAML --> StructureValidation
    StructureValidation --> ValidStructure : has 'environments' key
    StructureValidation --> RaiseConfigError : missing required keys
    
    ValidStructure --> EnvironmentSelection
    EnvironmentSelection --> ValidEnvironment : environment found
    EnvironmentSelection --> RaiseConfigError : environment not found
    
    ValidEnvironment --> PathValidation
    PathValidation --> ValidPaths : has required paths
    PathValidation --> RaiseConfigError : missing paths
    
    ValidPaths --> PathConversion
    PathConversion --> ConfigurationReady
    
    RaiseConfigError --> CatchException
    CatchException --> FallbackDefaults
    FallbackDefaults --> ConfigurationReady
    
    ConfigurationReady --> [*]
    
    note right of ConfigurationReady : Configuration loaded successfully\nLogging configured from YAML\nFile paths converted to absolute\nDiagnostics logged at WARNING level
    
    note right of FallbackDefaults : Using hardcoded defaults\nError logged\nGraceful degradation