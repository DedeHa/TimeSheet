"""Unit tests for backfill_ci_timings.py (PRO-369 CI-timing benchmark).

Verifies the historical sweep reuses the same exclusion / dedup rules as
collect_ci_timings.py and is idempotent on the dataset CSV. Runs in the
``.github/tests/ci-pipeline`` CI self-test group. Standard-library only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
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


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
