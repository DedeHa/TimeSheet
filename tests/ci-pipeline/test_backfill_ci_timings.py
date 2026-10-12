"""Unit tests for backfill_ci_timings.py (PRO-369 CI-timing benchmark).

Verifies the historical sweep reuses the same exclusion / dedup rules as
collect_ci_timings.py and is idempotent on the dataset CSV. Runs in the
``tests/ci-pipeline`` CI self-test group. Standard-library only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import backfill_ci_timings as bf  # noqa: E402
import collect_ci_timings as c  # noqa: E402


def _job(name, steps, started, completed, conclusion="success"):
    return {
        "name": name,
        "conclusion": conclusion,
        "started_at": started,
        "completed_at": completed,
        "steps": steps,
    }


def _step(name, num, started, completed, conclusion="success"):
    return {
        "name": name,
        "conclusion": conclusion,
        "number": num,
        "started_at": started,
        "completed_at": completed,
    }


def _run(run_id, attempt=1, pr=95):
    return {
        "id": run_id,
        "run_attempt": attempt,
        "head_sha": f"sha{run_id}",
        "workflow_sha": "wf1",
        "created_at": "2026-08-21T10:00:00Z",
        "conclusion": "success",
        "pull_requests": [{"number": pr}],
    }


def _jobs_payload():
    return {
        "jobs": [
            _job(
                "check",
                [
                    _step(
                        "Set up job", 1, "2026-08-21T10:00:00Z", "2026-08-21T10:00:02Z"
                    ),
                    _step(
                        "Run lint tools",
                        2,
                        "2026-08-21T10:00:05Z",
                        "2026-08-21T10:00:20Z",
                    ),
                ],
                "2026-08-21T10:00:00Z",
                "2026-08-21T10:00:30Z",
            ),
            _job(
                "test",
                [
                    _step(
                        "Run unit tests",
                        2,
                        "2026-08-21T10:00:05Z",
                        "2026-08-21T10:00:35Z",
                    ),
                ],
                "2026-08-21T10:00:00Z",
                "2026-08-21T10:00:40Z",
            ),
            _job(
                "deploy",
                [],
                "2026-08-21T10:00:00Z",
                "2026-08-21T10:00:40Z",
                conclusion="skipped",
            ),
        ]
    }


def test_backfill_excludes_failed_runs_and_is_idempotent(tmp_path):
    csv_path = tmp_path / "ci-timings.csv"

    def fake_api(path):
        if path.endswith("/runs?event=pull_request&status=success&per_page=100"):
            return {"workflow_runs": [_run(100), _run(101), _run(102)]}
        if path.endswith("/jobs"):
            return _jobs_payload()
        raise AssertionError(f"unexpected api path: {path}")

    with mock.patch.object(bf, "_gh_api", side_effect=fake_api):
        added = bf.backfill("owner/repo", csv_path)

    # 3 successful runs x 4 rows each (2 jobs x 2 rows incl. job totals) = 12.
    assert added == 12
    rows = c.read_csv(csv_path)
    assert len(rows) == 12
    assert all(r["conclusion"] == "success" for r in rows)
    assert not any(r["job_name"] == "deploy" for r in rows)

    # Idempotency: re-running the sweep adds nothing.
    with mock.patch.object(bf, "_gh_api", side_effect=fake_api):
        assert bf.backfill("owner/repo", csv_path) == 0
    assert len(c.read_csv(csv_path)) == 12


def test_backfill_supersedes_earlier_attempt(tmp_path):
    csv_path = tmp_path / "ci-timings.csv"

    def fake_api(path):
        if path.endswith("/runs?event=pull_request&status=success&per_page=100"):
            return {"workflow_runs": [_run(100, attempt=1), _run(100, attempt=2)]}
        if path.endswith("/jobs"):
            return _jobs_payload()
        raise AssertionError(f"unexpected api path: {path}")

    with mock.patch.object(bf, "_gh_api", side_effect=fake_api):
        bf.backfill("owner/repo", csv_path)

    rows = c.read_csv(csv_path)
    # Two attempts of the same run must collapse to one set of rows.
    assert len(rows) == 4
    assert all(int(r["run_attempt"]) == 2 for r in rows)


def test_list_successful_pr_runs_skips_non_success(tmp_path):
    runs = [
        _run(1),
        {"id": 2, "conclusion": "failure", "pull_requests": []},
        {"id": 3, "conclusion": "cancelled", "pull_requests": []},
    ]
    with mock.patch.object(bf, "_gh_api", return_value={"workflow_runs": runs}):
        out = list(bf.list_successful_pr_runs("owner/repo"))
    assert [r["id"] for r in out] == [1]


def test_list_successful_pr_runs_filters_since_run_id():
    runs = [
        _run(100),
        _run(99),
        _run(98),
    ]
    with mock.patch.object(
        bf, "_gh_api", return_value={"workflow_runs": runs}
    ) as mock_api:
        out = list(bf.list_successful_pr_runs("owner/repo", since_run_id=99))
    assert [r["id"] for r in out] == [100]
    assert "per_page=100" in mock_api.call_args.args[0]


def test_list_successful_pr_runs_filters_since_date():
    runs = [
        _run(100),
        _run(99),
        _run(98),
    ]
    with mock.patch.object(
        bf, "_gh_api", return_value={"workflow_runs": runs}
    ) as mock_api:
        out = list(bf.list_successful_pr_runs("owner/repo", since_date="2025-01-01"))
    assert [r["id"] for r in out] == [100, 99, 98]
    assert "created>=2025-01-01" in mock_api.call_args.args[0]


def test_migrate_csv_to_json_preserves_row_count(tmp_path):
    """CSV to JSON migration preserves row count and validates output."""
    import json

    csv_path = tmp_path / "ci-timings.csv"
    json_path = tmp_path / "runtimes.json"
    rows = [
        {
            "run_id": "100",
            "run_attempt": "1",
            "pr_number": "95",
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": "2",
            "duration_s": "15.0",
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    c.write_csv(csv_path, rows)
    count = bf.migrate_csv_to_json(csv_path, json_path)
    assert count == 1
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["schema_version"] == "v1.0"
    assert len(data["runs"]) == count
    assert data["runs"][0]["branch"] == "master"


def test_migrate_csv_to_json_rejects_invalid_data(tmp_path):
    """Migration rejects data that fails schema validation."""
    csv_path = tmp_path / "ci-timings.csv"
    json_path = tmp_path / "runtimes.json"
    rows = [
        {
            "run_id": "100",
            "run_attempt": "1",
            "pr_number": "95",
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": "2",
            "duration_s": "not-a-number",
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    c.write_csv(csv_path, rows)
    try:
        bf.migrate_csv_to_json(csv_path, json_path)
    except ValueError as exc:
        assert "invalid JSON data" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid JSON data")


def test_migrate_csv_to_json_validates_with_invalid_duration(tmp_path):
    """Migration rejects rows with invalid duration_s."""
    csv_path = tmp_path / "ci-timings.csv"
    json_path = tmp_path / "runtimes.json"
    rows = [
        {
            "run_id": "100",
            "run_attempt": "1",
            "pr_number": "95",
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": "2",
            "duration_s": "not-a-number",
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    c.write_csv(csv_path, rows)
    try:
        bf.migrate_csv_to_json(csv_path, json_path)
    except ValueError as exc:
        assert "invalid JSON data" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid duration")


def test_write_json_skips_on_corrupt_existing(tmp_path):
    """_write_json() skips the write when the existing JSON file is corrupt."""
    import sys
    from io import StringIO

    path = tmp_path / "runtimes.json"
    path.write_text("not valid json", encoding="utf-8")
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        sample = [
            {
                "run_id": 100,
                "run_attempt": 1,
                "job_name": "check",
                "step_number": 2,
                "duration_s": 15.0,
            }
        ]
        bf._write_json(sample, path)
        output = sys.stderr.getvalue()
    finally:
        sys.stderr = old_stderr
    assert "WARNING" in output
    assert path.read_text(encoding="utf-8") == "not valid json"


def test_write_json_skips_on_invalid_data(tmp_path):
    """_write_json() skips the write when validation fails."""
    path = tmp_path / "runtimes.json"
    runs = [
        {
            "run_id": 100,
            "run_attempt": 1,
            "job_name": "check",
            "step_number": 2,
            "duration_s": "not-a-number",
        }
    ]
    bf._write_json(runs, path)
    assert not path.exists()


def test_main_migrate_flag(tmp_path):
    """main() with --migrate flag calls migrate_csv_to_json."""
    import subprocess

    csv_path = tmp_path / "ci-timings.csv"
    json_path = tmp_path / "runtimes.json"
    rows = [
        {
            "run_id": "100",
            "run_attempt": "1",
            "pr_number": "95",
            "head_sha": "abc123",
            "workflow_sha": "wf123",
            "created_at": "2026-08-21T10:00:00Z",
            "branch": "master",
            "job_name": "check",
            "step_name": "Run lint tools",
            "step_number": "2",
            "duration_s": "15.0",
            "conclusion": "success",
            "cache_state": "miss",
        }
    ]
    c.write_csv(csv_path, rows)
    result = subprocess.run(
        [
            "python",
            "-m",
            "backfill_ci_timings",
            "--repo",
            "owner/repo",
            "--csv",
            str(csv_path),
            "--migrate",
            "--json-path",
            str(json_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2] / ".github" / "scripts"),
    )
    assert result.returncode == 0
    assert json_path.exists()


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
