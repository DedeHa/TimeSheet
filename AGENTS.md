# TimeSheetAlgo User and Project Guide

This is the user-facing entry point for the repository. It explains the
project, the top-level development workflow, the interaction modes, and the
commands users need to start or monitor work.

The detailed opencode implementation reference is in
[doc/AGENTS_WORKFLOW.md](doc/AGENTS_WORKFLOW.md). That document contains the
agent, skill, script, dependency, handoff, and runtime details.

## Table of Contents

- [Quick Setup](#quick-setup)
- [User Interaction Model](#user-interaction-model)
- [Top-Level Workflow](#top-level-workflow)
- [Development Modes](#development-modes)
- [User Pipeline Commands](#user-pipeline-commands)
- [Testing and Quality Checks](#testing-and-quality-checks)
- [Project Architecture](#project-architecture)
- [Git and Pull Request Conventions](#git-and-pull-request-conventions)
- [Configuration and Environment](#configuration-and-environment)
- [File System and Runtime Notes](#file-system-and-runtime-notes)
- [Where to Find Operational Details](#where-to-find-operational-details)

## Quick Setup

Install the project with development dependencies:

```bash
python -m pip install -e .[dev]
```

Activate the repository virtual environment:

```bash
source /workspaces/TimeSheet/.venv/bin/activate
echo "venv: $VIRTUAL_ENV"
```

Run commands from the repository root:

```bash
cd /workspaces/TimeSheet
```

## User Interaction Model

Users can interact with the team in natural language. Typical requests are:

- “Plan a feature for PRO-123.”
- “Start development on PRO-123.”
- “Run in automated mode.”
- “Run in interactive mode.”
- “Resume PRO-123.”
- “Validate the implementation.”
- “Prepare PRO-123 for release.”

Every feature follows the canonical lifecycle:

```text
backlog -> plan -> develop -> complete -> approved -> released
```

The lifecycle is enforced by the project runtime. Users should not ask an
agent to skip a required gate; instead, resolve the reported blocker or use
the documented recovery command.

## Top-Level Workflow

1. **Backlog** — identify the request and confirm its goal.
2. **Plan** — define the user story, acceptance criteria, scope, and estimate.
3. **Develop** — implement the approved plan and add or update tests.
4. **Complete** — validate the implementation against the acceptance criteria.
5. **Approved** — review the evidence and authorize closure or release.
6. **Released** — merge, publish, and close the completed work.

The normal collaboration path is:

```text
User -> Product Owner -> Architect -> Developer -> Tester -> Product Owner -> User
```

The Product Owner coordinates the process. The user is asked for
confirmation when the selected mode requires it and before irreversible
closure or release actions.

## Development Modes

### Interactive mode

Interactive mode pauses at handoff points and asks for confirmation before the
next agent proceeds. Use it when you want to inspect plans, implementation
scope, test evidence, or release decisions.

### Automated mode

Automated mode proceeds through valid handoffs without pausing. It still stops
for blockers, failed validation, invalid transitions, missing requirements, or
cycle limits.

Mode can be selected in a conversation:

```text
Run in automated mode
Run in interactive mode
```

If no mode is stated, interactive mode is used by default.

## User Pipeline Commands

Run these commands from the repository root:

```bash
python .opencode/scripts/detect_mode.py PRO-123 "Run in automated"
python .opencode/scripts/detect_mode.py PRO-123 --show

python .opencode/scripts/pipeline.py show state PRO-123
python .opencode/scripts/pipeline.py what-missed PRO-123
python .opencode/scripts/pipeline.py check-stuck PRO-123
python .opencode/scripts/pipeline.py dry-run PRO-123 resume
python .opencode/scripts/pipeline.py resume PRO-123
python .opencode/scripts/pipeline.py continue PRO-123
python .opencode/scripts/pipeline.py proceed PRO-123
python .opencode/scripts/pipeline.py history PRO-123
python .opencode/scripts/pipeline.py set-mode PRO-123 interactive
python .opencode/scripts/pipeline.py get-mode PRO-123
```

Use `what-missed`, `check-stuck`, and `dry-run` before resuming an interrupted
workflow. Do not edit pipeline state manually unless migration or recovery
instructions explicitly require it.

## Testing and Quality Checks

Fast project validation:

```bash
python -m pytest -m "not system"
```

Focused agent-team validation:

```bash
python -m pytest .opencode/tests/agents .opencode/tests/scripts -q
```

Full test and quality checks:

```bash
python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing
ruff check src_timesheetalgo tests
black --check src_timesheetalgo tests
pydocstyle src_timesheetalgo tests
radon cc src_timesheetalgo -a
python .github/scripts/generate_traceability_matrix.py
```

System tests may be skipped when their real workbook or extract fixtures are
not present.

## Project Architecture

- `src_timesheetalgo/` — primary application package
- `src_azesheetalgo/` — separate AZE sheet functionality
- `.opencode/` — agent-team runtime configuration and state
- `.opencode/tests/agents/` — agent setup and workflow policy tests
- `.opencode/tests/scripts/` — tests for opencode runtime and support scripts
- `doc/` — project documentation and implementation references

## Git and Pull Request Conventions

- Feature branches use `feature/PRO-123-description`.
- Bug fixes use `bugfix/PRO-123-description` or `hotfix/PRO-123-description`.
- Pull requests target `master`.
- Commit format is `type(scope): description`.
- Include `Refs: PRO-123` when a Jira ticket exists.
- Pull request bodies include `## Summary`, `## Testing`, and the Jira
  reference.
- Do not merge or delete remote branches without the required user or
  Product Owner confirmation.

See [doc/CONTRIBUTING.md](doc/CONTRIBUTING.md) for the complete repository
contribution and naming rules.

## Configuration and Environment

- `year` is required at the root of `src_timesheetalgo/config.yaml`.
- Paths are relative to the project root.
- Development and production environments are detected from the folder
  structure, not from a configuration flag.
- The default fallback environment is development.

## File System and Runtime Notes

- Pipeline state is stored in `.opencode/pipeline-state.json`.
- Pipeline history is stored in `.opencode/pipeline-history.json`.
- Close Excel files before running workflows that update workbooks.
- Configuration and pipeline commands must be run from the repository root.
- File I/O warnings may be recoverable; configuration and consistency errors
  must be addressed before proceeding.

## Where to Find Operational Details

Use [doc/AGENTS_WORKFLOW.md](doc/AGENTS_WORKFLOW.md) for:

- the complete agent and skill catalog
- script responsibilities and dependencies
- state-machine implementation details
- handoff payloads and escalation rules
- migration and pre-closure validation
- opencode frontmatter and binding conventions
- workflow policy tests and documentation governance

Use [doc/CONTRIBUTING.md](doc/CONTRIBUTING.md) for Git, branch, commit, pull
request, and release policy.
