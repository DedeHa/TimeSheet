"""Tests for the agent-team orchestration infrastructure.

Validates the ``orchestrate-feature`` skill, agent definitions, and pipeline
handoffs work together as designed. Like the other CI self-test files, this
lives under ``.github/tests/agents/`` (not in ``tests/``), so it does not
change the 103-test application suite or the coverage gate.

Run with::

    pytest -q .github/tests/agents/test_orchestration.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[3]
_SKILLS_DIR = _REPO / ".opencode/skills"
_AGENTS_DIR = _REPO / ".github/agents"
_PO_AGENT = _AGENTS_DIR / "product-owner.agent.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its parsed content."""
    with open(path) as fh:
        return yaml.safe_load(fh)


def _load_skills_frontmatter() -> dict[str, dict]:
    """Return {skill_name: frontmatter} for every .opencode/skill.

    The ``name:`` field in each frontmatter is the canonical skill key.
    """
    result: dict[str, dict] = {}
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        fpath = skill_dir / "SKILL.md"
        if not fpath.exists():
            continue
        content = fpath.read_text()
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1))
        result[fm["name"]] = fm
    return result


def _parse_agent_frontmatter(path: Path) -> dict:
    """Parse the YAML frontmatter of an agent file."""
    content = path.read_text()
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    assert m, f"No frontmatter in {path}"
    return yaml.safe_load(m.group(1))


# ---------------------------------------------------------------------------
# Skill existence & structure
# ---------------------------------------------------------------------------


def test_orchestrate_skill_exists():
    """``orchestrate-feature`` skill directory and SKILL.md must exist."""
    skill_path = _SKILLS_DIR / "orchestrate-feature" / "SKILL.md"
    assert skill_path.exists(), "orchestrate-feature/SKILL.md is missing"


def test_orchestrate_skill_valid_frontmatter():
    """orchestrate-feature SKILL.md must have parseable YAML frontmatter."""
    skill_path = _SKILLS_DIR / "orchestrate-feature" / "SKILL.md"
    content = skill_path.read_text()
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    assert m, "orchestrate-feature SKILL.md has no YAML frontmatter"
    fm = yaml.safe_load(m.group(1))
    assert "name" in fm, "orchestrate-feature frontmatter missing 'name'"
    assert (
        fm["name"] == "orchestrate-feature"
    ), f"expected name 'orchestrate-feature', got {fm['name']!r}"
    assert "description" in fm, "orchestrate-feature frontmatter missing 'description'"


def test_orchestrate_skill_description_mentions_pipeline():
    """Description must reference the pipeline it orchestrates."""
    skills = _load_skills_frontmatter()
    desc = skills["orchestrate-feature"]["description"].lower()
    assert any(
        kw in desc for kw in ["pipeline", "orchestrat"]
    ), "description should mention 'pipeline' or 'orchestrat'"


# ---------------------------------------------------------------------------
# Skills registry consistency
# ---------------------------------------------------------------------------


def test_orchestrate_in_skills_registry():
    """orchestrate-feature must appear in the skills index (frontmatter name)."""
    skills = _load_skills_frontmatter()
    assert (
        "orchestrate-feature" in skills
    ), "orchestrate-feature not found in skills registry"


def test_orchestrate_has_required_phases():
    """orchestrate-feature skill entry in PO agent must declare all pipeline phases."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    orch_skill = next(s for s in fm["skills"] if s["name"] == "orchestrate-feature")
    phases = set(orch_skill.get("phases", []))
    expected = {
        "state-detection",
        "dispatch",
        "cycle-tracking",
        "escalation",
        "handoff-coordination",
    }
    assert expected <= phases, f"missing phases: {expected - phases}"


def test_orchestrate_invoke_always():
    """orchestrate-feature must use invoke: always in the PO agent."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    orch_skill = next(s for s in fm["skills"] if s["name"] == "orchestrate-feature")
    assert (
        orch_skill["invoke"] == "always"
    ), "orchestrate-feature must have invoke: always"


# ---------------------------------------------------------------------------
# Product Owner agent
# ---------------------------------------------------------------------------


def test_po_agent_exists():
    """product-owner.agent.md must exist."""
    assert _PO_AGENT.exists(), "product-owner.agent.md is missing"


def test_po_agent_has_orchestrate_skill():
    """Product Owner agent must reference orchestrate-feature skill."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    skill_names = [s["name"] for s in fm.get("skills", [])]
    assert (
        "orchestrate-feature" in skill_names
    ), "product-owner.agent.md does not list orchestrate-feature skill"


def test_po_orchestrate_is_first_skill():
    """orchestrate-feature must be the first skill in the Product Owner agent."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    skill_names = [s["name"] for s in fm.get("skills", [])]
    pos = skill_names.index("orchestrate-feature")
    assert pos == 0, f"orchestrate-feature must be first skill, got position {pos}"


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------


@pytest.fixture
def agent_files():
    """Return {agent_name: frontmatter} for every .github/agents/*.agent.md."""
    result = {}
    for path in sorted(_AGENTS_DIR.glob("*.agent.md")):
        fm = _parse_agent_frontmatter(path)
        result[fm["name"]] = fm
    return result


def test_all_agent_files_have_frontmatter(agent_files):
    """Every agent file must have parseable frontmatter."""
    expected = {
        "product-owner-agent",
        "architect-agent",
        "developer-agent",
        "tester-agent",
    }
    assert (
        set(agent_files.keys()) == expected
    ), f"agent files: {set(agent_files.keys())}"


def test_po_role_is_dispatcher(agent_files):
    """Product Owner role must be dispatcher/orchestrator."""
    desc = agent_files["product-owner-agent"]["description"].lower()
    assert (
        "dispatcher" in desc or "orchestrator" in desc
    ), "Product Owner must be dispatcher/orchestrator"


# ---------------------------------------------------------------------------
# Pipeline handoff constraints
# ---------------------------------------------------------------------------


def test_po_must_not_close_jira(agent_files):
    """Product Owner must NOT close JIRA tickets — reserved for user."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    constraints = [c.lower() for c in fm.get("constraints", [])]
    assert any(
        "must not close jira" in c for c in constraints
    ), "PO must have constraint: Must NOT close JIRA tickets"


def test_po_must_not_merge_pr(agent_files):
    """Product Owner must NOT merge PRs — reserved for user."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    constraints = [c.lower() for c in fm.get("constraints", [])]
    assert any(
        "merge pr" in c for c in constraints
    ), "PO must have constraint: Must NOT merge PRs"


def test_po_dispatch_after_architect_review(agent_files):
    """Product Owner must NOT dispatch developer without architect review."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    constraints = [c.lower() for c in fm.get("constraints", [])]
    has_constraint = any(
        "architect review" in c or "without architect" in c for c in constraints
    )
    assert (
        has_constraint
    ), "PO must have constraint: Must NOT dispatch developer without architect review"


def test_cycle_limit_max_three(agent_files):
    """Product Owner must define max 3 cycles in its dispatch handoffs."""
    content = _PO_AGENT.read_text()
    assert (
        "max 3" in content or "/ max 3" in content
    ), "PO agent must reference max 3 cycles in handoff prompts"


# ---------------------------------------------------------------------------
# Cross-reference consistency
# ---------------------------------------------------------------------------


def test_skill_paths_resolve():
    """Every skill referenced in agent frontmatter must have a file."""
    for agent_path in sorted(_AGENTS_DIR.glob("*.agent.md")):
        fm = _parse_agent_frontmatter(agent_path)
        for skill in fm.get("skills", []):
            skill_path = _REPO / skill["path"]
            assert skill_path.exists(), (
                f"{agent_path.name} references skill "
                f"{skill['path']} which does not exist"
            )


def test_orchestrate_skill_path_resolves():
    """orchestrate-feature skill path must resolve to the correct file."""
    fm = _parse_agent_frontmatter(_PO_AGENT)
    orch_skill = next(s for s in fm["skills"] if s["name"] == "orchestrate-feature")
    skill_path = _REPO / orch_skill["path"]
    assert (
        skill_path.exists()
    ), f"orchestrate-feature skill path {orch_skill['path']} does not exist"
