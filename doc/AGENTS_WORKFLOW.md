# AGENTS_WORKFLOW.md

This file is the detailed operational reference for the opencode agent team. It complements [AGENTS.md](../AGENTS.md), which is the concise project index and quick-start guide.

The runtime in `.opencode/scripts/pipeline.py` remains the authoritative source of truth for workflow state, transition validation, interruption recovery, and handoff payload generation.

## Canonical Workflow Contract

The canonical lifecycle for every agent, skill, and operational doc is:

`backlog -> plan -> develop -> complete -> approved -> released`

This is the only lifecycle contract used by the project workflow. Shortened phrases such as `Plan -> Develop -> Complete` are acceptable only as shorthand when they are clearly tied back to the full canonical lifecycle and do not contradict the runtime state machine.

## Workflow Purpose

The workflow exists to coordinate four roles:

- Product Owner: intake, planning, approval, release gates
- Architect: design and implementation plan review
- Developer: implementation and quality-focused coding
- Tester: validation, evidence, and approval or fix requests

## Lifecycle and State Model

The canonical flow is:

```text
backlog -> plan -> develop -> complete -> approved -> released
```

Operationally, it is implemented as a state-driven pipeline with the following expectations:

1. backlog — no work is actively scheduled or accepted
2. plan — requirements, acceptance criteria, and sprint scope are prepared
3. develop — implementation work is underway under an approved plan
4. complete — implementation is done and validated, but not yet approved for release
5. approved — review and validation are complete and handoff is ready
6. released — the work is published, merged, or otherwise closed to production

The runtime script validates transitions, normalizes states, detects interruptions, and supports resume/continue workflows. Markdown documentation must stay consistent with these states even when it summarizes them more tersely.

## Agent Team Structure

```text
Product Owner
  ├─ intake and requirements
  ├─ lifecycle governance
  ├─ mode selection / interruption handling
  └─ final approval and release gate

Architect
  ├─ system design and architecture plan
  ├─ acceptance criteria alignment
  └─ implementation readiness assessment

Developer
  ├─ feature implementation
  ├─ test coverage and code quality
  └─ evidence for validation

Tester
  ├─ validation run
  ├─ defect reporting and fix requests
  └─ approval or rejection evidence
```

## Orchestration Rules

The orchestrator runs the feature lifecycle through defined states rather than ad hoc transitions.

### Required control points

- Mode must be explicit: automated or interactive
- Interrupted flows must be detected and resumed using pipeline commands
- The current state must be validated before advancing to the next stage
- Handoffs must include the relevant evidence, constraints, and expected next action

### Supported pipeline commands

```bash
python .opencode/scripts/pipeline.py show state PRO-373
python .opencode/scripts/pipeline.py what-missed PRO-373
python .opencode/scripts/pipeline.py resume PRO-373
python .opencode/scripts/pipeline.py continue PRO-373
python .opencode/scripts/pipeline.py proceed PRO-373
python .opencode/scripts/pipeline.py check-stuck PRO-373
python .opencode/scripts/pipeline.py dry-run PRO-373 <action>
python .opencode/scripts/pipeline.py history PRO-373
python .opencode/scripts/pipeline.py reset PRO-373
python .opencode/scripts/pipeline.py set-mode PRO-373 automated
python .opencode/scripts/pipeline.py get-mode PRO-373
```

## Handoff Contract

Each agent handoff should include the same minimum structure:

- current state
- evidence or output produced
- blocking issue or approval decision
- next expected stage
- required human or PO decision, if any

Typical handoff flow:

```text
PO -> Architect -> Developer -> Tester -> PO
```

Example labels:

- `Request Architecture Review`
- `Start Implementation`
- `Start Testing & Validation`
- `Request Fixes`
- `Approve & Complete`
- `Final Review`

## Quality Gates

The project enforces quality gates across the workflow:

- planning must define acceptance criteria and scope
- architecture must be reviewed before implementation proceeds
- developer work must be code-complete and testable
- tester validation must produce evidence-based results
- PO approval must be explicit before release completion
- runtime state must be consistent with the documented lifecycle

## Relationship to Agents and Skills

This document is the deeper workflow explanation. The runtime and agent frontmatter documents are operational hooks, while the skill files describe how a given task should be performed within this lifecycle.

The canonical workflow is enforced in:

- `.opencode/scripts/pipeline.py` — authoritative lifecycle and transition logic
- `.opencode/agents/*.agent.md` — role-level constraints and policy language
- `.opencode/skills/*/SKILL.md` — workflow-specific task guidance
- `AGENTS.md` — overview and quick-start guidance

## Rollout and Change Management

The project uses a simple staged rollout model for workflow changes:

1. Stage 1 — document the canonical lifecycle and current runtime contract
2. Stage 2 — align agent and skill wording with the same lifecycle
3. Stage 3 — validate the pipeline and recovery behavior in tests
4. Stage 4 — ship the change with documentation and explicit migration notes if needed

This makes workflow changes predictable and keeps tooling, docs, and agent behavior synchronized.

## Validation Expectations

The workflow is not considered complete unless the project checks the following:

- agent files share the same lifecycle wording
- skill files reference the same canonical lifecycle
- runtime state transitions remain valid
- documentation does not drift into conflicting phase names
- interrupted workflows have explicit recovery paths

## Summary

This file is intentionally the detailed workflow reference. It defines the project’s operational contract for the agent team while [AGENTS.md](../AGENTS.md) remains the entry point and quick-start document. The runtime remains the final authority for enforcement, but all docs should express the same lifecycle and governance story.
