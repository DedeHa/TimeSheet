"""Unit tests for the PR quality-gate summary generator (PRO-337).

These validate the parsing and rendering logic of ``generate_pr_summary.py`` in
isolation. Like ``test_generate_traceability_matrix.py`` this file lives under
``.github/tests/ci-pipeline/`` (not in ``tests/``), so it does not change the
103-test application suite or the coverage gate. This is a developer unit test
- the CI pipeline runs the generator script itself, not this test - and can
be run with::

    pytest -q .github/tests/ci-pipeline/test_generate_pr_summary.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "generate_pr_summary.py"
)
_spec = importlib.util.spec_from_file_location("generate_pr_summary", _MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
# Register before executing so dataclass type resolution can find the module.
sys.modules["generate_pr_summary"] = mod
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


def _write_traceability(path: Path, code_coverage: float):
    path.write_text(
        "# Traceability Matrix\n"
        "- Architecture coverage: 100.0%\n"
        f"- Code coverage: {code_coverage}%\n",
        encoding="utf-8",
    )


def _all_green_reports(tmp_path: Path):
    _write_junit(
        tmp_path / "unit-results.xml", tests=79, failures=0, errors=0, skipped=1
    )
    _write_junit(
        tmp_path / "integration-results.xml", tests=17, failures=0, errors=0, skipped=0
    )
    _write_junit(
        tmp_path / "system-results.xml", tests=7, failures=0, errors=0, skipped=0
    )
    _write_coverage(tmp_path / "coverage.json", 99.1)
    _write_traceability(tmp_path / "traceability-matrix.md", 100.0)


def _write_ci_coverage(path: Path, percent: float):
    path.write_text(
        json.dumps({"totals": {"percent_covered": percent}}), encoding="utf-8"
    )


def _all_green_reports_with_ci(tmp_path: Path):
    _all_green_reports(tmp_path)
    _write_junit(tmp_path / "ci-results.xml", tests=44, failures=0, errors=0, skipped=0)
    _write_ci_coverage(tmp_path / "ci-coverage.json", 98.5)


def test_parse_junit_counts(tmp_path):
    """Verify JUnit XML parsing sums tests, failures, errors and skipped."""
    _write_junit(
        tmp_path / "unit-results.xml", tests=79, failures=2, errors=1, skipped=1
    )
    stats = mod.parse_junit(tmp_path / "unit-results.xml")
    assert stats.executed == 79
    assert stats.failed == 3  # failures + errors
    assert stats.skipped == 1
    assert stats.passed == 75  # 79 - 3 - 1
    assert stats.status == mod.FAIL


def test_parse_junit_missing_file(tmp_path):
    """A missing JUnit file yields ``None`` instead of raising."""
    assert mod.parse_junit(tmp_path / "nope.xml") is None


def test_level_skipped_when_all_skipped(tmp_path):
    """A level where every test is skipped reports the skip status."""
    _write_junit(
        tmp_path / "system-results.xml", tests=7, failures=0, errors=0, skipped=7
    )
    stats = mod.parse_junit(tmp_path / "system-results.xml")
    assert stats.status == mod.SKIP


def test_read_coverage(tmp_path):
    """Coverage is read from coverage.json and missing files return ``None``."""
    _write_coverage(tmp_path / "coverage.json", 91.5)
    assert mod.read_coverage(tmp_path) == 91.5
    assert mod.read_coverage(tmp_path / "empty") is None


def test_read_traceability_coverage(tmp_path):
    """Traceability code coverage is parsed from the matrix, or ``None``."""
    _write_traceability(tmp_path / "traceability-matrix.md", 100.0)
    assert mod.read_traceability_coverage(tmp_path) == 100.0
    assert mod.read_traceability_coverage(tmp_path / "empty") is None


def test_read_ci_coverage(tmp_path):
    """CI pipeline coverage is read from ci-coverage.json or ``None``."""
    _write_ci_coverage(tmp_path / "ci-coverage.json", 97.5)
    assert mod.read_ci_coverage(tmp_path) == 97.5
    assert mod.read_ci_coverage(tmp_path / "empty") is None


def test_ci_pipeline_tests_reported_separately(tmp_path):
    """CI self-tests are a separate group from the application tests."""
    _all_green_reports_with_ci(tmp_path)
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "success"}
    )
    report = mod.render_markdown(data)
    # Two overview rows, application and CI pipeline, reported independently.
    assert "| Application Tests | ✅ Passed | 99.0% (102/103 passed) |" in report
    assert "| CI-Pipeline Tests | ✅ Passed | 100.0% (44/44 passed) |" in report
    # Separate subsections, each with its own Total (not a single blended total).
    assert "#### Application (unit + integration + system)" in report
    assert "#### CI Pipeline (`.github/tests`)" in report
    assert "| CI Self-Tests | 44 | 44 | 0 | 0 |" in report
    assert "| **Total** | 103 | 102 | 0 | 1 |" in report  # application total
    assert "| **Total** | 44 | 44 | 0 | 0 |" in report  # CI total
    # Coverage is split between application and CI pipeline sections.
    assert "| Application Code Coverage | ✅ Passed | 99.1% (gate 90%) |" in report
    assert "### CI Pipeline Coverage" in report
    assert "CI pipeline code coverage: **98.5%**" in report


def test_short_comment_has_overview_table_and_timestamp():
    """The per-run short comment is the overall result + overview table."""
    data = mod.SummaryData(
        lint_result="success",
        test_result="success",
        levels=[
            mod.LevelStats("Unit Tests", "u.xml", 79, 78, 0, 1, True),
        ],
        coverage_percent=99.6,
        ci_coverage_percent=98.5,
        run_url="https://example/run/9",
        traceability_coverage=100.0,
        generated_at="2026-08-19 20:14 UTC",
        run_number="42",
    )
    short = mod.render_short_comment(data)
    assert mod.LINE_MARKER in short
    assert "**Overall workflow result:** ✅ Passed" in short
    assert "| Step | Status | Summary |" in short
    assert "| Traceability | ✅ Passed | 100.0% |" in short
    # No numbering on the step rows.
    assert "1. Traceability" not in short
    # Update timestamp + run reference are present.
    assert "_Updated: 2026-08-19 20:14 UTC · [run #42](https://example/run/9)_" in short


def test_comment_and_job_summary_variants():
    """The comment links to the matrix; the job summary embeds the full table."""
    data = mod.SummaryData(
        lint_result="success",
        test_result="success",
        levels=[],
        coverage_percent=99.1,
        ci_coverage_percent=98.5,
        run_url="https://example/run/1",
        traceability_coverage=100.0,
    )
    matrix = (
        "# Traceability Matrix\n\n## Functional Requirements\n"
        "| Requirement | Type |\n| --- | --- |\n| FR-01 | Functional |\n"
        "- Code coverage: 100.0%\n"
    )

    comment = mod.render_markdown(data)
    assert "[Traceability matrix →](https://example/run/1)" in comment
    assert "## Functional Requirements" not in comment  # not embedded in comment

    job = mod.render_markdown(data, matrix_md=matrix)
    assert "## Functional Requirements" in job  # full matrix embedded
    assert "| FR-01 | Functional |" in job
    assert "# Traceability Matrix" not in job  # duplicate H1 stripped


def test_overall_pass(tmp_path):
    """All-green inputs produce an overall pass with correct totals."""
    _all_green_reports_with_ci(tmp_path)
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "success"}
    )
    assert data.overall_passed is True
    report = mod.render_markdown(data)
    assert mod.MARKER in report
    assert "Overall workflow result:** ✅ Passed" in report
    # Status overview at the top covers linting and all steps, without numbering.
    assert "| Lint & Formatting | ✅ Passed | — |" in report
    assert "| Traceability | ✅ Passed | 100.0% |" in report
    # Testing is split into application and CI-pipeline rows.
    assert "| Application Tests | ✅ Passed | 99.0% (102/103 passed) |" in report
    assert "| CI-Pipeline Tests |" in report
    # Coverage is split between application and CI pipeline sections.
    assert "| Application Code Coverage | ✅ Passed | 99.1% (gate 90%) |" in report
    assert "1. Traceability" not in report  # numbering removed everywhere
    # Sections appear in the required order, un-numbered.
    order = [
        "### Traceability",
        "### Testing",
        "### Code Coverage",
        "### CI Pipeline Coverage",
        "### Artifacts",
    ]
    positions = [report.index(section) for section in order]
    assert positions == sorted(positions), "sections out of order"
    # Traceability - summary percentage + matrix link (comment variant).
    assert "Traceability summary: **100.0%**" in report
    # Testing - separate application / CI subsections; application total row.
    assert "#### Application (unit + integration + system)" in report
    assert "#### CI Pipeline (`.github/tests`)" in report
    assert "| **Total** | 103 | 102 | 0 | 1 |" in report
    # Code Coverage - percentage + gate status.
    assert "Combined line + branch coverage: **99.1%**" in report
    # CI Pipeline Coverage - separate section.
    assert "### CI Pipeline Coverage" in report
    assert "CI pipeline code coverage: **98.5%**" in report
    # The obsolete PRO-337 footer is no longer emitted.
    assert "PRO-337" not in report


def test_coverage_below_gate_fails_overall(tmp_path):
    """Coverage below the 90% gate fails the overall result."""
    _all_green_reports(tmp_path)
    _write_coverage(tmp_path / "coverage.json", 88.0)
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "success"}
    )
    assert data.coverage_gate_passed is False
    assert data.overall_passed is False
    assert mod.FAIL in mod.render_markdown(data)


def test_failed_lint_still_renders(tmp_path):
    """A failed lint job still renders a degraded report with notes."""
    # test job skipped -> no artifacts at all
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "failure", "TEST_RESULT": "skipped"}
    )
    report = mod.render_markdown(data)
    assert data.overall_passed is False
    # Lint failure shows in the status overview.
    assert "| Lint & Formatting | ❌ Failed | — |" in report
    # With no reports, the testing status degrades to skipped and each level
    # shows placeholder statistics.
    assert "· Status: ⚠️ Skipped" in report
    assert "| Unit Tests | - | - | - | - |" in report
    assert "did not produce results" in report


def test_failing_test_level_marks_failure(tmp_path):
    """A failing test level marks the overall result as failed."""
    _all_green_reports(tmp_path)
    _write_junit(
        tmp_path / "integration-results.xml", tests=17, failures=1, errors=0, skipped=0
    )
    data = mod.build_summary(
        tmp_path, {"LINT_RESULT": "success", "TEST_RESULT": "failure"}
    )
    assert data.overall_passed is False
    report = mod.render_markdown(data)
    # Application testing status reflects the failure; the per-level row shows it.
    assert "· Status: ❌ Failed" in report
    assert "| Integration Tests | 17 | 16 | 1 | 0 |" in report


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
