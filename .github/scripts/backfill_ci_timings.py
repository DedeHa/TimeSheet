"""Backfill the CI-timing dataset from historical successful PR runs (PRO-369).

Sweeps every `pull_request` run of the `Python CI` workflow whose conclusion is
`success`, collects per-job / per-step timings for each via the GitHub Actions
API, applies the same run / job / step exclusion rules as
:mod:`collect_ci_timings`, and merges the result into the dataset CSV with
latest-attempt de-duplication (so a re-run supersedes its earlier attempt).

The sweep is **idempotent**: re-running it produces the same CSV (dedup key is
``run_id`` + ``run_attempt`` + ``job_name`` + ``step_number``), which is what
makes the ``workflow_dispatch`` backfill safe to run repeatedly.

Standard library only (``json``, ``argparse``, ``subprocess`` for ``gh api``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

# Reuse the parsing / exclusion / dedup logic so the backfill and the
# continuous capture path cannot drift apart.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import collect_ci_timings as c  # noqa: E402

#: Target workflow name; runs of any other workflow are out of scope.
TARGET_WORKFLOW = "Python CI"


def _gh_api(path: str) -> object:
    """Fetch JSON from the GitHub API via the ``gh`` CLI (thin wrapper)."""
    import subprocess

    out = subprocess.run(
        ["gh", "api", "--paginate", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def list_successful_pr_runs(repo: str) -> Iterable[dict]:
    """Yield successful `pull_request` runs of ``Python CI`` (newest first).

    Pagination via ``gh api --paginate`` handles the full history. Runs whose
    conclusion is anything other than ``success`` are skipped here so the
    per-run exclusion rule (A.4) is enforced at the source.
    """
    payload = _gh_api(
        f"repos/{repo}/actions/workflows/python-ci.yml/runs"
        "?event=pull_request&status=success&per_page=100"
    )
    runs = (payload or {}).get("workflow_runs", []) if isinstance(payload, dict) else []
    for run in runs:
        if run.get("conclusion") == "success":
            yield run


def backfill(repo: str, csv_path: Path, *, include_housekeeping: bool = False) -> int:
    """Append timings for every qualifying historical run; return rows added.

    Existing rows are preserved and de-duplicated against the new ones, so a
    re-run is a no-op on the dataset.
    """
    existing = c.read_csv(csv_path)
    # Index existing rows by the full dedup key (run_id, run_attempt, job, step)
    # so we can tell "same logical sample, different attempt" from "already
    # captured" - the backfill must skip the former and supersede with the
    # latter so the dataset never carries both.
    existing_by_key: dict[tuple, dict] = {}
    for r in existing:
        key = (
            str(r.get("run_id", "")),
            str(r.get("run_attempt", "")),
            r.get("job_name", ""),
            str(r.get("step_number", "")),
        )
        cur = existing_by_key.get(key)
        if cur is None or int(r.get("run_attempt") or 0) >= int(
            cur.get("run_attempt") or 0
        ):
            existing_by_key[key] = r

    new_rows: list[dict] = []
    runs_seen = 0
    for run in list_successful_pr_runs(repo):
        runs_seen += 1
        run_id = run.get("id")
        if run_id is None:
            continue
        jobs = _gh_api(f"repos/{repo}/actions/runs/{run_id}/jobs")
        run_meta = {
            "run_id": run_id,
            "run_attempt": run.get("run_attempt", 1),
            "pr_number": (run.get("pull_requests") or [{}])[0].get("number", ""),
            "head_sha": run.get("head_sha", ""),
            "workflow_sha": run.get("workflow_sha", ""),
            "created_at": run.get("created_at", ""),
            "conclusion": run.get("conclusion"),
        }
        for row in c.extract_rows(
            run_meta,
            (jobs or {}).get("jobs", []),
            include_housekeeping=include_housekeeping,
        ):
            key = (
                str(row["run_id"]),
                str(row["run_attempt"]),
                row["job_name"],
                str(row["step_number"]),
            )
            cur = existing_by_key.get(key)
            if cur is not None and int(row["run_attempt"]) <= int(cur["run_attempt"]):
                continue  # already captured at this attempt or a newer one
            existing_by_key[key] = row
            new_rows.append(row)

    merged = c.dedup_latest_attempt(list(existing_by_key.values()) + new_rows)
    c.write_csv(csv_path, merged)
    print(
        f"backfilled {runs_seen} qualifying runs; added {len(new_rows)} new rows; "
        f"dataset now {len(merged)}"
    )
    return len(new_rows)


def main() -> None:
    """Usage: ``backfill_ci_timings.py --repo OWNER/NAME --csv PATH``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        required=True,
        help="owner/name, e.g. mainhatten/TimeSheet",
    )
    parser.add_argument("--csv", required=True, help="path to ci-timings.csv")
    parser.add_argument(
        "--include-housekeeping",
        action="store_true",
        help="include GitHub housekeeping steps (Set up job / Post ...)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    backfill(args.repo, csv_path, include_housekeeping=args.include_housekeeping)


if __name__ == "__main__":
    main()
