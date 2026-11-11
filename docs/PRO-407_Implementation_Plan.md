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
| `.opencode/tests/agents/test_pipeline_recovery.py` | Recovery command tests (`what-missed`, `check-stuck`, `dry-run`, `resume`, `history`) | New |
| `docs/decisions/ODR-0001-agent-team-governance.md` | First decision record (accepted) | New |
| `docs/changes/2026-11/PRO-407/` | Artifact folder: `plan.md`, `test-plan.md`, `pm-notes.md` | New |
| `docs/REQUIREMENTS.md` | FR-21 to FR-25 and QR-14 | Modified |
| `docs/ARCHITECTURE.md` | Traceability rows and agent governance design section | Modified |
| `.github/scripts/generate_traceability_matrix.py` | Scans `.opencode/scripts` and `.opencode/tests/agents` for implementation references | Modified |
| `.opencode/agents/architect.agent.md`, `developer.agent.md`, `tester.agent.md`, `product-owner.agent.md` | Decision records, change artifacts, `pipeline.py handoff` | Modified |
| `.opencode/skills/orchestrate-feature/SKILL.md`, `refine-feature/SKILL.md` | DoR gate and handoff references | Modified |
| `AGENTS.md` | Document decisions folder, artifact layout, handoff command | Modified |
| `.opencode/skills/plan-feature/` | Empty directory, removed (repo hygiene) | Removed |
| `.opencode/scripts/pipeline.py` (completion round) | Read-only paths (`_peek_entry`), CLI-owned status and blocking, handoff gate on `continue`, `dor` / `waive` DoR gate, `reconcile`, `parse_work_item_ref` | Modified |
| `.opencode/tests/agents/test_pipeline_read_only.py` | FR-22 read-only guarantee (byte-identical or absent files) | New |
| `.opencode/tests/agents/test_pipeline_status.py` | Status transitions and derived interruption | New |
| `.opencode/tests/agents/test_handoff_gate.py` | Handoff status validation and the `continue` gate | New |
| `.opencode/tests/agents/test_dor_gate.py` | DoR checklist, waivers, and the develop gate | New |
| `.opencode/tests/agents/test_reconcile.py` | Reconciliation mapping and the git diff path | New |
| `.opencode/tests/agents/test_work_item_ref.py` | Tracker classification and handoff tracker field | New |
| `.opencode/tests/agents/test_pipeline_integration.py` | End-to-end CLI flow (`integration` marker) | New |
| `.opencode/tests/agents/conftest.py`, `test_isolation.py` | HOME isolation and the session guard against real-home writes | New |
| `.opencode/skills/readiness-review/SKILL.md` | Adversarial DoR reviewer (ticket Step 3) | New |
| `tests/setup/test_setup_verification.py` | Allow pytest `conftest.py` in agent test directories | Modified |

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
- ~~Tracker-agnostic `workItemRef` (Step 6 of ticket)~~. Back in scope on 2026-11-11 (user decision: all ticket features are in scope). Implemented, see B.6 gap 7.
- Changes to application code under `src/`.
- ~~Adversarial readiness reviewer for the DoR gate (ticket Step 3)~~. Back in scope on 2026-11-11. Implemented as the `readiness-review` skill, see B.6 gap 3.

### B.5 Rollout status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Pure code (handoff) + tests | Done (commit 49e4eb2) |
| 2 | Skill/agent docs (DoR, reconciliation, handoff) | Done |
| 3 | `docs/decisions/`, `docs/changes/` | Done |
| 4 | Cleanup and AGENTS.md | Done |
| 5 | Full quality gate (first round) | Done (agents 198, ci-pipeline 269, app 409 passed, coverage 98.53%; ruff and black clean; traceability exit 0) |
| 6 | Completion round (items 1 to 10 of the 2026-11-11 instruction, see B.7) | Done. Gate results in `docs/changes/2026-11/PRO-407/test-plan.md` |
| 7 | Fix round for the independent architect and tester reviews (items A to K, see B.8) | Done. Gate results in `docs/changes/2026-11/PRO-407/test-plan.md` |
| 8 | Round-3 blockers (items F1, B1, B2, F3, docs; see B.8 round 3) | Done. Gate results in `docs/changes/2026-11/PRO-407/test-plan.md` |

### B.6 Audit gap closure

Gaps found in the post-rollout audit, closed in this order.

| Gap | Item | Status |
|-----|------|--------|
| 1 | AC-1: decision records wired into Architect and PO agents; ODR-0001 written | DONE |
| 2 | AC-2: recovery tests for `what-missed`, `check-stuck`, `dry-run`, `resume`, `history`. Real bug fixed: `resume --force` left interrupted pipelines reported as interrupted | DONE |
| 3 | AC-3 and ticket Step 3: DoR gate referenced in `orchestrate-feature` and `refine-feature`; adversarial reviewer implemented as `readiness-review` (B.7 items 6) | DONE |
| 4 | AC-5: artifact-first folder `docs/changes/2026-11/PRO-407/` (plan, test-plan, pm-notes) and Architect/Developer references | DONE |
| 5 | AC-6: `pipeline.py handoff` referenced in all four agents and orchestrator | DONE |
| 6 | DoD: FR-21 to FR-25 and QR-14 in `docs/REQUIREMENTS.md`, mapped in `docs/ARCHITECTURE.md`; traceability gate scans `.opencode/scripts` and `.opencode/tests/agents` for implementation references | DONE |
| 7 | Ticket Step 6: tracker-agnostic `workItemRef` (`parse_work_item_ref`, handoff tracker field, ARCHITECTURE section) | DONE (B.7 item 7) |
| 8 | Status tables kept current | DONE (this section and B.7) |

### B.7 Completion round (2026-11-11 instruction)

Items in the order the user set them. Each item has its own commit and tests.

| Item | Change | Commit | Status |
|------|--------|--------|--------|
| 1 | FR-22: read-only commands create no state or history (`_peek_entry`) | b1c4c4b | DONE |
| 2 | Interruption model: CLI owns status; BLOCKED blocks and raises escalation; COMPLETED clears and counts a cycle; stored flag removed | 87262cf | DONE |
| 3 | Handoffs feed the state machine: `continue` needs a COMPLETED latest handoff; status validated; `--force` records `forced_advance` | b7f4c32 | DONE |
| 4 | DoR gate in code: `dor`, `waive`, develop gate, `dor_gate` history, `--force` recorded | 15772c0 (style fix a5e8c2a) | DONE |
| 5 | Documentation reconciliation gate: `reconcile` with injectable `--changed` list | f951da7 | DONE |
| 6 | Adversarial readiness reviewer: `.opencode/skills/readiness-review/SKILL.md`, linked from develop-feature Step 1f and refine-feature | 6785f97 | DONE |
| 7 | Tracker-agnostic `workItemRef`: `parse_work_item_ref`, handoff tracker in history and comment; ARCHITECTURE section | d9547c5 (code), 12547cf (docs) | DONE |
| 8 | End-to-end CLI integration test (`integration` marker) | 22f36b9 | DONE |
| 9 | Isolation guard: HOME on a session temp directory; session fails on real-home writes | 12576ae (style 6d5a822); test naming allowance 5299a29 | DONE |
| 10 | Documentation alignment (this section, test plan, pm-notes, AGENTS.md, ODR-0001, ARCHITECTURE, REQUIREMENTS) | see git log | DONE |

Deviations from the instruction, with reasons:

- **Item 8 flow:** the first `continue` is preceded by a COMPLETED plan handoff. The handoff gate (item 3) and the completed-cycle rule both require it. The test records the sequence and states why.
- **Item 2 interruption:** superseded by fix round item D (B.8). Interruption is now BLOCKED, an explicit marker, or an in_progress step with no update for 24 hours that has not been reported complete. A fresh step is not interrupted.
- **Item 4 waivers:** `dor` accepts only `pass` and `fail`. A waiver goes through `waive`, which requires a reason and an owner. The PRO-407 waivers are not yet recorded in the shared pipeline state (see `docs/changes/2026-11/PRO-407/pm-notes.md`).

### B.8 Fix round (architect and tester review findings)

Fixes for the blocking and major findings of the independent reviews, in the order the
fix brief set them. Each group has its own commit (one logical change per commit, each
with `Refs: PRO-407`). No new PR was opened; the work is on PR #138.

| Item | Change | Commit | Status |
|------|--------|--------|--------|
| A | `continue --force` never bypasses the DoR gate; it bypasses the handoff rule only (architect #1, blocker). FR-23 and ARCHITECTURE say so | 644e5f6 | DONE |
| B | Corrupt state or history file fails closed: exit 1, file unchanged, every command (architect #3, tester #7) | e242d06 | DONE |
| C | BLOCKED: IN_PROGRESS does not clear a block; forced continue clears it and records `cleared_block` (architect #4) | 482b7cd | DONE |
| D | Interruption from one clock-based rule (`interruption_reason`), `interrupt` marker, `INTERRUPT_AFTER_HOURS`; fresh continue is not interrupted (tester #3, architect #5) | fa1e044 | DONE |
| E | Handoff `--step` must equal the current step; agent docs use the pipeline steps (architect #6) | 6c950a0 | DONE |
| F | One ticket normaliser (`work_item_arg`) for every command; `PRO-`/`GH-` rejected as malformed (architect #7, tester #6) | 7088106 | DONE |
| G | D1 (story points) not waivable; D3 narrowed to the ACs and Steps (architect #8) | e2fefd9 | DONE |
| H | Exit codes 0/1/2, refusals exit 1, contract in AGENTS.md (tester #1) | a277ebc | DONE |
| I | Latest-handoff rule isolated with completed cycles; mutation check fails 2 tests (tester #2) | a1ab42f | DONE |
| J1 | `--base` validated; a leading `-` is rejected before git runs (architect minor #9) | 036aecc | DONE |
| J2 | Blank `--changed` entries are not counted (architect minor #8) | 8871002 | DONE |
| J3 | dor_gate records the refusal reasons (architect minor #13). Done in item A | 644e5f6 | DONE |
| J4 | Unique temp file in the same directory, fsync, `os.replace` (architect minor #14) | b676fee | DONE |
| J5 | Read commands never create `~/.opencode`; HOME-based test (tester #4) | 6614e1b | DONE |
| J6 | `continue --force` help text describes the handoff-only bypass | 60e567f | DONE |
| K | Accepted risks and follow-ups recorded in pm-notes; waiver commands and status recorded; V18 to V27 in the test plan | see git log (`docs:` commits after 60e567f) | DONE |

#### B.8 round 3 (final blockers, 2026-11-11)

| Item | Change | Commit | Status |
|------|--------|--------|--------|
| F1 (tester) | `detect_mode.py` loads `pipeline.py` from its own directory and reuses `_read_json_object` (fail closed, exit 1, bytes unchanged) and `_write_json_atomic` (unique temp file, `os.replace`). Reads never create `~/.opencode`. V28 | fffe457 | DONE |
| B1 (architect) | Lowercase JIRA-shaped references (`pro-12`) are rejected as malformed (exit 2 through the normaliser). `feat-login` stays generic. ARCHITECTURE work-item section updated. V29 | 4655d76 | DONE |
| B2 (architect) | FR-23 and the ARCHITECTURE gate row say "(D1 excepted: story points cannot be waived)", pinned by a test (704b20d). The skill text `develop-feature/SKILL.md` has the same unqualified wording; it is outside this item and is open (see pm-notes) | c40f714, 704b20d | DONE |
| F3 (tester, LOW) | Duplicate `INTERRUPT_AFTER_HOURS`: checked. `pipeline.py` has one definition, and the git history has no second one. No change was needed | none | DONE (verified, nothing to remove) |
| Docs | pm-notes: D3 pass (waiver removed), D4 waiver kept, D1 pass, round-3 follow-ups, handoff comment note (decision 4). V28 to V30 in the test plan | 036ef98 and the docs commit that follows it | DONE |

Deviations from the brief, with reasons:

- **`interrupt` command (D):** the marker needs a setter, and no command set it. `interrupt` is new CLI surface. It is recorded in pm-notes decision 10.
- **Step labels (E):** the agent and skill examples used labels such as `implementation`, `validation` and `readiness-review`. They now use `plan`, `develop` and `complete`, because a handoff must match the pipeline step.
- **Argparse usage errors exit 2 (F, H):** an invalid ticket reference is an argparse error, so it exits 2. The brief asked for 1 for refusals, and this is the standard argparse code. The contract documents both.
- **Completed step flag (D):** a `step_reported_complete` flag was added. Without it, a step with a COMPLETED handoff waiting for `continue` would be reported as stale after 24 hours.
- **`reset` without `--force` exits 1 (H):** it is a refused confirmation, so it follows the same rule.

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
- **V8:** FR-22 read-only commands on an unknown ticket create no state or history (`test_pipeline_read_only.py`).
- **V9:** CLI-owned status and blocking; interruption derived in one place (`test_pipeline_status.py`).
- **V10:** `continue` requires a COMPLETED latest handoff; `--force` records `forced_advance` (`test_handoff_gate.py`).
- **V11:** DoR gate refuses, allows, records waivers with reason and owner, and records `dor_gate` (`test_dor_gate.py`).
- **V12:** `reconcile` flags changed areas without their living document (`test_reconcile.py`).
- **V13:** `readiness-review` is adversarial, lists D1-D7, and is linked from the DoR workflows (`test_governance_docs.py`).
- **V14:** `parse_work_item_ref` classifies JIRA, GitHub, and generic references (`test_work_item_ref.py`).
- **V15:** End-to-end CLI flow through `pipeline.main()` (`test_pipeline_integration.py`, `integration` marker).
- **V16:** Isolation guard fails the session on real-home writes (`conftest.py`, `test_isolation.py`).
- **V17:** Traceability gate exits 0; test plan and pm-notes carry the current results.

### C.5 Fix-round verification (B.8)

- **V18:** `continue --force` never bypasses the DoR gate; a recorded waiver allows the forced advance (`test_dor_gate.py`).
- **V19:** A corrupt state or history file fails closed for every command: exit 1, bytes unchanged, no temp file (`test_pipeline_read_only.py`).
- **V20:** BLOCKED is kept by IN_PROGRESS and cleared by a forced continue with a recorded reason (`test_pipeline_status.py`).
- **V21:** Interruption from one clock-based rule; a fresh continue is not interrupted; the `interrupt` marker; the threshold (`test_pipeline_recovery.py`, `test_pipeline_status.py`, `test_pipeline_integration.py`).
- **V22:** Handoff `--step` must equal the current step; an omitted step means the current step (`test_record_handoff.py`).
- **V23:** One ticket normaliser for every command; malformed tracker keys rejected (`test_work_item_ref.py`).
- **V24:** D1 not waivable; D3 narrowed in the skills (`test_dor_gate.py`, `test_governance_docs.py`).
- **V25:** Exit-code contract 0/1/2 across one flow (`test_pipeline_integration.py`).
- **V26:** Latest-handoff rule isolated with completed cycles; mutation check (`test_handoff_gate.py`).
- **V27:** `--base` validation, blank `--changed`, atomic write, no home directory created by reads (`test_reconcile.py`, `test_pipeline_read_only.py`).
- **V28:** `detect_mode.py` shares the fail-closed reader and atomic writer; corrupt state gives exit 1 with bytes unchanged; reads do not create the directory; the write uses `os.replace` (`test_detect_mode_state.py`).
- **V29:** Lowercase JIRA-shaped references are malformed; `continue pro-407` exits 2 and creates no state; `feat-login` stays generic (`test_work_item_ref.py`).
- **V30:** D1 cannot be waived is stated in FR-23 and the ARCHITECTURE gate row (`test_governance_docs.py`).

### C.3 Acceptance criteria

- [x] AC-1: Decision record workflow (ADR/PDR/TDR/BDR/ODR) in `docs/decisions/` with template and index.
- [x] AC-2: Pipeline state management: interruption recovery, stuck detection, dry-run, history implemented and tested (existing plus handoff recording).
- [x] AC-3: DoR gate documented in `develop-feature` and enforced in code by `pipeline.py continue` (develop step), with waivers that need a reason and an owner.
- [x] AC-4: Doc reconciliation step in `complete-feature`.
- [x] AC-5: Artifact-first layout `docs/changes/` documented and linked.
- [x] AC-6: Handoff protocol recorded via `pipeline.py handoff` and rendered as JIRA comment.

### C.4 Definition of Done

- [ ] PR merged to master
- [ ] JIRA ticket transitioned to Fertig (after user/PO confirmation)
- [x] All ACs checked (AC-1 to AC-6, see C.3)
- [x] Story points: 8 (set)
- [x] Traceability updated for any new FR/QR entries in `docs/REQUIREMENTS.md`
- [x] Agent test suite passes
- [ ] Implementation plan deleted after merge (per decision A.1-3)
