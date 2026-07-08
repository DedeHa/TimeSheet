# REQUIREMENTS.md

# Top-Level System Requirements (SOPHISTEN Style)

## Traceability Approach

The project uses a lightweight identifier scheme so that requirements, architecture notes, and source modules can be cross-referenced without introducing heavy tooling. Requirement IDs follow the pattern FR-XX for functional requirements and QR-XX for quality requirements. When implementation work addresses a requirement, the relevant source module shall include the matching requirement ID in its documentation comment and the architecture documentation shall reference the implementation module.

A future change shall update the requirement identifier, the architecture traceability matrix, and the relevant implementation references in the same change.

---

## 1. Goal

The system shall automate the transfer of working time entries from an exported timelog (CSV) into an Excel-based yearly timesheet while ensuring consistency, minimizing manual effort, and preventing unintended data corruption.

---

# 2. Stakeholders

| Stakeholder  | Interest                                                       |
| ------------ | -------------------------------------------------------------- |
| Employee     | Maintain an accurate yearly timesheet with minimal manual work |
| User         | Execute the import process reliably                            |
| Maintainer   | Configure and maintain the application                         |
| Organization | Ensure complete and correct work time documentation            |

---

# 3. System Context

### Inputs

* Configuration file (`config.yaml`)
* Timelog export (`CSV`)
* Excel timesheet (`.xlsm`)
* User input for optional date range
* User overwrite decision

### Outputs

* Updated Excel timesheet
* Log messages
* Error messages

---

# 4. Top-Level Functional Requirements

## FR-01 Configuration Loading

**Requirement**

The system shall load its configuration from a YAML configuration file.

**Rationale**

Configuration shall be separated from the implementation.

---

## FR-02 Environment Detection

**Requirement**

The system shall automatically determine the execution environment and select the corresponding file paths.

---

## FR-03 Configuration Validation

**Requirement**

The system shall validate the configuration before processing begins.

The validation shall include at least:

* required configuration entries
* valid configuration structure
* readable configuration file

If validation fails, the system shall terminate before processing any data.

---

## FR-04 Input File Loading

**Requirement**

The system shall load

* one CSV timelog
* one Excel timesheet workbook

before processing begins.

---

## FR-05 Input File Validation

**Requirement**

Before processing, the system shall verify that all required input files exist and can be accessed.

If an input file cannot be accessed, the processing shall be aborted.

---

## FR-06 Timesheet Consistency Check

**Requirement**

The system shall verify that the configured work year matches the year stored in the Excel timesheet.

If the years differ, no modifications shall be performed.

---

## FR-07 Date Range Determination

**Requirement**

The system shall determine a processing date range.

The date range may be provided by the user.

If no valid user input exists, the system shall automatically determine suitable default dates.

---

## FR-08 Timelog Filtering

**Requirement**

The system shall import only timelog entries whose dates lie inside the selected processing interval.

---

## FR-09 Mapping of Timelog Entries

**Requirement**

The system shall map every selected timelog entry to the corresponding worksheet, row and columns of the yearly timesheet.

---

## FR-10 Existing Data Detection

**Requirement**

Before writing data, the system shall detect existing entries that would be overwritten.

---

## FR-11 Overwrite Decision

**Requirement**

If existing entries are detected, the system shall allow the user to choose between

* overwrite all entries
* skip existing entries
* abort processing

The selected decision shall be applied consistently to all affected entries.

---

## FR-12 Data Transfer

**Requirement**

The system shall write the selected start and end times into the corresponding cells of the Excel workbook.

---

## FR-13 Saving

**Requirement**

After successful processing, the system shall save the modified workbook.

---

## FR-14 Error Handling

**Requirement**

If processing errors occur, the system shall terminate gracefully without producing inconsistent output.

---

## FR-15 Logging

**Requirement**

The system shall record relevant processing information, warnings and errors using configurable logging.

---

# 5. Top-Level Quality Requirements

## QR-01 Reliability

The system shall prevent accidental modification of an incorrect yearly timesheet.

---

## QR-02 Data Integrity

The system shall never write data outside the identified date range.

---

## QR-03 Consistency

The system shall only modify the workbook if configuration and workbook year are consistent.

---

## QR-04 Usability

The system shall require only minimal user interaction during normal execution.

---

## QR-05 Robustness

The system shall detect invalid configuration files, invalid dates, inaccessible files and inconsistent workbooks before modifying data.

---

## QR-06 Maintainability

Configuration data shall be separated from program code.

---

## QR-07 Traceability

All important processing steps and detected errors shall be logged.

---

# 6. Business Rules

**BR-01**

Exactly one work year is processed during one execution.

**BR-02**

Only dates belonging to the configured work year are considered valid.

**BR-03**

The first twelve worksheets represent the months January through December.

**BR-04**

Each calendar day corresponds to exactly one worksheet row.

**BR-05**

Each imported timelog entry contains

* work date
* start time
* end time

---

# 7. Assumptions

* The CSV export follows the expected column structure.
* The Excel workbook follows the predefined template.
* The workbook contains one worksheet for each month.
* Users possess write permission for the workbook.
* Excel formulas and VBA macros remain unchanged by the import.

---

# 8. Constraints

* The implementation shall operate on Microsoft Excel workbooks (`.xlsm`).
* The implementation shall preserve existing VBA macros.
* Configuration shall be provided in YAML format.
* Timelog input shall be provided as CSV.
* Processing shall be performed locally without external services.

---

# 9. Success Criteria

The system is considered successful if

1. the configuration is loaded successfully,
2. the workbook passes the consistency check,
3. the desired date range is processed,
4. all matching timelog entries are transferred correctly,
5. no unintended workbook entries are modified,
6. the workbook is saved successfully,
7. all relevant actions and errors are logged.
