"""System tests for the CI-timing pipeline (PRO-375).

Verifies the end-to-end migration from ci-metrics CSV → data/runtimes.json
and the aggregation into data/metrics.json using real ci-metrics branch data.
Skipped when the ci-metrics branch is not available (e.g. shallow clones).
Standard-library only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import aggregate_ci_timings as agg  # noqa: E402
import backfill_ci_timings as bf  # noqa: E402
import collect_ci_timings as c  # noqa: E402
from validator import validate_json  # noqa: E402

pytestmark = pytest.mark.system

#: Branch holding the historical ci-timings.csv
CI_METRICS_BRANCH = "ci-metrics"
#: Source CSV file on the ci-metrics branch
CI_TIMINGS_CSV = "ci-timings.csv"


def _ci_metrics_available() -> bool:
    """Return True if the ci-metrics branch is reachable from the local repo."""
    try:
        result = subprocess.run(
            ["git", "show", f"{CI_METRICS_BRANCH}:{CI_TIMINGS_CSV}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


@pytest.fixture(scope="module")
def ci_metrics_csv(tmp_path_factory):
    """Extract ci-timings.csv from the ci-metrics branch into a tmp file."""
    if not _ci_metrics_available():
        pytest.skip("ci-metrics branch not available")
    out = tmp_path_factory.mktemp("ci_metrics")
    csv_path = out / "ci-timings.csv"
    result = subprocess.run(
        ["git", "show", f"{CI_METRICS_BRANCH}:{CI_TIMINGS_CSV}"],
        capture_output=True,
        text=True,
        check=True,
    )
    csv_path.write_text(result.stdout, encoding="utf-8")
    return csv_path


@pytest.fixture(scope="module")
def migrated_runtimes(tmp_path_factory, ci_metrics_csv):
    """Run the migrate step: CSV → data/runtimes.json."""
    out = tmp_path_factory.mktemp("migrated")
    json_path = out / "runtimes.json"
    count = bf.migrate_csv_to_json(ci_metrics_csv, json_path)
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return count, data


def test_ci_metrics_csv_has_rows(ci_metrics_csv):
    """The ci-metrics branch CSV contains a non-trivial dataset."""
    rows = c.read_csv(ci_metrics_csv)
    assert len(rows) > 100, f"Expected >100 rows, got {len(rows)}"
    assert all("run_id" in r for r in rows)


def test_migrate_preserves_row_count(migrated_runtimes):
    """migrate_csv_to_json preserves the exact row count from the CSV."""
    count, data = migrated_runtimes
    assert count == len(data["runs"])
    assert count > 100


def test_migrate_validates_schema(migrated_runtimes):
    """The migrated JSON passes schema validation."""
    _count, data = migrated_runtimes
    errors = validate_json(data)
    assert not errors, f"Validation errors: {errors}"


def test_migrate_preserves_all_fields(migrated_runtimes):
    """All CSV fields are present in the migrated JSON."""
    _count, data = migrated_runtimes
    csv_fields = {
        "run_id",
        "run_attempt",
        "pr_number",
        "head_sha",
        "workflow_sha",
        "created_at",
        "job_name",
        "step_name",
        "step_number",
        "duration_s",
        "conclusion",
        "cache_state",
    }
    for run in data["runs"]:
        missing = csv_fields - set(run.keys())
        assert not missing, f"Missing fields in run: {missing}"


def test_migrate_duration_s_is_numeric(migrated_runtimes):
    """duration_s is numeric in the migrated JSON."""
    _count, data = migrated_runtimes
    for run in data["runs"]:
        assert isinstance(
            run.get("duration_s"), (int, float)
        ), f"duration_s not numeric: {run.get('duration_s')!r}"


def test_migrate_step_number_is_int(migrated_runtimes):
    """step_number is an integer in the migrated JSON."""
    _count, data = migrated_runtimes
    for run in data["runs"]:
        assert isinstance(
            run.get("step_number"), int
        ), f"step_number not int: {run.get('step_number')!r}"


def test_aggregate_matches_migrated_data(migrated_runtimes, tmp_path):
    """Aggregating the migrated data produces valid metrics.json."""
    _count, data = migrated_runtimes
    agg_data = agg.aggregate(data["runs"])
    metrics_path = tmp_path / "metrics.json"
    agg.write_metrics(agg_data, metrics_path)
    with open(metrics_path, encoding="utf-8") as fh:
        metrics = json.load(fh)
    errors = validate_json(metrics, schema="metrics")
    assert not errors, f"Metrics validation errors: {errors}"
    assert metrics["schema_version"] == "v1.0"
    assert "ready" in metrics
    assert "withheld" in metrics


def test_csv_json_row_count_match(ci_metrics_csv, migrated_runtimes):
    """CSV row count matches JSON run count after migration."""
    csv_rows = c.read_csv(ci_metrics_csv)
    _count, json_data = migrated_runtimes
    assert len(csv_rows) == len(
        json_data["runs"]
    ), f"CSV rows {len(csv_rows)} != JSON runs {len(json_data['runs'])}"


def test_migrate_idempotent(ci_metrics_csv, tmp_path):
    """Re-running migration produces the same data (ignoring timestamps)."""
    json_path1 = tmp_path / "runtimes1.json"
    json_path2 = tmp_path / "runtimes2.json"
    bf.migrate_csv_to_json(ci_metrics_csv, json_path1)
    bf.migrate_csv_to_json(ci_metrics_csv, json_path2)
    f1 = open(json_path1, encoding="utf-8")
    f2 = open(json_path2, encoding="utf-8")
    with f1, f2:
        data1 = json.load(f1)
        data2 = json.load(f2)
    data1.pop("generated_at")
    data2.pop("generated_at")
    assert data1 == data2
