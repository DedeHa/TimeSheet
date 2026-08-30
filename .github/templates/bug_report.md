---
name: Bug Report
description: Create a bug report ticket for the TimeSheetAlgo project
title: "[fix][PRO-XXX] "
labels: ["bug"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        ## Bug Report
        Use this template to report a bug. All fields are required unless marked optional.
  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: Concise description of the bug
      placeholder: "Fix GitHub release signing to show verified signature"
    validations:
      required: true
  - type: textarea
    id: problem-statement
    attributes:
      label: Problem Statement
      description: Describe the bug — what goes wrong, where, and when
      placeholder: "When a GitHub release is created, the signature message does not appear as verified."
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Reproduction Steps
      description: Step-by-step instructions to reproduce the bug
      placeholder: |
        1. Trigger a GitHub Actions workflow that creates a release
        2. Check the release page on GitHub
        3. Observe that the signature message is missing or not marked as verified
    validations:
      required: true
  - type: textarea
    id: expected-vs-actual
    attributes:
      label: Expected vs Actual Behavior
      description: What should happen vs what actually happens
      placeholder: |
        **Expected:** Release shows "This commit was created on GitHub.com and signed with GitHub's verified signature"
        **Actual:** No signature message is displayed on the release page.
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: Where does the bug occur? (workflow, OS, version, etc.)
      placeholder: |
        - **Workflow:** `.github/workflows/python-ci.yml`
        - **Runner:** GitHub-hosted Ubuntu runner
        - **Version:** v4.2.0
    validations:
      required: false
  - type: textarea
    id: background
    attributes:
      label: Background
      description: Why does this bug matter? Reference related tickets or logs
      placeholder: "PRO-370 fixed a similar signing issue. This is a regression in the release workflow."
    validations:
      required: false
  - type: textarea
    id: acceptance-criteria
    attributes:
      label: Acceptance Criteria
      description: Numbered, testable acceptance criteria
      placeholder: |
        - [ ] AC-1: Release page displays verified signature message
        - [ ] AC-2: CI workflow passes without signature warnings
        - [ ] AC-3: No regressions in existing release creation flow
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
        - [ ] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md
        - [ ] CI self-tests pass
    validations:
      required: true
  - type: textarea
    id: severity
    attributes:
      label: Severity
      description: Impact level of the bug
      placeholder: |
        - [ ] Low — Minor cosmetic issue
        - [ ] Medium — Affects functionality but has a workaround
        - [ ] High — Critical functionality broken, no workaround
        - [ ] Blocker — Blocks the release pipeline
    validations:
      required: false
  - type: textarea
    id: references
    attributes:
      label: References
      description: Related tickets and documentation links
      placeholder: |
        * [PRO-370](https://mainhatten.atlassian.net/browse/PRO-370): Fix GitHub release signing
        * Refs: PRO-259
    validations:
      required: false
