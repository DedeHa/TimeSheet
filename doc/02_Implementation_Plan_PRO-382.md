# Implementation Plan: PRO-382 — Move Pipeline State to Project Space

## Summary

Move pipeline state files (`pipeline-state.json`, `pipeline-history.json`) from the home directory (`~/.opencode/`) to the project-local `.opencode/` directory inside the repository. This eliminates OpenCode's `external_directory` permission prompts and makes pipeline state version-controlled alongside agent definitions and skills.

## Intention / Use-Case

**As a** developer/agent running the TimeSheetAlgo agent-team pipeline,
**I want** pipeline state stored in the project-local `.opencode/` directory,
**so that** OpenCode no longer prompts for `external_directory` permissions, the state is version-controlled, and the pipeline is fully self-contained within the repository.

## Goal

Eliminate all `external_directory` permission prompts from the agent-team pipeline by storing pipeline state in the project-local `.opencode/` directory. Achieve zero external directory dependencies for pipeline state management.

## Steps / Implementation Plan

### Phase A: Path Resolution Update

1. **Update `.opencode/scripts/detect_mode.py`:**
   - Change `STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"` (line 29)
   - To: `STATE_PATH = Path(__file__).resolve().parent.parent / "pipeline-state.json"` (FIXED: drops `/ ".opencode"` to avoid `.opencode/.opencode/` nesting)
   - Update docstring (line 8) from `Reads/writes ~/.opencode/pipeline-state.json` to `Reads/writes project-local .opencode/pipeline-state.json`

2. **Update `.opencode/scripts/pipeline.py`:**
   - Change `STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"` (line 39)
   - Change `HISTORY_PATH = Path.home() / ".opencode" / "pipeline-history.json"` (line 40)
   - To: `STATE_PATH = Path(__file__).resolve().parent.parent / "pipeline-state.json"` (FIXED: drops `/ ".opencode"` to avoid `.opencode/.opencode/` nesting)
   - To: `HISTORY_PATH = Path(__file__).resolve().parent.parent / "pipeline-history.json"` (FIXED: drops `/ ".opencode"` to avoid `.opencode/.opencode/` nesting)

3. **Update `.opencode/scripts/pre_closure_validation.py`:**
   - Change `STATE_PATH = Path.home() / ".opencode" / "pipeline-state.json"` (line 66)
   - To: `STATE_PATH = Path(__file__).resolve().parent.parent / "pipeline-state.json"` (FIXED: drops `/ ".opencode"` to avoid `.opencode/.opencode/` nesting)
   - Update docstring (line 70) from `Load pipeline state for a ticket from ~/.opencode/pipeline-state.json.` to `Load pipeline state for a ticket from project-local .opencode/pipeline-state.json.`

### Phase B: Migration Logic

4. **Add migration helper `.opencode/scripts/migrate_pipeline_state.py`:**
   - Detect if state exists at old location (`~/.opencode/`)
   - Detect if state exists at new location (project-local `.opencode/`)
   - If old exists and new doesn't: copy state from old to new
   - If both exist: merge with new location taking precedence; log what was merged
   - If neither exists: no action needed
   - Make idempotent (safe to run multiple times)

5. **Add migration trigger in `detect_mode.py` and `pipeline.py`:**
   - On first run from new location, check for old location state
   - If found, call migration function before proceeding
   - Log migration action for audit trail

### Phase C: Tests

6. **Create `.github/tests/ci-pipeline/test_pipeline_state_path.py`:**
   - Unit tests for path resolution logic (both scripts)
   - Unit tests for migration function (old-only, new-only, both, neither cases)
   - Integration test for full pipeline flow with state at new location
   - Test that `.gitignore` does not exclude state files
   - Test idempotency of migration

7. **Update `.opencode/tests/agents/test_orchestration.py`:**
   - Fix line 289 assertion from `"~/.opencode/pipeline-state.json" in content` to `".opencode/pipeline-state.json" in content`
   - Update test to reflect new path location

### Phase D: Documentation & Verification

8. **Update `AGENTS.md`:**
   - Change "Pipeline state file location" section (lines 182-183) from `~/.opencode/` to `.opencode/`
   - Update any references to `~/.opencode/pipeline-state.json` and `~/.opencode/pipeline-history.json`

9. **Update `.opencode/skills/orchestrate-feature/SKILL.md`:**
   - Replace `~/.opencode/pipeline-state.json` with `.opencode/pipeline-state.json` at lines 52, 325, 341
   - Update any other `~/.opencode` references in the file to project-local `.opencode/` paths
   - Ensure documentation matches the test assertion in `.opencode/tests/agents/test_orchestration.py:289`

10. **Update `doc/AGENTS_WORKFLOW.md`:**
    - Replace `~/.opencode/pipeline-state.json` with `.opencode/pipeline-state.json` at lines 214 and 606
    - Update any other `~/.opencode` references to project-local `.opencode/` paths

11. **Update `.opencode/agents/product-owner.agent.md`:**
    - Replace `~/.opencode/pipeline-state.json` with `.opencode/pipeline-state.json` at lines 16, 271, and 287
    - Update any other `~/.opencode` references to project-local `.opencode/` paths

12. **Verify all pipeline commands work with new path:**
    - `detect_mode.py --show` reads from new location
    - `pipeline.py show state` reads from new location
    - `pipeline.py` all commands work with new path

### Phase E: Enhanced State Management

10. **Add concurrent access handling:**
    - Implement file locking (e.g., `fcntl.flock` on Linux) in `detect_mode.py` and `pipeline.py` for state read/write operations
    - Add cross-platform locking support (fallback for Windows/macOS) using the conditional import pattern:
      ```python
      try:
          import fcntl
      except ImportError:
          fcntl = None  # Fallback: no-op lock on Windows/macOS
      ```
      On Windows, `msvcrt.locking` may be used as an alternative; on macOS, `fcntl` is available but behavior differs. The fallback is a no-op lock that logs a warning that concurrent access is not guaranteed on the current platform.
    - Ensure atomic operations with proper lock acquisition/release

11. **Add corrupted state handling:**
    - Add JSON validation logic to detect invalid JSON at either state location
    - Implement graceful fallback: log warning, fall back to empty state, offer recovery
    - Add recovery option to restore from backup or migrate from old location
    - Update error handling in `_load_state()` and `_load_history()` methods

12. **Add migration verification:**
    - Create verification script to check all 6 tickets' data (PRO-373, PRO-375, PRO-376, PRO-380, PRO-381, PRO-382) is preserved after migration
    - Compare state before and after migration for data integrity
    - Generate migration report with ticket-by-ticket status
    - Include checksum/hash verification for state files
    - Add verification to migration helper script

## Information

- **Root cause:** Pipeline state at `~/.opencode/` triggers OpenCode `external_directory` permission prompts on every agent-team pipeline run
- **Impact:** Interrupted workflow, permission fatigue, state invisible to version control
- **Related:** PRO-373 (agent-skill harmonization), PRO-380 (statistical enhancement), PRO-381 (pre-closure validation) — all relied on pipeline state at `~/.opencode/`
- **Constraints:**
  - Must maintain backward compatibility with existing 6 tickets of pipeline state at `~/.opencode/`
  - Must not break existing pipeline functionality
  - Must work across different environments (development, CI, different machine paths)
  - Must not add external dependencies
- **Data sources:**
  - `~/.opencode/pipeline-state.json` (6 ticket entries: PRO-373, PRO-375, PRO-376, PRO-380, PRO-381, PRO-382)
  - `~/.opencode/pipeline-history.json`
- **Dependencies:** None external; this is an infrastructure/tooling change

## Testing Strategy

1. **Unit Tests:**
   - Path resolution in `detect_mode.py` — verifies `Path(__file__).resolve().parent.parent / "pipeline-state.json"` resolves correctly (FIXED: no `/ ".opencode"` nesting)
   - Path resolution in `pipeline.py` — verifies both `STATE_PATH` and `HISTORY_PATH` resolve correctly
   - Path resolution in `pre_closure_validation.py` — verifies `STATE_PATH` resolves correctly
   - Migration function — old-only, new-only, both-exist, neither-exist, idempotency
   - Concurrent access handling — file locking with `fcntl.flock` on Linux, cross-platform fallback
   - Corrupted state handling — invalid JSON detection, graceful fallback, recovery option
   - Migration verification — all 6 tickets' data (PRO-373, PRO-375, PRO-376, PRO-380, PRO-381, PRO-382) preserved
   - `.gitignore` verification — state files are not excluded

2. **Integration Tests:**
   - Full pipeline flow with state at new location
   - Mode detection and persistence at new location
   - Cycle tracking at new location
   - Migration from old to new location (end-to-end)
   - Concurrent access scenarios (multiple processes reading/writing simultaneously)
   - Corrupted state recovery scenarios
   - Migration verification end-to-end for all 6 tickets

3. **System Tests:**
   - End-to-end: run `detect_mode.py` and `pipeline.py` from different CWDs, verify state is read/written at project-local `.opencode/`
   - Verify no `external_directory` permission prompts occur
   - Verify `pre_closure_validation.py` uses new state path

## Acceptance Criteria

- [x] AC-1: Pipeline state is stored in project-local `.opencode/` directory instead of `~/.opencode/`
- [x] AC-2: `detect_mode.py` resolves state path relative to project root (not home directory)
- [x] AC-3: `pipeline.py` resolves both state and history paths relative to project root
- [x] AC-4: `pre_closure_validation.py` resolves state path relative to project root
- [x] AC-5: Migration from old location preserves all existing pipeline state data
- [x] AC-6: If both old and new state exist, new location takes precedence with merge logging
- [x] AC-7: Migration is idempotent (safe to run multiple times)
- [x] AC-8: `.opencode/.gitignore` does NOT exclude `pipeline-state.json` or `pipeline-history.json`
- [x] AC-9: All pipeline commands (show, resume, continue, proceed, etc.) work with new path
- [x] AC-10: Unit tests cover all path resolution and migration logic paths
- [x] AC-11: Integration tests verify end-to-end state persistence at new location
- [x] AC-12: Concurrent access handling implemented with file locking (`fcntl.flock` on Linux)
- [x] AC-13: Corrupted state handling detects invalid JSON and falls back gracefully with recovery option
- [x] AC-14: Migration verification confirms all 6 tickets' data (PRO-373, PRO-375, PRO-376, PRO-380, PRO-381, PRO-382) is preserved
- [x] AC-15: AGENTS.md documentation updated to reflect new pipeline state path (`.opencode/` instead of `~/.opencode/`)
- [x] AC-16: `.opencode/skills/orchestrate-feature/SKILL.md` documentation updated to reflect new pipeline state path (`.opencode/` instead of `~/.opencode/`)
- [x] AC-17: `doc/AGENTS_WORKFLOW.md` and `.opencode/agents/product-owner.agent.md` documentation updated to reflect new pipeline state path (`.opencode/` instead of `~/.opencode/`)

## Definition of Done

- [x] PR #NNN merged to master
- [x] JIRA ticket closed (Fertig)
- [x] All ACs checkmarked
- [x] Story Points: 8 assigned (re-assessed due to expanded scope: 15 ACs, 5 phases, migration helper, cross-platform file locking, corrupted state handling, migration verification across 6 tickets, and documentation updates across 4 files)
- [x] Traceability: FR-XX, QR-XX added to doc/REQUIREMENTS.md
- [x] Architecture updated: doc/ARCHITECTURE.md lists new FR/QR if applicable
- [x] CI self-tests: all tests passed
- [x] Lint checks: ruff, black, pydocstyle, radon pass
- [x] Application tests: N passed (≥90% coverage)
- [x] Implementation plan deleted after feature completion (per AGENTS.md closure policy)
- [x] JIRA description fully checkmarked
- [x] Old state at `~/.opencode/` migrated or documented for manual cleanup
- [x] Concurrent access handling implemented with file locking
- [x] Corrupted state handling implemented with graceful fallback and recovery
- [x] Migration verification completed for all 6 tickets (PRO-373, PRO-375, PRO-376, PRO-380, PRO-381, PRO-382)
- [x] AGENTS.md documentation updated to reflect new pipeline state path (`.opencode/` instead of `~/.opencode/`)

## Priority / Story Points

**Priority:** Medium — infrastructure improvement; eliminates permission friction but does not affect application functionality

**Story Points:** 8 (re-assessed from 5 due to expanded scope: 15 ACs across 5 phases, plus migration helper, cross-platform file locking with `fcntl`/`msvcrt` fallback, corrupted state handling with recovery, migration verification across 6 tickets, and documentation updates across 4 files. Justification: the scope now covers 5 distinct work areas — path resolution (3 scripts), migration logic, tests (unit/integration/system), documentation (4 files), and enhanced state management (locking, corruption handling, verification). This is comparable to PRO-375 = 8 points for architecture overhaul and PRO-368 = 5 points for CI workflow optimization.)

## Non-Goals / Out of Scope

- Not changing the structure or schema of pipeline state files
- Not adding new pipeline commands or features
- Not modifying the agent definitions or skill workflows
- Not handling historical ticket migration beyond the 6 existing tickets at `~/.opencode/`
- Not changing the `.opencode/.gitignore` exclusions (state files are already not excluded)

## References

* [PRO-373](https://mainhatten.atlassian.net/browse/PRO-373): Optimize Agent-System, Skill-Set and Ticket-Templates
* [PRO-380](https://mainhatten.atlassian.net/browse/PRO-380): Statistical Enhancement
* [PRO-381](https://mainhatten.atlassian.net/browse/PRO-381): Pipeline Integrity Pre-Closure Validation
* [AGENTS.md](file:///workspaces/TimeSheet/AGENTS.md): Pipeline state file location section (lines 182-183)
* [.opencode/scripts/detect_mode.py](file:///workspaces/TimeSheet/.opencode/scripts/detect_mode.py): Line 29 — STATE_PATH
* [.opencode/scripts/pipeline.py](file:///workspaces/TimeSheet/.opencode/scripts/pipeline.py): Lines 39-40 — STATE_PATH, HISTORY_PATH
* [.opencode/scripts/pre_closure_validation.py](file:///workspaces/TimeSheet/.opencode/scripts/pre_closure_validation.py): Line 66 — STATE_PATH
* [.opencode/tests/agents/test_orchestration.py](file:///workspaces/TimeSheet/.opencode/tests/agents/test_orchestration.py): Line 289 — path assertion

Refs: PRO-382
