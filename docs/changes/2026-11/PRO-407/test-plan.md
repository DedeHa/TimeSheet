# PRO-407 Test Plan

Verification items V1 to V7 from the implementation plan (`docs/PRO-407_Implementation_Plan.md`, Part C). Results come from the gate run on 2026-11-10 (commands below). Each V item maps to the test that checks it.

## Verification items

| ID | Check | Test | Result |
|----|-------|------|--------|
| V1 | `record_handoff()` appends action `handoff` with all schema fields | `.opencode/tests/agents/test_record_handoff.py::test_record_handoff_appends_history_with_full_schema` | PASS |
| V2 | `render_handoff_comment()` contains Header, Artifacts, Status, Accomplishments, Issues, Next Steps, Metadata | `test_record_handoff.py::test_render_handoff_comment_contains_all_sections` | PASS |
| V3 | `handoff` CLI writes history on a `tmp_path` state, never `~/.opencode` | `test_record_handoff.py::test_handoff_cli_writes_history_and_prints_comment` | PASS |
| V4 | `record_handoff()` rejects missing `from`, `to`, or `status` | `test_record_handoff.py::test_record_handoff_rejects_missing_required_fields` (3 cases) | PASS |
| V5 | `.opencode/tests/agents/` passes in full | `python -m pytest -q .opencode/tests/agents/` | PASS (198 passed) |
| V6 | `develop-feature` contains the DoR gate with D1-D7 before Step 3 | `test_governance_docs.py::test_develop_feature_enforces_dor_gate_before_branch` | PASS |
| V7 | `complete-feature` contains doc reconciliation before Step 5 | `test_governance_docs.py::test_complete_feature_has_doc_reconciliation_step` | PASS |

Additional tests added by the audit gap closure (not in V1-V7 but covering AC-1 to AC-6):

| Area | Test file | Covers |
|------|-----------|--------|
| Recovery commands (AC-2) | `test_pipeline_recovery.py` (14 tests) | `what-missed`, `check-stuck`, `dry-run`, `resume`, `history`, CLI dispatch. Includes the forced-resume fix. |
| Decision records (AC-1) | `test_governance_docs.py` | Architect and PO reference `docs/decisions/`; ODR-0001 is Accepted and indexed |
| DoR references (AC-3) | `test_governance_docs.py` | Orchestrator and refine-feature reference the DoR gate and D1-D7 |
| Handoff references (AC-6) | `test_governance_docs.py` | Four agents and orchestrator use `pipeline.py handoff` and post the comment |
| Change folder (AC-5) | `test_governance_docs.py` | `docs/changes/2026-11/PRO-407/` holds plan, test-plan, and pm-notes |
| Requirements and traceability (DoD) | `test_governance_docs.py` and `generate_traceability_matrix.py` | FR-21 to FR-25 and QR-14 are defined and mapped |

## Gate runs

| Gate | Command | Result |
|------|---------|--------|
| Agent tests | `python -m pytest -q .opencode/tests/agents/` | 198 passed |
| CI self-tests | `python -m pytest -q tests/ci-pipeline/` | 269 passed |
| Application tests and coverage | `coverage erase; python -m pytest -m "not system" --cov=src --cov-branch --cov-report=term-missing` | 409 passed, 16 deselected; total coverage 98.53% (threshold 90%) |
| Lint | `ruff check src tests .github` | All checks passed |
| Format | `black --check src tests .github` | 55 files unchanged |
| Traceability | `python .github/scripts/generate_traceability_matrix.py` | Exit 0 |

## Defects found and fixed

| Defect | Found by | Fix |
|--------|----------|-----|
| `resume --force` printed "resumed successfully" but left the pipeline reported as interrupted | `test_resume_with_force_clears_interruption` | `pipeline.py` `resume()` sets status to `resumed` when clearing an interruption |
| `test_agent_team_system.py` wrote to the real `~/.opencode/pipeline-state.json` | mtime of the real state file changed during the agent suite | Autouse fixture redirects `detect_mode.STATE_PATH` to `tmp_path` |
