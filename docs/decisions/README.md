# Decision Records

Formal, numbered records for decisions that shape the product, the process, or the agent team.

| Prefix | Kind | Scope | Example |
|--------|------|-------|---------|
| ADR | Architecture Decision Record | Technical design of the application | Persistence format for timesheet data |
| PDR | Product Decision Record | Product scope and behaviour | Which Excel sheets are supported |
| TDR | Test Decision Record | Test strategy, tooling, coverage gates | Coverage threshold for `src/` |
| BDR | Business Decision Record | Ways of working, release and budget constraints | Single-maintainer release policy |
| ODR | Operational Decision Record | CI, infrastructure, automation | Dependabot handling |

## Rules

1. One decision per file. Name: `<PREFIX>-NNNN-<kebab-title>.md`, e.g. `ADR-0001-timesheet-storage.md`.
2. Numbers are sequential per prefix and never reused.
3. Start from [TEMPLATE.md](TEMPLATE.md). Status is one of `Proposed`, `Accepted`, `Superseded by <ID>`, `Rejected`.
4. Reference the JIRA ticket in the record (`Refs: PRO-XXX`).
5. A decision made during a feature is recorded before the feature's PR merges.
6. To change a decision, add a new record that supersedes the old one. Do not edit an accepted decision's outcome.

## Workflow integration

- **Architect** drafts an ADR/TDR when the implementation plan (Part A) resolves an architectural question.
- **Product Owner** drafts a PDR/BDR when a user decision changes scope or process.
- **Developer** and **Tester** draft a TDR when a test strategy choice is made.
- **complete-feature** Step 4.5 checks that decisions taken during the feature are recorded here.

## Index

| ID | Title | Status | Ticket |
|----|-------|--------|--------|
| ODR-0001 | Decision records and artifact layout for agent team governance | Accepted | PRO-407 |
