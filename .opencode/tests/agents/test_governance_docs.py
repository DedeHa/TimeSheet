"""Governance documentation tests for PRO-407 (AC-3, AC-4, AC-5, AC-6)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_develop_feature_enforces_dor_gate_before_branch():
    """AC-3: DoR gate exists in develop-feature and precedes branch creation."""
    text = _read(".opencode/skills/develop-feature/SKILL.md")
    assert "Definition of Ready (DoR) gate" in text
    dor_pos = text.index("Definition of Ready (DoR) gate")
    branch_pos = text.index("## Step 3 — Prepare the Branch")
    assert dor_pos < branch_pos
    for check in ("D1", "D2", "D3", "D4", "D5", "D6", "D7"):
        assert f"| {check} |" in text


def test_complete_feature_has_doc_reconciliation_step():
    """AC-4: reconciliation step runs before closure."""
    text = _read(".opencode/skills/complete-feature/SKILL.md")
    assert "Documentation Reconciliation" in text
    assert text.index("Documentation Reconciliation") < text.index("## Step 5 — Closure Sequence")


def test_product_owner_documents_handoff_recording():
    """AC-6: PO agent references pipeline.py handoff and the JIRA comment step."""
    text = _read(".opencode/agents/product-owner.agent.md")
    assert "pipeline.py handoff" in text
    assert "atlassian_addCommentToJiraIssue" in text


@pytest.mark.parametrize(
    "rel",
    ["docs/decisions/README.md", "docs/decisions/TEMPLATE.md", "docs/changes/README.md"],
)
def test_artifact_and_decision_folders_exist(rel):
    """AC-1 and AC-5: decision and change artifact structure exists."""
    assert (ROOT / rel).is_file(), f"missing {rel}"


def test_decision_index_lists_all_record_types():
    """AC-1: ADR/PDR/TDR/BDR/ODR are all documented."""
    text = _read("docs/decisions/README.md")
    for kind in ("ADR", "PDR", "TDR", "BDR", "ODR"):
        assert kind in text


def test_changes_readme_documents_artifact_layout():
    """AC-5: artifact layout is documented with the four artifact types."""
    text = _read("docs/changes/README.md")
    for artifact in ("spec", "plan", "test-plan", "pm-notes"):
        assert artifact in text


def test_agents_md_links_governance_folders():
    """AC-1/AC-5: AGENTS.md points to the decision and change folders."""
    text = _read("AGENTS.md")
    assert "docs/decisions/" in text
    assert "docs/changes/" in text


@pytest.mark.parametrize(
    "rel",
    [".opencode/agents/architect.agent.md", ".opencode/agents/product-owner.agent.md"],
)
def test_decision_owner_agents_reference_decision_folder(rel):
    """AC-1: Architect drafts ADR/TDR and PO drafts PDR/BDR in docs/decisions/."""
    text = _read(rel)
    assert "docs/decisions/" in text
    assert "docs/decisions/TEMPLATE.md" in text


def test_odr_0001_record_is_accepted_and_indexed():
    """AC-1: ODR-0001 exists from the template, is Accepted, and is in the index."""
    rel = "docs/decisions/ODR-0001-agent-team-governance.md"
    text = _read(rel)
    assert "- **Status:** Accepted" in text
    assert "- **Ticket:** PRO-407" in text
    for heading in ("## Context", "## Options considered", "## Decision", "## Consequences"):
        assert heading in text
    assert "| ODR-0001 |" in _read("docs/decisions/README.md")


def test_orchestrator_dispatches_developer_only_after_dor_gate():
    """AC-3: orchestrate-feature references the DoR gate before the Developer dispatch."""
    text = _read(".opencode/skills/orchestrate-feature/SKILL.md")
    assert "Definition of Ready (DoR) gate" in text
    assert "develop-feature" in text and "Step 1f" in text
    assert text.index("Definition of Ready (DoR) gate") < text.index("**Dispatch**: Routes to Developer agent")


def test_refine_feature_produces_dor_inputs_d1_to_d7():
    """AC-3: refine-feature maps its finalization output to DoR inputs D1-D7."""
    text = _read(".opencode/skills/refine-feature/SKILL.md")
    assert "Definition of Ready (DoR) gate" in text
    assert "Step 1f" in text
    for check in ("D1", "D2", "D3", "D4", "D5", "D6", "D7"):
        assert f"| {check} " in text


@pytest.mark.parametrize(
    "rel",
    [
        ".opencode/agents/architect.agent.md",
        ".opencode/agents/developer.agent.md",
        ".opencode/agents/tester.agent.md",
        ".opencode/agents/product-owner.agent.md",
        ".opencode/skills/orchestrate-feature/SKILL.md",
    ],
)
def test_every_handoff_owner_uses_pipeline_handoff(rel):
    """AC-6: each agent and the orchestrator records handoffs with pipeline.py handoff
    and posts the rendered comment to JIRA."""
    text = _read(rel)
    assert "pipeline.py handoff" in text, f"{rel} does not record handoffs"
    assert "atlassian_addCommentToJiraIssue" in text, f"{rel} does not post handoff comments"
    assert "--status BLOCKED" in text, f"{rel} does not document blocked escalations"
