"""Aggregate the CI-timing dataset into a Markdown report (PRO-368).

Implements FR-19 (rolling stats, Bollinger bands, normal distribution)
and QR-12 (CI timing traceability via schema validation).

Reads the ``ci-timings.csv`` produced by ``collect_ci_timings.py`` and renders
running statistics per ``(job, step)`` — count, mean, sample standard deviation,
median, p95, min, max, last — recomputed from the full dataset on every update
(idempotent, no incremental-state drift). Keys with fewer than ``MIN_SAMPLES``
samples are withheld into a "needs more samples" appendix, and the report always
carries the shared-runner variance caveat.

Standard library only.
"""

from __future__ import annotations

import datetime
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from ci_stats import (
    compute_bollinger_bands,
    compute_normal_distribution,
    compute_rolling_stats,
)
from collect_ci_timings import JOB_TOTAL, read_csv
from validator import validate_json

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "docs" / "data"

#: Minimum successful samples before a key's stats are considered meaningful.
MIN_SAMPLES = 3

_CAVEAT = (
    "> ⚠️ GitHub-hosted runners are shared and noisy; per-step times vary "
    "run-to-run (often ±10–30%). Read **stddev alongside mean**, prefer "
    "**median / p95** for decisions, and treat these as **trend indicators**, "
    "not benchmarks of the code itself."
)


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (pct in [0, 100]) over a non-empty list."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(1, min(len(ordered), round(pct / 100 * len(ordered))))
    return ordered[rank - 1]


def stats_for(values: list[float]) -> dict:
    """Compute the summary statistics for one key's samples."""
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "mean": statistics.mean(ordered),
        "stddev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
        "median": statistics.median(ordered),
        "p95": _percentile(ordered, 95),
        "min": ordered[0],
        "max": ordered[-1],
        "last": values[-1],  # chronological last (input order preserved)
    }


def aggregate(rows: list[dict], min_samples: int = MIN_SAMPLES) -> dict:
    """Group rows by (job, step) and compute stats.

    Returns ``{"ready": {...}, "withheld": {...}, "values": {...}}`` where
    keys are ``(job_name, step_name)`` tuples and values are stat dicts.
    ``withheld`` holds keys with fewer than ``min_samples`` samples.
    ``values`` maps each key to the raw sorted duration list for rolling
    and distribution computations.
    """
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        try:
            grouped[(row["job_name"], row["step_name"])].append(
                float(row["duration_s"])
            )
        except (KeyError, ValueError, TypeError):
            continue

    ready: dict[tuple, dict] = {}
    withheld: dict[tuple, dict] = {}
    values: dict[tuple, list[float]] = {}
    for key, vals in grouped.items():
        bucket = ready if len(vals) >= min_samples else withheld
        bucket[key] = stats_for(vals)
        values[key] = sorted(vals)
    return {"ready": ready, "withheld": withheld, "values": values}


def _fmt(value: float) -> str:
    return f"{value:.1f}"


def _job_order(keys: list[tuple]) -> list[str]:
    """Stable job ordering: first-seen order of job names."""
    seen: list[str] = []
    for job, _step in keys:
        if job not in seen:
            seen.append(job)
    return seen


def render_report(agg: dict, meta: Optional[dict] = None) -> str:
    """Render the Markdown timing report from :func:`aggregate` output."""
    meta = meta or {}
    ready = agg["ready"]
    withheld = agg["withheld"]

    lines = ["# CI Pipeline Timing Benchmark", ""]
    if meta.get("pr_number"):
        lines.append(f"Pull request: #{meta['pr_number']}")
    if meta.get("generated_at"):
        lines.append(f"Generated: {meta['generated_at']}")
    if meta.get("run_count") is not None:
        lines.append(f"Included runs: {meta['run_count']}")
    lines += ["", _CAVEAT, ""]

    if not ready and not withheld:
        lines += ["_No timing data collected yet._", ""]
        return "\n".join(lines)

    header = (
        "| Step | n | mean (s) | stddev | median | p95 | min | max | last |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )

    for job in _job_order(list(ready)):
        lines += [f"## Job: {job}", ""]
        # Job total first, then steps by descending mean (slowest first).
        job_keys = [(j, s) for (j, s) in ready if j == job]
        job_keys.sort(key=lambda k: (k[1] != JOB_TOTAL, -ready[k]["mean"]))
        lines.append(header)
        for key in job_keys:
            s = ready[key]
            label = "**Job total**" if key[1] == JOB_TOTAL else key[1]
            lines.append(
                f"| {label} | {s['n']} | {_fmt(s['mean'])} | {_fmt(s['stddev'])} "
                f"| {_fmt(s['median'])} | {_fmt(s['p95'])} | {_fmt(s['min'])} "
                f"| {_fmt(s['max'])} | {_fmt(s['last'])} |"
            )
        lines.append("")

    if withheld:
        lines += [
            f"## Appendix: keys with < {MIN_SAMPLES} samples (withheld)",
            "",
            "| Job | Step | n |",
            "| --- | --- | ---: |",
        ]
        for (job, step), s in sorted(withheld.items()):
            label = "Job total" if step == JOB_TOTAL else step
            lines.append(f"| {job} | {label} | {s['n']} |")
        lines.append("")

    return "\n".join(lines)


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )


def _stringify_keys(d: dict) -> dict:
    """Convert tuple keys (job, step) to 'job / step' strings for JSON."""
    return {f"{job} / {step}": v for (job, step), v in d.items()}


def _add_withheld_reasons(d: dict) -> dict:
    """Add a reason to each withheld entry if missing."""
    result = {}
    for key, value in d.items():
        entry = dict(value)
        if "reason" not in entry:
            entry["reason"] = "insufficient samples"
        result[key] = entry
    return result


def write_metrics(agg_data: dict, path: Path, max_runs: int = 0) -> None:
    """Write aggregated metrics to a JSON file with the v1.0 schema wrapper.

    Formats the output from :func:`aggregate` with ``schema_version`` and
    ``generated_at``, validates it, and writes it to ``path``.
    Validation failures are logged as warnings and the write is skipped.

    For each ready bucket, also computes rolling window statistics,
    Bollinger bands, and normal-distribution parameters from the raw
    duration values.

    Args:
        agg_data: Output from :func:`aggregate`.
        path: Destination JSON path.
        max_runs: Reserved for future use (0 = unlimited).
    """
    raw_values = agg_data.get("values", {})
    ready = agg_data.get("ready", {})
    for key in ready:
        vals = raw_values.get(key)
        if vals:
            window = min(20, len(vals))
            try:
                ready[key]["rolling"] = compute_rolling_stats(vals, window=window)
                ready[key]["bollinger"] = compute_bollinger_bands(
                    vals, window=window, k=2
                )
                ready[key]["distribution"] = compute_normal_distribution(vals)
            except Exception as exc:
                print(f"WARNING: stats for {key}: {exc}", file=sys.stderr)
                ready[key]["rolling"] = []
                ready[key]["bollinger"] = {}
                ready[key]["distribution"] = {}
        else:
            ready[key]["rolling"] = []
            ready[key]["bollinger"] = {}
            ready[key]["distribution"] = {}
    payload = {
        "schema_version": "v1.0",
        "generated_at": _utc_now(),
        "ready": _stringify_keys(ready),
        "withheld": _add_withheld_reasons(
            _stringify_keys(agg_data.get("withheld", {}))
        ),
    }
    errors = validate_json(payload, schema="metrics")
    if errors:
        print(f"WARNING: invalid metrics JSON for {path}: {errors}", file=sys.stderr)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def main() -> None:
    """Read the dataset CSV and write the Markdown report.

    Usage: ``aggregate_ci_timings.py <csv_path> <report_path>``.
    """
    if len(sys.argv) != 3:
        print(
            "usage: aggregate_ci_timings.py <csv_path> <report_path>", file=sys.stderr
        )
        raise SystemExit(2)
    csv_path, report_path = Path(sys.argv[1]), Path(sys.argv[2])

    rows = read_csv(csv_path)
    run_ids = {r.get("run_id") for r in rows if r.get("run_id")}
    agg = aggregate(rows)
    report = render_report(agg, {"run_count": len(run_ids)})
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report + "\n", encoding="utf-8")
    max_runs = int(os.environ.get("MAX_RUNS", "0"))
    write_metrics(agg, DATA_DIR / "ci_metrics.json", max_runs=max_runs)
    print(f"aggregated {len(rows)} rows from {len(run_ids)} runs -> {report_path}")


if __name__ == "__main__":
    main()
