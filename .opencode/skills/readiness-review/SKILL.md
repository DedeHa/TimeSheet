---
name: readiness-review
description: "Adversarial readiness review for a JIRA ticket before development. Tries to REFUTE each Definition of Ready item D1-D7 with concrete counter-evidence and records PASS or FAIL per item in the ticket's pm-notes. Use from develop-feature Step 1f and refine-feature finalization. Triggers on requests to 'readiness review', 'DoR review', 'challenge the ticket', 'adversarial review', or 'is this ready for development'."
---

# Readiness Review (Adversarial DoR Reviewer)

## Purpose

The Definition of Ready (DoR) gate in `develop-feature` Step 1f checks seven items
(D1-D7) before any code is written. A checklist that is filled in by the team that
wrote the ticket tends to confirm itself. This skill adds a reviewer whose job is to
**refute** each item. An item passes only when the refutation attempt fails.

This implements the adversarial readiness reviewer from PRO-407 (ticket Step 3).

## When to Run

- In `develop-feature` Step 1f, before the DoR gate is recorded with
  `pipeline.py dor`.
- At the end of `refine-feature` finalization, so that D1-D7 are challenged before the
  ticket is handed to the Developer.

The reviewer is a role played by the agent that runs the gate. It does not need a
new agent. It must not be the same review pass that wrote the ticket's D-inputs
without a fresh read of the sources.

## Inputs

| Source | What to read |
|--------|--------------|
| JIRA ticket | `atlassian_getJiraIssue` for the summary, description (ACs, DoD, non-goals), and story points field |
| Implementation plan | `docs/PRO-XXX_Implementation_Plan.md` Part A (decisions) and Part C (acceptance criteria), if it exists |
| Change folder | `docs/changes/YYYY-MM/PRO-XXX/` (`spec.md`, `plan.md`), if it exists |
| Repository | Existing files the ticket names, and the parent epic link |

## Procedure

For each DoR item, perform the steps below. Write the counter-evidence first, then the
verdict.

1. **State the claim.** Quote the pass condition from the table below.
2. **Attack it.** Try to find a concrete reason the claim is false. Look for:
   placeholders left in the text (`PR #NNN`, `N tests`, `FR-XX`), ACs that cannot be
   observed by a test, DoD items that cannot be verified, non-goals that contradict an
   AC, open questions still in the text, and drift between the ticket and the plan.
3. **Cite the evidence.** Each finding names the exact source (ticket field, plan
   section, file path, or line). A finding without a source does not count.
4. **Verdict.** PASS only if no counter-evidence was found after step 2. Otherwise FAIL
   and name the smallest change that would make the item pass.

| # | DoR item | Pass condition the reviewer tries to refute |
|---|----------|---------------------------------------------|
| D1 | Story points | The story points field is set and is a number (not empty, not 0) |
| D2 | Acceptance criteria | Each AC is numbered and has an observable check (a test, a command, or a measurable outcome) |
| D3 | Definition of Done | The DoD is a `- [ ]` checklist with no unfilled placeholders (`PR #NNN`, `N tests`, `FR-XX`, `XX`) |
| D4 | Stakeholder review | `refine-feature` ran, or the PO confirmed the ticket is ready (name the confirmation) |
| D5 | Scope | A non-goals or out-of-scope section exists and does not contradict an AC |
| D6 | Drift | No unresolved drift between the ticket, the plan, and the repository (`develop-feature` Step 1d) |
| D7 | Decisions | Every open decision is resolved or recorded in the ticket or plan Part A |

## Output

Write the result to the ticket's pm-notes file, `docs/changes/YYYY-MM/PRO-XXX/pm-notes.md`,
under a heading `## Readiness review (adversarial)`. Use this table:

```markdown
## Readiness review (adversarial)

| # | Verdict | Counter-evidence attempted | Source | Smallest fix (FAIL only) |
|---|---------|----------------------------|--------|--------------------------|
| D1 | PASS | Searched for empty or zero story points | JIRA customfield_10028 = 8 | - |
| D3 | FAIL | DoD contains `PR #NNN` placeholder | JIRA description, DoD list | Replace with the PR link at closure, or waive D3 with a reason |
```

Then record the gate with the CLI. The `dor` command accepts only `pass` and `fail`.
A waiver is recorded separately with `waive`, which needs a reason and an owner:

```bash
python .opencode/scripts/pipeline.py dor PRO-XXX --json '{"D1":"pass","D2":"pass","D3":"fail", "D4":"pass","D5":"pass","D6":"pass","D7":"pass"}'
python .opencode/scripts/pipeline.py waive PRO-XXX D3 --reason "PR link cannot exist before the PR" --by "PO"
```

Post the handoff to JIRA as usual (see `develop-feature` Step 1f):

```bash
python .opencode/scripts/pipeline.py handoff PRO-XXX --from developer --to product-owner \
  --step readiness-review --status COMPLETED --artifact docs/changes/YYYY-MM/PRO-XXX/pm-notes.md
```

Use `--status BLOCKED` when a FAIL cannot be fixed inside the ticket.

## Rules

- Attack first, then verdict. A PASS without a written refutation attempt is invalid.
- Do not weaken a pass condition to make an item pass. Ask the PO for a waiver instead.
- Every FAIL names a concrete smallest fix.
- The reviewer does not edit the JIRA ticket. Ticket edits belong to `refine-feature`
  and need PO confirmation.
- Store the review in pm-notes. Do not paste it into the implementation plan.

## Related Documents

- `develop-feature` Step 1f: the DoR gate that consumes these verdicts
- `refine-feature`: produces the D1-D7 inputs
- `docs/changes/README.md`: artifact layout and the pm-notes file
