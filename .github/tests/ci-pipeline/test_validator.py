"""Unit tests for validator.py (PRO-375 JSON output & data validation).

Validates the JSON schema validation functions for CI timing data.
Runs in the .github/tests/ci-pipeline/ CI self-test group. Standard-library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from validator import validate_json  # noqa: E402


def test_validate_json_valid_runtimes():
    """Valid runtimes JSON passes validation."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [
            {
                "run_id": 12345,
                "run_attempt": 1,
                "pr_number": 42,
                "job_name": "check",
                "step_name": "Run lint tools",
                "step_number": 2,
                "duration_s": 15.0,
                "conclusion": "success",
            }
        ],
    }
    errors = validate_json(data, schema="runtimes")
    assert errors == [], f"Expected no errors, got: {errors}"


def test_validate_json_valid_metrics():
    """Valid metrics JSON passes validation."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {
            "check / Run lint tools": {
                "n": 128,
                "mean": 12.5,
                "stddev": 2.3,
                "median": 12.1,
                "p95": 18.2,
                "min": 8.1,
                "max": 25.4,
                "last": 14.2,
                "rolling": [],
                "bollinger": {},
                "distribution": {},
            }
        },
        "withheld": {
            "test / Slow step": {
                "n": 2,
                "reason": "insufficient_samples",
                "min_samples": 3,
            }
        },
    }
    errors = validate_json(data, schema="metrics")
    assert errors == [], f"Expected no errors, got: {errors}"


def test_validate_json_missing_root_keys():
    """Missing root keys produces errors."""
    # Missing schema_version
    data = {
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("missing root key: schema_version" in e for e in errors)

    # Missing generated_at
    data = {
        "schema_version": "v1.0",
        "runs": [],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("missing root key: generated_at" in e for e in errors)

    # Missing runs (runtimes schema)
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
    }
    errors = validate_json(data, schema="runtimes")
    assert any("missing root key: runs" in e for e in errors)

    # Missing ready (metrics schema)
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "withheld": {},
    }
    errors = validate_json(data, schema="metrics")
    assert any("missing metrics key: ready" in e for e in errors)


def test_validate_json_missing_run_keys():
    """Missing run keys produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [
            {
                "run_id": 12345,
                "run_attempt": 1,
                "pr_number": 42,
                "job_name": "check",
                "step_name": "Run lint tools",
                "step_number": 2,
                "duration_s": 15.0,
                # Missing conclusion
            }
        ],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("run[0] missing key: conclusion" in e for e in errors)


def test_validate_json_invalid_duration_type():
    """Invalid duration_s type produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [
            {
                "run_id": 12345,
                "run_attempt": 1,
                "pr_number": 42,
                "job_name": "check",
                "step_name": "Run lint tools",
                "step_number": 2,
                "duration_s": "fifteen",  # String instead of numeric
                "conclusion": "success",
            }
        ],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("duration_s not numeric" in e for e in errors)


def test_validate_json_invalid_schema_version():
    """Invalid schema_version produces errors."""
    data = {
        "schema_version": "v2.0",  # Wrong version
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("unsupported schema_version: v2.0" in e for e in errors)


def test_validate_json_empty_runs():
    """Empty runs array is valid."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [],
    }
    errors = validate_json(data, schema="runtimes")
    assert errors == [], f"Expected no errors for empty runs, got: {errors}"


def test_validate_json_invalid_step_number_type():
    """Invalid step_number type produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [
            {
                "run_id": 12345,
                "run_attempt": 1,
                "pr_number": 42,
                "job_name": "check",
                "step_name": "Run lint tools",
                "step_number": "two",  # String instead of int
                "duration_s": 15.0,
                "conclusion": "success",
            }
        ],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("step_number not int" in e for e in errors)


def test_validate_json_invalid_run_id_type():
    """Invalid run_id type produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "runs": [
            {
                "run_id": [],  # List instead of int/str
                "run_attempt": 1,
                "pr_number": 42,
                "job_name": "check",
                "step_name": "Run lint tools",
                "step_number": 2,
                "duration_s": 15.0,
                "conclusion": "success",
            }
        ],
    }
    errors = validate_json(data, schema="runtimes")
    assert any("run_id not int or str" in e for e in errors)


def test_validate_json_ready_missing_stat_key():
    """Ready bucket with missing stat key produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {
            "check / Run lint tools": {
                "n": 128,
                "mean": 12.5,
                # Missing stddev, median, p95, min, max, last
            }
        },
        "withheld": {},
    }
    errors = validate_json(data, schema="metrics")
    assert any("missing stat key: stddev" in e for e in errors)


def test_validate_json_ready_not_dict():
    """Valid ready entry must be a dict."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {
            "check / Run lint tools": "not a dict",
        },
        "withheld": {},
    }
    errors = validate_json(data, schema="metrics")
    assert len(errors) > 0
    assert any("ready[check / Run lint tools] must be a dict" in e for e in errors)


def test_validate_json_ready_with_new_stat_keys():
    """Ready entries may include rolling, bollinger, distribution keys (PRO-380)."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {
            "check / Run lint tools": {
                "n": 128,
                "mean": 12.5,
                "stddev": 2.3,
                "median": 12.1,
                "p95": 18.2,
                "min": 8.1,
                "max": 25.4,
                "last": 14.2,
                "rolling": [],
                "bollinger": {},
                "distribution": {},
            }
        },
        "withheld": {},
    }
    errors = validate_json(data, schema="metrics")
    assert errors == [], f"Expected no errors, got: {errors}"


def test_validate_json_withheld_missing_n():
    """Withheld bucket with missing n produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {},
        "withheld": {
            "test / Slow step": {
                "reason": "insufficient_samples",
                # Missing n
            }
        },
    }
    errors = validate_json(data, schema="metrics")
    assert any("missing n" in e for e in errors)


def test_validate_json_withheld_missing_reason():
    """Withheld bucket with missing reason produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {},
        "withheld": {
            "test / Slow step": {
                "n": 2,
                # Missing reason
            }
        },
    }
    errors = validate_json(data, schema="metrics")
    assert any("missing reason" in e for e in errors)


def test_validate_json_withheld_not_dict():
    """Withheld bucket with non-dict value produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {},
        "withheld": {
            "test / Slow step": "not a dict",  # String instead of dict
        },
    }
    errors = validate_json(data, schema="metrics")
    assert any("must be a dict" in e for e in errors)


def test_validate_json_missing_withheld():
    """Missing withheld key produces errors."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
        "ready": {},
    }
    errors = validate_json(data, schema="metrics")
    assert any("missing metrics key: withheld" in e for e in errors)


def test_validate_json_unknown_schema():
    """Unknown schema returns no errors (empty list)."""
    data = {
        "schema_version": "v1.0",
        "generated_at": "2026-09-14T20:57:40Z",
    }
    errors = validate_json(data, schema="unknown")
    assert errors == []


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
