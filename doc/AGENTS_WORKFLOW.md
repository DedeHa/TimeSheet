# opencode Agent Workflow Reference

This is the detailed operational reference for the opencode agent team. The
user-facing overview, interaction model, and top-level workflow are in
[AGENTS.md](../AGENTS.md). This document is the source for understanding how
the agents, skills, scripts, state files, and validation policies connect.

## Canonical Workflow Contract

The runtime in `.opencode/scripts/pipeline.py` is the authoritative source of truth
for workflow state, transitions, interruption recovery, and handoff payload
generation.

The canonical lifecycle is:

```text
backlog -> plan -> develop -> complete -> approved -> released
```

Agent and skill documents repeat this contract as operational guardrails. The
policy tests fail when an agent or skill omits or changes the lifecycle.

## Repository Components

```text
.opencode/
├── agents/                  role definitions and skill bindings
├── skills/                  task-specific operating procedures
├── scripts/                 runtime, migration, mode, and validation tools
├── pipeline-state.json      project-local ticket state
└── pipeline-history.json    transition and action history

.opencode/tests/agents/      agent, skill, and workflow policy tests
.opencode/tests/scripts/     runtime and support-script tests
AGENTS.md                    user-facing project and interaction guide
doc/AGENTS_WORKFLOW.md       this detailed operational reference
```

## Agents

The four agents are defined in `.opencode/agents/`:

| Agent | Responsibility | Main bindings |
|---|---|---|
| `product-owner.agent.md` | intake, prioritization, mode, orchestration, approval | `orchestrate-feature`, `plan-feature`, `develop-feature`, `complete-feature` |
| `architect.agent.md` | architecture review and implementation planning | `develop-feature` |
| `developer.agent.md` | implementation, tests, and development handoff | `develop-feature`, `complete-feature` |
| `tester.agent.md` | acceptance validation and evidence-based approval or fixes | `complete-feature` |

Every agent must:

- follow the canonical lifecycle
- respect runtime transition validation
- preserve the current ticket and handoff context
- stop on blockers or failed gates
- use the referenced skill rather than inventing a parallel process

## Skills

The five skills in `.opencode/skills/` provide the operating procedures:

| Skill | Purpose | Primary owner |
|---|---|---|
| `plan-feature` | requirements, Jira story, acceptance criteria, estimate | Product Owner |
| `orchestrate-feature` | state detection, dispatch, cycle tracking, escalation, handoffs | Product Owner |
| `develop-feature` | architecture handoff, implementation, tests, developer handoff | Architect / Developer |
| `complete-feature` | validation, acceptance criteria, DoD, closure preparation | Tester / Product Owner |
| `release-project` | release readiness, versioning, release notes, publication | Product Owner |

Skills are loaded through agent frontmatter. They are not independent
lifecycles: each skill operates within the canonical state machine and must
use the runtime for state-sensitive decisions.

## Test Organization

Tests are stored with the subsystem they validate:

| Test directory | Coverage |
|---|---|
| `.opencode/tests/agents/` | agent definitions, skill bindings, handoffs, constraints, outputs, and workflow policy |
| `.opencode/tests/scripts/` | pipeline runtime and mode-detection script behavior |
| `.github/tests/ci-pipeline/` | GitHub Actions workflow structure and CI support scripts |

The GitHub Actions `Agent System Tests` job executes both opencode test
directories, but their ownership remains under `.opencode/`.

## Scripts

All operational scripts live in `.opencode/scripts/` and are invoked from the
repository root.

| Script | Responsibility | Consumers / dependencies |
|---|---|---|
| `.opencode/scripts/pipeline.py` | state machine, transitions, recovery, history, handoff payloads | all stateful agents and skills; calls migration when needed |
| `.opencode/scripts/detect_mode.py` | parses user language and persists interactive/automated mode | Product Owner and `orchestrate-feature`; uses migration when state is absent |
| `.opencode/scripts/migrate_pipeline_state.py` | moves or merges legacy home state into project-local state | `pipeline.py` and `detect_mode.py`; used during migration |
| `.opencode/scripts/verify_migration.py` | checks preservation of migrated ticket data and optional checksums | migration validation and release/change-management checks |
| `.opencode/scripts/pre_closure_validation.py` | validates PR, repository, pipeline, plan, and cross-system closure conditions | completion/release gate before Jira closure |

### Script dependency flow

```text
User message
    │
    ▼
.opencode/scripts/detect_mode.py ───────────────┐
    │                         │
    └─ migrate_pipeline_state ─┤
                              ▼
                         pipeline.py
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       state/history     handoff payload   recovery checks
                              │
                              ▼
                 .opencode/scripts/pre_closure_validation.py
                              │
                              ▼
                    .opencode/scripts/verify_migration.py
```

`pipeline.py` and `detect_mode.py` use project-local state at
`.opencode/pipeline-state.json`. Migration is idempotent and preserves the
project-local entry when old and new state overlap. Validation scripts read
state and repository metadata but do not define a second lifecycle.

## Runtime State Machine

The runtime declares these canonical states:

| State | Meaning | Valid next state |
|---|---|---|
| `backlog` | request exists but is not ready | `plan` |
| `plan` | requirements and implementation plan are prepared | `develop`, `blocked` |
| `develop` | implementation is in progress | `complete`, `blocked` |
| `complete` | implementation is validated and closure is being prepared | `approved`, `blocked` |
| `approved` | review and validation have passed | `released` |
| `released` | work is published and closed | none |
| `blocked` | work cannot safely proceed | `plan`, `develop`, `complete` |

`PIPELINE_STEPS` tracks the working cycles (`plan`, `develop`, `complete`);
`CANONICAL_STATES` tracks the full lifecycle. A transition is invalid when
the current state does not allow it or the current cycle has not completed.

## Handoffs and Escalation

Every handoff should carry:

- ticket
- current step and workflow state
- development mode
- evidence or output
- cycle counts
- blockers and escalation status
- required next step
- requested human or Product Owner decision

Normal path:

```text
Product Owner -> Architect -> Developer -> Tester -> Product Owner
```

Typical labels:

- `Request Architecture Review`
- `Start Implementation`
- `Start Testing & Validation`
- `Request Fixes`
- `Approve & Complete`
- `Final Review`

Interactive mode pauses at handoffs. Automated mode continues only while
runtime validation, quality gates, and cycle limits pass.

## Recovery and Migration

For an interrupted ticket:

```bash
python .opencode/scripts/pipeline.py what-missed PRO-123
python .opencode/scripts/pipeline.py check-stuck PRO-123
python .opencode/scripts/pipeline.py dry-run PRO-123 resume
python .opencode/scripts/pipeline.py resume PRO-123
```

For legacy state migration:

```bash
python .opencode/scripts/migrate_pipeline_state.py
python .opencode/scripts/verify_migration.py
python .opencode/scripts/verify_migration.py --checksum
```

Migration must be idempotent. The verification script reports missing or
corrupted ticket entries and returns a non-zero status when preservation
fails.

## Pre-Closure Validation

Before Jira closure, `pre_closure_validation.py` checks:

1. PR merge status
2. pipeline state
3. implementation plan lifecycle
4. repository consistency
5. cross-system closure conditions

Typical invocation:

```bash
python -m pre_closure_validation PRO-123 456
python -m pre_closure_validation PRO-123 456 --verbose
```

The Product Owner must obtain the required user confirmation before
irreversible merge, Jira transition, branch deletion, or implementation-plan
deletion actions.

## Frontmatter and Binding Rules

Agent frontmatter is the binding layer between opencode and the skills. It
declares agent names, constraints, skill paths, invocation behavior, and
phase ordering. A skill reference must point to the existing
`.opencode/skills/<name>/SKILL.md` file.

The Product Owner is the orchestration entry point. Architect, Developer, and
Tester receive work through the handoffs defined by the Product Owner and the
orchestrator skill.

## Documentation Governance

Documentation responsibilities are intentionally separated:

- `AGENTS.md` — user intent, interaction examples, top-level lifecycle,
  setup, testing, and repository conventions
- `doc/AGENTS_WORKFLOW.md` — agent, skill, script, dependency, state-machine,
  handoff, migration, and validation details
- `.opencode/scripts/pipeline.py` — executable source of truth
- `.opencode/tests/agents/` — regression policy for agents, skills, and
  documentation
- `.opencode/tests/scripts/` — regression tests for opencode scripts

When prose and runtime behavior differ, update the prose to match the
runtime. Do not create a second lifecycle in a skill or script document.

## Validation Policy

The agent policy suite must verify:

- every agent contains the canonical lifecycle
- every skill contains the canonical lifecycle
- all five operational scripts are documented
- script dependency references point to existing files
- AGENTS.md remains user-facing and AGENTS_WORKFLOW.md remains operational
- runtime transitions and recovery behavior remain valid

Run the complete policy suite with:

```bash
python -m pytest .opencode/tests/agents .opencode/tests/scripts -q
```
