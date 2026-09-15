"""Collect per-step timing rows for a CI run from the GitHub Actions API (PRO-368).

Part of the continuous CI-timing benchmark (see
``doc/01_Implementation_Plan_CI_Timing_Benchmark.md``). This module reads the
authoritative per-job / per-step timings that GitHub records
(``started_at`` / ``completed_at`` / ``conclusion``) and turns a single run into
CSV rows, applying the run / job / step exclusion rules so that only clean,
successful samples are kept.

Design notes
------------
* Standard library only, matching the other CI support scripts.
* The parsing / exclusion logic (:func:`extract_rows`, :func:`dedup_latest_attempt`)
  is pure and unit-tested; the thin :func:`main` wrapper shells out to ``gh api``
  to fetch the JSON so the network layer stays out of the tested code path.

CSV schema (one row per successful step, plus one ``<job total>`` row per job)::

    run_id, run_attempt, pr_number, head_sha, workflow_sha, created_at,
    job_name, step_name, step_number, duration_s, conclusion, cache_state
"""

from __future__ import annotations

import csv
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

from validator import validate_json  # noqa: E402

#: CSV column order (kept stable; consumers rely on it).
FIELDS = [
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
    "branch",
]

#: GitHub's synthetic housekeeping steps, excluded from timing by default.
_HOUSEKEEPING = {"Set up job", "Complete job"}

#: Sentinel step name for the per-job total row.
JOB_TOTAL = "<job total>"


def parse_iso(value: Optional[str]) -> Optional[datetime.datetime]:
    """Parse an ISO-8601 timestamp (``...Z`` accepted); ``None`` on failure."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_s(started: Optional[str], completed: Optional[str]) -> Optional[float]:
    """Return ``completed - started`` in seconds, or ``None`` if unavailable."""
    a, b = parse_iso(started), parse_iso(completed)
    if a is None or b is None:
        return None
    delta = (b - a).total_seconds()
    return round(delta, 3) if delta >= 0 else None


def _is_housekeeping(name: str) -> bool:
    return name in _HOUSEKEEPING or name.startswith("Post ")


def extract_rows(
    run_meta: dict,
    jobs: list[dict],
    *,
    include_housekeeping: bool = False,
) -> list[dict]:
    """Turn one run's jobs JSON into timing rows, applying the exclusion rules.

    * Run level: nothing is emitted unless ``run_meta['conclusion'] == 'success'``.
    * Job level: only jobs whose ``conclusion == 'success'`` contribute.
    * Step level: only steps whose ``conclusion == 'success'`` with both
      timestamps; housekeeping steps are dropped unless ``include_housekeeping``.

    Each contributing job also yields a ``<job total>`` row (``step_number`` 0).
    """
    if run_meta.get("conclusion") != "success":
        return []

    base = {
        "run_id": run_meta.get("run_id"),
        "run_attempt": run_meta.get("run_attempt", 1),
        "pr_number": run_meta.get("pr_number", ""),
        "head_sha": run_meta.get("head_sha", ""),
        "workflow_sha": run_meta.get("workflow_sha", ""),
        "created_at": run_meta.get("created_at", ""),
        "branch": run_meta.get("branch", "master"),
        "cache_state": run_meta.get("cache_state", "unknown"),
    }

    rows: list[dict] = []
    for job in jobs:
        if job.get("conclusion") != "success":
            continue
        job_name = job.get("name", "")

        job_total = duration_s(job.get("started_at"), job.get("completed_at"))
        if job_total is not None:
            rows.append(
                {
                    **base,
                    "job_name": job_name,
                    "step_name": JOB_TOTAL,
                    "step_number": 0,
                    "duration_s": job_total,
                    "conclusion": "success",
                }
            )

        for step in job.get("steps", []):
            name = step.get("name", "")
            if step.get("conclusion") != "success":
                continue
            if _is_housekeeping(name) and not include_housekeeping:
                continue
            dur = duration_s(step.get("started_at"), step.get("completed_at"))
            if dur is None:
                continue
            rows.append(
                {
                    **base,
                    "job_name": job_name,
                    "step_name": name,
                    "step_number": step.get("number", 0),
                    "duration_s": dur,
                    "conclusion": "success",
                }
            )
    return rows


def dedup_latest_attempt(rows: list[dict]) -> list[dict]:
    """Keep one row per (run_id, job_name, step_number), preferring the latest attempt.

    A re-run (higher ``run_attempt``) supersedes the earlier attempt's samples so
    the dataset never double-counts a single logical run.
    """
    best: dict[tuple, dict] = {}
    for row in rows:
        key = (row["run_id"], row["job_name"], row["step_number"])
        current = best.get(key)
        if current is None or int(row["run_attempt"]) >= int(current["run_attempt"]):
            best[key] = row
    # Preserve a stable order: by run_id, job, step_number.
    return sorted(
        best.values(),
        key=lambda r: (str(r["run_id"]), r["job_name"], int(r["step_number"])),
    )


def read_csv(path: Path) -> list[dict]:
    """Read an existing timings CSV into a list of dict rows (empty if absent)."""
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write rows to a timings CSV using the stable :data:`FIELDS` order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDS})


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )


def write_json(rows: list[dict], run_meta: dict, path: Path) -> None:
    """Append run data to a JSON dataset with the v1.0 schema wrapper.

    Reads existing JSON data, appends new rows, deduplicates by
    ``(run_id, job_name, step_number)`` with the latest attempt winning,
    validates the result, and writes it back with ``schema_version`` and
    ``generated_at``. Validation failures are logged as warnings and the write
    is skipped to preserve the non-gating invariant.
    """
    existing: dict = {"schema_version": "v1.0", "generated_at": "", "runs": []}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"WARNING: unable to read existing JSON at {path}: {exc}",
                file=sys.stderr,
            )
            return

    merged = dedup_latest_attempt(existing.get("runs", []) + rows)
    payload = {
        "schema_version": "v1.0",
        "generated_at": _utc_now(),
        "runs": merged,
    }
    errors = validate_json(payload)
    if errors:
        print(f"WARNING: invalid JSON data for {path}: {errors}", file=sys.stderr)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def _gh_api(path: str) -> object:
    """Fetch JSON from the GitHub API via the ``gh`` CLI (thin, untested wrapper)."""
    out = subprocess.run(
        ["gh", "api", "--paginate", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def main() -> None:
    """Fetch one run's timings and merge them into the dataset CSV.

    Usage: ``collect_ci_timings.py <repo> <run_id> <csv_path>``. Run metadata is
    read from the environment where available (GITHUB_* / RUN_* variables).
    """
    import os

    if len(sys.argv) != 4:
        print(
            "usage: collect_ci_timings.py <repo> <run_id> <csv_path>", file=sys.stderr
        )
        raise SystemExit(2)
    repo, run_id, csv_path = sys.argv[1], sys.argv[2], Path(sys.argv[3])

    run = _gh_api(f"repos/{repo}/actions/runs/{run_id}")
    jobs = _gh_api(f"repos/{repo}/actions/runs/{run_id}/jobs")
    pulls = run.get("pull_requests") or []
    run_meta = {
        "run_id": run.get("id"),
        "run_attempt": run.get("run_attempt", 1),
        "pr_number": (
            pulls[0].get("number") if pulls else os.environ.get("PR_NUMBER", "")
        ),
        "head_sha": run.get("head_sha", ""),
        "workflow_sha": run.get("workflow_sha", ""),
        "created_at": run.get("created_at", ""),
        "conclusion": run.get("conclusion"),
        "branch": os.environ.get("GITHUB_HEAD_REF")
        or os.environ.get("GITHUB_REF_NAME")
        or "master",
    }
    new_rows = extract_rows(run_meta, jobs.get("jobs", []))
    merged = dedup_latest_attempt(read_csv(csv_path) + new_rows)
    write_csv(csv_path, merged)
    write_json(new_rows, run_meta, DATA_DIR / "runtimes.json")
    print(
        f"collected {len(new_rows)} rows from run {run_id}; dataset now {len(merged)}"
    )


if __name__ == "__main__":
    main()
