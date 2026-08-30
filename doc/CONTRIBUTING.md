# Contributing Guidelines & Naming Conventions

## 📌 Overview: Git Workflow + Agent-Based Development

This document covers **Git workflow** and **code standards**. For information about **agent-based feature development** (using Copilot agents for structured feature planning and implementation), see [AGENTS_WORKFLOW.md](AGENTS_WORKFLOW.md).

### Complete Development Process:
1. **Phase 0 (Pre-Development):** Feature planning with Copilot Agents → User Stories & Architecture (see [AGENTS_WORKFLOW.md](AGENTS_WORKFLOW.md))
2. **Phase 1 (Development):** Feature development on branch → Code & Tests (this document)
3. **Phase 2 (Integration):** Pull Request to master → Tests + Review (this document)
4. **Phase 3 (Release):** Release branch → Version bump → Deploy (this document)

---

## 1. Branch Protection Policy

### Protected Branches (Direct Pushes Blocked)

The following branches are **protected** and do not allow direct pushes:

- **`master`** - Production main branch
  - Status: ✅ Protected
  - Direct Pushes: ❌ Blocked
  - PRs required: ✅ Yes
  - Reviewer required: ✅ Yes
  - Status Checks required: ✅ Yes (Lint, Tests)

- **`release/*`** - Release branches (e.g., `release/v4.1.0`, `release/v4.1.1`)
  - Status: ✅ Protected
  - Direct Pushes: ❌ Blocked
  - PRs required: ✅ Yes
  - Reviewer required: ✅ Yes
  - Status Checks required: ✅ Yes (Lint, Tests)

### Development Branches (Direct Pushes Allowed)

The following branch types allow direct pushes for active development:

- **`feature/*`** - New features (e.g., `feature/PRO-123-login-api`)
- **`bugfix/*`** - Bug fixes (e.g., `bugfix/PRO-123-scan-timeout`)
- **`hotfix/*`** - Critical bug fixes (e.g., `hotfix/PRO-123-security-patch`)
- **`refactor/*`** - Code refactoring (e.g., `refactor/PRO-296-remaining`)
- **`docs/*`** - Documentation changes (e.g., `docs/PRO-123-api-docs`)
- **`test/*`** - Test improvements (e.g., `test/PRO-297-setup-verification`)

---

## 2. Branch Naming Conventions

### Standard Branch Naming
- **feature/PRO-123-description**: New features
- **bugfix/PRO-123-description**: Bug fixes
- **hotfix/PRO-123-description**: Critical bug fixes
- **refactor/PRO-123-description**: Code refactoring
- **docs/PRO-123-description**: Documentation changes
- **test/PRO-123-description**: Test improvements
- **release/vX.Y.Z**: Release preparation

### Branch Naming Rules:
- Only lowercase letters, numbers, hyphens, and slashes
- No spaces, colons, pipes, or special characters
- Maximum length: 50 characters
- Format: `type/PRO-123-short-description`

Example: `feature/PRO-123-login-api`, `bugfix/PRO-123-scan-timeout`, `release/v1.2.0`

---

## 3. Commit Naming (Conventional Commits Standard)
- **Format:** `type(scope): description`
- **Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `ci`, `build`
- **Description:** Clear, concise, imperative mood (max. 50 characters)
- **Footer:** JIRA reference: `Refs: PRO-123`

### Commit Format:
```
type(scope): subject line

Optional body explaining the change in more detail.

Refs: PRO-123
```

Examples:
- `feat(auth): add device scan functionality`
- `fix(vpn): resolve connection timeout issue`
- `docs(api): update authentication guide`

### Scope Guidelines:
- **Mandatory:** Scope improves clarity
- **Use scope** when the change affects a specific module/component (e.g., `auth`, `vpn`, `api`)
- **Cross scope** for cross-cutting changes (e.g., `arch`, `workflow`, `doc`)

## 4. Pull Request Requirements
- **Title Format:** `[type][PRO-XXX] Clear description of changes` where `PRO-XXX` can have multiple digits (e.g., `PRO-123`, `PRO-123456`)
- **Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `hotfix`, `release`
- **Description:** What is being changed? (max. 72 characters)
- **Body Requirements:**
  - Must include `## Summary` section
  - Must include `## Testing` section
  - **Must include JIRA reference:** `Refs: PRO-123`
  - No placeholder text (TODO, TBD, etc.)
- **Template:** Use PR templates for consistent structure

Examples:
- `[feat][PRO-123] Add dashboard UI with user authentication`
- `[fix][PRO-123] Prevent MAC address spoofing vulnerability`
- `[docs][PRO-123] Update API documentation for v2.0`

## 5. Release Naming (Semantic Versioning)

### Release Naming Convention
- **Format:** `vX.Y.Z` (no leading zeros)
  - **X**: MAJOR version – incompatible API changes
  - **Y**: MINOR version – new, backwards-compatible features
  - **Z**: PATCH version – backwards-compatible bug fixes
- **Example:** `v1.2.3`, `v2.0.0`, `v1.4.7`

### Release Branches:
- **Format:** `release/vX.Y.Z`
- **Purpose:** Stabilization and preparation before release
- **Naming:** After release, RC branches are renamed to `release/vX.Y.Z` format
- **Example:** `release/v4.1.0`, `release/v4.1.1`, `release/v2.0.0`

### Release Tags:
- **Format:** `vX.Y.Z` (Semantic Versioning)
- **Purpose:** Mark official, stable releases
- **Assignment:** Each `release/vX.Y.Z` branch gets a corresponding `vX.Y.Z` tag
- **Creation:** Tag is created on the final commit of the release branch
- **Example:** `v4.1.0`, `v4.1.1`, `v2.0.0`

### Historical Versioning (Legacy):
- Tags in format `RX.Y.Z` (e.g., `R04.01.00`, `R03.00.00`) are retained for traceability
- New releases use exclusively `vX.Y.Z` format with corresponding `release/vX.Y.Z` branches

### Release Workflow (Feature → Master → Release → Deployment):
1. **Feature development:** Create feature branch (e.g., `feature/PRO-123-xyz`)
2. **PR to Master:** Open PR targeting `master` (Tests + Lint + Review required)
3. **Merge to Master:** Only after successful tests and review approval
4. **Create release branch:** `git checkout -b release/vX.Y.Z master`
5. **Update version numbers** in relevant files (e.g., README.md, version constants)
6. **Create final release commit** with release notes
7. **Create tag:** `git tag vX.Y.Z` (marks the stable release point)
8. **Push to Origin:** `git push origin release/vX.Y.Z && git push origin vX.Y.Z`
9. **Deployment:** Deployment happens exclusively from release tags (automation or manual)

## 6. Git Compatibility Rules

### Forbidden Characters in Branch Names:
- Pipe (`|`), Colon (`:`), Question mark (`?`)
- Asterisks (`*`), Square brackets (`[]`), Backslash (`\`)
- Angle brackets (`<>`), Quotes (`"`), At sign (`@`)
- Curly braces (`{}`), Tilde (`~`)

### Allowed Characters:
- Lowercase letters (a-z)
- Numbers (0-9)
- Hyphens (-) - not at the beginning or end
- Slashes (/) - as separator between type and name

### Windows Compatibility:
- No reserved names: CON, PRN, AUX, NUL, COM1-9, LPT1-9
- Respect maximum path length (260 characters)

### JIRA Ticket Reference
- Every release, branch, commit, and pull request must include the JIRA ticket number
- **Branch:** Ticket number in name: `feature/PRO-123-description`
- **Commit:** Ticket number in footer: `Refs: PRO-123`
- **PR:** Ticket number in title: `[feat][PRO-123] Description`
- **Release:** Link ticket number in release notes

Examples:
- Branch: `feature/PRO-123-user-authentication`
- Commit: `feat(auth): add login validation\n\nRefs: PRO-123`
- PR: `[feat][PRO-123] Implement user authentication system`
- Release: `v1.2.0` (with PRO-123 in release notes)

**Note:**
The JIRA ticket number (prefix PRO-number) is fundamental to the project and should always be used for traceability and automatic linking with JIRA.

### Working Without JIRA Ticket
If no JIRA ticket is available, branches, commits, and pull requests should be created in `type/description` format without PRO-XXX:
- **Branch:** `type/description` (e.g., `feature/user-login`, `refactor/timesheet-2025-update`)
- **Commit:** Standard Conventional Commits without `Refs: PRO-XXX` footer
- **PR:** `[Type] Description` without ticket number (e.g., `[feat] Add user login functionality`)

**Important:** As soon as a JIRA ticket is available, the reference should be added retroactively.

---

## 7. Git Workflow & Development Process

### Development Workflow: Feature → Master (Tests) → Release (Deployment)

The workflow strategy follows a **Trunk-based Development** model with 3 phases:

```
feature/*  →  [PR + Tests + Review]  →  master  →  [Create release branch]  →  release/vX.Y.Z  →  [Deploy to Production]
bugfix/*   →  [PR + Tests + Review]  →  master  →       ↓
hotfix/*   →  [PR + Tests + Review]  →  master  →  Stable, Tested Code
```

**Important:**
- ✅ Tests are **run only on PRs to `master`** (required)
- ✅ Deployment happens **only on release tags** (production)

### Prerequisites: GitHub CLI (`gh`)

Pull requests are created with the [GitHub CLI](https://cli.github.com/). Install and authenticate it once.

**Install (Windows):**
```bash
winget install --id GitHub.cli -e        # requires admin (UAC elevation)
```
No admin rights? Use a portable install (no elevation):
```bash
# Download gh_<version>_windows_amd64.zip from https://github.com/cli/cli/releases
# unzip into %LOCALAPPDATA%\Programs\GitHubCLI, then add its \bin to the user PATH:
setx PATH "%PATH%;%LOCALAPPDATA%\Programs\GitHubCLI\bin"
```
(macOS: `brew install gh` · Linux: see the install docs. Restart the terminal after install so `gh` is on `PATH`.)

**Authenticate (one-time, interactive):**
```bash
gh auth login      # GitHub.com → HTTPS → log in via browser, grant the 'repo' scope
gh auth status     # verify
```

**No `gh`?** You can still open PRs via the GitHub web UI (`git push` prints a ready PR link) or the VS Code "GitHub Pull Requests" extension.

### Phase 1: Feature Development (Tests Optional)

When the change affects documentation traceability or CI behaviour, also update the relevant docs and run the local CI-equivalent checks before opening the pull request:

```bash
ruff check src_timesheetalgo tests
black --check src_timesheetalgo tests
python .github/scripts/generate_traceability_matrix.py
```

1. **Create feature branch** (always from `master`):
   ```bash
   git checkout -b feature/PRO-123-description master
   ```

2. **Make changes** and commit with Conventional Commits:
   ```bash
   git commit -m "feat(scope): description

   Refs: PRO-123"
   ```

3. **Push to branch**:
   ```bash
   git push origin feature/PRO-123-description
   ```

**Test requirement on feature branch:** No tests required (pure development/experimentation zone)

### Phase 1a: Switching Between Branches & Environment Management

**Important:** When switching between branches, you need to reactivate your virtual environment to ensure consistency.

#### Switching to a Different Branch:

```bash
# 1. Switch to the target branch
git checkout feature/PRO-123-description

# 2. Reactivate the virtual environment
source /workspaces/TimeSheet/.venv/bin/activate  # Linux/macOS
# or on Windows:
# .venv\Scripts\activate

# 3. Verify you're on the correct branch and environment
git branch --show-current     # Should show: feature/PRO-123-description
echo $VIRTUAL_ENV             # Should show: /workspaces/TimeSheet/.venv
```

#### Switching back to Master:

```bash
# 1. Switch to master
git checkout master

# 2. Reactivate the virtual environment
source /workspaces/TimeSheet/.venv/bin/activate

# 3. Verify
git branch --show-current     # Should show: master
```

#### Quick Alias for Branch Switching:

Create a shell alias for faster branch switching with automatic venv reactivation:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias switch-branch='function(){
  git checkout $1
  source /workspaces/TimeSheet/.venv/bin/activate
  echo "✅ Switched to branch: $(git branch --show-current)"
  echo "✅ venv activated: $VIRTUAL_ENV"
}; function'

# Usage:
switch-branch feature/PRO-123-description
switch-branch master
```

#### Documentation Traceability Maintenance

When a new requirement or implementation change is introduced, update the traceability chain in the same change:

1. Add or update the requirement ID in [doc/REQUIREMENTS.md](REQUIREMENTS.md).
2. Update the corresponding row in the traceability matrix in [doc/ARCHITECTURE.md](ARCHITECTURE.md).
3. Add the requirement ID to the relevant implementation function or class in [src_timesheetalgo/TimeSheetAlgo.py](../src_timesheetalgo/TimeSheetAlgo.py).
4. Re-run the relevant unit tests so the documentation and implementation remain aligned.

This keeps the documentation lightweight and reproducible without introducing external tooling.

#### Understanding venv Independence:

⚠️ **Important Concept:**
- The virtual environment (`.venv/`) is **independent of Git branches**
- It's stored in `.gitignore` and not tracked by Git
- When you switch branches, the `.venv/` directory doesn't change
- This is why you need to **reactivate** it for shell consistency
- The `.venv/` works across all branches automatically

**Recommended Practice:**
- Always reactivate venv when switching branches
- This ensures shell prompt and environment variables are consistent with your current branch
- You don't need to reinstall packages when switching branches

### Phase 2: Integration to Master - Quality Gate (Tests REQUIRED)

4. **Open pull request to `master`**:
   ```bash
   gh pr create --base master --title "[feat][PRO-123] Clear description"
   ```
   - All PRs must target `master`
   - PR title: `[type][PRO-123] Description`
   - PR body should include a short `## Summary` section with bullet points, a `## Testing` section with the exact validation commands, and an optional `## Notes` section when rollout or risk context matters

   Example structure:
   ```md
   ## Summary
   - what changed
   - why it matters

   ## Testing
   - command 1
   - command 2
   ```

5. **Wait for review and CI checks** (ALL required):
   - ✅ Lint checks (Ruff, Black, Pydocstyle, Radon) - **REQUIRED**
   - ✅ Unit tests - **REQUIRED**
   - ✅ Code coverage meets standards - **REQUIRED**
   - ✅ At least one approval required - **REQUIRED**

6. **Merge PR to `master`** after successful checks and approval:
   ```bash
   gh pr merge <PR_NUMBER> --merge
   ```
   - Master always remains stable and fully tested

### Phase 3: Release Deployment (Production Only)

7. **Create release branch** from `master` (already passed all tests):
   ```bash
   git checkout -b release/vX.Y.Z master
   ```

8. **Update version numbers** and create final commits:
   ```bash
   git commit -am "chore(release): bump version to vX.Y.Z

   Refs: PRO-123"
   ```

9. **Open pull request** targeting `master`:
   ```bash
   gh pr create --base master --title "[release][PRO-123] vX.Y.Z"
   ```

10. **After approval and merge**, create git tag:
    ```bash
    git tag vX.Y.Z
    git push origin vX.Y.Z
    ```

11. **Deployment to Production** (only on release tags):
    - Code has already passed all tests
    - Deployment does not cause additional tests
    - Automated or manual per deployment pipeline

### Workflow Overview by Phase and Testing Requirements

| Phase | Branch | Target | Tests | Deployment |
|-------|--------|--------|--------|-----------|
| **Phase 1: Feature Development** | feature/* | - | Optional | ❌ |
| **Phase 2: Integration to Master** | feature/* → PR | master | ✅ **REQUIRED** | ❌ |
| **Phase 3: Release Preparation** | master → release/vX.Y.Z | - | (Inherited, already tested) | ❌ |
| **Phase 3: Production Deployment** | release/vX.Y.Z → Tag | Production | (Already tested) | ✅ **DEPLOYMENT ONLY** |

### Attempting to Push Directly to Protected Branch:

If you try to push directly to a protected branch:

```bash
$ git push origin master
remote: error: GH006: Protected branch update failed for refs/heads/master.
remote: error: You have insufficient permissions to push to this branch on this repository.
```

**Solution:** Create a feature branch, make changes, open PR, and merge after successful tests (Lint + Unit Tests).

---

### GitHub Actions Workflow Enforcement

The CI/CD pipeline (`.github/workflows/python-ci.yml`) enforces these naming validations:

#### Commit Message Validation
- ✅ **Conventional Commits standard**: `type(scope): description`
- ✅ **Required JIRA reference**: `Refs: PRO-XXX` for commits with JIRA tickets
- ✅ **Allowed types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `ci`, `build`
- ✅ **Validation**: Performed via `commitlint` action using `.commitlintrc.json` at the start of the `lint` job

#### Pull Request Title Validation
- ✅ **Format**: `[type][PRO-XXX] Description`
- ✅ **Allowed types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `hotfix`
- ✅ **Validation**: Regex-based validation via `actions/github-script` in the `lint` job

#### Pull Request Description Validation
- ✅ **Mandatory sections**: `## Summary` and `## Testing`
- ✅ **Optional section**: `## Notes` (recommended for rollout context)
- ✅ **Placeholder check**: Automatically fails if TODO, TBD, etc. are present
- ✅ **Validation**: Performed via `actions/github-script` in the `lint` job

#### Workflow Behavior
- ✅ **Order**: The `check` job checks out and sets up Python via the reusable composite action, then runs the naming/metadata validators, then the lint tools
- ✅ **Timing**: Validation runs for every relevant PR event
- ✅ **Failure**: Invalid names fail the workflow immediately, blocking linting and testing
- ✅ **Blocks**: Merging through the existing **Python CI** status check

### Testing Strategy:
- ➖ **Development Branches** (push): No CI on branch pushes — checks run on the pull request, so a branch with an open PR is validated once instead of twice
- ✅ **Master PRs** (required): **Full tests required** (Lint + Unit Tests + Code Coverage)
- ✅ **Release Branches** (inherited): Tests already run on Master

### Quality-Gate Result Publication:
- ✅ **Master PRs**: a dedicated `publish` job (`if: always()`) publishes a consolidated **quality-gate summary** (regenerated every run) in the job summary and as a sticky PR comment. It opens with the overall result and a status-overview table (Lint + the steps, un-numbered), then sections — **Traceability** (0–100%; matrix embedded in the job summary, linked in the comment), **Testing** (split into **Application Tests** (unit/integration/system) and **CI-Pipeline Tests** (`.github/tests/ci-pipeline/` + `.github/tests/agents/`), each with its own pass-rate %, status and test per-level table), **Code Coverage** (% vs. the 90% gate), **Artifacts** (run, matrix, JUnit/coverage, htmlcov).
- ✅ Two comments per run (Option C): the full report as a **sticky** comment updated in place (with an `_Updated: … UTC_` timestamp), plus a compact **per-run comment** (overall result + overview table) posted fresh each run for a per-run trail. Because `publish` is separate and `if: always()`, a comment is posted on **every** run — including when `check` (lint/naming) fails and `test` is skipped.
- ℹ️ The `publish` job is **non-gating** — it only reports results; the merge is still gated by the `check` and `test` jobs. See [TESTING.md](TESTING.md#pull-request-quality-gate-summary).

### Deployment Strategy:
- ❌ **Development Branches**: No deployment
- ❌ **Master Branch**: No deployment
- ✅ **Release Tags** (vX.Y.Z): **Production deployment only**

### CI Timing Benchmark:
- A separate `ci-timing.yml` workflow continuously captures per-job / per-step execution
  times from successful `python-ci.yml` runs and persists them on the orphan
  `ci-metrics` branch (see `doc/01_Implementation_Plan_CI_Timing_Benchmark.md`).
- **Non-gating**: it never fails a PR. Results are purely observational.
- **No CI loop**: `python-ci.yml` does not trigger on push to `ci-metrics`.
- Data source: GitHub Actions API (`started_at` / `completed_at`), no instrumentation.
- Run `workflow_dispatch` with `backfill: true` to seed the initial dataset.

### Push Events trigger on:
- **Tags `vX.Y.Z`** (Production deployment) — branch pushes do **not** trigger CI
- Manual runs are available via `workflow_dispatch`

### PR Events trigger on:
- All target branches, especially:
  - **`master`** (Lint + Unit Tests + Code Coverage required)
  - **`release/*`** (Lint checks)
- A `concurrency` group supersedes an in-progress run when a new commit is pushed to the same PR

### Release/Deployment Events trigger on:
- **Tags `vX.Y.Z`** (Production Deployment)

### Workflow Model (Feature → Master → Release → Deployment):

```
feature/PRO-123          PR (Master)           master              release/vX.Y.Z        Tags vX.Y.Z
   ↓                        ↓                     ↓                    ↓                     ↓
[Development]  →  [Testing required]  →  [Stable, Tested]  →  [Release Branch]  →  [Production]
   ↓                  (Lint+Tests)          (Ready for PR)       (vX.Y.Z)              (Deployment)
Direct Push          Protected              Protected            Protected              Auto/Manual
                                                                                       Deployment
```

**Process:**
1. Feature development on `feature/PRO-123-xyz` (direct pushes allowed)
2. PR to `master` (tests required) - Lint + Unit Tests + Code Coverage
3. After successful merge: Master is stable and tested
4. Create release branch `release/vX.Y.Z` from Master
5. Create tag `vX.Y.Z` (marks release)
6. Deployment runs automatically on release tags (or manually)

---

## 9. Code Quality Requirements

All PRs must meet these requirements:

### 1. Lint Checks:
- ✅ **Ruff** - Python linter
- ✅ **Black** - Code formatter
- ✅ **Pydocstyle** - Docstring validator
- ✅ **Radon** - Complexity analyzer

### 2. Testing:
- ✅ All unit tests pass
- ✅ Code coverage maintained

### 3. Review:
- ✅ At least one approval
- ✅ No pending review requests

---

## 10. Quick Reference

| Type | Branch | PR Title | Commit | Protected |
|-----|--------|---------|--------|-----------|
| Feature | `feature/PRO-123-desc` | `[feat][PRO-123] Description` | `feat(scope): desc` | ❌ |
| Bugfix | `bugfix/PRO-123-desc` | `[fix][PRO-123] Description` | `fix(scope): desc` | ❌ |
| Hotfix | `hotfix/PRO-123-desc` | `[hotfix][PRO-123] Description` | `fix(scope): desc` | ❌ |
| Refactor | `refactor/PRO-123-desc` | `[refactor][PRO-123] Description` | `refactor(scope): desc` | ❌ |
| Docs | `docs/PRO-123-desc` | `[docs][PRO-123] Description` | `docs(scope): desc` | ❌ |
| Test | `test/PRO-123-desc` | `[test][PRO-123] Description` | `test(scope): desc` | ❌ |
| Release | `release/vX.Y.Z` | `[release][PRO-123] vX.Y.Z` | `chore(release): vX.Y.Z` | ✅ |
| Main | `master` | N/A | N/A | ✅ |

---

## 11. Additional Resources

- **Branch Protection Settings**: GitHub Repository Settings → Branches → Branch Protection Rules
- **GitHub Actions Workflow**: `.github/workflows/python-ci.yml`
- **Conventional Commits**: https://www.conventionalcommits.org/en/v1.0.0/
- **Semantic Versioning**: https://semver.org/

