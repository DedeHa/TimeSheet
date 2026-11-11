# PRO-407 PM Notes

- **Ticket:** PRO-407 (PR #138). Handoff comments live in JIRA and are not copied here.
- **Mode:** automated (set for PRO-407 in `~/.opencode/pipeline-state.json`)

## Decisions

| # | Decision | Record |
|---|----------|--------|
| 1 | Artifact path is `docs/`, not `doc/`. The ticket paths are superseded. | ODR-0001, plan A.1 |
| 2 | The DoR gate is enforced in `develop-feature` before any code is written, and in code by `pipeline.py continue` into develop. | ODR-0001, plan A.1 |
| 3 | The implementation plan is deleted after merge (existing `AGENTS.md` rule). | ODR-0001, `docs/changes/README.md` rule 3 |
| 4 | Handoffs are recorded with `pipeline.py handoff`. The script renders the comment and the agent posts it, because the script has no JIRA client. | plan A.4, note below |
| 5 | **Scope (2026-11-11, user):** all features in ticket PRO-407 are in scope. The tracker-agnostic `workItemRef` (ticket Step 6) is implemented: `parse_work_item_ref` and the `handoff` command. This replaces the earlier decision to defer it. | plan B.4, B.6 gap 7 |
| 6 | **Scope (2026-11-11, user):** the adversarial readiness reviewer (ticket Step 3) is implemented as the `readiness-review` skill. This replaces the earlier decision to defer it. | plan B.4, B.6 gap 3 |
| 7 | The DoR waivers are recorded with `pipeline.py waive` (reason and owner required), not only in prose. | Section "DoR waivers" |
| 8 | `continue --force` never overrides the DoR gate. It bypasses only the handoff rule (latest handoff COMPLETED and a completed cycle), records `forced_advance`, and clears a BLOCKED state. | plan B.8 item A, ARCHITECTURE, FR-23 |
| 9 | Interruption is one rule: BLOCKED, an explicit `interrupt` marker, or an in_progress step with no update for 24 hours that has not been reported complete. A fresh `continue` is not interrupted. | plan B.8 item D, ARCHITECTURE, FR-22 |
| 10 | A new `interrupt` command sets the marker. It is new CLI surface, added so the marker can be set. `resume` and a successful `continue` clear it. | plan B.8 item D |
| 11 | D1 (story points) cannot be waived. D3 checks placeholders in the ACs and Steps only. DoD closure items (PR number, test count, JIRA transition, plan deletion) are checked at closure. | plan B.8 item G, FR-23 |
| 12 | A corrupt state or history file fails closed: every command exits 1 and the file is left unchanged. | plan B.8 item B, ARCHITECTURE |

**Note on decision 4 (deviation from the ticket wording).** The ticket says the handoff
step posts a JIRA comment. The CLI does not post it: `pipeline.py handoff` records the
handoff in history and renders the comment markdown, and the agent posts that markdown
with `atlassian_addCommentToJiraIssue`. The reason is that the script has no JIRA client
and stays dependency-free (plan A.4). The comment content follows the ticket template.

## DoR waivers

The `develop-feature` Step 1f gate was run for this change. One item is waived for
PRO-407 (D4). The user, acting as Product Owner, gave the waiver in the automated run instruction.
The waivers are recorded here, and the commands below record the same checklist and
waivers in the pipeline state. They were not run against the shared state file during the
implementation rounds, so the Product Owner runs them once before closure.

Read-only check (fix round, 2026-11-11): the shared state for PRO-407 holds no DoR
checklist, no waivers, and `current_step` is `plan`. Nothing recorded here is in the
state yet.

```bash
python .opencode/scripts/pipeline.py dor PRO-407 --json '{"D1":"pass","D2":"pass","D3":"pass","D4":"fail","D5":"pass","D6":"pass","D7":"pass"}'
python .opencode/scripts/pipeline.py waive PRO-407 D4 \
  --reason "The user reviewed the ticket in the intake and confirmation step (decisions 1-6) instead of a full refine-feature round. Architect, Developer and Tester review happened inside the pipeline." \
  --by "Product Owner (user)"
python .opencode/scripts/pipeline.py dor PRO-407        # shows the checklist and the gate result
```

- **D3 (Definition of Done): pass, no waiver.** The ACs and Steps contain no
  placeholders. The closure placeholders (PR number, test count, JIRA transition, plan
  deletion) are excluded by the narrowed D3 rule (decision 11), so `"D3":"pass"`.
- **D4 (Stakeholder review): waived.** See the waiver command above.
- **D1 (Story points): pass, not waivable.** Story points are 8. JIRA `customfield_10028`
  is 8 (read-only check). A waiver is refused by the tool.

Other DoR checks (D2, D5, D6, D7) pass. The ACs are testable (plan C.3), non-goals are
in plan B.4, and there are no open drift signals.
The adversarial review of D1-D7 is recorded in the section below. After the round-3 fix,
D1 and D3 are pass (see the verdict note under the table).

## Readiness review (adversarial)

Run with `.opencode/skills/readiness-review/SKILL.md` against the ticket text. The
review tried to refute each item. Verdicts (before the fix round):

| # | Verdict | Counter-evidence attempted | Source | Smallest fix (FAIL only) |
|---|---------|----------------------------|--------|--------------------------|
| D1 | PASS | Story points field is empty or zero | JIRA PRO-407, Story Points: 8 (plan C.4) | - |
| D2 | PASS | An AC without an observable check | Plan C.3 AC-1 to AC-6, each mapped to a V item | - |
| D3 | FAIL (waived) | DoD contains `PR #NNN`, `N tests`, `FR-XX` | JIRA description, Definition of Done | Waived above, because the closure items cannot exist before the PR. Re-check under the narrowed D3 rule (decision 11). |
| D4 | FAIL (waived) | No `refine-feature` round and no written stakeholder sign-off | Intake and confirmation step (decisions 1-6) | Waived above |
| D5 | PASS | Non-goals contradict an AC | JIRA Non-Goals, plan B.4 (now only multi-tool, autonomous loop, full 11-phase model, app code under `src/`) | - |
| D6 | PASS | Unresolved drift between ticket, plan and repository | Drift from the ticket text: docs path (`doc/` to `docs/`, decision 1) and the two scope changes (decisions 5 and 6) are recorded | - |
| D7 | PASS | Open decisions still in the text | Plan A.1 decisions 1-4 are resolved; decisions 5 and 6 are resolved above | - |

**Current verdicts (after the round-3 fix):** D1 PASS (story points 8, JIRA customfield_10028 = 8).
D3 PASS under the narrowed rule: the ACs and Steps contain no placeholders, so the D3
waiver is no longer needed and is removed. D4 stays waived (refine-feature not run).

## Open items for user confirmation (not done by the agent team)

- **Waivers (before closure):** the PO runs the `dor` and `waive` commands in "DoR waivers" above, or accepts the waivers from this file. The state has no DoR record for PRO-407 yet. `continue` into develop is refused until the checklist is recorded (the gate is enforced in code).
- Merge PR #138.
- Transition PRO-407 to Fertig.
- Delete `docs/PRO-407_Implementation_Plan.md` after merge.
- Delete remote branch `feature/PRO-407-agent-governance` after merge.

## Accepted risks and follow-ups

These findings from the independent reviews were not fixed in the fix round. They are accepted for PR #138 and each one becomes a follow-up JIRA ticket after the merge (proposed titles below). The Product Owner decides whether to create them. The finding names are the titles used in the fix-round brief. The full review text is not stored in the repository.

| Finding | Risk | Proposed follow-up ticket title |
|---------|------|---------------------------------|
| architect #10 | The max-3 cycle limit is recorded (`max_cycles`) but not enforced by `continue` or `handoff`. | Enforce the max-3 cycle limit in `pipeline.py` continue and handoff |
| architect #11 | The agent that set a BLOCK can clear it with its own COMPLETED handoff. | Require a Product Owner resolution to clear a BLOCKED handoff |
| architect #12 | A reference that matches both the GitHub and the JIRA pattern (`GH-456`) is classified as GitHub. The precedence is implicit. | Define tracker precedence for references that match more than one pattern |
| architect #16 | The reconcile messages say a living document is "updated". The check only looks for a change to the file in the diff. | Reword reconcile messages to say a living-document change is present in the diff |
| architect #17 | `pipeline.py reconcile` is not wired into the CI pull-request check, and it only checks presence of a change. | Wire `pipeline.py reconcile` into the CI pull-request check |
| architect #18 | The reconciliation approach differs from the ticket and is not recorded as a decision. | Record the reconciliation deviation as a decision in `docs/decisions/` |
| tester #5 | Coverage of `.opencode/scripts` is not in the CI coverage gate (the gate covers `src` only). | Add `.opencode/scripts` to the coverage gate |
| tester #9 | The governance documentation tests check text presence, not behaviour. | Replace text-presence governance checks with behavioural checks where practical |
| tester #10 | There is no separate reconciliation skill; the step lives in `complete-feature` Step 4.5. | Decide whether documentation reconciliation needs its own skill |
| tester #11 | The PRO-407 change folder has no `spec.md` pointer (QR-14 lists it as an artifact). | Add a `spec.md` pointer to the PRO-407 change folder |
| tester #12 | `orchestrate-feature` can dispatch the Developer without calling the DoR gate first. | Make `orchestrate-feature` call the DoR gate before every Developer dispatch |
| architect r3: stuck | A step that is COMPLETED but not yet continued is never flagged stuck, so a forgotten `continue` is silent. | Flag a COMPLETED step that has waited for `continue` beyond a threshold in `check-stuck` |
| architect r3: dry-run | `dry-run continue` says "Would advance" even when the DoR gate refuses. | Make `dry-run continue` run the DoR and handoff gates and report the refusal |
| architect r3: reset | `reset --force` wipes the DoR record and the waivers, so a reset silently removes the recorded gate. | Keep the DoR record and waivers on reset, or require a separate confirmation to clear them |
| architect r3: atomicity | `handoff` writes the state and the history in two non-atomic steps; a failure between them leaves them out of step. | Write state and history in one transaction (or order the writes and recover) |
| architect r3: duplicate store | Waivers are stored twice: in `dor` (value `waived`) and in `dor_waivers` (reason and owner). | Keep one store for waivers and derive the `dor` value from it |
| architect r3: pruning | Candidates to remove or keep. `reconcile` CLI: keep the skill step, drop or keep the CLI. `max_cycles`: not enforced (same as architect #10). `escalation_level`: no consumer. | Decide per item: remove unused fields, or wire them up. Record the decision |

Fixed in the round-3 fix (2026-11-11): tester F1 (`detect_mode.py` reuses the fail-closed
reader and the atomic writer of `pipeline.py`; reads never create `~/.opencode`), architect
B1 (lowercase JIRA-shaped references such as `pro-12` are rejected), architect B2 (FR-23 and
the ARCHITECTURE gate row say D1 cannot be waived). Tester F3 (duplicate
`INTERRUPT_AFTER_HOURS`) was checked: `pipeline.py` has one definition, and the history has
no second one, so nothing was removed.

Fixed in the fix round, so not follow-ups: architect #1 (DoR bypass), #3 (corrupt state),
#4 (BLOCKED), #5 (interruption), #6 (step mismatch), #7 (ticket normalisation), #8 (D1 and
D3), minor #8 (blank entries), minor #9 (`--base` validation), minor #13 (dor_gate
reasons), minor #14 (atomic write), tester #1 (exit codes), #2 (latest-handoff
isolation), #3 (interruption), #4 (home directory), #6 (tracker stubs), and tester #7
(corrupt state, same fix as architect #3).
