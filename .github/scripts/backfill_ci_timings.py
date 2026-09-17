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
from validator import validate_json  # noqa: E402

#: Target workflow name; runs of any other workflow are out of scope.
TARGET_WORKFLOW = "Python CI"

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def _gh_api(path: str) -> object:
    """Fetch JSON from the GitHub API via the ``gh`` CLI (thin wrapper)."""
    import subprocess

    out = subprocess.run(
        ["gh", "api", "--paginate", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    # gh api --paginate emits one JSON document per page, concatenated.
    # Parse each document separately and merge list payloads.
    decoder = json.JSONDecoder()
    payloads = []
    idx = 0
    while idx < len(out):
        while idx < len(out) and out[idx].isspace():
            idx += 1
        if idx >= len(out):
            break
        payload, idx = decoder.raw_decode(out, idx)
        payloads.append(payload)
    if not payloads:
        return None
    if len(payloads) == 1:
        return payloads[0]
    if all(isinstance(p, list) for p in payloads):
        return [item for payload in payloads for item in payload]
    if all(
        isinstance(p, dict) and isinstance(p.get("workflow_runs"), list)
        for p in payloads
    ):
        merged = dict(payloads[0])
        merged["workflow_runs"] = [
            run for payload in payloads for run in payload.get("workflow_runs", [])
        ]
        return merged
    return payloads[0]


def list_successful_pr_runs(
    repo: str, since_run_id: int | None = None, since_date: str | None = None
) -> Iterable[dict]:
    """Yield successful `pull_request` runs of ``Python CI`` (newest first).

    Pagination via ``gh api --paginate`` handles the full history. Runs whose
    conclusion is anything other than ``success`` are skipped here so the
    per-run exclusion rule (A.4) is enforced at the source.

    Args:
        repo: Repository name, e.g. "owner/repo"
        since_run_id: Only yield runs with id > since_run_id (newer runs)
        since_date: ISO 8601 date string; only yield runs created after this date
    """
    query_parts = [
        "event=pull_request",
        "status=success",
        "per_page=100",
    ]
    if since_date:
        query_parts.append(f"created>={since_date}")
    payload = _gh_api(
        f"repos/{repo}/actions/workflows/python-ci.yml/runs" f"?{'&'.join(query_parts)}"
    )
    runs = (payload or {}).get("workflow_runs", []) if isinstance(payload, dict) else []
    for run in runs:
        if since_run_id is not None and run.get("id", 0) <= since_run_id:
            continue
        if run.get("conclusion") == "success":
            yield run


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    import datetime

    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )


def _write_json(runs: list[dict], path: Path) -> None:
    """Write runs to a JSON file with the v1.0 schema wrapper.

    Reads existing JSON data, appends new runs, deduplicates by
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

    merged = c.dedup_latest_attempt(existing.get("runs", []) + runs)
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


def migrate_csv_to_json(csv_path: Path, json_path: Path) -> int:
    """Migrate a CSV dataset to the JSON runtime format.

    Args:
        csv_path: Path to the source CSV file
        json_path: Path to the destination JSON file

    Returns:
        Number of rows migrated

    Raises:
        ValueError: If the source and destination row counts do not match
    """
    rows = c.read_csv(csv_path)
    # CSV parsing yields strings for all fields; the JSON schema requires
    # numeric types for duration_s and step_number. Convert where possible
    # so valid data passes validation, while invalid strings are left in place
    # so the validator can report them.
    typed_rows = []
    for row in rows:
        typed = dict(row)
        if "duration_s" in row:
            try:
                typed["duration_s"] = float(row["duration_s"])
            except (TypeError, ValueError):
                pass  # leave original string so validator can report the error
        if "step_number" in row:
            try:
                typed["step_number"] = int(row["step_number"])
            except (TypeError, ValueError):
                pass  # leave original string so validator can report the error
        typed_rows.append(typed)

    payload = {
        "schema_version": "v1.0",
        "generated_at": _utc_now(),
        "runs": typed_rows,
    }
    errors = validate_json(payload)
    if errors:
        raise ValueError(f"invalid JSON data for {json_path}: {errors}")

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    return len(rows)


def backfill(
    repo: str,
    csv_path: Path,
    *,
    include_housekeeping: bool = False,
    since_run_id: int | None = None,
    since_date: str | None = None,
) -> int:
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
    for run in list_successful_pr_runs(
        repo, since_run_id=since_run_id, since_date=since_date
    ):
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
            "branch": run.get("head_branch", "master"),
            "cache_state": "unknown",
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
    _write_json(new_rows, DATA_DIR / "runtimes.json")
    print(
        f"backfilled {runs_seen} qualifying runs; added {len(new_rows)} new rows; "
        f"dataset now {len(merged)}"
    )
    return len(new_rows)


def main() -> None:
    """Usage: ``backfill_ci_timings.py --repo OWNER/NAME --csv PATH``.

    Optional flags:
      --migrate: migrate CSV to JSON instead of running the backfill
      --json-path: destination for JSON migration (default: data/runtimes.json)
      --since-run-id: only backfill runs newer than this run ID
      --since-date: only backfill runs created on or after this date (ISO 8601)
    """
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
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="migrate CSV to JSON instead of running the backfill",
    )
    parser.add_argument(
        "--json-path",
        default=str(DATA_DIR / "runtimes.json"),
        help="destination for JSON migration",
    )
    parser.add_argument(
        "--since-run-id",
        type=int,
        default=None,
        help=(
            "only backfill runs newer than this run ID "
            "(extracts branch info from that point)"
        ),
    )
    parser.add_argument(
        "--since-date",
        default=None,
        help=(
            "only backfill runs created on or after this date "
            "(ISO 8601, e.g. 2025-01-01)"
        ),
    )
    args = parser.parse_args()

    if args.migrate:
        count = migrate_csv_to_json(Path(args.csv), Path(args.json_path))
        print(f"migrated {count} rows from {args.csv} -> {args.json_path}")
        return

    csv_path = Path(args.csv)
    backfill(
        args.repo,
        csv_path,
        include_housekeeping=args.include_housekeeping,
        since_run_id=args.since_run_id,
        since_date=args.since_date,
    )


if __name__ == "__main__":
    main()
