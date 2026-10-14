---
name: orchestrate-feature
description: "Central orchestrator for the entire feature pipeline. Reads JIRA state, tracks cycles, dispatches to Architect/Developer/Tester, handles escalations, and coordinates handoffs. This is the engine that makes the agent-team actually chain. Load this skill for any new feature or when the pipeline needs rebalancing. NOTE: Story points must be assigned before development pickup or sprint inclusion."
---

# Orchestrate Feature Pipeline

## Overview

The `orchestrate-feature` skill is the **central orchestrator** that coordinates
the entire feature pipeline. It lives in the Product Owner agent and manages
the flow from **Plan → Develop → Complete**, with built-in cycle tracking,
state management, and escalation handling.

## Simplified Model Context

In the simplified agent model, the `orchestrate-feature` skill operates **behind the scenes** as part of the Product Owner's workflow coordination. While the Product Owner provides the clean, human-friendly entry point for users, this skill handles the complex pipeline mechanics that make the agent team work together seamlessly.

The skill is **not directly invoked by users** but is automatically loaded by the Product Owner agent to manage the complete feature lifecycle from planning through closure.

## Discovery

Both agents and skills are discovered by `opencode` from the `.opencode/`
directory:

```
.opencode/
├── agents/          # Agent definitions (product-owner, architect, developer, tester)
│   └── *.agent.md   # YAML frontmatter + handoffs + constraints
└── skills/          # Workflow reference documents
    └── <skill>/
        └── SKILL.md
```

The Product Owner agent loads this skill via its `skills` frontmatter entry.
The agent definitions in `.opencode/agents/` are loaded by `opencode` and
provide the handoff prompts that chain the pipeline.

## When to Use

Use this skill when:
- A new feature needs to be started (e.g., "start feature PRO-373")
- The current pipeline needs rebalancing (e.g., "reset pipeline PRO-373")
- Cycle detection triggers (e.g., "check cycles PRO-373")
- Escalation handling is needed (e.g., "escalate PRO-373")
- State inspection is required (e.g., "show state PRO-373")

## Core Responsibilities

1. **State Detection**: Reads JIRA to determine current pipeline step
2. **Cycle Tracking**: Counts cycles per agent, stops at 3
3. **Dispatch**: Routes to the right next agent
4. **Escalation**: Handles blockers and PO evaluations
5. **Handoff Coordination**: Manages transitions between phases

## State Management

The orchestration skill maintains state in `~/.opencode/pipeline-state.json`:

```json
{
  "PRO-373": {
    "development_mode": "interactive",
    "current_step": "plan",
    "cycle_counts": {
      "plan": 1,
      "develop": 0,
      "complete": 0
    },
    "last_updated": "2025-08-30T14:30:00Z",
    "status": "in_progress",
    "blocked": false,
    "escalation_level": 0
  }
}
```

**Development modes:**
- **Interactive** (default): Pause at each handover for user confirmation
- **Automated**: Run the pipeline without pauses; escalations still trigger

**Mode detection from chat:**
The PO agent parses user chat messages for conversational patterns to derive the mode:
- "Run in automated", "go ahead", "proceed", "without confirmation" → `development_mode: automated`
- "Run in interactive", "pause", "confirm", "ask me" → `development_mode: interactive`
- Mode is checked before each handoff and at each dispatch step

**Mode detection script:**
The script `.opencode/scripts/detect_mode.py` parses chat messages and persists the mode:
```bash
python .opencode/scripts/detect_mode.py PRO-373 "Run in automated"
python .opencode/scripts/detect_mode.py PRO-373 --show
```
The PO agent invokes this script during intake (to set the mode from chat) and before each handoff (to read the persisted mode).

**Mode check step in pipeline flow:**
Before every dispatch and handoff, the orchestration skill runs:
1. `python .opencode/scripts/detect_mode.py <ticket> --show` to read the persisted mode
2. If `development_mode: automated` → proceed without user confirmation
3. If `development_mode: interactive` → pause for user confirmation
4. If no mode detected → default to `interactive`

## Pipeline Flow

### Step 1: Discover Phase
1. **State Detection**: Checks JIRA for existing PRO-XXXX ticket
2. **Dispatch**: Routes to PO agent via `discover-feature` skill to draft the ticket
3. **Update State**: Sets `current_step: "refine"`

### Step 2: Refine Phase
1. **State Detection**: Confirms we're in "refine" step
2. **Cycle Check**: Verifies stakeholder reviewers haven't exceeded 3 cycles
3. **Dispatch**: Routes to PO agent via `refine-feature` skill for stakeholder review
4. **Update State**: Sets `current_step: "plan"`

### Step 3: Plan Phase
1. **State Detection**: Confirms we're in "plan" step
2. **Cycle Check**: Verifies Architect agent hasn't exceeded 3 cycles
3. **Dispatch**: Routes to Architect agent via `develop-feature` skill
4. **Update State**: Sets `current_step: "develop"`, increments Architect cycles

### Step 4: Develop Phase
1. **State Detection**: Confirms we're in "develop" step
2. **Cycle Check**: Verifies Developer agent hasn't exceeded 3 cycles
3. **Story Points Validation**: Confirms PRO-XXX has story points assigned (required for development)
   - If missing → escalate to Product Owner, do NOT proceed to development
   - If present → proceed to Developer agent
4. **Dispatch**: Routes to Developer agent
5. **Update State**: Sets `current_step: "complete"`, increments Developer cycles

### Step 5: Complete Phase
1. **State Detection**: Confirms we're in "complete" step
2. **Cycle Check**: Verifies Tester agent hasn't exceeded 3 cycles
3. **Story Points Validation**: Confirms PRO-XXX has story points assigned (required for completion)
   - If missing → escalate to Product Owner, do NOT proceed to completion
   - If present → proceed to Tester agent
4. **Dispatch**: Routes to Tester agent via `complete-feature` skill
5. **Update State**: Sets `current_step: "done"`

## Agent Mapping

| Pipeline Step | Agent | Skill Trigger |
|---------------|-------|----------------|
| **Discover** | Product Owner | `discover-feature` |
| **Refine** | Product Owner | `refine-feature` |
| **Plan** | Architect | `develop-feature` (architect phase) |
| **Develop** | Developer | Direct execution |
| **Complete** | Tester | `complete-feature` (tester phase) |

## Cycle Tracking Rules

- **Max 3 cycles** per agent per pipeline
- **Reset on state change**: New PR ticket or manual reset
- **Escalation at cycle 3**: Notify Product Owner for evaluation
- **State persistence**: Cycle counts survive session restarts

## Escalation Protocol

If any agent exceeds 3 cycles:

1. **State Update**: Sets `escalation_level: 1`
2. **Blocker Detection**: Marks `blocked: true`
3. **Notification**: Sends update to Product Owner (or user)
4. **PO Evaluation**: Triggers `escalate-to-po` workflow
5. **Resolution Options**:
   - Reset the agent's cycles (new approach)
   - Pause the pipeline
   - Manual override by user

## State Commands

### Basic Commands

| Command | Purpose |
|---------|---------|
| `show state PRO-373` | Displays current pipeline state |
| `reset pipeline PRO-373` | Resets all cycles and state |
| `check cycles PRO-373` | Shows cycle counts |
| `escalate PRO-373` | Triggers escalation handling |

### Enhanced Commands (via `pipeline.py`)

The `pipeline.py` script provides enhanced pipeline management with
interrupted-pipeline detection, resume/continue/proceed, dry-run, and
history tracking. All commands are invoked via:

```bash
python .opencode/scripts/pipeline.py <command> <ticket> [options]
```

#### Resume / Continue / Proceed

| Command | Purpose |
|---------|---------|
| `resume PRO-373` | Resume pipeline at the current step (clears interruption flag) |
| `resume PRO-373 --force` | Force resume without validation |
| `continue PRO-373` | Advance to the next pipeline step |
| `continue PRO-373 --force` | Force advance without validation |
| `proceed PRO-373` | Proceed with current step execution |
| `proceed PRO-373 --force` | Force proceed without validation |

**When to use each:**
- **`resume`**: Pipeline was interrupted mid-step. Use to clear the
  interruption flag and attempt to complete the current step.
- **`continue`**: Current step is done. Use to advance to the next step
  (e.g., plan → develop).
- **`proceed`**: Same as `resume` but emphasizes continuing the current
  step's execution.

#### Inspection & Monitoring

| Command | Purpose |
|---------|---------|
| `what-missed PRO-373` | Show what work was missed in an interrupted pipeline |
| `check-stuck PRO-373` | Detect and alert on stuck pipelines |
| `dry-run PRO-373 <action>` | Preview action without executing |
| `history PRO-373` | Show pipeline history |

**What `what-missed` reveals:**
- Which step was interrupted
- How many cycles were expected vs. actually completed
- What work was supposed to be done in that step
- Whether the work is INCOMPLETE or COMPLETE

**What `check-stuck` detects:**
- Pipelines stuck in a step with 0 cycles
- Time since interruption (1h, 12h, 24h thresholds)
- Suggested next actions

**What `dry-run` does:**
- Simulates the action without modifying state
- Shows what would happen
- Useful for testing before committing

#### Mode Management

| Command | Purpose |
|---------|---------|
| `set-mode PRO-373 interactive` | Set development mode |
| `get-mode PRO-373` | Show persisted mode |

### Quick Reference: Pipeline Interruption Recovery

If a pipeline was interrupted (e.g., connection loss during agent
handoff), use this workflow:

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

## Integration with Other Skills

### Plan → Develop
The orchestration skill coordinates the transition:
1. Reads Architect's plan output
2. Validates completion of acceptance criteria
3. Updates state to "develop"
4. Routes to Developer agent

### Develop → Complete
Manages the handoff:
1. Reads Developer's PR/implementation output
2. Validates CI/test pass
3. Updates state to "complete"
4. Routes to Tester agent

### Complete → Done
Finalizes the pipeline:
1. Reads Tester's validation output
2. Updates state to "complete"
3. Routes to Tester agent
4. After user/PO confirmation, the agent-team executes the final closure
   (`atlassian_transitionJiraIssue` and `gh pr merge`) and verifies the
   JIRA ticket is in "Fertig" status and the PR is merged
5. Updates state to "done"

## Sample Interaction

**User**: "start feature PRO-373"

1. **Orchestration Skill**:
    - Reads JIRA for existing PRO-373
    - Initializes pipeline state
    - Routes to PO agent via `discover-feature` skill
    - Updates state: `current_step: "refine"`

**User**: "discover phase"

2. **PO Agent**:
    - Executes `discover-feature` skill
    - Drafts JIRA ticket (intention, goal, ACs, DoD, story points)
    - Returns to orchestration skill

**User**: "refine phase"

3. **PO Agent**:
    - Executes `refine-feature` skill
    - Conducts multi-stakeholder review (developer, architect, tester)
    - Holds common stakeholder review
    - Finalizes ticket
    - Returns to orchestration skill
    - Updates state: `current_step: "plan"`

**User**: "architect phase"

4. **Architect Agent**:
    - Executes `develop-feature` skill (architect phase)
    - Produces implementation plan
    - Returns to orchestration skill

5. **Orchestration Skill**:
    - Receives Architect output
    - Increments Architect cycle count
    - Updates state
    - Routes to Developer agent
    - Sets `current_step: "develop"`

**User**: "develop phase"

6. **Developer Agent**:
    - Implements feature
    - Opens PR
    - Returns to orchestration skill

7. **Orchestration Skill**:
    - Receives Developer output
    - Increments Developer cycle count
    - Updates state
    - Routes to Tester agent
    - Sets `current_step: "complete"`

**User**: "test phase"

8. **Tester Agent**:
    - Runs tests
    - Validates AC/DoD
    - Returns to orchestration skill

9. **Orchestration Skill**:
    - Receives Tester output
    - Increments Tester cycle count
    - Updates state
    - Sets `current_step: "done"`
    - Routes back to Product Owner for review

## State File Location

The pipeline state is stored in `~/.opencode/pipeline-state.json` (encrypted if enabled). This file contains:
- Cycle counts per agent
- Current pipeline step
- Escalation status
- Last update timestamps

## Security Considerations

1. **Permission Validation**: Only the Product Owner agent can invoke this skill
2. **State Isolation**: Each JIRA ticket has its own state entry
3. **Cycle Protection**: Hard limit prevents infinite loops
4. **Escalation Audit Trail**: All escalations are logged with user context

## Troubleshooting

### State Not Updating
- Check file permissions on `~/.opencode/pipeline-state.json`
- Verify the orchestration skill has write access
- Restart opencode if the state file is corrupted

### Agent Not Dispatching
- Verify the current step matches expected state
- Check if the agent is already in an error state
- Look for escalation flags that might be blocking

### Cycle Count Reset
- Manual reset: `reset pipeline PRO-xxx`
- State change: New JIRA ticket or PR reset
- Escalation override: User intervention

## Future Enhancements

1. **Pipeline Visualization**: Generate flow diagrams for complex pipelines
2. **Parallel Execution**: Support concurrent agent execution where safe
3. **Pipeline Templates**: Store and reuse pipeline configurations
4. **Metrics Collection**: Track cycle times and success rates
5. **Integration Hooks**: Connect to external CI/CD systems

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `.opencode/docs/WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `doc/CONTRIBUTING.md` — Development standards
- `doc/TESTING.md` — Test structure, test markers, test organization
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/orchestrate-feature/` — This skill
- `.opencode/skills/discover-feature/SKILL.md` — Feature discovery and ticket creation
- `.opencode/skills/refine-feature/SKILL.md` — Stakeholder review and finalization
- `.opencode/skills/develop-feature/SKILL.md` — Workflow for developing a feature
- `.opencode/skills/complete-feature/SKILL.md` — Workflow for closing a ticket
