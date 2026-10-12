# Agent Team Architecture

The Agent Team Architecture defines the organization, workflows, and validation patterns for the automated agent-team development pipeline that operates on top of the TimeSheetAlgo script project.

## System Context

The Agent Team Architecture operates at the project level, not the application level. It orchestrates the development of features, bug fixes, and documentation changes through a structured pipeline of specialized agents:

```
User → Product Owner (intake) → Architect → Developer → Tester → Product Owner (review) → User
```

This architecture is distinct from the TimeSheetAlgo application architecture (described in doc/ARCHITECTURE.md) and provides the meta-automation layer that coordinates the human-agent workflow.

## Core Components

### 1. Agent Team Structure

**Product Owner Agent (PO)**
- **Role**: Dispatcher and orchestrator of the entire feature pipeline
- **Primary responsibilities**:
  - Intakes user requests and extracts intent
  - Routes requests to correct agents (Architect, Developer, Tester)
  - Manages development mode (interactive/automated)
  - Coordinates handoffs between agents
  - Reviews completed work before final user agreement
  - Executes closure workflow via `complete-feature` skill

**Architect Agent**
- **Role**: Translates requirements into technical design
- **Primary responsibilities**:
  - Analyzes user stories and acceptance criteria
  - Defines system architecture and integration points
  - Produces structured implementation plans
  - Follows patterns from doc/ARCHITECTURE.md when relevant
  - Validates architectural decisions against existing codebase

**Developer Agent**
- **Role**: Implements features according to architectural plans
- **Primary responsibilities**:
  - Executes implementation phases (code, workflow, data, documentation)
  - Follows handoff protocols and commit conventions
  - Validates changes against quality gates
  - Reports progress and blockers to Product Owner

**Tester Agent**
- **Role**: Validates implementations against requirements
- **Primary responsibilities**:
  - Verifies acceptance criteria are met
  - Executes full test suite with coverage validation (≥90% gate)
  - Runs CI self-tests and traceability validation
  - Confirms code quality and documentation alignment
  - Provides pass/fail decision for Product Owner review

### 2. Pipeline Orchestration

The `orchestrate-feature` skill manages the entire feature lifecycle:

```
| Phase | Skill | Handoffs | Max Cycles |
|-------|--------|----------|------------|
| intake-handoff | discover-feature | PO → architect | 3 |
| ticket-creation | discover-feature | architect → refine-feature | 3 |
| story-points-estimation | discover-feature | refine-feature → develop-feature | 3 |
| sprint-placement | discover-feature | develop-feature → developer | 3 |
| prepare-branch | develop-feature | developer → architect | 3 |
| implement-rollout | develop-feature | architect → developer | 3 |
| final-verification | develop-feature | developer → tester | 3 |
| open-pr | develop-feature | tester → PO | 3 |
```

### 3. Skill-Based Workflow

**Specialized skills** define how each agent performs their role:

#### `discover-feature` skill
- Purpose: Create JIRA tickets from user requests
- Manages: Story drafting, acceptance criteria definition, story points, sprint placement
- Loads: Always (Phase 1 of feature discovery)
- Cycles: max 3

#### `refine-feature` skill
- Purpose: Stakeholder review and ticket finalization
- Manages: Multi-stakeholder validation, implementation planning, finalization
- Loads: After-refine (Phase 2 only)
- Cycles: max 3

#### `develop-feature` skill
- Purpose: Implement features according to architectural plans
- Manages: Branch preparation, implementation rollout, verification, PR creation
- Loads: After-refine (Phase 2 only)
- Cycles: max 3

#### `orchestrate-feature` skill
- Purpose: Central orchestrator for complete pipeline
- Manages: All phases from state detection to handoff coordination
- Loads: Always
- Cycles: max 3

#### `complete-feature` skill
- Purpose: Verify ACs, update JIRA ticket, checkmark PR description
- Manages: Final verification, evaluation, preparation, closure
- Loads: After-testing

### 4. Development Mode Patterns

The Product Owner detects development mode from user chat patterns and persists them in `~/.opencode/pipeline-state.json`:

```json
{
  "PRO-373": {
    "development_mode": "interactive",
    ...
  }
}
```

#### Interactive Mode
- **Behavior**: User confirmation before each handoff
- **Handoff process**:
  1. PO presents deliverable summary and current state
  2. PO asks: "Proceed to next stage?"
  3. On "yes": continue to next agent
  4. On "no": return to previous agent for fixes
  5. On blocker/cycle limit (3): escalate immediately

#### Automated Mode
- **Behavior**: Direct dispatch without user pauses
- **Handoff process**:
  1. Each handoff includes full deliverable and state
  2. Next agent receives all context and proceeds immediately
  3. Escalation still triggers on blockers or cycle limit (3)

### 5. Quality Gates and Validation

#### CI Gates
- **Traceability script**: Exits non-zero if any requirement is missing from architecture or implementation references
- **Test suite**: Full test suite with coverage threshold (≥90%)
- **Naming validation**: CI blocks merge entirely for naming violations

#### Agent-Level Validation
- **Architect**: Must reference doc/ARCHITECTURE.md patterns, minimize complexity
- **Developer**: Must follow CONTRIBUTING.md, add tests per TESTING.md, reference PRO ticket
- **Tester**: Must verify ACs, run CI self-tests, check traceability matrix

### 6. Escalation Protocol

The Product Owner monitors all agent cycles and escalates when:

1. **An agent cannot resolve an issue** → immediate evaluation (no cycle limit)
2. **The pipeline exceeds 3 cycles** → agent stops, reports to PO
3. **The process loops** → agent repeats same action without progress

## Architecture Decisions

### 1. Agent Team vs. Application Architecture

**Agent Team Architecture** (`.opencode/agents/`):
- Focuses on **development process**, **workflow**, and **validation**
- Defines **how** work is coordinated and quality is ensured
- Operates **above** the TimeSheetAlgo application layer
- Concerned with **human-agent interaction**, **code review**, **testing**

**Application Architecture** (`doc/ARCHITECTURE.md`):
- Focuses on **system design**, **component structure**, and **data flow**
- Defines **how** TimeSheetAlgo works internally
- Operates **below** the agent layer as the implementation target
- Concerned with **technical architecture**, **configuration**, **runtime behavior**

### 2. Separation of Concerns

**Agent Team Level** (`.opencode/agents/`):
- Software development process automation
- Human-agent workflow coordination
- Quality validation and enforcement
- Project governance and review

**Application Level** (`doc/ARCHITECTURE.md`):
- System design and implementation
- Technical architecture and data modeling
- Runtime behavior and error handling
- Configuration and deployment

### 3. Reference Patterns

Agent team components reference application architecture patterns:

```
 Architect → References patterns from `doc/ARCHITECTURE.md`
    ↓
    Ensures designs align with existing codebase constraints
    ↓
    Maps changes to specific implementation files in TimeSheetAlgo
```

## Key Files and References

### Agent Team Architecture Files
- `.opencode/docs/ARCHITECTURE.md` (this document)
- `.opencode/docs/REQUIREMENTS.md` (agent team requirements)
- `.opencode/agents/architect.agent.md` (architect agent definition)
- `.opencode/agents/developer.agent.md` (developer agent definition)
- `.opencode/agents/product-owner.agent.md` (product owner agent definition)
- `.opencode/agents/tester.agent.md` (tester agent definition)

### Skill Definitions
- `.opencode/skills/discover-feature/SKILL.md` (feature discovery)
- `.opencode/skills/refine-feature/SKILL.md` (stakeholder review)
- `.opencode/skills/develop-feature/SKILL.md` (feature implementation)
- `.opencode/skills/orchestrate-feature/SKILL.md` (pipeline orchestration)
- `.opencode/skills/complete-feature/SKILL.md` (feature closure)

### Cross-References
- **From**: `.opencode/docs/REQUIREMENTS.md` → `.opencode/skills/complete-feature/SKILL.md`
- **From**: `architect.agent.md` → `doc/ARCHITECTURE.md` (pattern references)
- **From**: `product-owner.agent.md` → `AGENTS.md` (top-level workflow)
- **From**: CI scripts → `.opencode/docs/REQUIREMENTS.md` (agent-team quality gates)

## Design Principles

### 1. Sequential Approval

All features must follow this sequence without bypass:

1. **User → Product Owner** (intake and intake conversation)
2. **Product Owner → Architect** (initial architecture review)
3. **Architect → Developer** (implementation approval)
4. **Developer → Tester** (validation approval)
5. **Tester → Product Owner** (test validation review)
6. **Product Owner → User** (final agreement and closure)

### 2. Mode-Detection from Chat

The Product Owner parses user chat for mode keywords:

**Automated mode keywords**: "run automated", "run automated mode", "go ahead", "proceed", "without confirmation", "no pauses"

**Interactive mode keywords**: "run interactive", "run interactive mode", "pause", "confirm", "ask me", "stop between steps"

### "3-Cycle Limitation

**Default Constraint**: Each agent pipeline has maximum 3 cycles:

- **Cycle 1**: Initial attempt
- **Cycle 2**: Minor correction
- **Cycle 3**: Last chance for resolution

**Escalation Triggers**:
- Agent reports a **blocker** (immediate PO evaluation)
- Cycle count reaches **3** (agent stops and escalates)
- Agent **loops** (same action repeated without progress)

## Quality Gates Summary

| Gate | Location | Validation | Result |
|------|----------|------------|--------|
| Naming validation | CI check | Commit message format, PR title, PR body | Blocks merge |
| Traceability matrix | CI script | All requirements traced to architecture/code | Non-zero exit |
| Coverage threshold | CI + test suite | ≥90% combined coverage | Gates PR merge |
| CI self-tests | CI test suite | `pytest -q tests/ci-pipeline/` | Must pass |
| Architecture alignment | Agent validation | References doc/ARCHITECTURE.md patterns | Pass/fail decision |
| Code quality | CI linting + CI lint checks | ruff, black, pydocstyle, radon | Must pass |

## Integration with Application Architecture

The Agent Team Architecture integrates with TimeSheetAlgo architecture through:

1. **Reference patterns**: Architect agents reference `doc/ARCHITECTURE.md`
2. **Implementation targeting**: All changes target specific files in TimeSheetAlgo
3. **Quality gate validation**: CI tests validate changes align with existing patterns
4. **Cross-file traceability**: Requirements ID mapping from agent team to application files

## Usage and Documentation

### For Users

This architecture document explains:
- How the agent-team pipeline works
- What agents are available and their roles
- How to set up development mode
- What validation gates are enforced
- How to escalate issues when they occur

### For Developers

This architecture document explains:
- How to follow agent-team patterns
- What architectural decisions are enforced
- How to reference application architecture correctly
- What validation is expected during implementation

### For Architects

This architecture document explains:
- How to design solutions that follow agent-team patterns
- What constraints and quality gates are enforced
- How to map agent-team requirements to application architecture
- How to validate architectural decisions against existing patterns

---

## Key Differentiators from TimeSheetAlgo Architecture

1. **Focus**: Development process automation vs. application design
2. **Scope**: Meta-automation layer vs. application layer
3. **Validation**: Process and quality gates vs. technical correctness
4. **References**: doc/ARCHITECTURE.md patterns vs. direct implementation
5. **Role**: Orchestrator and validator vs. application developer

This separation allows the TimeSheetAlgo project to maintain a clear distinction between:
- **HOW** the project develops (Agent Team Architecture)
- **WHAT** the project builds (TimeSheetAlgo Application Architecture)

Both architectures work together: the Agent Team Architecture ensures quality development processes, while the TimeSheetAlgo Application Architecture defines the technical implementation targets.
