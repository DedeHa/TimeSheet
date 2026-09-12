"""Tests for end-to-end pipeline simulation.

Validates the agent-team pipeline behaviour without live JIRA calls:
full flow, cycle escalation, and error propagation through handoffs.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[3]
_AGENTS_DIR = _REPO / ".github" / "agents"
_SKILLS_DIR = _REPO / ".opencode" / "skills"


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


def _handoffs(agent_name: str, agents: dict[str, dict]) -> dict[str, dict]:
    """Return {label: handoff} for an agent."""
    return {h["label"]: h for h in agents[agent_name].get("handoffs", [])}


# ---------------------------------------------------------------------------
# Full pipeline flow simulation
# ---------------------------------------------------------------------------


def test_pipeline_flow_po_to_architect_to_developer_to_tester():
    """The pipeline must chain PO -> Architect -> Developer -> Tester."""
    agents = _all_agents()
    po_handoffs = _handoffs("product-owner-agent", agents)

    assert po_handoffs["Request Architecture Review"]["agent"] == "architect"
    assert po_handoffs["Dispatch Developer"]["agent"] == "developer"
    assert po_handoffs["Dispatch Tester"]["agent"] == "tester"


def test_pipeline_flow_po_never_bypassed():
    """Every agent handoff must route through the Product Owner."""
    agents = _all_agents()

    for agent_name, agent in agents.items():
        if agent_name == "product-owner-agent":
            continue
        for handoff in agent.get("handoffs", []):
            target = handoff.get("agent")
            if target is None:
                continue
            assert target in {"product-owner", "developer", "tester", "architect"}
            assert target == "product-owner" or handoff["label"] in {
                "Start Implementation",
                "Start Testing & Validation",
                "Request Fixes",
            }


def test_pipeline_flow_returns_to_po_after_testing():
    """Tester approval must hand off back to the Product Owner."""
    agents = _all_agents()
    handoffs = _handoffs("tester-agent", agents)

    assert "Approve & Complete" in handoffs
    assert "Request Fixes" in handoffs
    approve_prompt = handoffs["Approve & Complete"]["prompt"]
    assert "complete-feature" in approve_prompt
    assert "all acceptance criteria have been met" in approve_prompt.lower()
    assert "complete-feature" in handoffs["Approve & Complete"]["prompt"]


# ---------------------------------------------------------------------------
# Cycle escalation handling
# ---------------------------------------------------------------------------


def test_cycle_escalation_on_cycle_three():
    """Cycle 3 must escalate to the Product Owner."""
    agents = _all_agents()
    handoffs = _handoffs("product-owner-agent", agents)

    escalate = handoffs["Escalate to Product Owner"]
    assert "cycle_number" in escalate["prompt"]
    assert "max 3" in escalate["prompt"]


def test_cycle_escalation_on_cycle_greater_than_three():
    """Cycle > 3 must stop the agent and report to the Product Owner."""
    agents = _all_agents()
    handoffs = _handoffs("product-owner-agent", agents)

    dispatch = handoffs["Dispatch Developer"]
    assert "If cycle > 3, STOP" in dispatch["prompt"]

    dispatch_tester = handoffs["Dispatch Tester"]
    assert "If cycle > 3, STOP" in dispatch_tester["prompt"]


def test_cycle_escalation_carry_context_to_po():
    """Escalation handoff must carry context for PO evaluation."""
    agents = _all_agents()
    handoffs = _handoffs("product-owner-agent", agents)

    escalate = handoffs["Escalate to Product Owner"]
    prompt = escalate["prompt"]
    assert "{{current_agent}}" in prompt
    assert "{{agent_report}}" in prompt
    assert "{{ticket}}" in prompt
    assert "{{blocker}}" in prompt


# ---------------------------------------------------------------------------
# Error propagation through handoffs
# ---------------------------------------------------------------------------


def test_error_propagation_blocker_to_escalation():
    """A blocker reported by an agent must propagate to the escalation handoff."""
    agents = _all_agents()
    handoffs = _handoffs("product-owner-agent", agents)

    escalate = handoffs["Escalate to Product Owner"]
    assert "reported:" in escalate["prompt"]
    assert "{{agent_report}}" in escalate["prompt"]


def test_error_propagation_developer_to_tester():
    """Developer output must propagate to the Tester for validation."""
    agents = _all_agents()
    handoffs = _handoffs("product-owner-agent", agents)

    dispatch_tester = handoffs["Dispatch Tester"]
    assert "{{developer_output}}" in dispatch_tester["prompt"]


def test_error_propagation_tester_to_developer():
    """Tester issues must propagate back to the Developer for fixes."""
    agents = _all_agents()
    handoffs = _handoffs("tester-agent", agents)

    request_fixes = handoffs["Request Fixes"]
    assert "{{issues}}" in request_fixes["prompt"]
    assert request_fixes["agent"] == "developer"


def test_error_propagation_tester_to_completion():
    """Tester approval must propagate to the completion workflow."""
    agents = _all_agents()
    handoffs = _handoffs("tester-agent", agents)

    approve = handoffs["Approve & Complete"]
    assert "complete-feature" in approve["prompt"]
    assert "all acceptance criteria have been met" in approve["prompt"].lower()


def test_pipeline_flow_has_no_direct_architect_to_tester_handoff():
    """Architect must not bypass the Developer by handing off to Tester."""
    agents = _all_agents()
    architect = agents["architect-agent"]

    for handoff in architect.get("handoffs", []):
        assert handoff.get("agent") != "tester"


def test_pipeline_flow_has_no_direct_developer_to_architect_handoff():
    """Developer must not bypass the Tester by handing off to Architect."""
    agents = _all_agents()
    developer = agents["developer-agent"]

    for handoff in developer.get("handoffs", []):
        assert handoff.get("agent") != "architect"
