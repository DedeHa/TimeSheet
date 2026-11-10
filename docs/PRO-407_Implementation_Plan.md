# PRO-407 Implementation Plan: Enhance Agent-Team Governance with ADOS-Inspired Patterns

- **JIRA:** PRO-407 (Story, 8 SP, backlog, unassigned)
- **Parent epic:** PRO-259 (Setup Timesheet)
- **Branch:** `feature/PRO-407-agent-governance`
- **Status:** In progress. Rollout steps tracked in section B.5.

## Part A: Preanalysis

### A.1 Decisions (confirmed by user on 2026-11-10)

| # | Question | Decision |
|---|----------|----------|
| 1 | Artifact / doc path | `docs/` (not `doc/`). Ticket paths are superseded by this decision. |
| 2 | Where is the Definition of Ready (DoR) gate enforced? | In `develop-feature` before any code is written. |
| 3 | Artifact retention | Delete the implementation plan after merge (existing `AGENTS.md` rule). Keep the rule. |
| 4 | Handoff protocol | Implement `record_handoff()` in `pipeline.py` and add an AC. |

### A.2 Current state (verified in repo)

- Pipeline recovery commands already exist: `show state`, `what-missed`, `check-stuck`, `dry-run`, `resume`, `continue`, `proceed`, `history`, `reset`, `set-mode`, `get-mode`.
- No handoff recording exists in `pipeline.py` (`record_handoff` / `_post_handoff_comment` absent).
- No DoR gate in `develop-feature`, `orchestrate-feature`, or `refine-feature`.
- No ADR/decision record structure (`docs/decisions/` absent).
- No doc reconciliation step.
- No `docs/changes/` artifact structure.
- `pipeline.py` writes to `~/.opencode/` by default. Tests must redirect `STATE_PATH` / `HISTORY_PATH` to `tmp_path`.
- `.opencode/tests/agents/` runs in CI via `pytest -q .opencode/tests/agents/` (`python-ci.yml`), not part of `testpaths`.

### A.3 Feasibility

Feasible within 8 SP. Agent and skill changes are documentation and workflow edits. The only executable code is the handoff function and its CLI subcommand.

### A.4 Deviation from ticket

- `_post_handoff_comment` is not implemented inside `pipeline.py` because the script has no JIRA client. `pipeline.py` renders the handoff comment markdown; the agent posts it via `atlassian_addCommentToJiraIssue`. This keeps the script dependency-free.

## Part B: Implementation Plan

### B.1 Files

| File | Change | Type |
|------|--------|------|
| `.opencode/scripts/pipeline.py` | Add `render_handoff_comment()`, `record_handoff()`, `handoff` CLI subcommand | Modified |
| `.opencode/tests/agents/test_record_handoff.py` | Unit tests for handoff recording and rendering | New |
| `.opencode/skills/develop-feature/SKILL.md` | Add Step 1f Definition of Ready gate | Modified |
| `.opencode/skills/complete-feature/SKILL.md` | Add doc reconciliation step | Modified |
| `.opencode/agents/product-owner.agent.md` | Reference handoff protocol | Modified |
| `docs/decisions/README.md` | ADR/PDR/TDR/BDR/ODR index and rules | New |
| `docs/decisions/TEMPLATE.md` | Decision record template | New |
| `docs/changes/README.md` | Artifact-first layout (`docs/changes/YYYY-MM/PRO-XXX/`) | New |
| `.opencode/tests/agents/test_governance_docs.py` | Tests that DoR gate, reconciliation, and decision/change layout are documented | New |
| `AGENTS.md` | Document decisions folder, artifact layout, handoff command | Modified |
| `.opencode/skills/plan-feature/` | Empty directory, removed (repo hygiene) | Removed |

### B.2 Handoff data schema

```json
{
  "ticket": "PRO-407",
  "from": "architect",
  "to": "developer",
  "step": "implementation-planning",
  "status": "COMPLETED",
  "artifacts": ["docs/PRO-407_Implementation_Plan.md"],
  "accomplishments": ["..."],
  "issues": [],
  "next_steps": ["..."],
  "mode": "automated",
  "cycle": 1,
  "max_cycles": 3
}
```

Stored in history as action `handoff`. Rendered comment follows the template in PRO-407 (Header, Artifacts, Status, Accomplishments, Issues, Next Steps, Metadata).

### B.3 Rollout steps

1. **Pure code:** `render_handoff_comment`, `record_handoff`, CLI subcommand, unit tests. Verify with `pytest -q .opencode/tests/agents/test_record_handoff.py`, `ruff`, `black`, `pydocstyle`.
2. **Skill and agent docs:** DoR gate in `develop-feature`, doc reconciliation in `complete-feature`, handoff reference in PO agent. Verify with `test_governance_docs.py`.
3. **Decision and change structure:** `docs/decisions/`, `docs/changes/`. Verify files exist and are linked from `AGENTS.md`.
4. **Cleanup and docs:** remove empty `plan-feature` dir, document in `AGENTS.md`.
5. **Full gate:** run agent tests, CI self-tests, application tests, lint, traceability.

### B.4 Non-goals

- Multi-tool support (OpenCode + Claude Code).
- Autonomous CEO delivery loop and batch delivery scripts.
- Replacing the 4-agent model.
- Tracker-agnostic `workItemRef` (Step 6 of ticket). Not in the confirmed AC list; moved to a follow-up ticket.
- Changes to application code under `src/`.

### B.5 Rollout status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Pure code (handoff) + tests | Done (commit 49e4eb2) |
| 2 | Skill/agent docs (DoR, reconciliation, handoff) | Done |
| 3 | `docs/decisions/`, `docs/changes/` | Done |
| 4 | Cleanup and AGENTS.md | Done |
| 5 | Full quality gate | Done (agents 167, ci-pipeline 269, app 409 passed; lint, traceability OK) |

## Part C: Verification Definition

### C.1 Unit-level

- **V1:** `record_handoff()` appends an action `handoff` with all schema fields to history.
- **V2:** `render_handoff_comment()` output contains the Header, Artifacts, Status, Accomplishments, Issues, Next Steps, and Metadata sections.
- **V3:** `handoff` CLI subcommand writes to history without touching real `~/.opencode` (test uses `tmp_path`).
- **V4:** `record_handoff()` rejects missing `from`, `to`, or `status`.

### C.2 Integration-level

- **V5:** `.opencode/tests/agents/` passes in full (`pytest -q .opencode/tests/agents/`).
- **V6:** `develop-feature/SKILL.md` contains a DoR gate section with the checklist; asserted by test.
- **V7:** `complete-feature/SKILL.md` contains a doc reconciliation step; asserted by test.

### C.3 Acceptance criteria

- [x] AC-1: Decision record workflow (ADR/PDR/TDR/BDR/ODR) in `docs/decisions/` with template and index.
- [x] AC-2: Pipeline state management: interruption recovery, stuck detection, dry-run, history implemented and tested (existing plus handoff recording).
- [x] AC-3: DoR gate documented and enforced in `develop-feature` before development.
- [x] AC-4: Doc reconciliation step in `complete-feature`.
- [x] AC-5: Artifact-first layout `docs/changes/` documented and linked.
- [x] AC-6: Handoff protocol recorded via `pipeline.py handoff` and rendered as JIRA comment.

### C.4 Definition of Done

- [ ] PR merged to master
- [ ] JIRA ticket transitioned to Fertig (after user/PO confirmation)
- [ ] All ACs checked
- [ ] Story points: 8 (set)
- [ ] Traceability updated for any new FR/QR entries in `docs/REQUIREMENTS.md`
- [x] Agent test suite passes
- [ ] Implementation plan deleted after merge (per decision A.1-3)
