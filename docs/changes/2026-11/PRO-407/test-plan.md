# PRO-407 Test Plan

Verification items V1 to V17 from the implementation plan (`docs/PRO-407_Implementation_Plan.md`, Part C). V1 to V7 come from the first rollout. V8 to V17 cover the remaining ticket scope (fixes 1 to 9 of the completion round). Each V item maps to the test that checks it. Results are from the gate runs listed at the end; a row is PASS only after its command ran.

## Verification items

| ID | Check | Test | Result |
|----|-------|------|--------|
| V1 | `record_handoff()` appends action `handoff` with all schema fields | `.opencode/tests/agents/test_record_handoff.py::test_record_handoff_appends_history_with_full_schema` | PASS |
| V2 | `render_handoff_comment()` contains Header, Artifacts, Status, Accomplishments, Issues, Next Steps, Metadata | `test_record_handoff.py::test_render_handoff_comment_contains_all_sections` | PASS |
| V3 | `handoff` CLI writes history on a `tmp_path` state, never `~/.opencode` | `test_record_handoff.py::test_handoff_cli_writes_history_and_prints_comment` | PASS |
| V4 | `record_handoff()` rejects missing `from`, `to`, or `status` | `test_record_handoff.py::test_record_handoff_rejects_missing_required_fields` (3 cases) | PASS |
| V5 | `.opencode/tests/agents/` passes in full | `python -m pytest -q .opencode/tests/agents/` | PASS (325 passed) |
| V6 | `develop-feature` contains the DoR gate with D1-D7 before Step 3 | `test_governance_docs.py::test_develop_feature_enforces_dor_gate_before_branch` | PASS |
| V7 | `complete-feature` contains doc reconciliation before Step 5 | `test_governance_docs.py::test_complete_feature_has_doc_reconciliation_step` | PASS |
| V8 | FR-22: `show`, `what-missed`, `check-stuck`, `dry-run`, `history`, `get-mode`, non-forced `reset` on an unknown ticket create no state or history (files absent, or byte-identical when present) | `test_pipeline_read_only.py` (20 cases: 9 commands x 2 file states, plus peek and get checks) | PASS (20 passed) |
| V9 | Status is owned by the CLI: `continue` sets `in_progress`; BLOCKED sets `blocked` and `escalation_level` +1; COMPLETED clears the block and counts a cycle; interruption is derived in one place; `resume` without `--force` refuses a blocked pipeline; `--force` clears it | `test_pipeline_status.py` (11 tests) | PASS (11 passed) |
| V10 | Handoff gate: `continue` refuses without a COMPLETED latest handoff; accepts after COMPLETED; `--force` records `forced_advance`; status validated against COMPLETED, BLOCKED, IN_PROGRESS | `test_handoff_gate.py` (17 tests) | PASS (17 passed) |
| V11 | DoR gate: missing or failing D1-D7 refuses `continue` into develop; all pass allows; a waiver with reason and owner allows and is recorded; a waiver without reason or owner is rejected; `--force` records `forced`; `dor_gate` action recorded on every decision | `test_dor_gate.py` (24 tests) | PASS (24 passed) |
| V12 | Reconcile gate: a changed area without its living document exits 1 and names the document; a reconciled diff exits 0; the git diff path works in a temp repo; a non-git directory reports a hint instead of a traceback | `test_reconcile.py` (20 tests) | PASS (20 passed) |
| V13 | Adversarial readiness reviewer: `readiness-review/SKILL.md` exists, is adversarial, lists D1-D7 with PASS/FAIL, writes to pm-notes; `develop-feature` and `refine-feature` link to it | `test_governance_docs.py::test_readiness_review_skill_is_adversarial_and_lists_dor_items`, `::test_readiness_review_is_linked_from_dor_workflows` (2 cases) | PASS |
| V14 | Tracker-agnostic work item reference: JIRA, GitHub, and generic classification; invalid references rejected before any write; `handoff` records and renders the tracker; other commands unchanged | `test_work_item_ref.py` (26 tests) | PASS (26 passed) |
| V15 | Integration: `set-mode`, `handoff`, `dor`, `continue`, BLOCKED, `show state`, `resume` (refused, then forced), read-only commands on an unknown ticket, and the exact history order, all driven through `pipeline.main()` on `tmp_path` | `test_pipeline_integration.py` (4 tests, marker `integration`) | PASS (4 passed) |
| V16 | Isolation guard: the agent session runs with `HOME` on a temp directory; a write to the original home's pipeline files fails the session | `conftest.py` (session finish check); `test_isolation.py` (2 tests) | PASS (2 passed). Probe run: a deliberate write to a fake real home made pytest exit 1 with the `ISOLATION FAILURE` message. The probe file was deleted afterwards. |
| V17 | Doc alignment: FR-22 to FR-25 and QR-14 defined and traced; traceability gate exits 0; artifacts (plan, test plan, pm-notes) list the current results | `test_governance_docs.py` and `.github/scripts/generate_traceability_matrix.py` | PASS (see gate runs) |

Existing test changed for V16: `tests/setup/test_setup_verification.py::test_ci_tests_use_test_prefix` now accepts pytest's `conftest.py` in the agent test directory. The check still requires every other module to be named `test_*`.

## Gate runs

Run after the last code commit of the completion round (commit `5299a29`). The documentation commit that updates these artifacts does not change any test.

| Gate | Command | Result |
|------|---------|--------|
| Agent tests | `python -m pytest -q .opencode/tests/agents/` | 325 passed |
| CI self-tests | `python -m pytest -q tests/ci-pipeline/` | 269 passed |
| Application tests and coverage | `coverage erase; python -m pytest -m "not system" --cov=src --cov-branch --cov-report=term-missing` | 409 passed, 16 deselected; total coverage 98.53% (threshold 90%) |
| Lint | `ruff check src tests .github` | All checks passed |
| Format | `black --check src tests .github` | 55 files unchanged |
| Traceability | `python .github/scripts/generate_traceability_matrix.py` | Exit 0 |

## Defects found and fixed

| Defect | Found by | Fix |
|--------|----------|-----|
| `resume --force` printed "resumed successfully" but left the pipeline reported as interrupted | `test_resume_with_force_clears_interruption` | `pipeline.py` `resume()` sets status to `resumed` when clearing an interruption |
| `test_agent_team_system.py` wrote to the real `~/.opencode/pipeline-state.json` | mtime of the real state file changed during the agent suite | Autouse fixture redirects `detect_mode.STATE_PATH` to `tmp_path`. The session-level guard (V16) now covers the whole suite. |
| Read-only commands (`show`, `what-missed`, `check-stuck`, `dry-run`, `history`, `get-mode`) created a state entry and a history entry for an unknown ticket | `test_pipeline_read_only.py`: 17 of 20 cases failed against the pre-change `pipeline.py` | Read paths use `_peek_entry`, which does not persist (item 1, FR-22) |
| The CLI never set the status, so `in_progress` (the interruption signal) was never produced; the stored `interrupted` flag was never set | Code review (architect finding 4) and `test_pipeline_status.py` | The CLI sets `in_progress` on advance and `blocked` on BLOCKED; interruption is derived in one place |
| `continue` could advance with no handoff and no DoR record | Architect finding 5 and 6 | Handoff gate (V10) and DoR gate (V11) in `continue` |
| The naming check rejected pytest's `conftest.py` after the isolation guard was added | `test_ci_tests_use_test_prefix` in the app suite | The check allows `conftest.py` by name (commit `5299a29`) |
