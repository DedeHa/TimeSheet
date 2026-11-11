"""Tracker-agnostic work item references (PRO-407, ticket Step 6; FR-25).

`parse_work_item_ref` classifies a reference as jira, github, or generic. `handoff`
accepts any valid reference, records the tracker in history, and renders it in the
JIRA-style comment. STATE_PATH and HISTORY_PATH are redirected to tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PIPELINE_PATH = (
    Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
)


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_ref_under_test", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


@pytest.mark.parametrize(
    "ref,tracker,key",
    [
        ("PRO-123", "jira", "PRO-123"),
        ("ABC-9", "jira", "ABC-9"),
        ("AB2-10", "jira", "AB2-10"),
        ("GH-456", "github", "GH-456"),
        ("owner/repo#456", "github", "owner/repo#456"),
        ("my-org.name/my_repo#7", "github", "my-org.name/my_repo#7"),
        ("pro-123", "generic", "pro-123"),
        ("FEAT-login", "generic", "FEAT-login"),
        ("task_42", "generic", "task_42"),
        ("A-1", "generic", "A-1"),
        ("  PRO-5  ", "jira", "PRO-5"),
    ],
)
def test_parse_work_item_ref_classifies_each_tracker(pipeline, ref, tracker, key):
    """JIRA keys, GitHub references, and generic identifiers are classified."""
    assert pipeline.parse_work_item_ref(ref) == {"tracker": tracker, "key": key}


@pytest.mark.parametrize(
    "ref",
    [
        "",
        "   ",
        "123",
        "-PRO-1",
        "owner/repo",
        "owner/repo#",
        "PRO 123",
        "PRO/123",
        "PRO-",
        "GH-",
        "ABC-",
        "PRO-12a",
        None,
        42,
    ],
)
def test_parse_work_item_ref_rejects_invalid_references(pipeline, ref):
    """Empty, numeric, malformed, and non-string references raise ValueError."""
    with pytest.raises(ValueError):
        pipeline.parse_work_item_ref(ref)


def test_handoff_accepts_github_reference_and_records_tracker(pipeline, tmp_path):
    """A GitHub issue reference is a valid handoff target and is recorded as github."""
    handoff = pipeline.PipelineManager().record_handoff(
        "owner/repo#456", "developer", "tester", "plan", "COMPLETED"
    )
    assert handoff["ticket"] == "owner/repo#456"
    assert handoff["tracker"] == "github"
    history = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert history["owner/repo#456"]["actions"][-1]["details"]["tracker"] == "github"


def test_handoff_rejects_invalid_reference_without_writing(pipeline, tmp_path):
    """An invalid reference is rejected before any state or history is written."""
    with pytest.raises(ValueError):
        pipeline.PipelineManager().record_handoff(
            "not a ref", "developer", "tester", "plan", "COMPLETED"
        )
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "history.json").exists()


def test_rendered_comment_names_the_tracker(pipeline, tmp_path):
    """The JIRA-style comment states which tracker the work item belongs to."""
    handoff = pipeline.PipelineManager().record_handoff(
        "GH-456", "developer", "tester", "plan", "COMPLETED"
    )
    body = pipeline.PipelineManager.render_handoff_comment(handoff)
    assert "Work item: GH-456 (tracker: github)" in body


def test_handoff_cli_accepts_generic_reference(pipeline, tmp_path, monkeypatch, capsys):
    """The handoff subcommand accepts a generic identifier and reports its tracker."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pipeline.py",
            "handoff",
            "feat-login",
            "--from",
            "architect",
            "--to",
            "developer",
            "--status",
            "COMPLETED",
        ],
    )
    pipeline.main()
    out = capsys.readouterr().out
    assert "Work item: feat-login (tracker: generic)" in out


COMMANDS_WITH_TICKET = [
    ["showstate", "{ref}"], ["reset", "{ref}"], ["history", "{ref}"], ["resume", "{ref}"],
    ["interrupt", "{ref}"], ["continue", "{ref}"], ["proceed", "{ref}"],
    ["what-missed", "{ref}"], ["dry-run", "{ref}", "resume"], ["check-stuck", "{ref}"],
    ["set-mode", "{ref}", "automated"], ["get-mode", "{ref}"], ["dor", "{ref}"],
    ["reconcile", "{ref}"],
]


@pytest.mark.parametrize("command", COMMANDS_WITH_TICKET, ids=lambda c: c[0])
def test_every_command_rejects_an_invalid_reference(pipeline, tmp_path, monkeypatch, capsys, command):
    """F: one validation point for every ticket argument. Usage errors exit 2, nothing is written."""
    argv = ["pipeline.py", *(part.replace("{ref}", "PRO 123") for part in command)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 2
    assert "invalid work item reference" in capsys.readouterr().err
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "history.json").exists()


def test_continue_normalises_surrounding_whitespace(pipeline, tmp_path, monkeypatch, capsys):
    """F: `continue " PRO-5 "` addresses PRO-5 (the stored key has no whitespace)."""
    monkeypatch.setattr(sys, "argv", ["pipeline.py", "set-mode", " PRO-5 ", "automated"])
    pipeline.main()
    monkeypatch.setattr(sys, "argv", ["pipeline.py", "continue", " PRO-5 "])
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 1  # refused: no handoff yet, but addressed PRO-5
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert list(state) == ["PRO-5"]
    assert "Continuing Pipeline: PRO-5" in capsys.readouterr().out


def test_normalise_work_item_ref_strips_and_validates(pipeline):
    """F: the single normaliser returns the key, and raises for an invalid reference."""
    assert pipeline.normalise_work_item_ref("  owner/repo#7 ") == "owner/repo#7"
    with pytest.raises(ValueError):
        pipeline.normalise_work_item_ref("GH-")
