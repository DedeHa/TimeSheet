---
name: release-project
description: Use when releasing a new version of the TimeSheetAlgo project. Triggers on requests to "release", "create a release", "tag vX.Y.Z", "publish release notes", or any JIRA version-release workflow. Covers version discovery, branch creation, tag management, GitHub Release publication, JIRA version release, and Confluence release-notes documentation.
---

# Release Project Skill

Reusable end-to-end release workflow for TimeSheetAlgo. Follows the conventions in `doc/CONTRIBUTING.md` §5 and §7.

## Prerequisites

- Working directory: `/workspaces/TimeSheet` (repository root)
- Virtual environment activated: `source /workspaces/TimeSheet/.venv/bin/activate`
- `gh` authenticated and `git` configured
- Atlassian MCP tools available (Jira + Confluence)

## Step 0 — Determine Version & JIRA Ticket

1. Identify the JIRA ticket(s) being released. Look for the most recent merged PRs and their associated tickets.
2. Query JIRA for the ticket's `fixVersions` to get the **target release version** (e.g. `v4.2.0`):
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["fixVersions"])
   ```
3. Confirm the version does not already exist as a tag or release in GitHub.

## Step 1 — Prepare Master

```bash
git checkout master
git pull origin master
```

Verify `pyproject.toml` version is correct. If not, bump it in a separate commit *before* creating the release branch.

## Step 2 — Create Release Branch

```bash
git checkout -b release/vX.Y.Z master
```

## Step 3 — Bump Version

Update `version` in `pyproject.toml` from the current value to `X.Y.Z`.

Commit:
```bash
git add pyproject.toml
git commit -m "chore(release): bump version to vX.Y.Z

Refs: PRO-XXX"
```

## Step 4 — Push & Open Release PR

```bash
git push origin release/vX.Y.Z
gh pr create --base master \
  --title "[release][PRO-XXX] vX.Y.Z" \
  --body "## Summary
- Bump version to vX.Y.Z
- Target release for PRO-XXX

## Testing
- python -m pytest tests/ --cov=src_timesheetalgo --cov-report=term-missing
- python .github/scripts/generate_traceability_matrix.py
- pytest -q .github/tests/ci-pipeline/

Refs: PRO-XXX"
```

**PR title must use `[release][PRO-XXX] vX.Y.Z`** — the `release` type is in `VALID_PR_TYPES` in `.github/scripts/validate_pr.py`.

## Step 5 — Wait for CI & Merge

- Verify all 4 CI jobs pass: Naming Conventions & Linting Check, Run all test levels, Build & Deploy (skipped for non-tag), Publish.
- Merge the PR: `gh pr merge <PR_NUMBER> --merge`

## Step 6 — Create Annotated Tag on Release Branch

**Best practice:** Tag must point to the **release branch tip**, not the master merge commit.

```bash
git checkout release/vX.Y.Z
git tag -d vX.Y.Z 2>/dev/null
git tag -a vX.Y.Z -m "Release vX.Y.Z

Refs: PRO-XXX"
git push origin --delete vX.Y.Z 2>/dev/null
git push origin vX.Y.Z --force
```

Verify:
```bash
git rev-parse vX.Y.Z^{}
git rev-parse origin/release/vX.Y.Z
# Both must match
```

## Step 7 — Publish GitHub Release

If a draft release exists (auto-created from the old tag), repoint it:

```bash
gh release edit vX.Y.Z \
  --target release/vX.Y.Z \
  --draft=false \
  --title "vX.Y.Z" \
  --notes-file /tmp/vX.Y.Z_release_notes.md
```

**Release notes format** — mirror the v4.1.2 template:

```markdown
## Release vX.Y.Z

### Features & Improvements
- **<Area>**: <description>
- **Code Quality**: All linting checks passed (Ruff, Black, Pydocstyle, Radon)
- **Documentation**: <what docs changed>
- **Testing**: <test changes>

### What's Changed
- <bullet 1>
- <bullet 2>

### Technical Details
- **Branch**: release/vX.Y.Z
- **Type**: <Minor|Patch|Major> Release (vX.Y.Z)
- **Semantic Versioning**: <description>
- **Status**: Published

### Related Issues
- PRO-XXX: <summary>
- PRO-YYY: <summary>

### Commits Included
- <conventional commit 1>
- <conventional commit 2>

## What's Changed
* <PR changelog entries from GitHub auto-generation>

**Full Changelog**: https://github.com/<owner>/<repo>/compare/<previous_tag>...vX.Y.Z
```

## Step 8 — Release JIRA Version

The JIRA version `vX.Y.Z` is typically set with `released: false` and a future `releaseDate`. After deployment:

1. Check the version state:
   ```
   atlassian_getJiraIssue(issueIdOrKey="PRO-XXX", fields=["fixVersions"])
   ```
2. If `released` is still `false`, update via the Jira REST API (the MCP tools don't expose version-release):
   ```
   PUT /rest/api/3/version/<versionId>
   Body: {"released": true, "releaseDate": "YYYY-MM-DD"}
   ```
   Or flip it manually in the Jira UI: **Versions → vX.Y.Z → Release**.

## Step 9 — Publish Confluence Release Notes

Find the draft release-notes page (parent: the "Versionshinweise" index page). It has a metadata table (Release, Datum, Version, Beschreibung, Beitragende) and placeholder sections.

Update it:

1. Set **Datum** to the actual release date.
2. Fill **Beschreibung** with a one-line summary.
3. Replace the `<h1>Zusammenfassung</h1>` placeholder with structured content:
   - Summary bullets (what changed + why it matters)
   - `Neue Funktionen` (new features, or "Keine neuen Anwendungsfunktionen" for infra-only releases)
   - `Verbesserungen an bestehenden Funktionen` (improvements)
   - `Fehlerbehebungen` (bug fixes)
4. Publish the page (status changes from `draft` → `current`).

Use `atlassian_updateConfluencePage` with `contentFormat: "html"`.

## Step 10 — Verify

```bash
# Tag points to release branch tip
git rev-parse vX.Y.Z^{}
git rev-parse origin/release/vX.Y.Z

# GitHub Release is published (not draft)
gh release view vX.Y.Z --json isDraft,targetCommitish

# Tag-triggered CI passed
gh run list --branch vX.Y.Z --limit 1
```

## Reference: Quick Command Cheatsheet

| Action | Command |
|--------|---------|
| Create release branch | `git checkout -b release/vX.Y.Z master` |
| Bump version | Edit `pyproject.toml`, `git commit -am "chore(release): bump version to vX.Y.Z\n\nRefs: PRO-XXX"` |
| Push branch | `git push origin release/vX.Y.Z` |
| Create PR | `gh pr create --base master --title "[release][PRO-XXX] vX.Y.Z"` |
| Merge PR | `gh pr merge <N> --merge` |
| Create annotated tag | `git tag -a vX.Y.Z -m "Release vX.Y.Z\n\nRefs: PRO-XXX"` |
| Push tag | `git push origin vX.Y.Z --force` |
| Fix draft release | `gh release edit vX.Y.Z --target release/vX.Y.Z --draft=false` |
| Update release notes | `gh release edit vX.Y.Z --notes-file /tmp/vX.Y.Z_release_notes.md` |
| Release JIRA version | `PUT /rest/api/3/version/<id>` with `{"released": true}` |
| Publish Confluence | `atlassian_updateConfluencePage(pageId, body, contentFormat="html")` |

## Related Documents

- `AGENTS.md` — Top-level guide: project conventions, modes, CI gates
- `doc/AGENTS_WORKFLOW.md` — Agent team workflow, diagrams, quality gates, handoff labels
- `doc/CONTRIBUTING.md` — Development standards
- `doc/ARCHITECTURE.md` — System architecture and design decisions
- `.opencode/skills/release-project/` — This skill
- `.opencode/skills/plan-feature/SKILL.md` — Workflow for planning a feature
- `.opencode/skills/orchestrate-feature/SKILL.md` — Workflow for orchestrating the pipeline