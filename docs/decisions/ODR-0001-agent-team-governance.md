# ODR-0001: Decision records and artifact layout for agent team governance

- **Status:** Accepted
- **Date:** 2026-11-10
- **Ticket:** PRO-407
- **Deciders:** Product Owner (user), agent team (Architect, Developer, Tester)

## Context

The agent team (Product Owner, Architect, Developer, Tester) makes architectural,
product, test, and process decisions during each feature. Before PRO-407 these
decisions lived in chat history, JIRA comments, and short-lived implementation
plans. Once a feature closed, the reasoning was gone. Handoffs were recorded
inconsistently, and the Definition of Ready was not enforced before development.

The ADOS-inspired governance pattern adds durable, numbered records and a per-ticket
artifact folder. The working plan `docs/PRO-XXX_Implementation_Plan.md` is deleted
after merge (existing `AGENTS.md` rule), so anything that must outlive the ticket
needs a permanent home.

## Options considered

1. **Keep decisions in JIRA comments and the implementation plan only.** Pros: no new
   structure. Cons: decisions are lost when the plan is deleted, and they are hard to find.
2. **Single `docs/DECISIONS.md` log.** Pros: one file. Cons: merge conflicts across
   features, no per-decision status or supersession, no clear owner per kind.
3. **Numbered records by kind (ADR/PDR/TDR/BDR/ODR) in `docs/decisions/`, plus
   per-ticket artifacts in `docs/changes/YYYY-MM/PRO-XXX/`.** Pros: one decision per
   file, status and supersession, clear owner per kind, survives plan deletion.
   Cons: more files to maintain.

## Decision

Option 3. Decision records live in `docs/decisions/` with the prefixes ADR, PDR, TDR,
BDR, and ODR. Change artifacts live in `docs/changes/YYYY-MM/PRO-XXX/`. The
Architect drafts ADR and TDR records. The Product Owner drafts PDR and BDR records.
The Developer and Tester draft TDR records. `complete-feature` checks decisions
during documentation reconciliation.

This record is an ODR because it governs how the agent team operates (process and
automation), not the product or the application architecture.

## Consequences

- Positive: decisions outlive implementation plans. Each record has a status and can
  be superseded without rewriting history. The index in `docs/decisions/README.md`
  gives one place to look.
- Negative / trade-offs: agents must create and link a record for each decision.
  Discipline is enforced by convention and by `complete-feature` Step 4.5, not by a
  script.
- Follow-up work (superseded on 2026-11-11): the tracker-agnostic `workItemRef` and the
  adversarial readiness reviewer were first deferred. The user then put all ticket
  features in scope. Both are implemented: `parse_work_item_ref` with the handoff
  tracker field, and the `readiness-review` skill (see `docs/PRO-407_Implementation_Plan.md`, B.7).
- The DoR gate is enforced in code (`pipeline.py dor`, `waive`, and `continue`), not only
  by convention. Waivers need a reason and an owner. The documentation reconciliation
  gate is also a command (`pipeline.py reconcile`). It checks which living documents
  changed, not whether their content is correct.

## Links

- Implementation plan: `docs/PRO-407_Implementation_Plan.md`
- Change artifacts: `docs/changes/2026-11/PRO-407/`
- Related records: none
