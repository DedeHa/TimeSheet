"""Tests for the agent-team handoff protocol.

Validates that handoff prompts carry the required placeholders, cycle
tracking, escalation context, and agent references so that the pipeline can
chain agents without losing state between handoffs.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[3]
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


def _placeholders(prompt: str) -> set[str]:
    """Return all ``{{placeholder}}`` tokens in a prompt."""
    return set(re.findall(r"\{\{([^}]+)\}\}", prompt))


def _agent_name_to_file() -> dict[str, Path]:
    """Return {agent_name: agent_file_path}."""
    result: dict[str, Path] = {}
    for path in sorted(_AGENTS_DIR.glob("*.agent.md")):
        fm = _parse_agent_frontmatter(path)
        result[fm["name"]] = path
    return result


# ---------------------------------------------------------------------------
# Handoff placeholder extraction
# ---------------------------------------------------------------------------


def test_handoff_placeholders_are_extracted_from_prompts():
    """Handoff prompts must declare every placeholder they consume."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    request_review = handoffs["Request Architecture Review"]
    placeholders = _placeholders(request_review["prompt"])
    assert "output" in placeholders
    assert "plan_output" not in placeholders


def test_plan_handoff_carries_plan_output_placeholder():
    """Dispatch Developer handoff must carry the architect plan."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    dispatch = handoffs["Dispatch Developer"]
    placeholders = _placeholders(dispatch["prompt"])
    assert "plan_output" in placeholders


def test_tester_handoff_carries_developer_output_and_acceptance_criteria():
    """Dispatch Tester handoff must carry the implementation and the ACs."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    dispatch = handoffs["Dispatch Tester"]
    placeholders = _placeholders(dispatch["prompt"])
    assert "developer_output" in placeholders
    assert "acceptance_criteria" in placeholders


def test_escalation_handoff_carries_required_context():
    """Escalation handoff must carry agent, report, ticket, cycle, and blocker."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    escalate = handoffs["Escalate to Product Owner"]
    placeholders = _placeholders(escalate["prompt"])
    required = {
        "current_agent",
        "agent_report",
        "ticket",
        "cycle_number",
        "last_action",
        "blocker",
    }
    assert required <= placeholders


def test_final_review_handoff_carries_validation_and_status_placeholders():
    """Final Review handoff must carry validation results and status fields."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    review = handoffs["Final Review"]
    placeholders = _placeholders(review["prompt"])
    required = {
        "validation_result",
        "ac_status",
        "plan_status",
        "gate_status",
        "pr_status",
        "summary",
        "test_summary",
        "remaining",
    }
    assert required <= placeholders


# ---------------------------------------------------------------------------
# Cycle tracking
# ---------------------------------------------------------------------------


def test_cycle_tracking_placeholder_in_dispatch_prompts():
    """Developer and Tester dispatch prompts must carry cycle tracking."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    for label in ("Dispatch Developer", "Dispatch Tester"):
        placeholders = _placeholders(handoffs[label]["prompt"])
        assert "cycle_number" in placeholders


def test_cycle_limit_is_max_three_in_prompts():
    """All cycle-aware prompts must reference the max-3 limit."""
    agents = _all_agents()
    po = agents["product-owner-agent"]

    for handoff in po["handoffs"]:
        prompt = handoff["prompt"]
        if "cycle_number" in _placeholders(prompt):
            assert "max 3" in prompt


def test_escalation_handoff_includes_cycle_context():
    """Escalation handoff must include current cycle and max-3 context."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    escalate = handoffs["Escalate to Product Owner"]
    assert "cycle_number" in _placeholders(escalate["prompt"])
    assert "max 3" in escalate["prompt"]


# ---------------------------------------------------------------------------
# Escalation triggers
# ---------------------------------------------------------------------------


def test_escalation_handoff_lists_blocker_and_last_action():
    """Escalation handoff must carry blocker and last-action context."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    escalate = handoffs["Escalate to Product Owner"]
    placeholders = _placeholders(escalate["prompt"])
    assert "blocker" in placeholders
    assert "last_action" in placeholders


def test_escalation_handoff_requests_decision_and_next_step():
    """Escalation handoff must ask the Product Owner for a decision."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}

    escalate = handoffs["Escalate to Product Owner"]
    prompt = escalate["prompt"].lower()
    assert "decision" in prompt
    assert "next step" in prompt


# ---------------------------------------------------------------------------
# Handoff agent references
# ---------------------------------------------------------------------------


def test_handoff_agent_references_resolve_to_existing_agents():
    """Every handoff 'agent' reference must resolve to an existing agent file."""
    agents = _all_agents()
    known = set(agents)

    for agent_name, agent in agents.items():
        for handoff in agent.get("handoffs", []):
            target = handoff.get("agent")
            if target is None:
                continue
            # Normalize target name
            if target == "architect":
                target = "architect-agent"
            elif target == "developer":
                target = "developer-agent"
            elif target == "tester":
                target = "tester-agent"
            elif target == "product-owner":
                target = "product-owner-agent"

            assert target in known, (
                f"{agent_name} handoff '{handoff['label']}' references "
                f"unknown agent '{handoff.get('agent')}'"
            )


def test_handoff_labels_are_unique_and_non_empty():
    """Handoff labels must be unique within an agent and non-empty."""
    agents = _all_agents()

    for agent_name, agent in agents.items():
        labels = [h["label"] for h in agent.get("handoffs", [])]
        assert all(labels), f"{agent_name} has an empty handoff label"
        assert len(labels) == len(
            set(labels)
        ), f"{agent_name} has duplicate handoff labels: {labels}"


def test_po_handoffs_cover_architect_developer_tester_and_escalation():
    """Product Owner must have handoffs for all pipeline stages."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    labels = {h["label"] for h in po["handoffs"]}

    assert {
        "Request Architecture Review",
        "Dispatch Developer",
        "Dispatch Tester",
        "Escalate to Product Owner",
        "Final Review",
    } <= labels
