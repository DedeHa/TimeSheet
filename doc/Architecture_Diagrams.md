# YAML Configuration System Architecture Diagrams

## System Architecture Overview

```mermaid
graph TB
    subgraph "TimeSheetAlgo Application"
        TSA[TimeSheetAlgo.py]
        LCF[load_config function]
        CF[src_timesheetalgo/config.yaml]
    end
    
    subgraph "Environment Detection"
        ED[determine_environment function]
        FD[Folder Detection]
        CWD[Current Working Directory]
    end
    
    subgraph "Configuration Sources"
        DEV[Development Config]
        PROD[Production Config]
        DEFAULT[Hardcoded Defaults]
    end
    
    subgraph "External Dependencies"
        YAML[PyYAML Library]
        LOG[Python Logging]
        PATH[pathlib.Path]
        OS[os module]
    end
    
    TSA --> LCF
    LCF --> CF
    LCF --> ED
    LCF --> YAML
    LCF --> LOG
    
    ED --> FD
    FD --> CWD
    
    CF --> DEV
    CF --> PROD
    
    LCF -.-> DEFAULT
    LCF --> PATH
    LCF --> OS
    
    style TSA fill:#e1f5fe
    style LCF fill:#f3e5f5
    style CF fill:#fff3e0
    style DEFAULT fill:#ffebee
```

## Configuration Loading Flow

```mermaid
sequenceDiagram
    participant TSA as TimeSheetAlgo.py
    participant LCF as load_config
    participant CF as config.yaml
    participant LOG as Logging System
    participant ED as determine_environment
    
    TSA->>LCF: Call load_config
    LCF->>LCF: Set default configuration
    LCF->>LOG: Configure basic logging (force=True)
    LCF->>LCF: Get script directory path
    
    alt Config file exists
        LCF->>CF: Load YAML content
        CF-->>LCF: Return config data
        LCF->>ED: Call determine_environment
        ED->>ED: Check current directory name
        ED-->>LCF: Return environment (development/production)
        LCF->>LOG: Log detected environment
        LCF->>LOG: Reconfigure logging from YAML (force=True)
        LCF-->>TSA: Return file paths dict
    else Config file missing or error
        LCF->>LOG: Log warning about fallback
        LCF-->>TSA: Return default config
    end
```

## Environment Detection Logic

```mermaid
flowchart TD
    START([Start Environment Detection])
    
    GET_CWD[Get current working directory]
    GET_NAME[Extract directory name]
    
    CHECK_SRC{Directory name == 'src_timesheetalgo'?}
    SET_DEV[Set environment: development]
    
    CHECK_ZEITEN{Directory name == '01_Zeiten'?}
    SET_PROD[Set environment: production]
    
    CHECK_SCRIPT[Check script directory]
    SCRIPT_SRC{Script in 'src_timesheetalgo'?}
    FALLBACK_DEV[Fallback: development]
    
    END([Environment Determined])
    
    START --> GET_CWD
    GET_CWD --> GET_NAME
    GET_NAME --> CHECK_SRC
    
    CHECK_SRC -->|Yes| SET_DEV
    CHECK_SRC -->|No| CHECK_ZEITEN
    
    CHECK_ZEITEN -->|Yes| SET_PROD
    CHECK_ZEITEN -->|No| CHECK_SCRIPT
    
    CHECK_SCRIPT --> SCRIPT_SRC
    SCRIPT_SRC -->|Yes| SET_DEV
    SCRIPT_SRC -->|No| FALLBACK_DEV
    
    SET_DEV --> END
    SET_PROD --> END
    FALLBACK_DEV --> END
    
    style START fill:#e8f5e8
    style END fill:#e8f5e8
    style SET_PROD fill:#ffebee
    style SET_DEV fill:#e3f2fd
    style FALLBACK_DEV fill:#fff3e0
```

## Configuration Structure

```mermaid
graph LR
    subgraph "config.yaml Structure"
        ROOT[config.yaml]
        
        subgraph "Default Environment"
            DEFAULT[default_environment: development]
        end
        
        subgraph "Environments Section"
            ENVS[environments]
            
            subgraph "Development"
                DEV_ENV[development]
                DEV_PATHS[file_paths]
                DEV_LOG[logging]
                DEV_TL[timelog_path: FDTech_timelog.csv]
                DEV_TS[timesheet_path: 2025_FDTech_Dennis_Hartel.xlsm]
                DEV_LVL[level: INFO]
                DEV_FMT[format: %(asctime)s - %(levelname)s - %(message)s]
            end
            
            subgraph "Production"
                PROD_ENV[production]
                PROD_PATHS[file_paths]
                PROD_LOG[logging]
                PROD_TL[timelog_path: /data/timelog/FDTech_timelog.csv]
                PROD_TS[timesheet_path: /data/timesheet/2025_FDTech_Dennis_Hartel.xlsm]
                PROD_LVL[level: WARNING]
                PROD_FMT[format: %(asctime)s - %(levelname)s - %(message)s]
            end
        end
    end
    
    ROOT --> DEFAULT
    ROOT --> ENVS
    
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
    style DEV_ENV fill:#e3f2fd
    style PROD_ENV fill:#ffebee
```

## Error Handling Flow

```mermaid
flowchart TD
    LOAD[Load Configuration]
    
    FILE_EXISTS{Config file exists?}
    YAML_VALID{Valid YAML?}
    ENV_VALID{Valid environment?}
    
    SUCCESS[Configuration Loaded Successfully]
    
    WARN_MISSING[Log warning: Config file missing]
    WARN_YAML[Log warning: YAML parsing failed]
    WARN_ENV[Log warning: Environment not found]
    
    FALLBACK[Use hardcoded defaults]
    SETUP_BASIC_LOG[Setup basic logging]
    
    LOAD --> FILE_EXISTS
    
    FILE_EXISTS -->|No| WARN_MISSING
    FILE_EXISTS -->|Yes| YAML_VALID
    
    YAML_VALID -->|No| WARN_YAML
    YAML_VALID -->|Yes| ENV_VALID
    
    ENV_VALID -->|No| WARN_ENV
    ENV_VALID -->|Yes| SUCCESS
    
    WARN_MISSING --> FALLBACK
    WARN_YAML --> FALLBACK
    WARN_ENV --> FALLBACK
    FALLBACK --> SETUP_BASIC_LOG
    SETUP_BASIC_LOG --> SUCCESS
    
    style SUCCESS fill:#e8f5e8
    style FALLBACK fill:#fff3e0
    style WARN_MISSING fill:#fff9c4
    style WARN_YAML fill:#fff9c4
    style WARN_ENV fill:#fff9c4
```

## Class Relationship Diagram

```mermaid
classDiagram
    class TimeSheetAlgo {
        +CONFIG: Dict[str, str]
        +DATE_FORMAT: str
        +MAX_RETRIES: int
        +ROW_OFFSET: int
        +TIMESHEET_SHEETS: int
        +YEAR: int
        +load_config(): Dict[str, str]
        +determine_environment(): str
        +main()
    }
    
    class TimeSheetProcessor {
        -timelog_path: str
        -timesheet_path: str
        -timelog: List
        -timedata: List
        -timesheet: Workbook
        -obj_date_startpoint: datetime
        -obj_date_endpoint: datetime
        
        +__init__(config: Dict[str, str])
        +load_files(): None
        +request_date_input(): None
        +select_timelog_data(): None
        +store_data(): None
        +save_timesheet(): None
        +confirm_overwrite(): bool
        +set_default_start_date(): datetime
        +set_default_end_date(): datetime
    }
    
    class PyYAML {
        <<External Library>>
        +safe_load(stream): Any
    }
    
    class PythonLogging {
        <<Standard Library>>
        +basicConfig()
        +getLogger()
    }
    
    class PathLib {
        <<Standard Library>>
        +Path.cwd()
        +Path(__file__).parent
    }
    
    class OSModule {
        <<Standard Library>>
        +getenv()
    }
    
    TimeSheetAlgo --> TimeSheetProcessor : creates
    TimeSheetAlgo --> PyYAML : uses
    TimeSheetAlgo --> PythonLogging : configures
    TimeSheetAlgo --> PathLib : uses
    TimeSheetAlgo --> OSModule : uses
    
    note for TimeSheetAlgo "Minimal YAML configuration\nFolder-based environment detection\nConstants remain in script"
    note for TimeSheetProcessor "Handles timesheet processing\nUnchanged from original"
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment (src_timesheetalgo folder)"
        DEV_SCRIPT[TimeSheetAlgo.py]
        DEV_CONFIG[config.yaml]
        DEV_DATA[FDTech_timelog.csv<br/>2025_FDTech_Dennis_Hartel.xlsm]
        DEV_LOGS[Console Output - INFO level]
    end
    
    subgraph "Production Environment (01_Zeiten folder)"
        PROD_SCRIPT[TimeSheetAlgo.py]
        PROD_CONFIG[config.yaml]
        PROD_DATA[/data/timelog/FDTech_timelog.csv<br/>/data/timesheet/2025_FDTech_Dennis_Hartel.xlsm]
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
    
    note for DEV_SCRIPT "Folder-based detection:<br/>src_timesheetalgo → development"
    note for PROD_SCRIPT "Folder-based detection:<br/>01_Zeiten → production"
```

## Configuration Validation Process

```mermaid
stateDiagram-v2
    [*] --> LoadingConfig
    
    LoadingConfig --> FileCheck
    FileCheck --> FileExists : file found
    FileCheck --> MissingFile : file not found
    
    FileExists --> YAMLParsing
    YAMLParsing --> ValidYAML : parsing successful
    YAMLParsing --> InvalidYAML : parsing failed
    
    ValidYAML --> EnvironmentDetection
    EnvironmentDetection --> ValidEnvironment : environment found
    EnvironmentDetection --> InvalidEnvironment : environment not found
    
    ValidEnvironment --> ConfigurationReady
    
    MissingFile --> FallbackDefaults
    InvalidYAML --> FallbackDefaults
    InvalidEnvironment --> FallbackDefaults
    
    FallbackDefaults --> ConfigurationReady
    ConfigurationReady --> [*]
    
    note right of ConfigurationReady : Configuration loaded successfully\nLogging configured\nFile paths available\nEnvironment detected from folder
    
    note right of FallbackDefaults : Using hardcoded defaults\nBasic logging setup\nWarning logged\nGraceful degradation