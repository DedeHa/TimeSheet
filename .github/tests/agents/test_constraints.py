"""Tests for agent boundary enforcement via constraints.

Validates that each agent's frontmatter carries the constraints that enforce
the boundaries between the Product Owner, Architect, Developer, and Tester.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[3]
_AGENTS_DIR = _REPO / ".github" / "agents"


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


def _constraints(agent_name: str, agents: dict[str, dict]) -> list[str]:
    """Return lower-cased constraint strings for an agent."""
    return [c.lower() for c in agents[agent_name].get("constraints", [])]


# ---------------------------------------------------------------------------
# Product Owner boundary enforcement
# ---------------------------------------------------------------------------


def test_po_must_not_dispatch_developer_without_architect_review():
    """PO must not dispatch the developer before architect review."""
    agents = _all_agents()
    constraints = _constraints("product-owner-agent", agents)
    assert any(
        "architect review" in c or "without architect" in c for c in constraints
    ), "PO must require architect review before developer dispatch"


def test_po_must_require_confirmation_before_closure_actions():
    """PO must require final agreement before closure actions."""
    agents = _all_agents()
    constraints = _constraints("product-owner-agent", agents)
    assert any(
        "final agreement" in c or "confirmation" in c for c in constraints
    ), "PO must require confirmation before final actions"


def test_po_must_not_dispatch_without_escalation():
    """PO must escalate when an agent reports a problem or the pipeline loops."""
    agents = _all_agents()
    constraints = _constraints("product-owner-agent", agents)
    assert any(
        "escalation" in c and "dispatch" in c for c in constraints
    ), "PO must not dispatch without escalation when problems occur"


def test_po_must_interrupt_when_agent_cannot_resolve_issue():
    """PO must interrupt and evaluate when an agent cannot resolve an issue."""
    agents = _all_agents()
    constraints = _constraints("product-owner-agent", agents)
    assert any("interrupt" in c or "evaluate" in c for c in constraints)


# ---------------------------------------------------------------------------
# Architect boundary enforcement
# ---------------------------------------------------------------------------


def test_architect_must_not_change_requirements():
    """Architect must not change the validated requirements."""
    agents = _all_agents()
    constraints = _constraints("architect-agent", agents)
    assert any("must not change requirements" in c for c in constraints)


def test_architect_must_not_implement_code():
    """Architect must not implement code."""
    agents = _all_agents()
    constraints = _constraints("architect-agent", agents)
    assert any("must not implement code" in c for c in constraints)


def test_architect_must_minimize_complexity():
    """Architect must minimize complexity."""
    agents = _all_agents()
    constraints = _constraints("architect-agent", agents)
    assert any("minimize complexity" in c for c in constraints)


# ---------------------------------------------------------------------------
# Developer boundary enforcement
# ---------------------------------------------------------------------------


def test_developer_must_only_modify_files_in_plan():
    """Developer must only modify files listed in the implementation plan."""
    agents = _all_agents()
    constraints = _constraints("developer-agent", agents)
    assert any(
        "only modify files" in c or "files specified" in c for c in constraints
    ), "Developer must only modify files specified in the plan"


def test_developer_must_not_change_architecture_without_approval():
    """Developer must not make architectural changes without approval."""
    agents = _all_agents()
    constraints = _constraints("developer-agent", agents)
    assert any(
        "architectural changes" in c and "approval" in c for c in constraints
    ), "Developer must not change architecture without architect approval"


def test_developer_must_reference_pro_ticket_in_commits():
    """Developer must reference the PRO ticket in every commit."""
    agents = _all_agents()
    constraints = _constraints("developer-agent", agents)
    assert any("pro ticket" in c for c in constraints)


def test_developer_must_keep_changes_minimal_and_scoped():
    """Developer must keep changes minimal and scoped."""
    agents = _all_agents()
    constraints = _constraints("developer-agent", agents)
    assert any("minimal and scoped" in c for c in constraints)


def test_developer_must_add_tests_per_testing_md():
    """Developer must add tests per TESTING.md requirements."""
    path = _AGENTS_DIR / "developer.agent.md"
    content = path.read_text()
    assert "Write tests according to TESTING.md requirements" in content
    assert "MUST add comprehensive tests per TESTING.md" in content


# ---------------------------------------------------------------------------
# Tester boundary enforcement
# ---------------------------------------------------------------------------


def test_tester_must_not_approve_without_verification():
    """Tester must not approve without verifying all acceptance criteria."""
    agents = _all_agents()
    constraints = _constraints("tester-agent", agents)
    assert any(
        "approval" in c and "acceptance criteria" in c for c in constraints
    ), "Tester must not approve without verification of all acceptance criteria"


def test_tester_must_produce_reproducible_results():
    """Tester decisions must be reproducible."""
    agents = _all_agents()
    constraints = _constraints("tester-agent", agents)
    assert any("reproducible" in c for c in constraints)


def test_tester_must_be_data_driven():
    """Tester decisions must be data-driven."""
    agents = _all_agents()
    constraints = _constraints("tester-agent", agents)
    assert any("data-driven" in c for c in constraints)


def test_tester_must_not_ignore_test_failures():
    """Tester must not ignore test failures."""
    path = _AGENTS_DIR / "tester.agent.md"
    content = path.read_text()
    assert "Must NOT ignore test failures" in content


# ---------------------------------------------------------------------------
# Cycle limit enforcement
# ---------------------------------------------------------------------------


def test_cycle_limit_max_three_in_po_handoffs():
    """PO handoffs must enforce the max-3 cycle limit."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    content = po["name"] + " " + "\n".join(h["prompt"] for h in po["handoffs"])
    assert "max 3" in content, "PO must define max 3 cycles in dispatch handoffs"


def test_cycle_limit_max_three_in_developer_handoff():
    """Developer handoff must carry the cycle limit."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}
    assert "max 3" in handoffs["Dispatch Developer"]["prompt"]


def test_cycle_limit_max_three_in_tester_handoff():
    """Tester handoff must carry the cycle limit."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}
    assert "max 3" in handoffs["Dispatch Tester"]["prompt"]


def test_cycle_limit_max_three_in_escalation_handoff():
    """Escalation handoff must carry the cycle limit."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}
    assert "max 3" in handoffs["Escalate to Product Owner"]["prompt"]
