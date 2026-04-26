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

## 4. Pull Request Naming
- **Format:** `[Type][PRO-123] Clear description of changes`
- **Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `hotfix`
- **Description:** What is being changed? (max. 72 characters)
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

### Phase 1: Feature Development (Tests Optional)

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
source /workspaces/TimeSheet/venv/bin/activate  # Linux/macOS
# or on Windows:
# venv\Scripts\activate

# 3. Verify you're on the correct branch and environment
git branch --show-current     # Should show: feature/PRO-123-description
echo $VIRTUAL_ENV             # Should show: /workspaces/TimeSheet/venv
```

#### Switching back to Master:

```bash
# 1. Switch to master
git checkout master

# 2. Reactivate the virtual environment
source /workspaces/TimeSheet/venv/bin/activate

# 3. Verify
git branch --show-current     # Should show: master
```

#### Quick Alias for Branch Switching:

Create a shell alias for faster branch switching with automatic venv reactivation:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias switch-branch='function(){
  git checkout $1
  source /workspaces/TimeSheet/venv/bin/activate
  echo "✅ Switched to branch: $(git branch --show-current)"
  echo "✅ venv activated: $VIRTUAL_ENV"
}; function'

# Usage:
switch-branch feature/PRO-123-description
switch-branch master
```

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
   - PR should document description and changes in detail

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

## 8. GitHub Actions Workflow Enforcement

The CI/CD pipeline (`.github/workflows/python-ci.yml`) enforces these protections:

### Testing Strategy:
- ✅ **Development Branches** (push): Run lint checks
- ✅ **Master PRs** (required): **Full tests required** (Lint + Unit Tests + Code Coverage)
- ✅ **Release Branches** (inherited): Tests already run on Master

### Deployment Strategy:
- ❌ **Development Branches**: No deployment
- ❌ **Master Branch**: No deployment
- ✅ **Release Tags** (vX.Y.Z): **Production deployment only**

### Push Events trigger on:
- `feature/*`, `refactor/*`, `docs/*`, `test/*`, `bugfix/*`, `hotfix/*` (Lint checks)

### PR Events trigger on:
- All target branches, especially:
  - **`master`** (Lint + Unit Tests + Code Coverage required)
  - **`release/*`** (Lint checks)

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
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Semantic Versioning**: https://semver.org/
