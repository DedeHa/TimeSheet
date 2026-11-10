# PRO-407 Plan Pointer

- **Ticket:** PRO-407 — Enhance Agent-Team Governance with ADOS-Inspired Patterns (Story, 8 SP, parent PRO-259)
- **Branch:** `feature/PRO-407-agent-governance` (PR #138, base `master`)
- **Working plan:** [`docs/PRO-407_Implementation_Plan.md`](../../../PRO-407_Implementation_Plan.md). It stays the active document until the PR is merged and the JIRA ticket is closed, then it is deleted (see `AGENTS.md`).

## Summary

The plan has three parts:

- **Part A (Preanalysis):** four confirmed decisions (`docs/` path, DoR gate in `develop-feature`, plan deleted after merge, handoff via `pipeline.py handoff`), the verified current state, feasibility, and one deviation (no JIRA client in `pipeline.py`; the agent posts the comment).
- **Part B (Implementation):** the file list, handoff schema, rollout steps 1–5, non-goals, and the audit gap closure table (B.6).
- **Part C (Verification):** verification items V1–V7 and acceptance criteria AC-1 to AC-6. The results for V1–V7 are in [`test-plan.md`](test-plan.md).

## Governance components

| Component | Location |
|-----------|----------|
| Handoff recording | `.opencode/scripts/pipeline.py` (`handoff`, `record_handoff`, `render_handoff_comment`) |
| Recovery commands | `.opencode/scripts/pipeline.py` (`what-missed`, `check-stuck`, `dry-run`, `resume`, `history`) |
| DoR gate | `.opencode/skills/develop-feature/SKILL.md` Step 1f |
| Doc reconciliation | `.opencode/skills/complete-feature/SKILL.md` Step 4.5 |
| Decision records | `docs/decisions/` (ODR-0001 is the first record) |
| Change artifacts | `docs/changes/` (this folder is the first) |
