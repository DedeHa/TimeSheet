---
name: Feature Request
description: Create a new feature story ticket for the TimeSheetAlgo project
title: "[feat][PRO-XXX] "
labels: ["feature"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        ## Feature Story
        Use this template to create a new feature story ticket. All fields are required unless marked optional.
  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: Concise, action-oriented title following `[Verb] [Target] [Context]` pattern
      placeholder: "Implement continuous CI timing measurement and historical aggregation"
    validations:
      required: true
  - type: textarea
    id: story-block
    attributes:
      label: Story Block
      description: User story in `**As a** / **I want** / **so that**` format
      placeholder: |
        **As a** development team,
        **I want** to measure CI pipeline timing,
        **so that** we can optimize workflow performance.
    validations:
      required: true
  - type: textarea
    id: background
    attributes:
      label: Background
      description: Why does this work need to happen now? Reference prior tickets with PRO-XXX.
      placeholder: "PRO-368 introduced CI timing benchmarks. This ticket extends that work to include historical aggregation."
    validations:
      required: false
  - type: textarea
    id: goal
    attributes:
      label: Goal / Business Value
      description: What does success look like? Quantifiable outcomes if possible.
      placeholder: "Reduce CI pipeline runtime by 15% based on timing data analysis."
    validations:
      required: false
  - type: textarea
    id: scope
    attributes:
      label: Scope
      description: What is included and explicitly NOT included
      placeholder: |
        ### In Scope
        - Historical aggregation of CI timing data
        - Report generation

        ### Out of Scope
        - CI pipeline execution changes
        - Notification system updates
    validations:
      required: false
  - type: textarea
    id: implementation-plan
    attributes:
      label: Implementation Plan
      description: High-level approach or phases with key files to be changed
      placeholder: |
        1. Update `.github/workflows/ci-timing.yml` for historical data collection
        2. Add `ci_timing_aggregator.py` in `.github/scripts/`
        3. Update `docs/ARCHITECTURE.md` with new component
        4. Add unit tests in `tests/unit/`
    validations:
      required: false
  - type: textarea
    id: acceptance-criteria
    attributes:
      label: Acceptance Criteria
      description: Numbered, testable acceptance criteria
      placeholder: |
        - [ ] AC-1: Historical CI timing data is collected for every successful PR run
        - [ ] AC-2: Aggregation script renders stats and CI_TIMING_REPORT.md
        - [ ] AC-3: All existing tests continue to pass
        - [ ] AC-4: Code coverage remains ≥ 90%
    validations:
      required: true
  - type: textarea
    id: definition-of-done
    attributes:
      label: Definition of Done
      description: Checklist of criteria that must be met before closing
      placeholder: |
        - [ ] PR #NNN merged to master
        - [ ] JIRA ticket closed (Fertig)
        - [ ] All ACs checkmarked
        - [ ] Story Points: N assigned
        - [ ] Traceability: FR-XX, QR-XX added to docs/REQUIREMENTS.md
        - [ ] CI self-tests pass
    validations:
      required: true
  - type: textarea
    id: references
    attributes:
      label: References
      description: Related tickets and documentation links
      placeholder: |
        * [PRO-259](https://mainhatten.atlassian.net/browse/PRO-259): Setup Timesheet Testing
        * Refs: PRO-368, PRO-369
    validations:
      required: false
  - type: textarea
    id: story-points
    attributes:
      label: Story Points
      description: Fibonacci scale: 1, 2, 3, 5, 8, 13. Fill in when closing the ticket.
      placeholder: "5 — Moderate feature, multi-file, integration tests (see PRO-368, PRO-369)"
    validations:
      required: false
