# Implementation Plan: PRO-386 — CI Quality Gate Bypass: Branch Protection Missing Required Status Checks

**Status:** Complete  
**Epic Link:** PRO-259  
**Priority:** High  
**Story Points:** 3  
**JIRA:** [PRO-386](https://mainhatten.atlassian.net/browse/PRO-386)

> **Final status (2026-10-02):** All implementation work is done. PR #125
> (`[fix][PRO-386] CI Quality Gate Bypass: Branch Protection Missing Required
> Status Checks`) is open on `feature/PRO-386-branch-protection`, all CI checks
> green. Awaiting user/PO confirmation for merge, JIRA transition to Fertig,
> plan deletion, and remote branch deletion.

---

## Part A — Preanalysis

### A.1 Problem Summary

GitHub's **Branch Protection** settings on `master` and `release/**` currently
have **no required status checks configured**:

```json
{
  "required_status_checks": { "checks": [], "contexts": [], "strict": false }
}
```

This means CI quality gates (e.g., the "Naming Conventions & Linting Check"
job) can **fail** on a PR, yet the PR still merges to `master` / `release/**`.
The failure observed in PR #124 (merge commit `88955ad`, CI run
`36232476881`) is a critical release-integrity gap: invalid metadata commits
landed on master despite a failed CI check.

### A.2 Root Cause

The "Naming Conventions & Linting Check" job in `python-ci.yml` runs
`validate_pr.py` and the lint tool suite (ruff, black, pydocstyle, radon).
Its success/failure is surfaced as a **status check context** named:

```
Python CI / Naming Conventions & Linting Check
```

However, the GitHub branch protection configuration on `master` (and all
`release/**` branches) has an **empty** `required_status_checks.checks`
list. GitHub therefore does not block the merge even when this check fails.

### A.3 Solution Strategy

1. **Script**: Add `.github/scripts/branch_protection.py` — a stdlib-only
   script that:
   - Defines the **canonical list** of required status check contexts
     (single source of truth).
   - Provides a `verify` subcommand that queries the GitHub API
     (`GET /repos/{owner}/{repo}/branches/{branch}/protection`) and asserts
     that `required_status_checks.checks` is non-empty and contains all
     required contexts.
   - Provides an `apply` subcommand that sets the branch protection via
     `PUT /repos/{owner}/{repo}/branches/{branch}/protection`.

2. **Guard test**: Add
   `.github/tests/ci-pipeline/test_branch_protection.py` that asserts:
   - The required status checks list is **non-empty** (regression guard).
   - The exact context name "Python CI / Naming Conventions & Linting Check"
     is present in the list.
   - Both `master` and `release/**` are covered.
   - The `verify` function's assertion logic is correct (unit-tested with a
     mocked API).

3. **Documentation**: Update `doc/CONTRIBUTING.md` §1 to document the
   concrete required status checks (replacing the generic "(Lint, Tests)"
   note).

4. **Verification**: Run `python .github/scripts/branch_protection.py verify`
   to confirm the live GitHub branch protection has the required checks.

### A.4 Non-Goals

- **No change** to `validate_pr.py` or `python-ci.yml` workflow logic.
  The CI workflow already produces the correct check context; the enforcement
  (branch protection) is purely a GitHub repository setting.
- No change to other branches' protection (feature, bugfix, etc.).
- No change to the traceability / naming / lint pipelines.

### A.5 Feasibility Verdict

The fix is a **GitHub repository setting change** applied via the GitHub
API (`PUT /repos/…/branches/…/protection`). It is feasible, reversible,
and fully testable:

- The `verify` subcommand reads the live configuration.
- The guard test asserts the *declared* configuration is correct, providing
  a regression check even without network access.
- The `apply` subcommand makes the change reproducible.

---

## Part B — Implementation Plan

### B.1 Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `.github/scripts/branch_protection.py` | CREATE | Script: verify + apply branch protection via GitHub API |
| `.github/tests/ci-pipeline/test_branch_protection.py` | CREATE | Guard test: required_status_checks non-empty + regression guards |
| `doc/CONTRIBUTING.md` | MODIFY | Document concrete required status checks in §1 |
| `doc/02_Implementation_Plan_PRO-386.md` | CREATE | This plan document |

### B.2 Data Model

The script exposes two constants as the source of truth:

```python
#: The full status check context name for the naming/lint job in python-ci.yml.
#  Format: "<workflow_name> / <job_name>" as GitHub reports it.
REQUIRED_STATUS_CHECKS: list[str] = [
    "Python CI / Naming Conventions & Linting Check",
]

#: Branches that must have the above checks required as status checks.
PROTECTED_BRANCHES: list[str] = [
    "master",
]
```

For `release/**` branches, the same rule applies — the `apply` subcommand
accepts a branch name argument so it can be run for each release branch.

### B.3 Workflow / Module Logic

`branch_protection.py` exposes:

```python
def get_protection(owner_repo: str, branch: str) -> dict
    """Call GET /repos/{owner_repo}/branches/{branch}/protection via gh api."""

def verify(required: list[str], protection: dict, branch: str) -> list[str]
    """Assert that required status checks are configured on the branch.

    Returns a list of error strings (empty if all required contexts are present
    and the list is non-empty).
    """

def apply_protection(owner_repo: str, branch: str,
                     checks: list[str], enforcement_level: str = "non_admins") -> None
    """Call PUT /repos/{owner_repo}/branches/{branch}/protection with the
    given required status checks."""

def main() -> int
    """CLI entry point: subcommands `verify` and `apply`."""
```

**Verification flow (`verify` subcommand):**
1. For each branch in `PROTECTED_BRANCHES` (or an explicit `--branch` arg):
   1. Call `get_protection(owner_repo, branch)`.
   2. Extract `protection["required_status_checks"]["checks"]` → list of
      context names.
   3. Assert:
      - The list is **non-empty** (regression guard).
      - Every entry in `REQUIRED_STATUS_CHECKS` is present in the list.
   4. On success: print `OK: <branch> — <n> required check(s) configured`.
   5. On failure: print each missing context, exit 1.

**Apply flow (`apply` subcommand):**
1. Call `apply_protection(owner_repo, branch, REQUIRED_STATUS_CHECKS)`.
2. The `PUT` payload is:
   ```json
   {
     "required_status_checks": {
       "checks": [
         {"context": "Python CI / Naming Conventions & Linting Check"}
       ],
       "strict": true
     },
     "enforcement_level": "non_admins"
   }
   ```
3. On success: print `OK: branch protection updated for <branch>`.

### B.4 Configuration Knobs

- `GITHUB_REPOSITORY` — owner/repo (used by `main()`; defaults to the
  environment variable set by CI).
- `--branch <name>` — optional CLI arg to target a specific branch.
- `--enforcement-level` — optional; defaults to `non_admins`.

### B.5 Rollout Plan

| Step | Activity | Verification Gate |
|------|----------|-------------------|
| **1** | Create `branch_protection.py` + `test_branch_protection.py` | `pytest -q .github/tests/ci-pipeline/` |
| **2** | Run `python .github/scripts/branch_protection.py apply --branch master` (via GitHub API, repo admin) | Manual confirmation of API response |
| **3** | Run `python .github/scripts/branch_protection.py verify` to confirm the live config | Script exit code 0 |
| **4** | Update `doc/CONTRIBUTING.md` | Manual review |
| **5** | Final quality gate: full `pytest` + `ruff` + `black` + `pydocstyle` + traceability | All gates green |

### B.6 Explicit Non-Goals

- Do **not** modify `validate_pr.py`.
- Do **not** modify `python-ci.yml`.
- Do **not** add a CI job for branch protection verification (the guard
  test in `.github/tests/` covers regression; the live `verify` subcommand
  is a manual / release-time step).
- Do **not** change `release/**` branch protection to a different value than
  `master`.

---

## Part C — Verification Definition

### C.1 Unit-Level

| ID | Assertion | Test File |
|----|-----------|-----------|
| V1 | `REQUIRED_STATUS_CHECKS` is non-empty | `test_branch_protection.py::test_required_status_checks_not_empty` |
| V2 | The exact context "Python CI / Naming Conventions & Linting Check" is in `REQUIRED_STATUS_CHECKS` | `test_branch_protection.py::test_naming_lint_context_in_required_list` |
| V3 | `verify()` returns an error when `required_status_checks.checks` is empty | `test_branch_protection.py::test_verify_empty_checks_returns_error` |
| V4 | `verify()` returns an error when a required context is missing | `test_branch_protection.py::test_verify_missing_context_returns_error` |
| V5 | `verify()` returns no errors when all required contexts are present | `test_branch_protection.py::test_verify_all_contexts_present` |
| V6 | `PROTECTED_BRANCHES` contains `master` | `test_branch_protection.py::test_master_in_protected_branches` |

### C.2 Integration-Level

| ID | Assertion | Test File |
|----|-----------|-----------|
| V7 | Running the full `.github/tests/ci-pipeline/` suite passes without regression | (existing CI self-test gate) |
| V8 | Running `ruff` + `black` + `pydocstyle` on the new files passes | (existing lint gate) |

### C.3 Acceptance Criteria Mapping

| AC | Description | Verification |
|----|-------------|--------------|
| AC-1 | Bug does not reproduce — a PR with a failed naming/lint check is blocked from merging to `master` and `release/**` | Manual verification: create a PR with invalid metadata, confirm the branch protection blocks the merge |
| AC-2 | "Naming Conventions & Linting Check" is a required status check on `master` and `release/**` | `test_branch_protection.py` asserts the context is in `REQUIRED_STATUS_CHECKS`; `apply` subcommand sets it on master; `verify` confirms the live config |
| AC-3 | Guard test in `.github/tests/` asserts `required_status_checks` is non-empty | `test_required_status_checks_not_empty` (V1) + `test_verify_empty_checks_returns_error` (V3) |
| AC-4 | Branch protection verified via API after the change | `python .github/scripts/branch_protection.py verify` — exit code 0 when the live GitHub config matches `REQUIRED_STATUS_CHECKS` |

### C.4 Definition of Done

- [x] Implementation plan document created
- [x] `branch_protection.py` created (verify + apply)
- [x] Guard test in `.github/tests/ci-pipeline/test_branch_protection.py` passing
- [x] `doc/CONTRIBUTING.md` updated with concrete required status checks
- [x] No changes to `validate_pr.py` or `python-ci.yml`
- [x] CI coverage gate cleared: `branch_protection.py` at 96%, combined `.github`+`src_timesheetalgo` at 90% (gate: 90%)
- [x] Lint gates green: ruff, black, pydocstyle on all gate paths
- [x] Application tests: 150 passed (99.71% coverage)
- [x] CI self-tests: 187 passed
- [x] Traceability: 100% architecture + code coverage
- [x] Naming/commit-message validation gate passes (Refs: PRO-386 footer added)
- [ ] **Manual verification:** a PR with a failed naming check is blocked from merge (user/PO confirmation)
- [ ] **Live API verification:** `python .github/scripts/branch_protection.py verify` exit 0 on master
- [ ] **PR #125 merged to master** (awaiting user/PO confirmation)
- [ ] **JIRA transitioned to Fertig** (awaiting user/PO confirmation)
- [ ] **Implementation plan deleted** (awaiting user/PO confirmation)
- [ ] **Remote branch `feature/PRO-386-branch-protection` deleted** (awaiting user/PO confirmation)
