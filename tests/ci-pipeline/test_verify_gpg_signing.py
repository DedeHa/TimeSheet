"""Structural verification of the GPG signing composite action (PRO-370).

Validates that the setup-gpg-signing action is properly configured for GitHub
releases to show "This commit was created on GitHub.com and signed with GitHub's
verified signature". Can be run locally with::

    pytest -q tests/ci-pipeline/test_verify_gpg_signing.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github" / "actions" / "setup-gpg-signing" / "action.yml"


def _action() -> dict:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def test_gpg_signing_action_exists():
    """The PRO-370 GPG signing action must be present."""
    assert ACTION.exists(), f"{ACTION} is missing"


def test_action_has_proper_metadata():
    """The action has name, description and composite execution."""
    action = _action()
    assert action.get("name") == "Setup GPG Signing"
    assert "description" in action
    assert action["runs"]["using"] == "composite"


def test_action_configures_git_signing():
    """The action must configure git to sign commits and tags."""
    action = _action()
    steps = action["runs"]["steps"]
    run_steps = [s for s in steps if "run" in s]
    assert run_steps, "no run steps found"

    config_step = next((s for s in run_steps if "git config" in s.get("run", "")), None)
    assert config_step is not None, "git config step missing"
    run_text = config_step["run"]
    assert "commit.gpgsign" in run_text
    assert "tag.gpgsign" in run_text
    assert "gpg.program gh-gpgsign" in run_text


def test_action_installs_gpg_tools():
    """The action must install GPG tools."""
    action = _action()
    steps = action["runs"]["steps"]
    run_steps = [s for s in steps if "run" in s]
    apt_step = next(
        (
            s
            for s in run_steps
            if "apt-get" in s.get("run", "") and "gnupg" in s.get("run", "")
        ),
        None,
    )
    assert apt_step is not None, "GPG tools installation step missing"


def test_action_has_verification_step():
    """The action must verify signing capability after setup."""
    action = _action()
    steps = action["runs"]["steps"]
    run_steps = [s for s in steps if "run" in s]

    verify_step = next(
        (
            s
            for s in run_steps
            if "verify" in s.get("name", "").lower()
            or "signing capability" in s.get("run", "")
        ),
        None,
    )
    assert verify_step is not None, "signing verification step missing"


def test_action_defines_required_inputs():
    """The action must define gpg-key-id, signing-key and github-token inputs."""
    action = _action()
    inputs = action.get("inputs", {})
    assert "gpg-key-id" in inputs
    assert "signing-key" in inputs
    assert "github-token" in inputs


def test_action_authenticates_gh_cli():
    """The action must authenticate GitHub CLI when token is provided."""
    action = _action()
    steps = action["runs"]["steps"]
    run_steps = [s for s in steps if "run" in s]

    auth_step = next(
        (s for s in run_steps if "gh auth" in s.get("run", "")),
        None,
    )
    assert auth_step is not None, "GitHub CLI authentication step missing"
    assert "github-token" in auth_step.get("if", "")


def test_action_handles_key_import():
    """The action must conditionally import GPG key when provided."""
    action = _action()
    steps = action["runs"]["steps"]
    run_steps = [s for s in steps if "run" in s]

    import_step = next(
        (s for s in run_steps if "gpg --batch --import" in s.get("run", "")),
        None,
    )
    assert import_step is not None, "GPG key import step missing"
    assert "signing-key" in import_step.get("if", "")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
