"""JSON schema validation for CI timing data (PRO-375).

Validates the structure of docs/data/ci_runtimes.json and docs/data/ci_metrics.json.
Standard library only, non-gating invariant (returns error list, never raises).

The module doubles as a command-line tool so the publish workflow can validate
JSON payloads before copying them to the served location::

    python3 .github/scripts/validator.py docs/data/ci_metrics.json metrics
    python3 .github/scripts/validator.py docs/data/ci_runtimes.json runtimes

The CLI reads the file, validates it against the appropriate schema, and exits
with status ``0`` on success or ``1`` if the payload is invalid.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_ROOT_KEYS = {"schema_version", "generated_at", "runs"}
REQUIRED_RUN_KEYS = {
    "run_id",
    "run_attempt",
    "pr_number",
    "job_name",
    "step_name",
    "step_number",
    "duration_s",
    "conclusion",
}
REQUIRED_METRICS_KEYS = {"ready", "withheld"}
STAT_KEYS = {
    "n",
    "mean",
    "stddev",
    "median",
    "p95",
    "min",
    "max",
    "last",
    "rolling",
    "bollinger",
    "distribution",
}


def _validate_root(data: dict, errors: list[str]) -> None:
    if "schema_version" not in data:
        errors.append("missing root key: schema_version")
    elif data["schema_version"] != "v1.0":
        errors.append(f"unsupported schema_version: {data.get('schema_version')}")
    if "generated_at" not in data:
        errors.append("missing root key: generated_at")


def _validate_runs(data: dict, errors: list[str]) -> None:
    if "runs" not in data:
        errors.append("missing root key: runs")
        return
    for i, run in enumerate(data["runs"]):
        for key in REQUIRED_RUN_KEYS:
            if key not in run:
                errors.append(f"run[{i}] missing key: {key}")
        if "duration_s" in run and not isinstance(run["duration_s"], (int, float)):
            errors.append(f"run[{i}] duration_s not numeric")
        if "step_number" in run and not isinstance(run["step_number"], int):
            errors.append(f"run[{i}] step_number not int")
        if "run_id" in run and not isinstance(run["run_id"], (int, str)):
            errors.append(f"run[{i}] run_id not int or str")


def _validate_metrics_root(data: dict, errors: list[str]) -> None:
    for key in REQUIRED_METRICS_KEYS:
        if key not in data:
            errors.append(f"missing metrics key: {key}")


def _validate_metrics_bucket(bucket: dict[str, dict], name: str) -> list[str]:
    errors: list[str] = []
    for key, value in bucket.items():
        if not isinstance(value, dict):
            errors.append(f"{name}[{key}] must be a dict")
        else:
            for stat_key in STAT_KEYS:
                if stat_key not in value:
                    errors.append(f"{name}[{key}] missing stat key: {stat_key}")
    return errors


def _validate_metrics_withheld(data: dict, errors: list[str]) -> None:
    if "withheld" in data:
        for key, value in data["withheld"].items():
            if not isinstance(value, dict):
                errors.append(f"withheld[{key}] must be a dict")
            else:
                if "n" not in value:
                    errors.append(f"withheld[{key}] missing n")
                if "reason" not in value:
                    errors.append(f"withheld[{key}] missing reason")


def _validate_metrics(data: dict, errors: list[str]) -> None:
    _validate_metrics_root(data, errors)
    if "ready" in data:
        errors.extend(_validate_metrics_bucket(data["ready"], "ready"))
    _validate_metrics_withheld(data, errors)


def validate_json(data: dict, schema: str = "runtimes") -> list[str]:
    """Validate JSON structure against schema.

    Args:
        data: JSON data to validate
        schema: "runtimes" or "metrics"

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []
    _validate_root(data, errors)
    if schema == "runtimes":
        _validate_runs(data, errors)
    elif schema == "metrics":
        _validate_metrics(data, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    """Validate a JSON file against the CI timing schema.

    Usage::

        validator.py <file> <schema>

    Returns:
        ``0`` on success, ``1`` if the payload is invalid.
    """
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 2:
        print(f"usage: {Path(__file__).name} <file> <schema>", file=sys.stderr)
        return 1

    file_path, schema = argv
    path = Path(file_path)
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to read {path}: {exc}", file=sys.stderr)
        return 1

    errors = validate_json(data, schema)
    if errors:
        print(f"ERROR: invalid {schema} payload {path}:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    print(f"OK: {path} is valid {schema} payload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
