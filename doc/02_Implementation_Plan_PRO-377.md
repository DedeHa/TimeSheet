# Implementation Plan PRO-377: Add Branch Deletion to complete-feature Skill

**Status:** ✅ Done  
**Epic Link:** PRO-259  
**Fix Version:** v4.3.0  
**Priority:** Medium  
**Story Points:** 1  

---

## Background

Currently, `complete-feature` ends at PR merge. Feature branches are left remotely with no cleanup step. No skill or workflow defines branch deletion. Branches accumulate in the repo with no standard process for removing them after merge.

## Goal

- `complete-feature` includes branch deletion as a defined step in the feature lifecycle
- Agent prepares deletion command, user/PO confirms and executes
- Policy remains intact: agent-team does NOT autonomously delete remote branches

## Scope

### In Scope

- Add "Delete Remote Branch" step to `.opencode/skills/complete-feature/SKILL.md` (post-merge)
- Add branch deletion to the reference command cheatsheet table
- Update Step 6 "Verify Final State" to include branch deletion status check
- Update the agent-team closure policy table if needed (confirm it still says "User/PO" for deletion)

### Out of Scope

- Automated branch deletion by the agent (violates closure policy)
- Deletion of release branches (different lifecycle, covered by `release-project`)
- GitHub auto-delete setting changes (repository-level config, outside skill scope)
- `develop-feature` or `orchestrate-feature` changes

## Implementation Plan

### Phase 1: Skill Update

1. Add "Delete Remote Branch" step after Step 5 (Push) in `complete-feature/SKILL.md`
2. Step content: Agent prepares `git push origin --delete <branch>` command, presents to user/PO for confirmation
3. Add to reference cheatsheet table: `| Delete remote branch | \`git push origin --delete <branch>\` — **User/PO confirms and executes** |`
4. Update Step 6 verification: confirm branch no longer exists on remote

### Phase 2: Policy Consistency Check

5. Verify AGENTS.md closure policy table still correctly marks branch deletion as User/PO
6. Verify `.opencode/skills/complete-feature/SKILL.md` description note reflects the policy

## Verification

- CI self-tests: 93 passed
- Traceability: 100%
- Application tests: 150 passed (99.71% coverage)
- Lint checks: ruff, black, pydocstyle, radon all pass

## References

- `.opencode/skills/complete-feature/SKILL.md`: Skill to be updated
- `AGENTS.md`: Agent-team closure policy

Refs: PRO-259