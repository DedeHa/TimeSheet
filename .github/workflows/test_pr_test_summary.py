"""Unit tests for the PR quality-gate summary generator (PRO-337).

These validate the parsing and rendering logic of ``pr_test_summary.py`` in
isolation. Like ``test_docs_traceability.py`` this file lives next to the
workflow and is *not* part of the ``tests/`` suite (``testpaths = ["tests"]``),
so it does not change the 103-test application suite or the coverage gate. It is
executed explicitly by the CI ``test`` job and can be run locally with::

    pytest -q .github/workflows/test_pr_test_summary.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).with_name("pr_test_summary.py")
_spec = importlib.util.spec_from_file_location("pr_test_summary", _MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
# Register before executing so dataclass type resolution can find the module.
sys.modules["pr_test_summary"] = mod
_spec.loader.exec_module(mod)


def _write_junit(path: Path, tests: int, failures: int, errors: int, skipped: int):
    path.write_text(
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuites><testsuite name="pytest" tests="{tests}" '
        f'failures="{failures}" errors="{errors}" skipped="{skipped}" '
        f'time="1.0"></testsuite></testsuites>',
        encoding="utf-8",
    )


def _write_coverage(path: Path, percent: float):
    path.write_text(
        json.dumps({"totals": {"percent_covered": percent}}), encoding="utf-8"
    )


def _all_green_reports(tmp_path: Path):
    _write_junit(tmp_path / "unit-results.xml", tests=79, failures=0, errors=0, skipped=1)
    _write_junit(
        tmp_path / "integration-results.xml", tests=17, failures=0, errors=0, skipped=0
    )
    _write_junit(
        tmp_path / "system-results.xml", tests=7, failures=0, errors=0, skipped=0
    )
    _write_coverage(tmp_path / "coverage.json", 99.1)


def test_parse_junit_counts(tmp_path):
    _write_junit(tmp_path / "unit-results.xml", tests=79, failures=2, errors=1, skipped=1)
    stats = mod.parse_junit(tmp_path / "unit-results.xml")
    assert stats.executed == 79
    assert stats.failed == 3  # failures + errors
    assert stats.skipped == 1
    assert stats.passed == 75  # 79 - 3 - 1
    assert stats.status == mod.FAIL


def test_parse_junit_missing_file(tmp_path):
    assert mod.parse_junit(tmp_path / "nope.xml") is None


def test_level_skipped_when_all_skipped(tmp_path):
    _write_junit(tmp_path / "system-results.xml", tests=7, failures=0, errors=0, skipped=7)
    stats = mod.parse_junit(tmp_path / "system-results.xml")
    assert stats.status == mod.SKIP


def test_read_coverage(tmp_path):
    _write_coverage(tmp_path / "coverage.json", 91.5)
    assert mod.read_coverage(tmp_path) == 91.5
    assert mod.read_coverage(tmp_path / "empty") is None


def test_overall_pass(tmp_path):
    _all_green_reports(tmp_path)
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "success"}
    )
    assert data.overall_passed is True
    report = mod.render_markdown(data)
    assert mod.MARKER in report
    assert "Overall workflow result:** ✅ Passed" in report
    assert "| **Total** | 103 | 102 | 0 | 1 |" in report
    assert "99.1%" in report


def test_coverage_below_gate_fails_overall(tmp_path):
    _all_green_reports(tmp_path)
    _write_coverage(tmp_path / "coverage.json", 88.0)
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "success"}
    )
    assert data.coverage_gate_passed is False
    assert data.overall_passed is False
    assert mod.FAIL in mod.render_markdown(data)


def test_failed_lint_still_renders(tmp_path):
    # test job skipped -> no artifacts at all
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "failure", "TEST_RESULT": "skipped"}
    )
    report = mod.render_markdown(data)
    assert data.overall_passed is False
    assert "| Lint & Formatting | ❌ Failed |" in report
    # Every level degrades to skipped with placeholder statistics.
    assert "| Unit Tests | ⚠️ Skipped |" in report
    assert "| Unit Tests | - | - | - | - |" in report
    assert "did not produce results" in report


def test_failing_test_level_marks_failure(tmp_path):
    _all_green_reports(tmp_path)
    _write_junit(
        tmp_path / "integration-results.xml", tests=17, failures=1, errors=0, skipped=0
    )
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "failure"}
    )
    assert data.overall_passed is False
    report = mod.render_markdown(data)
    assert "| Integration Tests | ❌ Failed |" in report


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
