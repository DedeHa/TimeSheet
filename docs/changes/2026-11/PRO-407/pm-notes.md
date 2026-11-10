# PRO-407 PM Notes

- **Ticket:** PRO-407 (PR #138). Handoff comments live in JIRA and are not copied here.
- **Mode:** automated (set for PRO-407 in `~/.opencode/pipeline-state.json`)

## Decisions

| # | Decision | Record |
|---|----------|--------|
| 1 | Artifact path is `docs/`, not `doc/`. The ticket paths are superseded. | ODR-0001, plan A.1 |
| 2 | The DoR gate is enforced in `develop-feature` before any code is written. | ODR-0001, plan A.1 |
| 3 | The implementation plan is deleted after merge (existing `AGENTS.md` rule). | ODR-0001, `docs/changes/README.md` rule 3 |
| 4 | Handoffs are recorded with `pipeline.py handoff`. The script renders the comment and the agent posts it, because the script has no JIRA client. | plan A.4 |
| 5 | Tracker-agnostic `workItemRef` (ticket Step 6) is out of the agreed ACs and is a follow-up, not part of this PR. | plan B.4 |
| 6 | The adversarial readiness reviewer for DoR is a follow-up, not part of this PR. | plan B.4 |

## DoR waivers

The `develop-feature` Step 1f gate was run for this change. Two items are waived for
PRO-407. The user, acting as Product Owner, gave the waiver in the automated run instruction.

- **D3 (Definition of Done has no unfilled placeholders): waived.** The DoD contains
  closure items that cannot be filled before the PR exists (PR merged, JIRA transition,
  plan deletion). These are tracked in the plan's C.4 and the final review, not by placeholders.
- **D4 (Stakeholder review): waived.** The ticket was reviewed by the user in the intake
  and confirmation step (decisions 1–4 above) instead of a full `refine-feature` round.
  Architect, Developer, and Tester review happened inside the pipeline (this change).

Other DoR checks (D1, D2, D5, D6, D7) pass. Story points are set to 8, the ACs are
testable (plan C.3), non-goals are in plan B.4, and there are no open drift signals.

## Open items for user confirmation (not done by the agent team)

- Merge PR #138.
- Transition PRO-407 to Fertig.
- Delete `docs/PRO-407_Implementation_Plan.md` after merge.
- Delete remote branch `feature/PRO-407-agent-governance` after merge.
