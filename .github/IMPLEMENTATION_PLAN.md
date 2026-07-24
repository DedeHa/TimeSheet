# Implementation Plan – Automated Naming Convention Validation (PRO-336)

## Overview
Automate enforcement of commit messages, pull request titles, and PR descriptions against documented naming conventions using GitHub Actions.

## Prerequisites
- JIRA ticket PRO-336 (ticket reference required in all commits/PRs)
- Existing branch protection rules for `master`, `release/*`

## Validation Stack (GitHub Actions Tools)

### 1. Commit Message Validation
- **Action**: `pre-commit` with `commitlint` hook.
- **Config**: `.commitlintrc` matching Conventional Commits + project-specific rules:
  - Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `ci`, `build`
  - Format: `type(scope): description` (scope optional)
  - Footer युद्ध Not required. JIRA reference will be handled by the dedicated validation job.
- **Integration**: Added to `.github/workflows/python-ci.yml` lint stage.

### 2. PR Title Validation
- **Action**: `actions/github-script` with regex validation.
- **Rule**: Must match `[type][PRO-XXX] Description` format (type lowercase) where `PRO-XXX` can have multiple digits (e.g., `PRO-123`, `PRO-123456`).
- **Allowed types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `hotfix`
- **Failure**: Fail CI job immediately.

### 3. PR Description Validation
- **Action**: `actions/github-script` with content check.
- **Mandatory sections**: `## Summary`, `## Testing`
- **Optional section**: `## Notes` (per CONTRIBUTING.md)
- **Enforcement**: Fail CI if mandatory sections missing or empty.

### 4. Branch Name Validation (Optional Enhancement)
- **Action**: `actions/github-script` in PR workflow.
- **Rule**: Must match `type/PRO-\d+-description` format.
- **Allowed types**: `feature`, `bugfix`, `hotfix`, `refactor`, `docs`, `test`
- **Note**: Only enforced on PR creation (not direct pushes to feature branches).

## Workflow Integration

```yaml
# Within python-ci.yml lint job
- name: Validate Commit Message
  uses: pre-commit/pre-commit-action@v4
  with:
    rev: v3.7.0
    hooks: ["commitlint"]  # configure .commitlintrc

- name: Validate PR Title
  uses: actions/github-script@v8
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    script: |
      const prTitle = context.payload.pull_request.title;
      // Format: [type][PRO-123] Description
      // Types from CONTRIBUTING.md: feat, fix, docs, refactor, test, chore, hotfix
      const regex = /^\[(feat|fix|docs|refactor|test|chore|hotfix)\]\[PRO-\d+\]\s+.+$/i;
      if (!regex.test(prTitle)) {
        core.setFailed('PR title format invalid. Expected: [type][PRO-XXX] Description');
      }

- name: Validate PR Body
  uses: actions/github-script@v8
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    script: |
      const body = context.payload.pull_request.body || '';
      const hasSummary = /##\s+Summary\s*\n/.test(body);
      const hasTesting = /##\s+Testing\s*\n/.test(body);
      if (!hasSummary) {
        core.setFailed('PR body missing mandatory "## Summary" section');
      }
      if (!hasTesting) {
        core.setFailed('PR body missing mandatory "## Testing" section');
      }
      // Check for placeholder text
      if (/TODO|TBD|Describe your changes\.\.\./i.test(body)) {
        core.setFailed('PR body contains placeholder text (TODO, TBD, etc.)');
      }
```

## Testing Plan
- **Positive**: Valid commit/PR passes CI.
  - Commit: `feat(auth): add login\n\nRefs: PRO-123`
  - PR Title: `[feat][PRO-123] Add user authentication`
  - PR Body: Contains `## Summary` and `## Testing` sections
- **Negative**: Invalid format fails CI with clear error message.
  - Missing JIRA ref, wrong type, missing sections, placeholder text

## Documentation Updates
- Add validation tool descriptions to `CONTRIBUTING.md` (Section 8).
- Update `ARCHITECTURE.md` diagram to show CI validation flow (lint → naming validation → tests).
- Provide examples in `README.md` for correct formats.

## Rollout Strategy
- Deploy to `feature/*` branches first; monitor failures.
- Gradually tighten validation rules if needed.
- Communicate changes via PR comments and team channels.

</content>