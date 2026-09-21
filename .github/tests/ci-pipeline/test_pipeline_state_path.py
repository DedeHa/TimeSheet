"""Tests for PRO-382: pipeline state path resolution and migration logic.

These tests verify that pipeline state is stored in project-local `.opencode/`
instead of `~/.opencode/` and that migration between locations works correctly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / ".opencode" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import detect_mode  # noqa: E402
import migrate_pipeline_state as m  # noqa: E402
import pipeline as pipe_module  # noqa: E402
import pre_closure_validation as pcl  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Return a temporary project root."""
    return tmp_path / "project"


@pytest.fixture
def opencode_dir(project_root: Path) -> Path:
    """Return the project-local .opencode directory."""
    return project_root / ".opencode"


@pytest.fixture
def old_opencode_dir(tmp_path: Path) -> Path:
    """Return the legacy home .opencode directory."""
    return tmp_path / "home" / ".opencode"


# ---------------------------------------------------------------------------
# Path Resolution Tests
# ---------------------------------------------------------------------------


class TestPathResolution:
    """Tests for path resolution in pipeline scripts."""

    @property
    def project_root(self) -> Path:
        """Return the project root directory (parent of .opencode/scripts)."""
        return Path(__file__).resolve().parent.parent.parent.parent

    def test_detect_mode_state_path_is_project_local(self):
        """detect_mode.STATE_PATH must not use Path.home()."""
        expected = self.project_root / ".opencode" / "pipeline-state.json"
        assert detect_mode.STATE_PATH == expected

    def test_pipeline_state_path_is_project_local(self):
        """pipeline.STATE_PATH must not use Path.home()."""
        expected = self.project_root / ".opencode" / "pipeline-state.json"
        assert pipe_module.STATE_PATH == expected

    def test_pipeline_history_path_is_project_local(self):
        """pipeline.HISTORY_PATH must not use Path.home()."""
        expected = self.project_root / ".opencode" / "pipeline-history.json"
        assert pipe_module.HISTORY_PATH == expected

    def test_pre_closure_validation_state_path_is_project_local(self):
        """pre_closure_validation.STATE_PATH must not use Path.home()."""
        expected = self.project_root / ".opencode" / "pipeline-state.json"
        assert pcl.STATE_PATH == expected


# ---------------------------------------------------------------------------
# Migration Tests
# ---------------------------------------------------------------------------


class TestMigration:
    """Tests for migrate_pipeline_state logic."""

    def test_migrate_old_only_copies_to_new(self, tmp_path: Path):
        """Old state exists, new doesn't — should copy to new location."""
        old_state = tmp_path / "home" / ".opencode" / "pipeline-state.json"
        new_state = tmp_path / "project" / ".opencode" / "pipeline-state.json"
        _write_json(old_state, {"PRO-373": {"development_mode": "automated"}})

        with (
            patch.object(m, "OLD_STATE_PATH", old_state),
            patch.object(
                m,
                "OLD_HISTORY_PATH",
                tmp_path / "home" / ".opencode" / "pipeline-history.json",
            ),
            patch.object(m, "_new_state_path", return_value=new_state),
            patch.object(
                m,
                "_new_history_path",
                return_value=tmp_path
                / "project"
                / ".opencode"
                / "pipeline-history.json",
            ),
        ):
            m.migrate_pipeline_state()

        assert new_state.exists()
        data = json.loads(new_state.read_text())
        assert "PRO-373" in data

    def test_migrate_new_only_no_action(self, tmp_path: Path):
        """New state exists, old doesn't — should not modify new."""
        new_state = tmp_path / "project" / ".opencode" / "pipeline-state.json"
        _write_json(new_state, {"PRO-382": {"development_mode": "automated"}})

        with (
            patch.object(
                m,
                "OLD_STATE_PATH",
                tmp_path / "home" / ".opencode" / "pipeline-state.json",
            ),
            patch.object(m, "_new_state_path", return_value=new_state),
        ):
            m.migrate_pipeline_state()

        data = json.loads(new_state.read_text())
        assert "PRO-382" in data

    def test_migrate_both_existing_new_takes_precedence(self, tmp_path: Path):
        """Both exist — new takes precedence, merged keys logged."""
        old_state = tmp_path / "home" / ".opencode" / "pipeline-state.json"
        new_state = tmp_path / "project" / ".opencode" / "pipeline-state.json"
        _write_json(
            old_state, {"PRO-373": {"development_mode": "interactive"}, "PRO-375": {}}
        )
        _write_json(
            new_state, {"PRO-373": {"development_mode": "automated"}, "PRO-382": {}}
        )

        with (
            patch.object(m, "OLD_STATE_PATH", old_state),
            patch.object(m, "_new_state_path", return_value=new_state),
        ):
            m.migrate_pipeline_state()

        data = json.loads(new_state.read_text())
        assert data["PRO-373"]["development_mode"] == "automated"
        assert "PRO-382" in data

    def test_migrate_neither_no_action(self, tmp_path: Path):
        """Neither exists — no action, no error."""
        new_state = tmp_path / "project" / ".opencode" / "pipeline-state.json"

        with (
            patch.object(
                m,
                "OLD_STATE_PATH",
                tmp_path / "home" / ".opencode" / "pipeline-state.json",
            ),
            patch.object(m, "_new_state_path", return_value=new_state),
        ):
            m.migrate_pipeline_state()

        assert not new_state.exists()

    def test_migration_is_idempotent(self, tmp_path: Path):
        """Running migration twice should produce same result."""
        old_state = tmp_path / "home" / ".opencode" / "pipeline-state.json"
        new_state = tmp_path / "project" / ".opencode" / "pipeline-state.json"
        _write_json(old_state, {"PRO-373": {"development_mode": "automated"}})

        with (
            patch.object(m, "OLD_STATE_PATH", old_state),
            patch.object(m, "_new_state_path", return_value=new_state),
        ):
            m.migrate_pipeline_state()
            m.migrate_pipeline_state()

        assert new_state.exists()
        data1 = json.loads(new_state.read_text())
        assert data1 == {"PRO-373": {"development_mode": "automated"}}

    def test_migration_handles_invalid_json(self, tmp_path: Path):
        """Invalid JSON at old location is logged and skipped."""
        old_state = tmp_path / "home" / ".opencode" / "pipeline-state.json"
        old_state.parent.mkdir(parents=True, exist_ok=True)
        old_state.write_text("not valid json")
        new_state = tmp_path / "project" / ".opencode" / "pipeline-state.json"

        with (
            patch.object(m, "OLD_STATE_PATH", old_state),
            patch.object(m, "_new_state_path", return_value=new_state),
        ):
            result = m.migrate_pipeline_state()

        assert result is not None


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests for pipeline flow at new location."""

    def test_detect_mode_writes_to_project_local(self, tmp_path: Path):
        """detect_mode.py writes state to project-local .opencode/ only with --init."""
        state_file = tmp_path / ".opencode" / "pipeline-state.json"
        with (
            patch.object(detect_mode, "STATE_PATH", state_file),
            patch.object(
                sys, "argv", ["detect_mode.py", "PRO-382", "Run in automated", "--init"]
            ),
        ):
            detect_mode.main()

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "PRO-382" in data

    def test_pipeline_state_is_persisted_at_new_location(self, tmp_path: Path):
        """pipeline.py persists state to project-local .opencode/."""
        state_file = tmp_path / ".opencode" / "pipeline-state.json"
        with patch.object(pipe_module, "STATE_PATH", state_file):
            manager = pipe_module.PipelineManager()
            manager.set_mode("PRO-382", "automated")

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert "PRO-382" in data
        assert data["PRO-382"]["development_mode"] == "automated"


# ---------------------------------------------------------------------------
# Gitignore Tests
# ---------------------------------------------------------------------------


class TestGitignore:
    """Tests verifying state files are not gitignored."""

    def test_state_files_not_gitignored(self, project_root: Path):
        """pipeline-state.json and pipeline-history.json must not be excluded."""
        gitignore = project_root / ".opencode" / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            assert "pipeline-state.json" not in content
            assert "pipeline-history.json" not in content


# ---------------------------------------------------------------------------
# Migration Trigger Tests
# ---------------------------------------------------------------------------


class TestMigrationTrigger:
    """Tests verifying migration is triggered when new state missing."""

    def test_detect_mode_triggers_migration(self, tmp_path: Path):
        """detect_mode._load_state triggers migration if needed."""
        old_state = tmp_path / "home" / ".opencode" / "pipeline-state.json"
        _write_json(old_state, {"PRO-373": {"development_mode": "automated"}})
        new_state = tmp_path / ".opencode" / "pipeline-state.json"

        with (
            patch.object(detect_mode, "STATE_PATH", new_state),
            patch.object(pipe_module, "STATE_PATH", new_state),
            patch("migrate_pipeline_state.migrate_pipeline_state") as mock_migrate,
        ):
            try:
                detect_mode._load_state()
            except Exception:
                pass

            mock_migrate.assert_called_once()

    def test_pipeline_triggers_migration(self, tmp_path: Path):
        """pipeline._load_state triggers migration if needed."""
        old_state = tmp_path / "home" / ".opencode" / "pipeline-state.json"
        _write_json(old_state, {"PRO-373": {"development_mode": "automated"}})
        new_state = tmp_path / ".opencode" / "pipeline-state.json"

        with (
            patch.object(pipe_module, "STATE_PATH", new_state),
            patch.object(
                pipe_module,
                "HISTORY_PATH",
                tmp_path / ".opencode" / "pipeline-history.json",
            ),
            patch("migrate_pipeline_state.migrate_pipeline_state") as mock_migrate,
        ):
            try:
                pipe_module.PipelineManager()
            except Exception:
                pass

            mock_migrate.assert_called_once()
