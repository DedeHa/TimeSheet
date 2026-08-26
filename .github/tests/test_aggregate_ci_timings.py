"""Unit tests for aggregate_ci_timings.py (PRO-368 CI-timing benchmark).

Validates the per-(job, step) statistics, min-samples withholding, the rendered
report (caveat, job tables, appendix) and the empty-dataset case. Runs in the
``.github/tests`` CI self-test group. Standard-library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import aggregate_ci_timings as agg  # noqa: E402


def _rows(job, step, durations):
    return [
        {"run_id": str(i), "job_name": job, "step_name": step, "duration_s": str(d)}
        for i, d in enumerate(durations)
    ]


def test_stats_for_known_values():
    s = agg.stats_for([10.0, 20.0, 30.0])
    assert s["n"] == 3
    assert s["mean"] == 20.0
    assert s["median"] == 20.0
    assert round(s["stddev"], 3) == 10.0
    assert s["min"] == 10.0
    assert s["max"] == 30.0
    assert s["last"] == 30.0


def test_percentile_nearest_rank():
    assert agg._percentile([5.0], 95) == 5.0
    assert agg._percentile([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10.0


def test_aggregate_withholds_under_min_samples():
    rows = _rows("test", "Run unit tests", [30.0, 31.0, 29.0])  # 3 samples -> ready
    rows += _rows("test", "Run system tests", [7.0])  # 1 sample -> withheld
    out = agg.aggregate(rows, min_samples=3)
    assert ("test", "Run unit tests") in out["ready"]
    assert ("test", "Run system tests") in out["withheld"]
    assert out["ready"][("test", "Run unit tests")]["n"] == 3


def test_render_report_has_caveat_and_tables():
    rows = _rows("test", "Run unit tests", [30.0, 31.0, 29.0])
    rows += _rows("test", agg.JOB_TOTAL, [40.0, 41.0, 39.0])
    report = agg.render_report(agg.aggregate(rows), {"pr_number": 95, "run_count": 3})
    assert "# CI Pipeline Timing Benchmark" in report
    assert "runners are shared and noisy" in report  # variance caveat
    assert "## Job: test" in report
    assert "**Job total**" in report
    assert "Run unit tests" in report
    assert "Pull request: #95" in report


def test_render_report_withheld_appendix():
    rows = _rows("check", "Run lint tools", [12.0])  # under min samples
    report = agg.render_report(agg.aggregate(rows))
    assert "Appendix" in report
    assert "Run lint tools" in report


def test_empty_dataset_renders_placeholder():
    report = agg.render_report(agg.aggregate([]))
    assert "No timing data collected yet" in report


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
