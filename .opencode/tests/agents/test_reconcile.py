"""Documentation reconciliation gate for pipeline.py (PRO-407, AC-4; FR-24).

`reconcile` maps changed paths to the living documents that must move with them
(the table in complete-feature Step 4.5). It exits non-zero when a changed area has
no matching living-document change in the diff. The mapping is pure and takes an
injectable file list; only the git tests touch a real repository (tmp_path).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

PIPELINE_PATH = (
    Path(__file__).resolve().parents[3] / ".opencode" / "scripts" / "pipeline.py"
)
TICKET = "PRO-407"


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Load pipeline.py with state and history redirected to tmp_path."""
    spec = importlib.util.spec_from_file_location(
        "pipeline_reconcile_under_test", PIPELINE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(module, "HISTORY_PATH", tmp_path / "history.json")
    return module


@pytest.mark.parametrize(
    "changed,expected_labels",
    [
        (["src/TimeSheetAlgo.py"], ["application code (src/)"]),
        (["tests/unit/test_x.py"], ["tests"]),
        ([".opencode/tests/agents/test_x.py"], ["tests"]),
        (
            [".opencode/scripts/pipeline.py"],
            ["agent team (.opencode scripts, skills, agents)"],
        ),
        (
            [".opencode/skills/develop-feature/SKILL.md"],
            ["agent team (.opencode scripts, skills, agents)"],
        ),
        (
            [".opencode/agents/tester.agent.md"],
            ["agent team (.opencode scripts, skills, agents)"],
        ),
        (["docs/changes/2026-11/PRO-407/plan.md"], []),
        ([], []),
    ],
)
def test_gap_detection_flags_areas_without_living_docs(
    pipeline, changed, expected_labels
):
    """Each changed area with no matching living document is reported as a gap."""
    labels = [label for label, _docs in pipeline.find_reconciliation_gaps(changed)]
    assert labels == expected_labels


def test_src_change_with_architecture_doc_passes(pipeline):
    """A src change reconciled by docs/ARCHITECTURE.md has no gap."""
    changed = ["src/TimeSheetAlgo.py", "docs/ARCHITECTURE.md"]
    assert pipeline.find_reconciliation_gaps(changed) == []


def test_src_change_with_requirements_doc_passes(pipeline):
    """docs/REQUIREMENTS.md also reconciles application code."""
    assert pipeline.find_reconciliation_gaps(["src/a.py", "docs/REQUIREMENTS.md"]) == []


def test_tests_change_needs_testing_doc(pipeline):
    """A test change without docs/TESTING.md is a gap; with it, no gap."""
    assert pipeline.find_reconciliation_gaps(["tests/unit/test_a.py"])
    assert (
        pipeline.find_reconciliation_gaps(["tests/unit/test_a.py", "docs/TESTING.md"])
        == []
    )


def test_agent_change_accepts_agents_md_or_contributing(pipeline):
    """Agent-team changes are reconciled by AGENTS.md or docs/CONTRIBUTING.md."""
    base = [".opencode/scripts/pipeline.py"]
    assert pipeline.find_reconciliation_gaps(base + ["AGENTS.md"]) == []
    assert pipeline.find_reconciliation_gaps(base + ["docs/CONTRIBUTING.md"]) == []


def test_mixed_change_reports_every_gap(pipeline):
    """Each uncovered area is reported, not only the first."""
    gaps = pipeline.find_reconciliation_gaps(
        ["src/a.py", "tests/t.py", ".opencode/scripts/p.py"]
    )
    assert len(gaps) == 3


def test_backslash_and_leading_dot_slash_are_normalised(pipeline):
    """Windows separators and ./ prefixes map to the same areas."""
    changed = [".\\src\\a.py", "./docs/ARCHITECTURE.md"]
    assert pipeline.find_reconciliation_gaps(changed) == []


def test_reconcile_cli_passes_with_matching_docs(
    pipeline, tmp_path, monkeypatch, capsys
):
    """--changed supplies the file list; a reconciled diff exits zero."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pipeline.py",
            "reconcile",
            TICKET,
            "--changed",
            "src/a.py",
            "--changed",
            "docs/ARCHITECTURE.md",
        ],
    )
    pipeline.main()
    assert "reconciled" in capsys.readouterr().out


def test_reconcile_cli_fails_when_doc_missing(pipeline, tmp_path, monkeypatch, capsys):
    """A changed area without its living document exits non-zero and names the gap."""
    monkeypatch.setattr(
        sys, "argv", ["pipeline.py", "reconcile", TICKET, "--changed", "src/a.py"]
    )
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "docs/ARCHITECTURE.md" in out
    assert "docs/REQUIREMENTS.md" in out


def test_reconcile_does_not_write_state(pipeline, tmp_path, monkeypatch, capsys):
    """reconcile is a check: it creates no state or history."""
    monkeypatch.setattr(
        sys, "argv", ["pipeline.py", "reconcile", TICKET, "--changed", "src/x.py"]
    )
    with pytest.raises(SystemExit):
        pipeline.main()
    assert not (tmp_path / "state.json").exists()
    assert not (tmp_path / "history.json").exists()


def test_changed_files_reads_branch_diff_from_git(pipeline, tmp_path):
    """changed_files lists files changed on the branch against the base."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-q", "-b", "master")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "tester")
    (repo / "a.txt").write_text("a", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "feature")
    (repo / "src").mkdir()
    (repo / "src" / "m.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "src/m.py")
    git("commit", "-q", "-m", "change")

    assert pipeline.changed_files("master", cwd=repo) == ["src/m.py"]


def test_changed_files_reports_non_git_directory_gracefully(pipeline, tmp_path):
    """Outside a repository changed_files raises RuntimeError, not a traceback."""
    with pytest.raises(RuntimeError):
        pipeline.changed_files("master", cwd=tmp_path)


def test_reconcile_cli_reports_missing_git_without_changed(
    pipeline, tmp_path, monkeypatch, capsys
):
    """Without --changed and without a readable diff, reconcile fails with guidance."""

    def boom(base, cwd=None):
        raise RuntimeError("fatal: not a git repository")

    monkeypatch.setattr(pipeline, "changed_files", boom)
    monkeypatch.setattr(sys, "argv", ["pipeline.py", "reconcile", TICKET])
    with pytest.raises(SystemExit) as exc:
        pipeline.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Cannot read the diff" in out
    assert "--changed" in out


@pytest.mark.parametrize("base", ["-x", "--output=/tmp/x", "master;rm", "a b", "", "-"])
def test_reconcile_rejects_unsafe_base_ref(pipeline, tmp_path, monkeypatch, capsys, base):
    """J (architect 9): a base that is not a safe ref name, or starts with '-', exits 1.

    git is never run with it: the diff reader is replaced by a function that fails.
    """

    def must_not_run(*args, **kwargs):
        raise AssertionError("git must not be called with an unsafe base")

    monkeypatch.setattr(pipeline, "changed_files", must_not_run)
    assert pipeline.PipelineManager().reconcile(TICKET, base=base) == 1
    assert "invalid base ref" in capsys.readouterr().out


@pytest.mark.parametrize("base", ["master", "origin/master", "HEAD~2", "v1.2.3", "feature/PRO-407-x"])
def test_validate_base_ref_accepts_normal_refs(pipeline, base):
    """J (architect 9): ordinary branch, tag, and relative refs stay valid."""
    assert pipeline.validate_base_ref(base) == base
