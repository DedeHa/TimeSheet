"""Unit tests for collect_ci_timings.py (PRO-368 CI-timing benchmark).

Validates the run / job / step exclusion rules, duration parsing, the per-job
total row and latest-attempt de-duplication against sample API JSON. Runs in the
``.github/tests/ci-pipeline`` CI self-test group. Standard-library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import collect_ci_timings as mod  # noqa: E402


def _run_meta(conclusion="success"):
    return {
        "conclusion": conclusion,
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
    }


def _jobs():
    return [
        {
            "name": "check",
            "conclusion": "success",
            "started_at": "2026-08-21T10:00:00Z",
            "completed_at": "2026-08-21T10:00:30Z",
            "steps": [
                {
                    "name": "Set up job",
                    "conclusion": "success",
                    "number": 1,
                    "started_at": "2026-08-21T10:00:00Z",
                    "completed_at": "2026-08-21T10:00:02Z",
                },
                {
                    "name": "Run lint tools",
                    "conclusion": "success",
                    "number": 2,
                    "started_at": "2026-08-21T10:00:05Z",
                    "completed_at": "2026-08-21T10:00:20Z",
                },
                {
                    "name": "Flaky step",
                    "conclusion": "skipped",
                    "number": 3,
                    "started_at": None,
                    "completed_at": None,
                },
                {
                    "name": "Post Run actions/checkout",
                    "conclusion": "success",
                    "number": 4,
                    "started_at": "2026-08-21T10:00:28Z",
                    "completed_at": "2026-08-21T10:00:30Z",
                },
            ],
        },
        {
            "name": "test",
            "conclusion": "success",
            "started_at": "2026-08-21T10:00:00Z",
            "completed_at": "2026-08-21T10:00:40Z",
            "steps": [
                {
                    "name": "Run unit tests",
                    "conclusion": "success",
                    "number": 2,
                    "started_at": "2026-08-21T10:00:05Z",
                    "completed_at": "2026-08-21T10:00:35Z",
                },
            ],
        },
        {"name": "deploy", "conclusion": "skipped", "steps": []},
    ]


def test_duration_and_parse_edge_cases():
    assert mod.duration_s("2026-08-21T10:00:00Z", "2026-08-21T10:00:30Z") == 30.0
    assert mod.duration_s(None, "2026-08-21T10:00:30Z") is None
    assert mod.duration_s("2026-08-21T10:00:30Z", "2026-08-21T10:00:00Z") is None
    assert mod.parse_iso("not-a-date") is None


def test_extract_rows_applies_exclusions():
    rows = mod.extract_rows(_run_meta(), _jobs())
    names = {(r["job_name"], r["step_name"]) for r in rows}
    # Housekeeping (Set up job / Post ...) and skipped step excluded.
    assert ("check", "Set up job") not in names
    assert ("check", "Post Run actions/checkout") not in names
    assert ("check", "Flaky step") not in names
    # Skipped deploy job contributes nothing.
    assert not any(r["job_name"] == "deploy" for r in rows)
    # Real steps + per-job totals kept, with correct durations.
    by_key = {(r["job_name"], r["step_name"]): r["duration_s"] for r in rows}
    assert by_key[("check", mod.JOB_TOTAL)] == 30.0
    assert by_key[("check", "Run lint tools")] == 15.0
    assert by_key[("test", mod.JOB_TOTAL)] == 40.0
    assert by_key[("test", "Run unit tests")] == 30.0
    assert len(rows) == 4


def test_failed_run_yields_no_rows():
    assert mod.extract_rows(_run_meta(conclusion="failure"), _jobs()) == []


def test_include_housekeeping_flag():
    rows = mod.extract_rows(_run_meta(), _jobs(), include_housekeeping=True)
    names = {(r["job_name"], r["step_name"]) for r in rows}
    assert ("check", "Set up job") in names
    assert ("check", "Post Run actions/checkout") in names


def test_dedup_keeps_latest_attempt():
    a1 = {
        "run_id": 100,
        "run_attempt": 1,
        "job_name": "check",
        "step_number": 2,
        "duration_s": 15.0,
    }
    a2 = {
        "run_id": 100,
        "run_attempt": 2,
        "job_name": "check",
        "step_number": 2,
        "duration_s": 12.0,
    }
    out = mod.dedup_latest_attempt([a1, a2])
    assert len(out) == 1
    assert out[0]["duration_s"] == 12.0
    assert out[0]["run_attempt"] == 2


def test_extract_rows_includes_branch():
    """branch field is present in all rows from extract_rows."""
    rows = mod.extract_rows(_run_meta(), _jobs())
    assert len(rows) > 0
    for r in rows:
        assert "branch" in r, f"row missing branch field: {r}"
        assert r["branch"] == "master", f"unexpected branch: {r['branch']}"


def test_write_json_creates_file(tmp_path):
    """write_json() creates data/runtimes.json with correct schema."""
    import json

    path = tmp_path / "runtimes.json"
    run_meta = {
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "feature/PRO-375",
    }
    rows = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "feature/PRO-375",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    mod.write_json(rows, run_meta, path)
    assert path.exists(), "write_json did not create the file"
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["schema_version"] == "v1.0"
    assert "generated_at" in data
    assert "runs" in data
    assert len(data["runs"]) == 1
    assert data["runs"][0]["run_id"] == 100


def test_write_json_deduplicates(tmp_path):
    """write_json() deduplicates by (run_id, job_name, step_number)."""
    import json

    path = tmp_path / "runtimes.json"
    run_meta = {
        "run_id": 100,
        "run_attempt": 2,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "master",
    }
    rows_a = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    rows_b = [
        {
            "run_id": 100,
            "run_attempt": 2,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 12.0,
            "conclusion": "success",
            "cache_state": "hit",
        }
    ]
    mod.write_json(rows_a, run_meta, path)
    mod.write_json(rows_b, run_meta, path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert len(data["runs"]) == 1
    assert data["runs"][0]["duration_s"] == 12.0
    assert data["runs"][0]["run_attempt"] == 2


def test_write_json_schema_version(tmp_path):
    """write_json() output has schema_version v1.0."""
    import json

    path = tmp_path / "runtimes.json"
    run_meta = {
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "master",
    }
    rows = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    mod.write_json(rows, run_meta, path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["schema_version"] == "v1.0"


def test_write_json_skips_on_corrupt_existing(tmp_path, capsys):
    """write_json() skips the write when the existing file is corrupt."""
    path = tmp_path / "runtimes.json"
    path.write_text("not valid json", encoding="utf-8")
    run_meta = {
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "master",
    }
    rows = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    mod.write_json(rows, run_meta, path)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    # File should still be the corrupt original
    assert path.read_text(encoding="utf-8") == "not valid json"


def test_write_json_skips_on_invalid_data(tmp_path, capsys):
    """write_json() skips the write when validation fails."""
    path = tmp_path / "runtimes.json"
    run_meta = {
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "master",
    }
    # Second row missing conclusion — validation should fail
    rows = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        },
        {
            "run_id": 100,
            "run_attempt": 2,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 12.0,
            "cache_state": "hit",
        },
    ]
    mod.write_json(rows, run_meta, path)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert not path.exists()


def test_write_json_appends_to_existing_valid(tmp_path):
    """write_json() appends to an existing valid file."""
    import json

    path = tmp_path / "runtimes.json"
    run_meta = {
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "master",
    }
    rows_a = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    rows_b = [
        {
            "run_id": 101,
            "run_attempt": 1,
            "pr_number": 96,
            "head_sha": "def456",
            "workflow_sha": "wf456",
            "created_at": "2026-08-21T11:00:00Z",
            "branch": "master",
            "job_name": "test",
            "step_name": "Run unit tests",
            "step_number": 2,
            "duration_s": 30.0,
            "conclusion": "success",
            "cache_state": "hit",
        }
    ]
    mod.write_json(rows_a, run_meta, path)
    mod.write_json(rows_b, run_meta, path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert len(data["runs"]) == 2


def test_write_json_creates_parent_dir(tmp_path):
    """write_json() creates parent directories if needed."""
    path = tmp_path / "nested" / "runtimes.json"
    run_meta = {
        "run_id": 100,
        "run_attempt": 1,
        "pr_number": 95,
        "head_sha": "abc123",
        "workflow_sha": "wf123",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "branch": "master",
    }
    rows = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "pr_number": 95,
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": 2,
            "duration_s": 15.0,
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    mod.write_json(rows, run_meta, path)
    assert path.exists()


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
