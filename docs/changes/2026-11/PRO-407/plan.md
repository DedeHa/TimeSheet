# PRO-407 Plan Pointer

- **Ticket:** PRO-407 — Enhance Agent-Team Governance with ADOS-Inspired Patterns (Story, 8 SP, parent PRO-259)
- **Branch:** `feature/PRO-407-agent-governance` (PR #138, base `master`)
- **Working plan:** [`docs/PRO-407_Implementation_Plan.md`](../../../PRO-407_Implementation_Plan.md). It stays the active document until the PR is merged and the JIRA ticket is closed, then it is deleted (see `AGENTS.md`).

## Summary

The plan has three parts:

- **Part A (Preanalysis):** four confirmed decisions (`docs/` path, DoR gate in `develop-feature`, plan deleted after merge, handoff via `pipeline.py handoff`), the verified current state, feasibility, and one deviation (no JIRA client in `pipeline.py`; the agent posts the comment).
- **Part B (Implementation):** the file list, handoff schema, rollout steps 1–5, non-goals, and the audit gap closure table (B.6).
- **Part C (Verification):** verification items V1–V17 and acceptance criteria AC-1 to AC-6. The results are in [`test-plan.md`](test-plan.md).
- **Completion round:** items 1–10 of the 2026-11-11 instruction (plan B.7), with one commit per item.

## Governance components

| Component | Location |
|-----------|----------|
| Handoff recording | `.opencode/scripts/pipeline.py` (`handoff`, `record_handoff`, `render_handoff_comment`) |
| Recovery commands | `.opencode/scripts/pipeline.py` (`what-missed`, `check-stuck`, `dry-run`, `resume`, `history`; read-only paths never write) |
| Status and handoff gate | `.opencode/scripts/pipeline.py` (`continue` needs a COMPLETED latest handoff; BLOCKED blocks until `resume --force`) |
| DoR gate | `.opencode/skills/develop-feature/SKILL.md` Step 1f; enforced by `pipeline.py dor`, `waive`, and `continue` |
| Adversarial readiness review | `.opencode/skills/readiness-review/SKILL.md` |
| Documentation reconciliation | `.opencode/skills/complete-feature/SKILL.md` Step 4.5; `pipeline.py reconcile` |
| Work item references | `pipeline.py` (`parse_work_item_ref`); section in `docs/ARCHITECTURE.md` |
| Doc reconciliation | `.opencode/skills/complete-feature/SKILL.md` Step 4.5 |
| Decision records | `docs/decisions/` (ODR-0001 is the first record) |
| Change artifacts | `docs/changes/` (this folder is the first) |
