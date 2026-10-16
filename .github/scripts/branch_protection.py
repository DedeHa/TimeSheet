#!/usr/bin/env python3
"""Manage required status checks on protected branches (PRO-386).

Branch protection for ``master`` (and ``release/**``) is a GitHub repository
setting, not a file in this repository. This script makes the required status
checks **declarative, auditable, and testable** by:

1. Holding the canonical list of required status check context names in
   :data:`REQUIRED_STATUS_CHECKS` - the single source of truth for
   :ref:`AC-2` (the ``Naming Conventions & Linting Check`` job must be
   required) and the regression guard in
   ``tests/ci-pipeline/test_branch_protection.py`` (ref :ref:`AC-3`).
2. Providing a ``verify`` subcommand that queries the GitHub API
   (``GET /repos/{owner}/{repo}/branches/{branch}/protection``) and asserts
   that ``required_status_checks.checks`` is non-empty and contains every
   required context. This is the API-based verification required by
   :ref:`AC-4`.
3. Providing an ``apply`` subcommand that sets the branch protection via
   ``PUT /repos/{owner}/{repo}/branches/{branch}/protection`` with the
   required checks.

Context name format
-------------------

A status check context is rendered by GitHub as ``<workflow_name> /
<job_name>``. The naming/lint job in ``python-ci.yml`` is named
``Naming Conventions & Linting Check`` and runs in the ``Python CI``
workflow, so the context is ``Python CI / Naming Conventions & Linting Check``.

Usage
-----

    python .github/scripts/branch_protection.py verify [--branch master]
    python .github/scripts/branch_protection.py apply --branch master

Exit codes
----------

    0  - all checks pass
    1  - one or more checks fail

Environment variables
---------------------

    GITHUB_REPOSITORY - owner/repo, e.g. mainhatten/TimeSheet
    GITHUB_TOKEN      - used by ``gh api`` (required for verify/apply)

Standard library only (``json``, ``argparse``, ``subprocess`` for ``gh api``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

# ---------------------------------------------------------------------------
# Configuration - source of truth for required status checks on protected
# branches.
# ---------------------------------------------------------------------------

#: Required status check context names (full ``<workflow> / <job>`` context).
#:
#: The CI workflow ``python-ci.yml`` exposes the job named ``Naming Conventions
#: & Linting Check`` under the workflow ``Python CI``, which GitHub renders as
#: the status check context below. This must be required on every protected
#: branch so a failed CI quality gate blocks the merge to ``master``.
REQUIRED_STATUS_CHECKS: list[str] = [
    "Python CI / Naming Conventions & Linting Check",
]

#: Protected branches that must enforce the checks in
#: :data:`REQUIRED_STATUS_CHECKS`. ``master`` is required; ``release/**``
#: branches are protected by the same rule - run ``apply``/``verify`` with
#: ``--branch`` for each release branch.
PROTECTED_BRANCHES: list[str] = [
    "master",
]

#: Enforcement level applied when branch protection is set. ``non_admins``
#: means administrators are also subject to the status check requirement.
ENFORCEMENT_LEVEL: str = "non_admins"

#: Strict mode: all checks must pass in a single commit push.
STRICT: bool = True


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _gh_api(path: str) -> object:  # pragma: no cover
    """Fetch JSON from the GitHub API via the ``gh`` CLI (thin wrapper).

    Retries on transient failures with exponential backoff (up to 3 attempts).
    """
    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            out = subprocess.run(
                ["gh", "api", "--paginate", path],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            return json.loads(out)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)


def get_owner_repo() -> str:  # pragma: no cover
    """Return the repository identifier ``owner/repo``."""
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,name"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            "ERROR: GitHub CLI error; are you authenticated with gh?",
            file=sys.stderr,
        )
        raise SystemExit(1)
    parsed = json.loads(result.stdout)
    return f"{parsed['owner']['login']}/{parsed['name']}"


# ---------------------------------------------------------------------------
# Branch protection operations
# ---------------------------------------------------------------------------


def get_protection(owner_repo: str, branch: str) -> dict:  # pragma: no cover
    """Fetch current branch protection for ``branch``.

    Returns the full protection config dict from
    ``GET /repos/{owner_repo}/branches/{branch}/protection``.
    """
    path = f"repos/{owner_repo}/branches/{branch}/protection"
    return _gh_api(path)


def extract_context_names(protection: dict) -> list[str]:
    """Extract the list of required check context names from a protection dict.

    Handles both the ``checks`` array form and the legacy ``contexts`` string
    form, returning an empty list when no required checks are configured.
    """
    rsc = protection.get("required_status_checks", {})
    if isinstance(rsc, dict):
        if "checks" in rsc:
            return [c["context"] for c in rsc["checks"] if isinstance(c, dict)]
        if "contexts" in rsc:
            return list(rsc["contexts"])
    return []


def verify(required: list[str], protection: dict, branch: str) -> list[str]:
    """Assert that the branch protection config for ``branch`` enforces ``required``.

    Checks:
    1. ``required_status_checks`` is configured (not ``None``).
    2. The list of required contexts is **non-empty** (regression guard: an
       empty list lets any CI check fail without blocking the merge).
    3. Every context in ``required`` is present in the configured list.

    Returns a list of error strings (empty if all required contexts are present
    and the list is non-empty).
    """
    errors: list[str] = []
    if not protection:
        errors.append(f"no branch protection configured for {branch}")
        return errors
    configured = extract_context_names(protection)
    if not configured:
        errors.append(
            f"{branch}: required_status_checks.checks is EMPTY - "
            f"CI checks cannot block the merge"
        )
        return errors
    missing = [c for c in required if c not in configured]
    if missing:
        errors.append(
            f"{branch}: missing required checks {missing}; "
            f"current required checks are {configured}"
        )
    return errors


def apply_protection(  # pragma: no cover
    owner_repo: str,
    branch: str,
    checks: list[str] | None = None,
    enforcement_level: str = ENFORCEMENT_LEVEL,
    strict: bool = STRICT,
) -> None:
    """Set required status checks on ``branch`` via the GitHub API.

    Uses ``PUT /repos/{owner_repo}/branches/{branch}/protection`` with the
    context names from :data:`REQUIRED_STATUS_CHECKS` by default.
    """
    path = f"repos/{owner_repo}/branches/{branch}/protection"
    payload = {
        "required_status_checks": {
            "checks": [{"context": c} for c in checks or REQUIRED_STATUS_CHECKS],
            "strict": strict,
        },
        "enforcement_level": enforcement_level,
    }
    subprocess.run(
        ["gh", "api", "--method", "PUT", path, "-f", json.dumps(payload)],
        check=True,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_verify(args: argparse.Namespace) -> int:
    """Run the verify subcommand."""
    owner_repo = get_owner_repo()
    branches = args.branches or PROTECTED_BRANCHES
    exit_code = 0
    for branch in branches:
        try:
            protection = get_protection(owner_repo, branch)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            print(
                f"ERROR: failed to fetch branch protection for {branch}: {exc}",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        errors = verify(REQUIRED_STATUS_CHECKS, protection, branch)
        configured = extract_context_names(protection)
        if errors:
            exit_code = 1
            for error in errors:
                print(f"FAIL: {error}")
        else:
            print(
                f"OK: {branch} - {len(configured)} required check(s) configured, "
                f"all {len(REQUIRED_STATUS_CHECKS)} required context(s) present"
            )
    return exit_code


def cmd_apply(args: argparse.Namespace) -> int:
    """Run the apply subcommand."""
    owner_repo = get_owner_repo()
    branches = args.branches or PROTECTED_BRANCHES
    exit_code = 0
    for branch in branches:
        try:
            apply_protection(
                owner_repo,
                branch,
                enforcement_level=args.enforcement_level,
                strict=args.strict,
            )
            print(
                f"OK: set required status checks on {branch}: "
                f"{REQUIRED_STATUS_CHECKS}"
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"ERROR: failed to update branch protection for {branch}: {exc.stderr}",
                file=sys.stderr,
            )
            exit_code = 1
    return exit_code


def main() -> int:
    """CLI entry point: subcommands ``verify`` and ``apply``."""
    parser = argparse.ArgumentParser(
        description="Manage required status checks on protected branches (PRO-386)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify", help="Verify required status checks on protected branches"
    )
    verify_parser.add_argument(
        "--branch",
        dest="branches",
        action="append",
        default=None,
        help="branch to verify (can be passed multiple times; "
        "defaults to PROTECTED_BRANCHES)",
    )
    verify_parser.set_defaults(func=cmd_verify)

    apply_parser = subparsers.add_parser(
        "apply", help="Set required status checks on protected branches"
    )
    apply_parser.add_argument(
        "--branch",
        dest="branches",
        action="append",
        default=None,
        help="branch to update (can be passed multiple times; "
        "defaults to PROTECTED_BRANCHES)",
    )
    apply_parser.add_argument(
        "--enforcement-level",
        default=ENFORCEMENT_LEVEL,
        help="enforcement level (default: non_admins)",
    )
    apply_parser.add_argument(
        "--strict",
        action="store_true",
        default=STRICT,
        help="require strict mode (default: True)",
    )
    apply_parser.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
