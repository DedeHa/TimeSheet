# PRO-407 PM Notes

- **Ticket:** PRO-407 (PR #138). Handoff comments live in JIRA and are not copied here.
- **Mode:** automated (set for PRO-407 in `~/.opencode/pipeline-state.json`)

## Decisions

| # | Decision | Record |
|---|----------|--------|
| 1 | Artifact path is `docs/`, not `doc/`. The ticket paths are superseded. | ODR-0001, plan A.1 |
| 2 | The DoR gate is enforced in `develop-feature` before any code is written, and in code by `pipeline.py continue` into develop. | ODR-0001, plan A.1 |
| 3 | The implementation plan is deleted after merge (existing `AGENTS.md` rule). | ODR-0001, `docs/changes/README.md` rule 3 |
| 4 | Handoffs are recorded with `pipeline.py handoff`. The script renders the comment and the agent posts it, because the script has no JIRA client. | plan A.4 |
| 5 | **Scope (2026-11-11, user):** all features in ticket PRO-407 are in scope. The tracker-agnostic `workItemRef` (ticket Step 6) is implemented: `parse_work_item_ref` and the `handoff` command. This replaces the earlier decision to defer it. | plan B.4, B.6 gap 7 |
| 6 | **Scope (2026-11-11, user):** the adversarial readiness reviewer (ticket Step 3) is implemented as the `readiness-review` skill. This replaces the earlier decision to defer it. | plan B.4, B.6 gap 3 |
| 7 | The DoR waivers are recorded with `pipeline.py waive` (reason and owner required), not only in prose. | Section "DoR waivers" |

## DoR waivers

The `develop-feature` Step 1f gate was run for this change. Two items are waived for
PRO-407. The user, acting as Product Owner, gave the waiver in the automated run instruction.
The waivers are recorded here, and the commands below record the same waivers in the
pipeline state. They were not run against the shared state file during the
implementation round, so the Product Owner runs them once before closure:

```bash
python .opencode/scripts/pipeline.py waive PRO-407 D3 \
  --reason "The DoD closure items (PR merged, JIRA transition, plan deletion) cannot be filled before the PR exists; they are tracked in plan C.4." \
  --by "Product Owner (user)"
python .opencode/scripts/pipeline.py waive PRO-407 D4 \
  --reason "The user reviewed the ticket in the intake and confirmation step (decisions 1-6) instead of a full refine-feature round. Architect, Developer and Tester review happened inside the pipeline." \
  --by "Product Owner (user)"
```

- **D3 (Definition of Done has no unfilled placeholders): waived.** See the first command.
- **D4 (Stakeholder review): waived.** See the second command.

Other DoR checks (D1, D2, D5, D6, D7) pass. Story points are set to 8, the ACs are
testable (plan C.3), non-goals are in plan B.4, and there are no open drift signals.
The adversarial review of D1-D7 is recorded in the section below.

## Readiness review (adversarial)

Run with `.opencode/skills/readiness-review/SKILL.md` against the ticket text. The
review tried to refute each item. Verdicts:

| # | Verdict | Counter-evidence attempted | Source | Smallest fix (FAIL only) |
|---|---------|----------------------------|--------|--------------------------|
| D1 | PASS | Story points field is empty or zero | JIRA PRO-407, Story Points: 8 (plan C.4) | - |
| D2 | PASS | An AC without an observable check | Plan C.3 AC-1 to AC-6, each mapped to a V item | - |
| D3 | FAIL (waived) | DoD contains `PR #NNN`, `N tests`, `FR-XX` | JIRA description, Definition of Done | Waived above, because the closure items cannot exist before the PR |
| D4 | FAIL (waived) | No `refine-feature` round and no written stakeholder sign-off | Intake and confirmation step (decisions 1-6) | Waived above |
| D5 | PASS | Non-goals contradict an AC | JIRA Non-Goals, plan B.4 (now only multi-tool, autonomous loop, full 11-phase model, app code under `src/`) | - |
| D6 | PASS | Unresolved drift between ticket, plan and repository | Drift from the ticket text: docs path (`doc/` to `docs/`, decision 1) and the two scope changes (decisions 5 and 6) are recorded | - |
| D7 | PASS | Open decisions still in the text | Plan A.1 decisions 1-4 are resolved; decisions 5 and 6 are resolved above | - |

## Open items for user confirmation (not done by the agent team)

- Merge PR #138.
- Transition PRO-407 to Fertig.
- Run the two `waive` commands above against the shared pipeline state, or accept the waivers from this file.
- Delete `docs/PRO-407_Implementation_Plan.md` after merge.
- Delete remote branch `feature/PRO-407-agent-governance` after merge.
