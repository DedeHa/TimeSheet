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

## FR-INTEGRITY-001 Pre-Closure Validation

**Requirement**

The complete-feature workflow shall validate all critical post-implementation conditions before transitioning a JIRA ticket to "Fertig" (Done). The validation shall include:

* PR merge status verification using `gh pr view`
* Implementation plan document deletion
* Working tree cleanliness (no uncommitted changes)
* Remote branch deletion
* No unverified PR merge claims in JIRA comments

**Rationale**

Premature JIRA closure corrupts the audit trail and misleads stakeholders about actual delivery state. Automated validation prevents the integrity failure discovered in PRO-380.

**Acceptance Criteria**

* [x] The complete-feature workflow calls `gh pr view` to verify the PR is actually merged before transitioning JIRA to Fertig
* [x] If the PR is NOT merged, the workflow blocks the transition and reports: "PR #XXX is not merged. Current state: OPEN/CLOSED. Cannot transition to Fertig."
* [x] The workflow does NOT post a comment claiming PR merge unless `gh pr view` confirms the merge
* [x] The workflow verifies that the implementation plan document (`doc/02_Implementation_Plan_PRO-XXX.md`) has been deleted before closure
* [x] The workflow verifies there are no uncommitted changes in the working tree before closure
* [x] The workflow verifies the remote branch has been deleted (or reports it as a remaining action for the user/PO)
* [x] If any check fails, the workflow reports the specific failing check and halts — not transition the ticket
* [x] A pre-closure validation checklist is added to the complete-feature skill, executed automatically before any JIRA transition

**Location**

`.opencode/skills/complete-feature/SKILL.md` (pre-closure validation phase), `.github/scripts/validate_pr_merge.py`, `.github/scripts/validate_filesystem.py`

**Related**

PRO-380 (bug where premature closure was discovered), PRO-383 (fix ticket)

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

## QR-INTEGRITY-002 Pipeline Integrity Validation

**Requirement**

The agent-team pipeline shall provide automated validation of pipeline integrity to prevent premature JIRA closure, with all validation logic covered by a test suite (unit, integration and system tests) that runs as CI self-tests.

**Rationale**

The integrity failure in PRO-380 could not be caught automatically because no tests existed for the complete-feature closure workflow. A dedicated test suite makes validation failures observable in CI before any JIRA transition is permitted.

**Acceptance Criteria**

* [ ] Unit tests cover all validation scenarios (PR merged / not merged / fetch failure, plan deletion, working tree clean / dirty, remote branch present / absent)
* [ ] Integration tests validate the end-to-end validation sequence with mocked PR states
* [ ] System tests verify real-world scenarios against the actual repository state
* [ ] Validation failures are reported with specific error messages identifying the failing check

**Location**

`tests/ci-pipeline/test_complete_feature_validation.py`, `doc/REQUIREMENTS.md`

**Related**

PRO-380 (bug where premature closure was discovered), PRO-383 (fix ticket)

---

## FR-16 CI Dependency Caching

The CI pipeline shall cache pip downloads, keyed on `pyproject.toml`, so that unchanged dependencies are restored from cache instead of re-downloaded; the cache is invalidated automatically when `pyproject.toml` changes.

## FR-17 CI Reusable Environment Setup

The CI pipeline shall use a single reusable composite action for repository checkout, Python setup, and dependency installation across all jobs.

## FR-18 GitHub Release Signing

The CI pipeline shall configure GPG signing so that all release commits and tags are signed with GitHub's verified signature, displaying "This commit was created on GitHub.com and signed with GitHub's verified signature".

---

## QR-08 CI Performance

The CI pipeline shall avoid redundant work by caching pip downloads, centralising environment setup in one action, and removing unnecessary runtime setup (no unconditional Node.js installation).

## QR-09 CI Maintainability

The CI pipeline shall centralise common setup logic in a single reusable action so that environment changes require a single point of modification.

## QR-10 GitHub Signing Verification

The CI pipeline shall verify that release tags are signed with the configured GPG program (gh-gpgsign) and that signing capability is validated before deployment.

## QR-11 CI GPG Action Maintainability

The CI pipeline shall isolate GPG signing setup in a dedicated reusable composite action so that signing configuration changes require a single point of modification, consistent with the pattern established by FR-17 and QR-09.

## FR-19 CI Timing Statistical Enhancement

The CI timing pipeline shall compute and include rolling window statistics (rolling mean and sample stddev over a configurable window, default 20 runs), Bollinger bands (mean ± k·stddev, default k=2), and normal distribution parameters (μ, σ) per `(job, step)` bucket in `data/ci_metrics.json`. All statistical computations shall use only the Python standard library (`statistics.stdev` for sample stddev).

## QR-12 CI Timing Traceability

The CI timing pipeline shall validate that every `ready` entry in `data/ci_metrics.json` includes the new statistical keys (`rolling`, `bollinger`, `distribution`) via the schema validator, and shall regenerate metrics from the full dataset on every update to ensure idempotent, drift-free output.

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
