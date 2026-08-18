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

#: Ordered test levels and the JUnit file each level writes.
TEST_LEVELS: list[tuple[str, str]] = [
    ("Unit Tests", "unit-results.xml"),
    ("Integration Tests", "integration-results.xml"),
    ("System Tests", "system-results.xml"),
]

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
    run_url: Optional[str] = None
    traceability_coverage: Optional[float] = None
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


def _fmt_percent(value: Optional[float]) -> str:
    """Format a percentage to one decimal place, or ``n/a`` when unknown."""
    return "n/a" if value is None else f"{value:.1f}%"


def render_markdown(data: SummaryData) -> str:
    """Render the full Markdown report (including the sticky-comment marker)."""
    overall = PASS if data.overall_passed else FAIL
    totals = _totals(data.levels)

    if data.coverage_gate_passed is None:
        coverage_status = SKIP
    elif data.coverage_gate_passed:
        coverage_status = PASS
    else:
        coverage_status = FAIL

    lines: list[str] = [
        MARKER,
        "## CI/CD Quality Gate Summary",
        "",
        f"**Overall workflow result:** {overall}",
        "",
        "| Quality Gate | Status |",
        "| --- | --- |",
        f"| Lint & Formatting | {_result_indicator(data.lint_result)} |",
    ]
    for level in data.levels:
        lines.append(f"| {level.name} | {level.status} |")
    lines.append(
        f"| Code Coverage (>= {COVERAGE_GATE:.0f}%) | "
        f"{coverage_status} ({_fmt_percent(data.coverage_percent)}) |"
    )

    lines += [
        "",
        "### Test statistics",
        "",
        "| Level | Executed | Passed | Failed | Skipped |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for level in data.levels:
        if level.found:
            lines.append(
                f"| {level.name} | {level.executed} | {level.passed} "
                f"| {level.failed} | {level.skipped} |"
            )
        else:
            lines.append(f"| {level.name} | - | - | - | - |")
    lines.append(
        f"| **Total** | {totals['executed']} | {totals['passed']} "
        f"| {totals['failed']} | {totals['skipped']} |"
    )

    lines += [
        "",
        "### Code coverage",
        "",
        f"Combined line + branch coverage: **{_fmt_percent(data.coverage_percent)}** "
        f"- quality gate (>= {COVERAGE_GATE:.0f}%): {coverage_status}",
    ]

    lines += ["", "### Artifacts"]
    if data.run_url:
        lines.append(f"- [Workflow run & downloadable artifacts]({data.run_url})")
    lines.append(
        "- HTML coverage report: `htmlcov/index.html` inside the "
        "`test-results` artifact"
    )
    lines.append(
        "- Traceability matrix: `traceability-matrix.md` / "
        "`traceability-matrix.html` inside the `test-results` artifact"
    )

    if data.notes:
        lines += ["", "### Notes"]
        lines += [f"- {note}" for note in data.notes]

    # Traceability summary, folded in from the traceability matrix so the PR
    # carries a single combined comment instead of two separate ones.
    lines += [
        "",
        "---",
        "",
        "## Traceability Summary",
        "",
        f"**Code Coverage:** {_fmt_percent(data.traceability_coverage)}",
    ]
    if data.run_url:
        lines += ["", f"[Complete traceability matrix →]({data.run_url})"]

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

    run_url = None
    server = env.get("GITHUB_SERVER_URL")
    repo = env.get("GITHUB_REPOSITORY")
    run_id = env.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        run_url = f"{server}/{repo}/actions/runs/{run_id}"

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

    return SummaryData(
        lint_result=env.get("LINT_RESULT", ""),
        test_result=env.get("TEST_RESULT", ""),
        levels=levels,
        coverage_percent=coverage,
        run_url=run_url,
        traceability_coverage=traceability_coverage,
        notes=notes,
    )


def main() -> None:
    """Generate the report and write it to disk and the job step summary."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = build_summary(REPORTS_DIR, dict(os.environ))
    report = render_markdown(data)

    SUMMARY_PATH.write_text(report, encoding="utf-8")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(report)
            handle.write("\n")

    print(report)


if __name__ == "__main__":
    main()
