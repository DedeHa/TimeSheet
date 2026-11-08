"""Seed the GitHub Pages dashboard dataset from the canonical CI datasets.

The dashboard (docs/frontend/) consumes ``docs/data/metrics.json`` and
``docs/data/runtimes.json``. Those files are refreshed automatically by the
``publish-dashboard.yml`` workflow, but the repository must ship a valid,
populated seed so the dashboard is meaningful from the moment the branch is
merged.

This script derives the seed from the canonical datasets that live next to it:

* ``docs/data/ci_metrics.json``  -> ``docs/data/metrics.json``
* ``docs/data/ci_runtimes.json`` -> ``docs/data/runtimes.json``

The metrics payload is copied verbatim (it already satisfies the v1.0 schema
and carries the rolling / Bollinger / distribution series the charts need).
The runtimes payload is trimmed to the most recent ``--runs`` *distinct* CI
runs (default 50, the AC-5 minimum) to keep the repository size sane while
still providing a meaningful history for the run table and the summary panel.

The script is idempotent: ``generated_at`` is inherited from the source
payloads, so re-running it reproduces byte-identical output.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from validator import validate_json  # noqa: E402

#: Default number of distinct CI runs kept in the seeded runtime dataset.
DEFAULT_RUNS = 50

#: Canonical dataset locations relative to the repository root.
DEFAULT_METRICS_SRC = Path("docs") / "data" / "ci_metrics.json"
DEFAULT_RUNTIMES_SRC = Path("docs") / "data" / "ci_runtimes.json"
DEFAULT_METRICS_DST = Path("docs") / "data" / "metrics.json"
DEFAULT_RUNTIMES_DST = Path("docs") / "data" / "runtimes.json"


def _load(path: Path) -> dict:
    """Load a JSON payload from ``path``."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dump(payload: dict, path: Path) -> None:
    """Write ``payload`` to ``path`` as pretty-printed JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def select_recent_runs(runs: list[dict], max_runs: int) -> list[dict]:
    """Keep the rows of the ``max_runs`` most recent distinct CI runs.

    Runs are ordered by their ``created_at`` timestamp (newest first); every
    row belonging to a selected run is kept so per-step detail stays intact.

    Args:
        runs: Rows from the runtimes payload.
        max_runs: Number of distinct runs to keep (<= 0 keeps all).

    Returns:
        The retained rows, ordered by run id then step number.
    """
    if max_runs <= 0:
        return list(runs)

    by_run: dict[str, list[dict]] = {}
    for row in runs:
        by_run.setdefault(str(row.get("run_id", "")), []).append(row)

    def _newest(rows: list[dict]) -> str:
        stamps = [str(r.get("created_at", "")) for r in rows if r.get("created_at")]
        return max(stamps) if stamps else ""

    ordered = sorted(by_run.items(), key=lambda kv: _newest(kv[1]), reverse=True)
    kept_ids = {run_id for run_id, _rows in ordered[:max_runs]}

    selected = [row for row in runs if str(row.get("run_id", "")) in kept_ids]
    return sorted(
        selected,
        key=lambda r: (
            str(r.get("run_id", "")),
            str(r.get("job_name", "")),
            int(r.get("step_number", 0) or 0),
        ),
    )


def seed_metrics(src: Path, dst: Path) -> int:
    """Copy the canonical metrics payload to the dashboard location.

    Returns:
        The number of ``ready`` entries in the seeded payload.
    """
    payload = _load(src)
    errors = validate_json(payload, schema="metrics")
    if errors:
        raise ValueError(f"invalid metrics source {src}: {errors}")
    _dump(payload, dst)
    return len(payload.get("ready", {}))


def seed_runtimes(src: Path, dst: Path, max_runs: int = DEFAULT_RUNS) -> int:
    """Copy (and optionally trim) the runtimes payload to the dashboard location.

    Returns:
        The number of distinct CI runs in the seeded payload.
    """
    payload = _load(src)
    runs = payload.get("runs", [])
    selected = select_recent_runs(runs, max_runs)
    seeded = {
        "schema_version": payload.get("schema_version", "v1.0"),
        "generated_at": payload.get("generated_at", ""),
        "runs": selected,
    }
    errors = validate_json(seeded, schema="runtimes")
    if errors:
        raise ValueError(f"invalid runtimes seed for {dst}: {errors}")
    _dump(seeded, dst)
    return len({str(row.get("run_id", "")) for row in selected})


def main() -> None:
    """Seed the dashboard dataset files.

    Usage: ``seed_dashboard_data.py [--runs N] [--root DIR]``.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="repository root that holds docs/data (default: current directory)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"distinct CI runs to keep in the runtime seed (default: {DEFAULT_RUNS})",
    )
    args = parser.parse_args()

    root = Path(args.root)
    metrics_src = root / DEFAULT_METRICS_SRC
    runtimes_src = root / DEFAULT_RUNTIMES_SRC
    metrics_dst = root / DEFAULT_METRICS_DST
    runtimes_dst = root / DEFAULT_RUNTIMES_DST

    ready = seed_metrics(metrics_src, metrics_dst)
    runs = seed_runtimes(runtimes_src, runtimes_dst, max_runs=args.runs)
    print(
        f"seeded {metrics_dst} ({ready} ready entries) and "
        f"{runtimes_dst} ({runs} distinct runs)"
    )


if __name__ == "__main__":
    main()
