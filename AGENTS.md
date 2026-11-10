# AGENTS.md — TimeSheetAlgo

## Quick Setup (Critical for Ramping Up)

**Install development environment:**
```bash
# Always install in development mode with dev extras
python -m pip install -e .[dev]
```

**Virtual environment activation (non-negotiable):**
```bash
# Git checkout always requires this
git checkout <branch-name>
source /workspaces/TimeSheet/.venv/bin/activate
echo "✅ venv activated: $VIRTUAL_ENV"  # Must show /.venv path
```

## Testing Strategy

**Run different test suites:**
```bash
# Full test suite with coverage (CI requirement)
python -m pytest tests/ --cov=src --cov-report=term-missing

# Fast CI mode (what actual PRs run)
python -m pytest -m "not system"

# Individual levels
python -m pytest tests/unit -m unit          # Unit tests only
python -m pytest tests/integration -m integration  # Integration tests only
python -m pytest tests/system -m system      # System tests (real files required)
```

**Code quality checks (gates PRs):**
```bash
# Order matters - run in sequence
ruff check src tests
black --check src tests
pydocstyle src tests
radon cc src -a

# Traceability - CI gate, exits non-zero if incomplete
python .github/scripts/generate_traceability_matrix.py
```

## Architecture & Configuration

**Package structure:**
- `src/` - Main package (tested, covered)
  - `TimeSheetAlgo.py` - Entrypoint application
  - `config.yaml` - Configuration file
- `src_azesheetalgo/` - Separate package (AZE sheet functionality, NOT packaged, NOT tested)

**Critical config requirements:**
- Year is **required** at root level in `config.yaml` - no fallback
- Environment auto-detected by folder structure, not config parameter
- Paths are **relative to project root**, not script location

## Environment Detection Rules

**Environment detection logic:**
- Development: Running from `src/` directory
- Production: Contains `Timealarm/` subfolder in path
- Fallback: Always development

**Configuration auto-detection:**
```python
# From TimeSheetAlgo.py:96-110
def detect_environment(base_path: str) -> str:
    if os.path.basename(base_path) == "src":
        return "development"
    elif os.path.isdir(os.path.join(base_path, "Timealarm")):
        return "production"
    else:
        return "development"
```

## Git & PR Conventions

**Branch strategy:**
- Feature branches: `feature/PRO-123-description` (direct pushes allowed)
- PRs always target `master`
- Release branches: `release/vX.Y.Z` (protected, PR required)

**Naming validation (CI blockers):**
- **Commit messages:** `type(scope): description` + `Refs: PRO-XXX` footer
- **PR title:** `[type][PRO-XXX] Description`
- **PR body:** Must contain `## Summary` + `## Testing` + `Refs: PRO-XXX`

**No tests on direct branch pushes:**
- CI only runs on PRs to `master` or `release/**`
- CI also runs on release tags
- Feature branch commits are not tested

**Closure policy:**
- Remote branch deletion is User / PO responsibility — agent prepares command, user confirms and executes
- Agent-team closure executes `atlassian_transitionJiraIssue` and `gh pr merge` only after user / PO confirmation
- **Implementation plan deletion:** After a feature is fully completed (PR merged to master, JIRA ticket transitioned to Fertig), the implementation plan document (`docs/PRO-XXX_Implementation_Plan.md`) must be deleted. The plan is a working document that becomes stale once the feature is complete and merged. Deletion is part of the finalization commit/push.

## Simplified Agent Model

### Overview

The TimeSheetAlgo agent workflow is simplified behind a single, clean entry point: the **Product Owner**. This hides the complexity of agent YAML files, skill files, multiple script names, and migration helpers while preserving the underlying technical separation of concerns.

### User Journey

**Only 3-4 main commands:**

1. **Run in mode** — Set the development mode
   - `Run in automated mode` — Full pipeline without user pauses
   - `Run in interactive mode` — Pause at every handover for confirmation

2. **Start feature** — Begin work on a JIRA ticket
   - The Product Owner orchestrates the complete pipeline: PO → Architect → Developer → Tester → PO (review)

3. **Continue feature** — Advance to the next pipeline step
   - The Product Owner dispatches the next agent in the pipeline

4. **Validate feature** — Complete and close the feature
   - The Product Owner reviews completed work, checks off acceptance criteria, and prepares JIRA closure

### Architecture (Behind the Scenes)

The simplified model preserves the technical separation of concerns:

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Interaction** | Product Owner | Sole entry point, user-facing intent parsing, mode detection |
| **Policy** | Skills | Workflow coordination, stakeholder review, feature lifecycle management |
| **Runtime** | Scripts | Pipeline state machine, migration/validation helpers, CI integration |

### Scripts (Hidden from Users)

| Script | Responsibility | Visibility |
|--------|---------------|------------|
| `detect_mode.py` | User-facing intent parsing (interactive/automated mode detection) | Behind Product Owner |
| `pipeline.py` | Workflow state machine (pipeline state, history, interruption recovery) | Behind Product Owner |
| Migration/Validation helpers | Behind-the-scenes support for pipeline transitions | Behind Product Owner |

### Development Modes

**Mode selection (set before starting a feature):**
- `interactive` — pause at every handover for user confirmation before the next agent takes over
- `automated` — run the full pipeline without user pauses; only blockers and cycle limits interrupt

**Mode detection from chat:**
The Product Owner agent parses user chat messages for conversational patterns to derive the mode and persists it in `~/.opencode/pipeline-state.json`:

```bash
python .opencode/scripts/detect_mode.py PRO-373 "Run in automated"
python .opencode/scripts/detect_mode.py PRO-373 --show
```

- "Run in automated", "go ahead", "proceed", "without confirmation" → `development_mode: automated`
- "Run in interactive", "pause", "confirm", "ask me" → `development_mode: interactive`
- Default is `interactive` when no mode is detected

**Pipeline state:**
State is persisted per ticket in `~/.opencode/pipeline-state.json` (encrypted if enabled). The `development_mode` field is read before every dispatch and handoff so all 4 agents respect the user's mode choice.

**Enhanced Pipeline Management:**
The `pipeline.py` script provides enhanced pipeline management for handling
interrupted pipelines, resuming stuck steps, and inspecting state. All commands
are invoked from the repository root:

```bash
python .opencode/scripts/pipeline.py <command> <ticket> [options]
```

| Command | Purpose |
|---------|---------|
| `show state PRO-373` | Show current pipeline state with interruption detection |
| `what-missed PRO-373` | Show what work was missed in an interrupted pipeline |
| `check-stuck PRO-373` | Detect and alert on stuck pipelines |
| `dry-run PRO-373 <action>` | Preview action without executing |
| `resume PRO-373` | Resume pipeline at current step (clears interruption flag) |
| `resume PRO-373 --force` | Force resume without validation |
| `continue PRO-373` | Advance to next pipeline step |
| `continue PRO-373 --force` | Force advance without validation |
| `proceed PRO-373` | Proceed with current step execution |
| `history PRO-373` | Show pipeline history |
| `reset PRO-373` | Reset all cycles and state |
| `set-mode PRO-373 interactive` | Set development mode |
| `get-mode PRO-373` | Show persisted mode |

**Interruption recovery workflow:**
```bash
# 1. Check what was missed
python .opencode/scripts/pipeline.py what-missed PRO-373

# 2. Check if pipeline is stuck
python .opencode/scripts/pipeline.py check-stuck PRO-373

# 3. Preview the resume action
python .opencode/scripts/pipeline.py dry-run PRO-373 resume

# 4. Resume the pipeline
python .opencode/scripts/pipeline.py resume PRO-373

# 5. Verify state
python .opencode/scripts/pipeline.py show state PRO-373
```

**Pipeline state file location:**
- State: `~/.opencode/pipeline-state.json`
- History: `~/.opencode/pipeline-history.json`

## Simplified User Journey

The simplified model provides a clean, human-friendly user experience with only 3-4 main commands:

### 1. Run in Mode

Set the development mode before starting a feature:

```bash
# Run in automated mode — full pipeline without user pauses
Run in automated mode

# Run in interactive mode — pause at every handover for confirmation
Run in interactive mode
```

**Mode detection:** The Product Owner agent parses conversational patterns from your chat messages to determine the mode:
- "Run in automated", "go ahead", "proceed", "without confirmation" → `development_mode: automated`
- "Run in interactive", "pause", "confirm", "ask me" → `development_mode: interactive`
- Default is `interactive` when no mode is detected

### 2. Start Feature

Begin work on a JIRA ticket using the simplified pipeline:

```bash
# The Product Owner orchestrates: PO → Architect → Developer → Tester → PO (review)
start feature PRO-384
```

This initiates the complete agent-team pipeline with the Product Owner as the sole entry point.

### 3. Continue Feature

Advance to the next pipeline step:

```bash
# Continue to the next agent in the pipeline
continue feature PRO-384
```

The Product Owner dispatches the appropriate agent based on the current pipeline state.

### 4. Validate Feature

Complete and close the feature:

```bash
# Review completed work and prepare JIRA closure
validate feature PRO-384
```

The Product Owner reviews all work, checks off acceptance criteria, and prepares for final handoff.

## Simplified Model Benefits

### For New Contributors

- **Reduced complexity:** No need to understand agent YAML files, skill files, or multiple script names
- **Clear entry point:** Product Owner is the only documented entry point for workflow initiation
- **Simplified documentation:** All complexity hidden behind clean, user-friendly documentation

### For Experienced Contributors

- **Preserved technical separation:** Core architecture remains intact (interaction, policy, runtime)
- **Full functionality:** All existing features and capabilities are preserved
- **Enhanced control:** Choice between automated (fast) or interactive (controlled) workflow modes

### Technical Architecture

The simplified model maintains the underlying technical separation of concerns:

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Interaction** | Product Owner | User-facing intent parsing, mode detection, workflow coordination |
| **Policy** | Skills | Multi-stakeholder review, feature lifecycle management |
| **Runtime** | Scripts | Pipeline state machine, migration/validation helpers, CI integration |

### Behind-the-Scenes Scripts

| Script | Purpose | User Visibility |
|--------|---------|-----------------|
| `detect_mode.py` | Parse user intent for interactive/automated mode | Hidden (Product Owner only) |
| `pipeline.py` | Manage workflow state, interruption recovery, history | Hidden (Product Owner only) |
| Migration/Validation helpers | Support pipeline transitions and validation | Hidden (Product Owner only) |

## Governance Artifacts (PRO-407)

- **Decision records:** `docs/decisions/` holds ADR / PDR / TDR / BDR / ODR records. Start from `docs/decisions/TEMPLATE.md`. Index in `docs/decisions/README.md`.
- **Change artifacts:** `docs/changes/YYYY-MM/PRO-XXX/` holds `spec.md`, `plan.md`, `test-plan.md`, `pm-notes.md` when applicable. Layout in `docs/changes/README.md`.
- **Active plan:** `docs/PRO-XXX_Implementation_Plan.md` is deleted after merge and JIRA closure (user / PO confirmed).
- **Definition of Ready:** enforced in `develop-feature` Step 1f before branch creation.
- **Doc reconciliation:** `complete-feature` Step 4.5 updates living docs before closure.
- **Handoff record:** `python .opencode/scripts/pipeline.py handoff PRO-XXX --from <agent> --to <agent> --status <status> ...` records the handoff and prints the JIRA comment to post.

## Handoff Gates

### Interactive Mode

Before each handoff to the next agent, the Product Owner pauses and waits for user confirmation:

| Handoff | Gate | PO Presents | User Confirms |
|---------|------|-------------|---------------|
| PO → discover-feature | After intake | Intake output (goal, use-case, information) | "Proceed to discovery?" |
| discover-feature → refine-feature | After ticket draft | Ticket summary, ACs, DoD, story points, sprint placement | "Proceed to stakeholder review?" |
| refine-feature → develop-feature | After finalization | Finalized ticket (stakeholders confirmed, ACs testable, DoD realistic, story points assigned) | "Proceed to development?" |
| Architect → Developer | After plan | Architecture plan, implementation plan | "Proceed to development?" |
| Developer → Tester | After implementation | Changes made, test coverage | "Proceed to testing?" |
| Tester → PO | After validation | Test results, pass/fail decision | "Proceed to review?" |
| PO → User | After review | Complete summary, AC status | "Close ticket & merge PR?" |

### Automated Mode

In automated mode, handoffs proceed without user pauses:

- Each handoff includes the full deliverable and state
- The next agent receives all context and proceeds immediately
- **Escalation still triggers** on blockers or cycle limit (3) — the Product Owner interrupts and evaluates

## Pipeline Management

The enhanced pipeline management provides tools for handling interrupted workflows:

### Key Commands

```bash
# Show current pipeline state with interruption detection
python .opencode/scripts/pipeline.py show state PRO-384

# Show what work was missed in an interrupted pipeline
python .opencode/scripts/pipeline.py what-missed PRO-384

# Detect and alert on stuck pipelines
python .opencode/scripts/pipeline.py check-stuck PRO-384

# Preview an action without executing
python .opencode/scripts/pipeline.py dry-run PRO-384 <action>

# Resume pipeline at current step (clears interruption flag)
python .opencode/scripts/pipeline.py resume PRO-384

# Force resume without validation
python .opencode/scripts/pipeline.py resume PRO-384 --force

# Advance to next pipeline step
python .opencode/scripts/pipeline.py continue PRO-384

# Force advance without validation
python .opencode/scripts/pipeline.py continue PRO-384 --force

# Proceed with current step execution
python .opencode/scripts/pipeline.py proceed PRO-384

# Show pipeline history
python .opencode/scripts/pipeline.py history PRO-384

# Reset all cycles and state
python .opencode/scripts/pipeline.py reset PRO-384

# Set development mode
python .opencode/scripts/pipeline.py set-mode PRO-384 interactive

# Show persisted mode
python .opencode/scripts/pipeline.py get-mode PRO-384
```

### Interruption Recovery Workflow

```bash
# 1. Check what was missed
python .opencode/scripts/pipeline.py what-missed PRO-384

# 2. Check if pipeline is stuck
python .opencode/scripts/pipeline.py check-stuck PRO-384

# 3. Preview the resume action
python .opencode/scripts/pipeline.py dry-run PRO-373 resume

# 4. Resume the pipeline
python .opencode/scripts/pipeline.py resume PRO-384

# 5. Verify state
python .opencode/scripts/pipeline.py show state PRO-384
```

## Mode Persistence

Pipeline state is persisted per ticket in `~/.opencode/pipeline-state.json`:

```json
{
  "PRO-384": {
    "development_mode": "interactive",
    "last_updated": "2026-10-14T11:11:25.066544+00:00"
  }
}
```

The `development_mode` field is read before every dispatch and handoff so all agents respect the user's mode choice.

## Development Workflow Summary

The simplified agent model provides a streamlined development workflow:

1. **Set mode** — Choose between automated (fast) or interactive (controlled)
2. **Start feature** — Initiate the complete pipeline with Product Owner orchestration
3. **Continue feature** — Progress through the agent-team pipeline
4. **Validate feature** — Complete and close the feature

**Key benefits:**
- **Reduced complexity:** No need to understand agent YAML, skill files, or multiple scripts
- **Clear entry point:** Product Owner is the only documented entry point
- **Preserved architecture:** Technical separation of concerns maintained
- **Enhanced control:** Choice between automated and interactive modes
- **Better user experience:** Clean, human-friendly documentation

**Technical separation preserved:**
- **Interaction:** Product Owner handles user intent and mode detection
- **Policy:** Skills coordinate multi-stakeholder review and feature lifecycle
- **Runtime:** Scripts manage pipeline state and workflow execution

This model successfully hides complexity while maintaining all functionality, making TimeSheetAlgo easier to understand and use for both new and experienced contributors.