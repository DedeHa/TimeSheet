"""Generate the requirement-to-architecture-to-code traceability matrix (PRO-368).

This is a *production* CI support script (not a test). It scans
``doc/REQUIREMENTS.md``, ``doc/ARCHITECTURE.md`` and
``src_timesheetalgo/TimeSheetAlgo.py`` for requirement identifiers (FR-XX /
QR-XX) and renders a Markdown + HTML matrix under ``tests/reports/``. The CI
``test`` job runs this to produce the artifact that the "Comment traceability
report" step publishes on the pull request; completeness of the matrix is
asserted separately by
``.github/tests/ci-pipeline/test_generate_traceability_matrix.py``.

Standard library only, mirroring the lightweight, dependency-free approach of
``generate_pr_summary.py``.

Run with::

    python .github/scripts/generate_traceability_matrix.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "doc" / "REQUIREMENTS.md"
ARCHITECTURE = ROOT / "doc" / "ARCHITECTURE.md"
SOURCE = ROOT / "src_timesheetalgo" / "TimeSheetAlgo.py"
CI_SCRIPTS = ROOT / ".github" / "scripts"
REPORT_PATH = ROOT / "tests" / "reports" / "traceability-matrix.md"


@dataclass
class TraceabilityData:
    """Requirement identifiers discovered in each traceability source."""

    requirement_ids: list[str]
    architecture_ids: set[str]
    code_ids: set[str]

    @property
    def missing_in_architecture(self) -> list[str]:
        """Requirements absent from the architecture document."""
        return [r for r in self.requirement_ids if r not in self.architecture_ids]

    @property
    def missing_in_code(self) -> list[str]:
        """Requirements absent from the implementation references."""
        return [r for r in self.requirement_ids if r not in self.code_ids]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_requirement_ids(text: str) -> list[str]:
    """Return every FR-XX / QR-XX identifier found in ``text`` (in order)."""
    return re.findall(r"\b(FR-\d{2}|QR-\d{2})\b", text)


def collect_ids() -> TraceabilityData:
    """Read the sources and collect their requirement identifiers."""
    code_text = _read_text(SOURCE)
    for script in CI_SCRIPTS.iterdir():
        if script.suffix in (".py",):
            code_text += "\n" + _read_text(script)
    return TraceabilityData(
        requirement_ids=extract_requirement_ids(_read_text(REQUIREMENTS)),
        architecture_ids=set(extract_requirement_ids(_read_text(ARCHITECTURE))),
        code_ids=set(extract_requirement_ids(code_text)),
    )


def _coverage_percent(requirement_ids: list[str], present_ids: set[str]) -> float:
    total = len(requirement_ids)
    return round(
        100 * sum(1 for r in requirement_ids if r in present_ids) / max(1, total), 1
    )


def _group_by_type(requirement_ids: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"FR": [], "QR": []}
    for req in requirement_ids:
        groups["FR" if req.startswith("FR-") else "QR"].append(req)
    return groups


def build_markdown(data: TraceabilityData) -> str:
    """Render the compact Markdown traceability matrix."""

    def indicator(present: bool) -> str:
        return "🟢" if present else "◯"

    lines: list[str] = ["# Traceability Matrix", ""]

    groups = _group_by_type(data.requirement_ids)
    for label, reqs in (
        ("Functional Requirements", groups["FR"]),
        ("Quality Requirements", groups["QR"]),
    ):
        if not reqs:
            continue
        lines.append(f"## {label}")
        header_cols = ["Requirement", "Type", "In Architecture", "In Code"]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

        for req in reqs:
            row = [
                req,
                "Functional" if req.startswith("FR-") else "Quality",
                indicator(req in data.architecture_ids),
                indicator(req in data.code_ids),
            ]
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    lines.append(
        f"- Architecture coverage: "
        f"{_coverage_percent(data.requirement_ids, data.architecture_ids)}%"
    )
    lines.append(
        f"- Code coverage: {_coverage_percent(data.requirement_ids, data.code_ids)}%"
    )

    return "\n".join(lines)


def build_html(data: TraceabilityData) -> str:
    """Render the compact HTML traceability matrix for richer PR artifacts."""

    def cell(val: str) -> str:
        return f"<td>{val}</td>"

    html_lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Traceability Matrix</title>",
        "<style>",
        "body{font-family:Arial,Helvetica,sans-serif;margin:16px;"
        "background:#0f1724;color:#e6eef8}",
        "table{border-collapse:collapse;width:100%;overflow:auto}",
        "th,td{border:1px solid #2b3350;padding:8px;text-align:left}",
        "th{background:#111827;color:#9fb4ff}",
        "tr:nth-child(even){background:#071026}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Traceability Matrix</h1>",
    ]

    groups = _group_by_type(data.requirement_ids)
    for title, reqs in (
        ("Functional Requirements", groups["FR"]),
        ("Quality Requirements", groups["QR"]),
    ):
        if not reqs:
            continue
        html_lines.append(f"<h2>{title}</h2>")
        html_lines.append("<table>")
        header_cols = ["Requirement", "Type", "In Architecture", "In Code"]
        html_lines.append(
            "<thead><tr>"
            + "".join(f"<th>{c}</th>" for c in header_cols)
            + "</tr></thead>"
        )
        html_lines.append("<tbody>")

        for req in reqs:
            row_cells = [
                req,
                ("Functional" if req.startswith("FR-") else "Quality"),
                ("✅" if req in data.architecture_ids else "◯"),
                ("✅" if req in data.code_ids else "◯"),
            ]
            html_lines.append("<tr>" + "".join(cell(c) for c in row_cells) + "</tr>")

        html_lines.append("</tbody></table>")

    arch_cov = _coverage_percent(data.requirement_ids, data.architecture_ids)
    code_cov = _coverage_percent(data.requirement_ids, data.code_ids)
    html_lines.append(
        f"<p>Architecture coverage: {arch_cov}%<br/>Code coverage: {code_cov}%</p>"
    )
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def write_reports(data: TraceabilityData) -> Path:
    """Write the Markdown + HTML matrices and return the Markdown path.

    Only files are written here. The GitHub Actions job summary ("PR Run") is
    rendered by generate_pr_summary.py, which reads this Markdown and embeds the
    matrix under its Traceability section - so the matrix is not appended to
    ``$GITHUB_STEP_SUMMARY`` here (that would duplicate it).
    """
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_markdown(data), encoding="utf-8")
    html_path = REPORT_PATH.with_suffix(".html")
    html_path.write_text(build_html(data), encoding="utf-8")
    return REPORT_PATH


def main() -> None:
    """Generate the traceability matrix artifacts and enforce completeness.

    Writes the Markdown + HTML matrices (so the artifact is available even on
    failure), then exits with a non-zero status when any requirement is missing
    from the architecture document or the implementation references. This makes
    the script the CI quality gate - the workflow invokes it directly and needs
    no separate pytest step.
    """
    data = collect_ids()
    write_reports(data)

    problems: list[str] = []
    if not data.requirement_ids:
        problems.append("No requirement identifiers were discovered")
    if data.missing_in_architecture:
        problems.append(f"Missing from architecture: {data.missing_in_architecture}")
    if data.missing_in_code:
        problems.append(
            f"Missing from implementation references: {data.missing_in_code}"
        )

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        sys.exit(1)

    print(build_markdown(data))


if __name__ == "__main__":
    main()
