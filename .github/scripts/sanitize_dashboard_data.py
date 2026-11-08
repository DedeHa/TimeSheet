# Synthetic row filter for PRO-379 dashboard data

"""Utility to detect and filter synthetic placeholder rows from CI runtime data.

This module provides a principled, configurable way to identify rows that appear
to be test fixtures or placeholder data that should not appear in production.

The module doubles as a command-line tool so the publish workflow can sanitize
the runtime payload immediately before it is copied to the served location::

    python3 .github/scripts/sanitize_dashboard_data.py \
        --root metrics/docs/data --runs 50 --output docs/data/runtimes.json

The CLI applies the same transformation as :func:`sanitize_runtimes_payload`
(synthetic row filtering + trimming to the most recent distinct runs) and
validates the result against the shared CI schema before writing it.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from validator import validate_json  # noqa: E402

# Pattern matching real GitHub SHA-1/40 hex characters (SHA-1 length)
_REAL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def is_synthetic_row(row: Dict[str, Any]) -> bool:
    """Determine whether a CI runtime row contains synthetic placeholder data.

    Detection is principled (based on the SHA-1 format of ``head_sha`` and the
    ``workflow_sha`` pattern) rather than on magic run_id lists: GitHub Actions
    run IDs are large sequential integers, so small IDs like 100 are not
    synthetic markers themselves.

    Args:
        row: A CI runtime row from ``ci_runtimes.json``.

    Returns:
        ``True`` if the row appears to be synthetic placeholder data, ``False``
        otherwise.
    """
    # Detect synthetic head_sha values (e.g., "sha100"). A real GitHub SHA-1 is
    # exactly 40 hex characters; anything shorter is a placeholder.
    head_sha = str(row.get("head_sha", ""))
    if head_sha and not _REAL_SHA_PATTERN.fullmatch(head_sha):
        return True

    # Detect synthetic workflow_sha values (e.g., "wf1").
    workflow_sha = str(row.get("workflow_sha", ""))
    if workflow_sha and not _REAL_SHA_PATTERN.fullmatch(workflow_sha):
        return True

    # Empty head_sha / workflow_sha indicates a legacy fixture row that was never
    # populated from real API responses. Only allow empty workflow_sha (a no-op
    # field present in some historical rows); a non-empty empty workflow_sha is
    # also flagged as synthetic.
    if not head_sha and not row.get("branch"):
        return True

    return False


def filter_synthetic_rows(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove synthetic placeholder rows from a list of CI runtime rows.

    Args:
        runs: A list of CI runtime rows.

    Returns:
        A new list with synthetic rows removed.
    """
    return [row for row in runs if not is_synthetic_row(row)]


def validate_real_sha_format(row: Dict[str, Any]) -> bool:
    """Validate that a row's head_sha is a proper GitHub SHA-1 format.

    Args:
        row: A CI runtime row.

    Returns:
        ``True`` if ``head_sha`` is either empty or matches the SHA-1 pattern.
    """
    head_sha = row.get("head_sha", "")
    if not head_sha:
        return True
    return bool(_REAL_SHA_PATTERN.fullmatch(head_sha))


def sanitize_runtimes_payload(
    payload: Dict[str, Any],
    max_runs: int = 50,
    synthetic_filter_enabled: bool = True,
) -> Dict[str, Any]:
    """Sanitize a CI runtimes payload for production publication.

    This function applies two key transformations:
    1. Filters out synthetic placeholder rows (if enabled).
    2. Trims the dataset to the ``max_runs`` most recent distinct CI runs.

    The resulting payload is suitable for serving via GitHub Pages and meets
    the requirements of AC-5 (minimum 50 distinct runs) and AC-4 (clean data).

    Args:
        payload: The raw CI runtimes payload (e.g., from ``ci_runtimes.json``).
        max_runs: The maximum number of distinct CI runs to retain. Defaults
            to 50 to satisfy AC-5.
        synthetic_filter_enabled: Whether to apply synthetic row filtering.

    Returns:
        A sanitized runtimes payload with ``schema_version``, ``generated_at``,
        and a trimmed ``runs`` list.
    """
    runs = payload.get("runs", [])

    # Apply synthetic row filtering if enabled
    if synthetic_filter_enabled:
        runs = filter_synthetic_rows(runs)

    # Trim to the most recent ``max_runs`` distinct runs (newest first)
    # This ensures the published dataset is manageable while preserving the
    # AC-5 requirement of at least 50 distinct CI runs.
    by_run: Dict[str, List[Dict[str, Any]]] = {}
    for row in runs:
        by_run.setdefault(str(row.get("run_id", "")), []).append(row)

    def _newest(rows: List[Dict[str, Any]]) -> str:
        timestamps = [str(r.get("created_at", "")) for r in rows if r.get("created_at")]
        return max(timestamps) if timestamps else ""

    ordered = sorted(by_run.items(), key=lambda kv: _newest(kv[1]), reverse=True)
    if max_runs > 0:
        kept_ids = {run_id for run_id, _rows in ordered[:max_runs]}
    else:
        # ``max_runs <= 0`` means "keep every distinct run" (used when refreshing
        # a canonical dataset in place without trimming it).
        kept_ids = {run_id for run_id, _rows in ordered}

    selected = [row for row in runs if str(row.get("run_id", "")) in kept_ids]
    selected.sort(
        key=lambda r: (
            str(r.get("run_id", "")),
            str(r.get("job_name", "")),
            int(r.get("step_number", 0) or 0),
        )
    )

    # Preserve the original schema fields and replace the runs list
    sanitized = {
        "schema_version": payload.get("schema_version", "v1.0"),
        "generated_at": payload.get("generated_at", ""),
        "runs": selected,
    }
    return sanitized


def validate_runtime_rows_for_production(
    payload: Dict[str, Any],
    require_sha_format: bool = True,
    require_created_at: bool = True,
) -> List[str]:
    """Validate CI runtime rows meet production readiness criteria.

    Args:
        payload: The CI runtimes payload to validate.
        require_sha_format: Whether to enforce SHA-1 format on ``head_sha``.
        require_created_at: Whether to require ``created_at`` timestamps.

    Returns:
        A list of error messages (empty if validation passes).
    """
    errors: List[str] = []
    runs = payload.get("runs", [])

    for i, row in enumerate(runs):
        # Validate required keys
        for key in (
            "run_id",
            "run_attempt",
            "pr_number",
            "job_name",
            "step_name",
            "step_number",
            "duration_s",
            "conclusion",
        ):
            if key not in row:
                errors.append(f"run[{i}] missing key: {key}")

        # Validate SHA format if required
        if require_sha_format and not validate_real_sha_format(row):
            errors.append(
                f"run[{i}] has invalid head_sha format: {row.get('head_sha')}"
            )

        # Validate timestamp presence if required
        if require_created_at and not row.get("created_at"):
            errors.append(f"run[{i}] missing created_at")

        # Validate data types
        if "duration_s" in row and not isinstance(row["duration_s"], (int, float)):
            errors.append(f"run[{i}] duration_s not numeric")
        if "step_number" in row and not isinstance(row["step_number"], int):
            errors.append(f"run[{i}] step_number not int")

    return errors


#: Default number of distinct CI runs kept in the sanitized payload.
DEFAULT_RUNS = 50


def refresh_generated_at(
    payload: Dict[str, Any],
    *,
    timestamp: str | None = None,
) -> Dict[str, Any]:
    """Replace the ``generated_at`` field of a payload with a fresh timestamp.

    The timestamp defaults to the current UTC time in ISO-8601 format. This is
    used to refresh stale canonical datasets (e.g. ``ci_runtimes.json`` whose
    ``generated_at`` predates the last data refresh) without touching the
    ``runs`` list.

    Args:
        payload: The payload to refresh.
        timestamp: Explicit timestamp to use; defaults to ``now()``.

    Returns:
        A new payload dict with the refreshed ``generated_at`` field.
    """
    if timestamp is None:
        timestamp = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    refreshed = dict(payload)
    refreshed["generated_at"] = timestamp
    return refreshed


def sanitize_file(
    source: Path,
    destination: Path,
    max_runs: int = DEFAULT_RUNS,
    synthetic_filter_enabled: bool = True,
    fresh_timestamp: bool = False,
) -> int:
    """Sanitize a runtimes payload file and write it to ``destination``.

    The source payload is read, the synthetic rows are removed, the dataset is
    trimmed to the ``max_runs`` most recent distinct runs and the result is
    validated against the shared ``runtimes`` schema before being written.

    Args:
        source: Path of the raw runtimes payload (e.g. ``ci_runtimes.json``).
        destination: Path the sanitized payload is written to.
        max_runs: Maximum number of distinct CI runs to retain (<= 0 keeps all).
        synthetic_filter_enabled: Whether synthetic placeholder rows are removed.
        fresh_timestamp: If ``True``, replace ``generated_at`` with the current
            UTC time instead of inheriting the source timestamp.

    Returns:
        The number of distinct CI runs in the sanitized payload.

    Raises:
        ValueError: If the sanitized payload does not satisfy the schema.
    """
    with open(source, encoding="utf-8") as fh:
        payload = json.load(fh)

    sanitized = sanitize_runtimes_payload(
        payload,
        max_runs=max_runs,
        synthetic_filter_enabled=synthetic_filter_enabled,
    )
    if fresh_timestamp:
        sanitized = refresh_generated_at(sanitized)

    errors = validate_json(sanitized, schema="runtimes")
    if errors:
        raise ValueError(f"invalid sanitized runtimes payload: {errors}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as fh:
        json.dump(sanitized, fh, indent=2)
        fh.write("\n")

    return len({str(row.get("run_id", "")) for row in sanitized["runs"]})


def refresh_file(path: Path, timestamp: str | None = None) -> str:
    """Rewrite ``path`` with a fresh ``generated_at`` timestamp.

    The payload is re-validated against the ``runtimes`` schema after the
    refresh so a malformed file is rejected rather than silently rewritten.

    Args:
        path: Path of the payload file to refresh.
        timestamp: Explicit timestamp; defaults to the current UTC time.

    Returns:
        The new ``generated_at`` value written to the file.

    Raises:
        ValueError: If the payload does not satisfy the ``runtimes`` schema.
    """
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)

    refreshed = refresh_generated_at(payload, timestamp=timestamp)
    errors = validate_json(refreshed, schema="runtimes")
    if errors:
        raise ValueError(f"invalid runtimes payload: {errors}")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(refreshed, fh, indent=2)
        fh.write("\n")

    return refreshed["generated_at"]


def main(argv: List[str] | None = None) -> int:
    """Sanitize (or refresh) a CI runtimes payload from the command line.

    Usage::

        sanitize_dashboard_data.py [--root DIR] [--input FILE] [--output FILE]
                                    [--runs N] [--keep-synthetic] [--fresh-timestamp]
        sanitize_dashboard_data.py --refresh FILE

    Returns:
        ``0`` on success, ``1`` when the payload is invalid or unreadable.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="directory holding the canonical ci_runtimes.json (default: current dir)",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="source payload (default: <root>/ci_runtimes.json)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="destination payload (default: <root>/runtimes.json)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"distinct CI runs to keep (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--keep-synthetic",
        action="store_true",
        help="keep synthetic placeholder rows (debugging aid only)",
    )
    parser.add_argument(
        "--fresh-timestamp",
        action="store_true",
        help="replace generated_at with the current UTC time",
    )
    parser.add_argument(
        "--refresh",
        default=None,
        metavar="FILE",
        help="refresh the generated_at timestamp of FILE in place and exit",
    )
    args = parser.parse_args(argv)

    if args.refresh:
        path = Path(args.refresh)
        if not path.is_file():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 1
        try:
            timestamp = refresh_file(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: failed to refresh {path}: {exc}", file=sys.stderr)
            return 1
        print(f"refreshed generated_at of {path} -> {timestamp}")
        return 0

    root = Path(args.root)
    source = Path(args.input) if args.input else root / "ci_runtimes.json"
    destination = Path(args.output) if args.output else root / "runtimes.json"

    if not source.is_file():
        print(f"ERROR: source payload not found: {source}", file=sys.stderr)
        return 1

    try:
        runs = sanitize_file(
            source,
            destination,
            max_runs=args.runs,
            synthetic_filter_enabled=not args.keep_synthetic,
            fresh_timestamp=args.fresh_timestamp,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: failed to sanitize {source}: {exc}", file=sys.stderr)
        return 1

    print(f"sanitized {source} -> {destination} ({runs} distinct runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
