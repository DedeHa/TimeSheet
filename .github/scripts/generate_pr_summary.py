"""Render a CI/CD quality-gate summary for a GitHub Pull Request (PRO-337).

The CI ``test`` job produces one JUnit XML per test level
(``unit-results.xml``, ``integration-results.xml``, ``system-results.xml``) and
a machine-readable coverage file (``coverage.json``). This script parses those
artifacts, combines them with the ``lint`` / ``test`` job outcomes passed in via
the environment, and renders a single Markdown report that a downstream
``github-script`` step publishes as a *sticky* Pull Request comment.

Design notes
------------
* Standard library only - this mirrors the lightweight, tooling-free approach of
  ``generate_traceability_matrix.py`` so it stays local-runnable and dependency-free.
* Every input is optional. When the ``test`` job is skipped (e.g. because
  ``lint`` failed) the artifacts are absent; the report degrades gracefully and
  still reports the gates it knows about, satisfying the "failed workflows still
  publish available results" acceptance criterion.

The rendered report always begins with :data:`MARKER` so the publishing step can
find and update the previous comment instead of creating a duplicate.
"""

from __future__ import annotations

import datetime
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "tests" / "reports"
SUMMARY_PATH = REPORTS_DIR / "test-summary.md"
COVERAGE_JSON = "coverage.json"
#: Traceability matrix produced by generate_traceability_matrix.py; its
#: requirement->code coverage line is folded into the combined summary.
TRACEABILITY_MD = "traceability-matrix.md"

#: Combined-coverage quality gate, kept in sync with ``fail_under`` in pyproject.
COVERAGE_GATE = 90.0

#: Hidden HTML marker used to locate and update the sticky PR comment on re-runs.
MARKER = "<!-- pro-337-ci-quality-gate-summary -->"

#: Marker for the compact, one-per-run status-line comment (Option C). Distinct
#: from MARKER so the two comment kinds are individually identifiable.
LINE_MARKER = "<!-- pro-337-ci-run-line -->"

#: Compact status line written for the per-run comment.
LINE_PATH = REPORTS_DIR / "test-summary-line.md"

#: Application test levels (the TimeSheet script) and the JUnit file each writes.
APP_TEST_LEVELS: list[tuple[str, str]] = [
    ("Unit Tests", "unit-results.xml"),
    ("Integration Tests", "integration-results.xml"),
    ("System Tests", "system-results.xml"),
]

#: CI-pipeline test levels: the tests/ci-pipeline suite (CI support scripts).
#: Reported separately from the application tests.
CI_TEST_LEVELS: list[tuple[str, str]] = [
    ("CI Self-Tests", "ci-results.xml"),
]

#: All levels, in display order (application first, then CI pipeline).
TEST_LEVELS: list[tuple[str, str]] = APP_TEST_LEVELS + CI_TEST_LEVELS

#: Names that belong to the CI-pipeline group (used to split the levels list).
CI_LEVEL_NAMES = {name for name, _ in CI_TEST_LEVELS}

PASS = "✅ Passed"
FAIL = "❌ Failed"
SKIP = "⚠️ Skipped"


@dataclass
class LevelStats:
    """Aggregated JUnit statistics for a single test level."""

    name: str
    file_name: str
    executed: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    found: bool = False

    @property
    def status(self) -> str:
        """Return the success/failure/skip indicator for this level."""
        if not self.found:
            return SKIP
        if self.failed:
            return FAIL
        if self.executed == 0 or self.executed == self.skipped:
            return SKIP
        return PASS


@dataclass
class SummaryData:
    """Everything needed to render the report."""

    lint_result: str
    test_result: str
    levels: list[LevelStats]
    coverage_percent: Optional[float]
    ci_coverage_percent: Optional[float]
    run_url: Optional[str] = None
    traceability_coverage: Optional[float] = None
    generated_at: Optional[str] = None
    run_number: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    @property
    def coverage_gate_passed(self) -> Optional[bool]:
        """Return whether coverage met the gate, or ``None`` when unknown."""
        if self.coverage_percent is None:
            return None
        return self.coverage_percent >= COVERAGE_GATE

    @property
    def overall_passed(self) -> bool:
        """Compute the overall gate: lint + tests + no failures + coverage gate."""
        if _result_indicator(self.lint_result) != PASS:
            return False
        if _result_indicator(self.test_result) != PASS:
            return False
        if any(level.status == FAIL for level in self.levels):
            return False
        return self.coverage_gate_passed is True


def _result_indicator(result: str) -> str:
    """Map a GitHub job ``result`` string to a display indicator."""
    normalized = (result or "").strip().lower()
    if normalized == "success":
        return PASS
    if normalized == "failure":
        return FAIL
    return SKIP


def parse_junit(path: Path) -> Optional[LevelStats]:
    """Parse a single JUnit XML file into :class:`LevelStats`.

    Handles both a ``<testsuites>`` root and a bare ``<testsuite>`` root and
    sums the ``tests``/``failures``/``errors``/``skipped`` attributes across
    every suite. Returns ``None`` when the file is missing or unparseable.
    """
    if not path.exists():
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None

    total = failed = skipped = 0
    for suite in root.iter("testsuite"):
        total += _int_attr(suite, "tests")
        failed += _int_attr(suite, "failures") + _int_attr(suite, "errors")
        skipped += _int_attr(suite, "skipped")

    return LevelStats(
        name="",
        file_name=path.name,
        executed=total,
        passed=max(total - failed - skipped, 0),
        failed=failed,
        skipped=skipped,
        found=True,
    )


def _int_attr(element: ET.Element, name: str) -> int:
    """Read an integer attribute, defaulting to 0 when missing/blank."""
    try:
        return int(element.get(name, "0") or "0")
    except ValueError:
        return 0


def collect_levels(reports_dir: Path) -> list[LevelStats]:
    """Build the ordered list of level statistics from the reports directory."""
    levels: list[LevelStats] = []
    for display_name, file_name in TEST_LEVELS:
        stats = parse_junit(reports_dir / file_name)
        if stats is None:
            stats = LevelStats(name=display_name, file_name=file_name, found=False)
        else:
            stats.name = display_name
        levels.append(stats)
    return levels


def read_coverage(reports_dir: Path) -> Optional[float]:
    """Return the combined ``percent_covered`` from ``coverage.json``, or ``None``."""
    path = reports_dir / COVERAGE_JSON
    if not path.exists():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return float(data["totals"]["percent_covered"])
    except (ValueError, KeyError, OSError):
        return None


def read_traceability_coverage(reports_dir: Path) -> Optional[float]:
    """Return the requirement->code coverage % from the traceability matrix.

    Parses the ``- Code coverage: N%`` line written by
    ``generate_traceability_matrix.py``. Returns ``None`` when the matrix is
    missing or the line cannot be found.
    """
    path = reports_dir / TRACEABILITY_MD
    if not path.exists():
        return None
    match = re.search(
        r"Code coverage:\s*([0-9.]+)%", path.read_text(encoding="utf-8"), re.IGNORECASE
    )
    return float(match.group(1)) if match else None


def read_ci_coverage(reports_dir: Path) -> Optional[float]:
    """Return the CI pipeline code coverage % from ``ci-coverage.json``.

    The ``test`` job runs ``coverage json -o tests/reports/ci-coverage.json``
    on the ``tests/ci-pipeline`` suite. This reads the combined
    ``percent_covered`` from that file, or ``None`` when it is missing or
    unparseable.
    """
    path = reports_dir / "ci-coverage.json"
    if not path.exists():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return float(data["totals"]["percent_covered"])
    except (ValueError, KeyError, OSError):
        return None


def read_traceability_matrix_md(reports_dir: Path) -> Optional[str]:
    """Return the full traceability matrix Markdown, or ``None`` when missing."""
    path = reports_dir / TRACEABILITY_MD
    return path.read_text(encoding="utf-8") if path.exists() else None


def _fmt_percent(value: Optional[float]) -> str:
    """Format a percentage to one decimal place, or ``n/a`` when unknown."""
    return "n/a" if value is None else f"{value:.1f}%"


def _tests_status(levels: list[LevelStats]) -> str:
    """Derive an overall test status indicator from the per-level results."""
    if any(level.status == FAIL for level in levels):
        return FAIL
    if any(level.found and level.status == PASS for level in levels):
        return PASS
    return SKIP


def _traceability_status(coverage: Optional[float]) -> str:
    """Derive a traceability status from the requirement->code coverage.

    Fully traced (100%) passes; a known lower value fails (the generator gate
    would also have failed the run); an unknown value is reported as skipped.
    """
    if coverage is None:
        return SKIP
    return PASS if coverage >= 100.0 else FAIL


def _app_levels(levels: list[LevelStats]) -> list[LevelStats]:
    """Application (script) test levels: unit / integration / system."""
    return [level for level in levels if level.name not in CI_LEVEL_NAMES]


def _ci_levels(levels: list[LevelStats]) -> list[LevelStats]:
    """CI-pipeline test levels: the tests/ci-pipeline suite."""
    return [level for level in levels if level.name in CI_LEVEL_NAMES]


def _group_summary(levels: list[LevelStats]) -> tuple[str, str]:
    """Return (status, "N% (passed/executed passed)") for a group of levels."""
    totals = _totals(levels)
    executed = totals["executed"]
    rate = (100.0 * totals["passed"] / executed) if executed else None
    cell = f"{_fmt_percent(rate)} ({totals['passed']}/{executed} passed)"
    return _tests_status(levels), cell


def _coverage_status(data: SummaryData) -> str:
    """Map the coverage-gate result to a status indicator."""
    if data.coverage_gate_passed is None:
        return SKIP
    return PASS if data.coverage_gate_passed else FAIL


def _status_overview(data: SummaryData) -> list[str]:
    """Return the Step / Status / Summary overview table (no numbering).

    Testing is split into two rows: the application (script) tests and the
    CI-pipeline tests (`tests/ci-pipeline`).
    """
    lint_status = _result_indicator(data.lint_result)
    trace_status = _traceability_status(data.traceability_coverage)
    trace_cell = _fmt_percent(data.traceability_coverage)
    app_status, app_cell = _group_summary(_app_levels(data.levels))
    ci_status, ci_cell = _group_summary(_ci_levels(data.levels))
    app_coverage_cell = (
        f"{_fmt_percent(data.coverage_percent)} " f"(gate {COVERAGE_GATE:.0f}%)"
    )
    traceability_coverage_cell = trace_cell

    return [
        "| Step | Status | Summary |",
        "| --- | --- | --- |",
        f"| Lint & Formatting | {lint_status} | — |",
        f"| Traceability | {trace_status} | {traceability_coverage_cell} |",
        f"| Application Tests | {app_status} | {app_cell} |",
        f"| CI-Pipeline Tests | {ci_status} | {ci_cell} |",
        f"| Application Code Coverage | {_coverage_status(data)} "
        f"| {app_coverage_cell} |",
        "| Artifacts | — | see Artifacts section |",
    ]


def _level_table(levels: list[LevelStats]) -> list[str]:
    """Render a per-level table (with a Total row) for a group of levels."""
    lines = [
        "| Level | Executed | Passed | Failed | Skipped |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for level in levels:
        if level.found:
            lines.append(
                f"| {level.name} | {level.executed} | {level.passed} "
                f"| {level.failed} | {level.skipped} |"
            )
        else:
            lines.append(f"| {level.name} | - | - | - | - |")
    t = _totals(levels)
    lines.append(
        f"| **Total** | {t['executed']} | {t['passed']} "
        f"| {t['failed']} | {t['skipped']} |"
    )
    return lines


def _footer(data: SummaryData) -> list[str]:
    """Return the update-timestamp / run-reference footer (empty if no time)."""
    if not data.generated_at:
        return []
    ref = f"run #{data.run_number}" if data.run_number else "run"
    if data.run_url:
        ref = f"[{ref}]({data.run_url})"
    return ["", f"_Updated: {data.generated_at} · {ref}_"]


def render_short_comment(data: SummaryData) -> str:
    """Render the compact per-run comment: overall result + overview table.

    Posted fresh on every run (Option C) as a lightweight per-run trail that
    complements the detailed sticky comment, and carries the update timestamp.
    """
    overall = PASS if data.overall_passed else FAIL
    lines = [
        LINE_MARKER,
        f"**Overall workflow result:** {overall}",
        "",
        *_status_overview(data),
        *_footer(data),
    ]
    return "\n".join(lines) + "\n"


def render_markdown(data: SummaryData, matrix_md: Optional[str] = None) -> str:
    """Render the combined CI/CD quality-gate report.

    Sections are emitted in a fixed order: 1 Traceability, 2 Testing,
    3 Code Coverage, 4 Artifacts. When ``matrix_md`` is provided (the job-summary
    variant for the "PR Run"), the full traceability matrix table is embedded
    under section 1; the PR-comment variant omits it and links to the artifact
    instead. The leading :data:`MARKER` lets the publishing step update the
    sticky comment in place.
    """
    overall = PASS if data.overall_passed else FAIL
    coverage_status = _coverage_status(data)
    trace_status = _traceability_status(data.traceability_coverage)
    trace_pct = _fmt_percent(data.traceability_coverage)
    app_status, app_cell = _group_summary(_app_levels(data.levels))
    ci_status, ci_cell = _group_summary(_ci_levels(data.levels))

    # Header + status overview: the overall result plus a one-line-per-aspect
    # table covering linting and all steps, so the whole gate is readable at a
    # glance before the detailed sections below.
    lines: list[str] = [
        MARKER,
        "## CI/CD Quality Gate Summary",
        "",
        f"**Overall workflow result:** {overall}",
        "",
        *_status_overview(data),
    ]

    # Traceability
    lines += [
        "",
        "### Traceability",
        "",
        f"- Traceability summary: **{trace_pct}**",
        f"- Status: {trace_status}",
    ]
    if matrix_md:
        body = re.sub(r"^\s*#\s+Traceability Matrix\s*", "", matrix_md.strip()).strip()
        lines += ["", body]
    elif data.run_url:
        lines.append(f"- [Traceability matrix →]({data.run_url})")

    # Testing - split into application (script) tests and CI-pipeline tests.
    lines += [
        "",
        "### Testing",
        "",
        "#### Application (unit + integration + system)",
        "",
        f"- Summary: **{app_cell}** · Status: {app_status}",
        "",
        *_level_table(_app_levels(data.levels)),
        "",
        "#### CI Pipeline (`tests/ci-pipeline`)",
        "",
        f"- Summary: **{ci_cell}** · Status: {ci_status}",
        "",
        *_level_table(_ci_levels(data.levels)),
    ]

    # Code Coverage
    lines += [
        "",
        "### Code Coverage",
        "",
        f"- Combined line + branch coverage: **{_fmt_percent(data.coverage_percent)}**",
        f"- Quality gate (>= {COVERAGE_GATE:.0f}%): {coverage_status}",
    ]

    # CI Pipeline Coverage
    lines += [
        "",
        "### CI Pipeline Coverage",
        "",
        f"- CI pipeline code coverage: **{_fmt_percent(data.ci_coverage_percent)}**",
    ]

    # Artifacts (for all aspects)
    lines += ["", "### Artifacts"]
    if data.run_url:
        lines.append(f"- [Workflow run & downloadable artifacts]({data.run_url})")
    lines.append(
        "- Traceability matrix: `traceability-matrix.md` / "
        "`traceability-matrix.html` (in `test-results`)"
    )
    lines.append(
        "- Test results (JUnit): `*-results.xml` and `coverage.json` "
        "(in `test-results`)"
    )
    lines.append("- HTML coverage report: `htmlcov/index.html` (in `test-results`)")

    if data.notes:
        lines += ["", "### Notes"]
        lines += [f"- {note}" for note in data.notes]

    lines += _footer(data)

    return "\n".join(lines) + "\n"


def _totals(levels: list[LevelStats]) -> dict[str, int]:
    """Sum executed/passed/failed/skipped across the levels that produced data."""
    return {
        "executed": sum(level.executed for level in levels),
        "passed": sum(level.passed for level in levels),
        "failed": sum(level.failed for level in levels),
        "skipped": sum(level.skipped for level in levels),
    }


def build_summary(reports_dir: Path, env: dict[str, str]) -> SummaryData:
    """Assemble :class:`SummaryData` from the reports directory and environment."""
    levels = collect_levels(reports_dir)
    coverage = read_coverage(reports_dir)
    traceability_coverage = read_traceability_coverage(reports_dir)
    ci_coverage = read_ci_coverage(reports_dir)

    run_url = None
    server = env.get("GITHUB_SERVER_URL")
    repo = env.get("GITHUB_REPOSITORY")
    run_id = env.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        run_url = f"{server}/{repo}/actions/runs/{run_id}"

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    notes: list[str] = []
    if _result_indicator(env.get("TEST_RESULT", "")) != PASS and not any(
        level.found for level in levels
    ):
        notes.append(
            "The test job did not produce results (it was skipped or failed "
            "before running). Only the gates above with available data are shown."
        )
    if coverage is None:
        notes.append("Coverage data was not available for this run.")
    if ci_coverage is None:
        notes.append("CI pipeline coverage data was not available for this run.")

    return SummaryData(
        lint_result=env.get("LINT_RESULT", ""),
        test_result=env.get("TEST_RESULT", ""),
        levels=levels,
        coverage_percent=coverage,
        ci_coverage_percent=ci_coverage,
        run_url=run_url,
        traceability_coverage=traceability_coverage,
        generated_at=generated_at,
        run_number=env.get("GITHUB_RUN_NUMBER"),
        notes=notes,
    )


def main() -> None:
    """Render the report for the PR comment and the job step summary.

    Three artifacts are produced: the sticky full report (``test-summary.md``,
    traceability as a percentage + link); the compact per-run short comment
    (``test-summary-line.md``, overall result + overview table); and the
    job-summary variant (appended to ``$GITHUB_STEP_SUMMARY``, i.e. the "PR Run")
    which embeds the full traceability matrix.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = build_summary(REPORTS_DIR, dict(os.environ))

    comment_report = render_markdown(data)
    SUMMARY_PATH.write_text(comment_report, encoding="utf-8")
    LINE_PATH.write_text(render_short_comment(data), encoding="utf-8")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        matrix_md = read_traceability_matrix_md(REPORTS_DIR)
        job_report = render_markdown(data, matrix_md=matrix_md)
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(job_report)
            handle.write("\n")

    print(comment_report)


if __name__ == "__main__":
    main()
