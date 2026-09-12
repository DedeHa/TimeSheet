"""Tests for agent output format validation.

Validates that each agent's markdown output template contains every
required section, so downstream consumers (human or automated) can
rely on a stable contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[3]
_AGENTS_DIR = _REPO / ".opencode" / "agents"
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


def _agent_body(agent_name: str) -> str:
    """Return the markdown body (after frontmatter) of an agent file."""
    file_name = agent_name.replace("-agent", "") + ".agent.md"
    path = _AGENTS_DIR / file_name
    content = path.read_text()
    m = re.match(r"^---\s*\n.*?\n---", content, re.DOTALL)
    assert m, f"No frontmatter in {path}"
    return content[m.end() :].strip()


# ---------------------------------------------------------------------------
# Product Owner output format
# ---------------------------------------------------------------------------


def test_po_output_has_feature_summary():
    """PO output must include the Feature Summary section."""
    body = _agent_body("product-owner-agent")
    assert "Feature Summary" in body


def test_po_output_has_stakeholders_section():
    """PO output must include the Stakeholders & Concerns section."""
    body = _agent_body("product-owner-agent")
    assert "Stakeholders" in body


def test_po_output_has_acceptance_criteria():
    """PO output must include an Acceptance Criteria section."""
    body = _agent_body("product-owner-agent")
    assert "Acceptance Criteria" in body


def test_po_output_has_definition_of_done():
    """PO output must include a Definition of Done section."""
    body = _agent_body("product-owner-agent")
    assert "Definition of Done" in body


def test_po_output_has_jira_ticket_fields():
    """PO output must include JIRA Ticket Fields section."""
    body = _agent_body("product-owner-agent")
    assert "JIRA Ticket Fields" in body


def test_po_output_has_user_stories():
    """PO output must include User Stories section."""
    body = _agent_body("product-owner-agent")
    assert "User Stories" in body


# ---------------------------------------------------------------------------
# Architect output format
# ---------------------------------------------------------------------------


def test_architect_output_has_feature_summary():
    """Architect output must include the Feature Summary section."""
    body = _agent_body("architect-agent")
    assert "Feature Summary" in body


def test_architect_output_has_architecture_analysis():
    """Architect output must include the Architecture Analysis section."""
    body = _agent_body("architect-agent")
    assert "Architecture Analysis" in body


def test_architect_output_has_implementation_plan():
    """Architect output must include an Implementation Plan section."""
    body = _agent_body("architect-agent")
    assert "Implementation Plan" in body


def test_architect_output_has_files_to_modify():
    """Architect output must include a Files to Modify section."""
    body = _agent_body("architect-agent")
    assert "Files to Modify" in body


def test_architect_output_has_test_strategy():
    """Architect output must include a Test Strategy section."""
    body = _agent_body("architect-agent")
    assert "Test Strategy" in body


# ---------------------------------------------------------------------------
# Developer output format
# ---------------------------------------------------------------------------


def test_developer_output_has_changes_made():
    """Developer output must include a Changes Made section."""
    body = _agent_body("developer-agent")
    assert "Changes Made" in body


def test_developer_output_has_files_modified():
    """Developer output must include a Files Modified section."""
    body = _agent_body("developer-agent")
    assert "Files Modified" in body


def test_developer_output_has_tests_added_updated():
    """Developer output must include a Tests Added/Updated section."""
    body = _agent_body("developer-agent")
    assert "Tests Added/Updated" in body


def test_developer_output_has_code_quality_checks():
    """Developer output must include a Code Quality Checks section."""
    body = _agent_body("developer-agent")
    assert "Code Quality Checks" in body


def test_developer_output_has_issues_encountered():
    """Developer output must include an Issues Encountered & Resolved section."""
    body = _agent_body("developer-agent")
    assert "Issues Encountered" in body


# ---------------------------------------------------------------------------
# Tester output format
# ---------------------------------------------------------------------------


def test_tester_output_has_validation_result():
    """Tester output must include a Validation Result section."""
    body = _agent_body("tester-agent")
    assert "Validation Result" in body


def test_tester_output_has_acceptance_criteria_validation():
    """Tester output must include an Acceptance Criteria Validation section."""
    body = _agent_body("tester-agent")
    assert "Acceptance Criteria Validation" in body


def test_tester_output_has_test_results_summary():
    """Tester output must include a Test Results Summary section."""
    body = _agent_body("tester-agent")
    assert "Test Results Summary" in body


def test_tester_output_has_decision_next_steps():
    """Tester output must include a Decision & Next Steps section."""
    body = _agent_body("tester-agent")
    assert "Decision & Next Steps" in body


def test_tester_output_has_validation_checklist():
    """Tester output must include a Validation Checklist."""
    body = _agent_body("tester-agent")
    assert "Validation Checklist" in body


def test_tester_output_has_audit_trail():
    """Tester output must include an Audit Trail section."""
    body = _agent_body("tester-agent")
    assert "Audit Trail" in body


# ---------------------------------------------------------------------------
# Closure confirmation output format
# ---------------------------------------------------------------------------


def test_final_review_output_has_validation_result():
    """Final Review handoff output must include the validation result."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}
    review = handoffs["Final Review"]
    assert "validation_result" in review["prompt"]


def test_final_review_output_has_summary_and_remaining():
    """Final Review handoff must include summary and remaining work."""
    agents = _all_agents()
    po = agents["product-owner-agent"]
    handoffs = {h["label"]: h for h in po["handoffs"]}
    review = handoffs["Final Review"]
    prompt = review["prompt"]
    assert "{{summary}}" in prompt
    assert "{{remaining}}" in prompt
