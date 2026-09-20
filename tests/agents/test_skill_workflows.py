"""Tests for skill workflow phase ordering.

Validates that each skill's phases are declared in the correct
execution order in the agent frontmatter, so that the pipeline
steps are predictable and consistent across the agent-team system.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]
_AGENTS_DIR = _REPO / ".opencode" / "agents"


def _parse_agent_frontmatter(path: Path) -> dict:
    """Parse the YAML frontmatter of an agent file."""
    content = path.read_text()
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    assert m, f"No frontmatter in {path}"
    return yaml.safe_load(m.group(1))


def _all_agents() -> dict[str, dict]:
    """Return {agent_name: frontmatter} for every agent file."""
    result: dict[str, dict] = {}
    for path in sorted(_AGENTS_DIR.glob("*.agent.md")):
        fm = _parse_agent_frontmatter(path)
        result[fm["name"]] = fm
    return result


def _skill_in_agent(agent_name: str, skill_name: str) -> dict:
    """Return the skill reference dict for a given agent."""
    agents = _all_agents()
    agent = agents[agent_name]
    for skill in agent["skills"]:
        if skill["name"] == skill_name:
            return skill
    raise KeyError(f"{skill_name} not found in {agent_name}")


# ---------------------------------------------------------------------------
# orchestrate-feature phase order (PO agent)
# ---------------------------------------------------------------------------


def test_orchestrate_feature_phases_in_po_agent():
    """orchestrate-feature must declare phases in the PO agent."""
    skill = _skill_in_agent("product-owner-agent", "orchestrate-feature")
    assert "phases" in skill, "orchestrate-feature must declare phases"
    assert len(skill["phases"]) >= 5


def test_orchestrate_feature_phase_order_in_po_agent():
    """orchestrate-feature phases must execute in pipeline order."""
    skill = _skill_in_agent("product-owner-agent", "orchestrate-feature")
    phases = skill["phases"]

    expected_order = [
        "state-detection",
        "dispatch",
        "cycle-tracking",
        "escalation",
        "handoff-coordination",
    ]
    for i, expected in enumerate(expected_order):
        assert phases[i] == expected


def test_orchestrate_feature_invoke_always_in_po_agent():
    """orchestrate-feature must use invoke: always in the PO agent."""
    skill = _skill_in_agent("product-owner-agent", "orchestrate-feature")
    assert skill["invoke"] == "always"


# ---------------------------------------------------------------------------
# develop-feature phase order (developer agent)
# ---------------------------------------------------------------------------


def test_develop_feature_phases_in_developer_agent():
    """develop-feature must declare phases in the developer agent."""
    skill = _skill_in_agent("developer-agent", "develop-feature")
    assert "phases" in skill, "develop-feature must declare phases"
    assert len(skill["phases"]) >= 4


def test_develop_feature_phase_order_in_developer_agent():
    """develop-feature phases must execute in implementation order."""
    skill = _skill_in_agent("developer-agent", "develop-feature")
    phases = skill["phases"]

    expected_order = [
        "prepare-branch",
        "implement-rollout",
        "final-verification",
        "open-pr",
    ]
    for i, expected in enumerate(expected_order):
        assert phases[i] == expected


def test_develop_feature_invoke_always_in_developer_agent():
    """develop-feature must use invoke: always in the developer agent."""
    skill = _skill_in_agent("developer-agent", "develop-feature")
    assert skill["invoke"] == "always"


# ---------------------------------------------------------------------------
# develop-feature phase order (architect agent)
# ---------------------------------------------------------------------------


def test_develop_feature_phases_in_architect_agent():
    """develop-feature must declare phases in the architect agent."""
    skill = _skill_in_agent("architect-agent", "develop-feature")
    assert "phases" in skill, "develop-feature must declare phases in architect"
    assert len(skill["phases"]) >= 2


def test_develop_feature_phase_order_in_architect_agent():
    """develop-feature phases must execute in architect planning order."""
    skill = _skill_in_agent("architect-agent", "develop-feature")
    phases = skill["phases"]

    expected_order = ["adopt-plan", "draft-plan"]
    for i, expected in enumerate(expected_order):
        assert phases[i] == expected


# ---------------------------------------------------------------------------
# complete-feature phase order (PO agent)
# ---------------------------------------------------------------------------


def test_complete_feature_phases_in_po_agent():
    """complete-feature must declare phases in the PO agent."""
    skill = _skill_in_agent("product-owner-agent", "complete-feature")
    assert "phases" in skill, "complete-feature must declare phases in PO agent"
    assert len(skill["phases"]) >= 4


def test_complete_feature_phase_order_in_po_agent():
    """complete-feature phases must execute in closure order."""
    skill = _skill_in_agent("product-owner-agent", "complete-feature")
    phases = skill["phases"]

    expected_order = [
        "final-verification",
        "evaluate-ac",
        "assign-story-points",
        "prepare-closure",
    ]
    for i, expected in enumerate(expected_order):
        assert phases[i] == expected


def test_complete_feature_invoke_after_testing_in_po_agent():
    """complete-feature must use invoke: after-testing."""
    skill = _skill_in_agent("product-owner-agent", "complete-feature")
    assert skill["invoke"] == "after-testing"


# ---------------------------------------------------------------------------
# complete-feature phase order (tester agent)
# ---------------------------------------------------------------------------


def test_complete_feature_phases_in_tester_agent():
    """complete-feature must declare phases in the tester agent."""
    skill = _skill_in_agent("tester-agent", "complete-feature")
    assert "phases" in skill, "complete-feature must declare phases in tester"
    assert len(skill["phases"]) >= 4


def test_complete_feature_phase_order_in_tester_agent():
    """complete-feature phases must execute in tester closure order."""
    skill = _skill_in_agent("tester-agent", "complete-feature")
    phases = skill["phases"]

    expected_order = [
        "final-verification",
        "evaluate-ac",
        "assign-story-points",
        "close-ticket",
    ]
    for i, expected in enumerate(expected_order):
        assert phases[i] == expected


def test_complete_feature_invoke_after_approval_in_tester_agent():
    """complete-feature must use invoke: after-approval in tester agent."""
    skill = _skill_in_agent("tester-agent", "complete-feature")
    assert skill["invoke"] == "after-approval"


# ---------------------------------------------------------------------------
# plan-feature phase order (PO agent)
# ---------------------------------------------------------------------------


def test_plan_feature_phases_in_po_agent():
    """plan-feature must declare phases in the PO agent."""
    skill = _skill_in_agent("product-owner-agent", "plan-feature")
    assert "phases" in skill, "plan-feature must declare phases"
    assert len(skill["phases"]) >= 4


def test_plan_feature_phase_order_in_po_agent():
    """plan-feature phases must execute in planning order."""
    skill = _skill_in_agent("product-owner-agent", "plan-feature")
    phases = skill["phases"]

    expected_order = [
        "ticket-creation",
        "ac-definition",
        "story-points-estimation",
        "backlog-refinement",
    ]
    for i, expected in enumerate(expected_order):
        assert phases[i] == expected


def test_plan_feature_invoke_always_in_po_agent():
    """plan-feature must use invoke: always in the PO agent."""
    skill = _skill_in_agent("product-owner-agent", "plan-feature")
    assert skill["invoke"] == "always"


def test_root_docs_share_same_canonical_lifecycle_contract():
    """AGENTS.md and AGENTS_WORKFLOW.md must describe the same canonical lifecycle."""
    root = (_REPO / "AGENTS.md").read_text()
    workflow = (_REPO / "doc" / "AGENTS_WORKFLOW.md").read_text()
    assert "backlog -> plan -> develop -> complete -> approved -> released" in root
    assert "backlog -> plan -> develop -> complete -> approved -> released" in workflow
    assert ".opencode/scripts/pipeline.py" in root
    assert "authoritative source of" in workflow


# ---------------------------------------------------------------------------
# Canonical workflow governance
# ---------------------------------------------------------------------------

_CANONICAL_LIFECYCLE = "backlog -> plan -> develop -> complete -> approved -> released"


def test_all_agents_reference_canonical_workflow_contract():
    """Every agent must reference the same canonical lifecycle contract."""
    for path in sorted((_REPO / ".opencode" / "agents").glob("*.agent.md")):
        content = path.read_text()
        assert _CANONICAL_LIFECYCLE in content, (
            f"{path.name} lacks the canonical workflow contract"
        )


def test_all_skills_reference_canonical_workflow_contract():
    """Every skill must use the same canonical lifecycle wording."""
    for path in sorted((_REPO / ".opencode" / "skills").glob("*/SKILL.md")):
        content = path.read_text()
        assert _CANONICAL_LIFECYCLE in content, (
            f"{path.relative_to(_REPO)} lacks the canonical workflow contract"
        )


def test_workflow_docs_are_split_by_role():
    """AGENTS.md stays user-facing while AGENTS_WORKFLOW holds operational detail."""
    root = (_REPO / "AGENTS.md").read_text()
    workflow = (_REPO / "doc" / "AGENTS_WORKFLOW.md").read_text()
    assert "user-facing entry point" in root.lower()
    assert "user interaction model" in root.lower()
    assert "detailed operational reference" in workflow.lower()
    assert "complete agent and skill catalog" in root.lower()
    assert "script responsibilities and dependencies" in root.lower()
    assert "state machine" in workflow.lower()


def test_all_operational_scripts_are_documented():
    """Every script in .opencode/scripts must be listed in the workflow reference."""
    workflow = (_REPO / "doc" / "AGENTS_WORKFLOW.md").read_text()
    scripts = sorted((_REPO / ".opencode" / "scripts").glob("*.py"))
    for path in scripts:
        assert str(path.relative_to(_REPO)) in workflow, (
            f"{path.relative_to(_REPO)} is not documented in AGENTS_WORKFLOW.md"
        )


def test_workflow_dependency_references_exist():
    """Documented agent, skill, and script paths must resolve in the repository."""
    workflow = (_REPO / "doc" / "AGENTS_WORKFLOW.md").read_text()
    expected_paths = [
        ".opencode/scripts/pipeline.py",
        ".opencode/scripts/detect_mode.py",
        ".opencode/scripts/migrate_pipeline_state.py",
        ".opencode/scripts/verify_migration.py",
        ".opencode/scripts/pre_closure_validation.py",
    ]
    for relative_path in expected_paths:
        assert relative_path in workflow
        assert (_REPO / relative_path).exists()


def test_user_guide_does_not_duplicate_operational_catalog():
    """The user guide should link to, not reproduce, the operational catalog."""
    root = (_REPO / "AGENTS.md").read_text()
    assert "complete agent and skill catalog" in root
    assert "script responsibilities and dependencies" in root
    assert ".opencode/agents/*.agent.md" not in root
    assert ".opencode/skills/*/SKILL.md" not in root
