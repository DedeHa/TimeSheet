# Change Artifacts

Artifact-first storage for each feature or bugfix. One folder per ticket, grouped by month the work started.

## Layout

```
docs/changes/
└── YYYY-MM/
    └── PRO-XXX/
        ├── spec.md        What is built and why (from the JIRA ticket and refinement)
        ├── plan.md        Implementation plan (Parts A/B/C) — same content as docs/PRO-XXX_Implementation_Plan.md while active
        ├── test-plan.md   Verification items V1..Vn and results
        └── pm-notes.md    Product/PO notes, decisions taken, handoff log summary
```

## Rules

1. `spec.md`, `plan.md`, `test-plan.md`, and `pm-notes.md` are the four artifact types. Create only those that apply.
2. The working plan `docs/PRO-XXX_Implementation_Plan.md` remains the active document during development.
3. Lifecycle follows the existing `AGENTS.md` rule: the implementation plan is deleted after the PR is merged and the JIRA ticket is closed (user / PO confirmed).
4. Durable knowledge that must outlive the ticket moves out of the change folder into `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, `docs/TESTING.md`, or `docs/decisions/` before deletion.
5. Architecture and product decisions are recorded in `docs/decisions/`, not in change artifacts.
6. Handoff comments live in JIRA. `pm-notes.md` links to the ticket instead of copying them.
