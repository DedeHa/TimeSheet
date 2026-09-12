---
name: orchestrate-feature
description: "Orchestrates the complete feature pipeline: reads JIRA state, tracks cycles, dispatches to Architect/Developer/Tester, handles escalations, and coordinates handoffs. Use when starting a feature (PRO-xxxx) or when the pipeline needs rebalancing. NOTE: Story points must be assigned before development pickup or sprint inclusion."
---

# Orchestrate Feature Pipeline

## Overview

The `orchestrate-feature` skill is the central orchestrator that coordinates
the entire feature pipeline. It lives in the Product Owner agent and manages
the flow from **Plan → Develop → Complete**, with built-in cycle tracking,
state management, and escalation handling.

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

## Pipeline Flow

### Step 1: Plan Phase
1. **State Detection**: Checks JIRA for existing PRO-xxxx ticket
2. **Cycle Check**: Verifies Architect agent hasn't exceeded 3 cycles
3. **Dispatch**: Routes to Architect agent via `develop-feature` skill
4. **Update State**: Sets `current_step: "develop"`, increments Architect cycles

### Step 2: Develop Phase
1. **State Detection**: Confirms we're in "develop" step
2. **Cycle Check**: Verifies Developer agent hasn't exceeded 3 cycles
3. **Story Points Validation**: Confirms PRO-XXX has story points assigned (required for development)
   - If missing → escalate to Product Owner, do NOT proceed to development
   - If present → proceed to Developer agent
4. **Dispatch**: Routes to Developer agent
5. **Update State**: Sets `current_step: "complete"`, increments Developer cycles

### Step 3: Complete Phase
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

| Command | Purpose |
|---------|---------|
| `show state PRO-373` | Displays current pipeline state |
| `reset pipeline PRO-373` | Resets all cycles and state |
| `check cycles PRO-373` | Shows cycle counts |
| `escalate PRO-373` | Triggers escalation handling |

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
   - Routes to Architect agent
   - Updates state: `current_step: "plan"`

**User**: "architect phase"

2. **Architect Agent**:
   - Executes `develop-feature` skill (architect phase)
   - Produces implementation plan
   - Returns to orchestration skill

3. **Orchestration Skill**:
   - Receives Architect output
   - Increments Architect cycle count
   - Updates state
   - Routes to Developer agent
   - Sets `current_step: "develop"`

**User**: "develop phase"

4. **Developer Agent**:
   - Implements feature
   - Opens PR
   - Returns to orchestration skill

5. **Orchestration Skill**:
   - Receives Developer output
   - Increments Developer cycle count
   - Updates state
   - Routes to Tester agent
   - Sets `current_step: "complete"`

**User**: "test phase"

6. **Tester Agent**:
   - Runs tests
   - Validates AC/DoD
   - Returns to orchestration skill

7. **Orchestration Skill**:
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
