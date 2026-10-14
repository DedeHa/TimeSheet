"""Generate the requirement-to-architecture-to-code traceability matrix (PRO-368).

This is a *production* CI support script (not a test). It scans
``doc/REQUIREMENTS.md`` (TimeSheetAlgo / SCRIPT requirements) and
``.opencode/docs/REQUIREMENTS.md`` (Agent Dev Team requirements),
``doc/ARCHITECTURE.md`` and ``src_timesheetalgo/TimeSheetAlgo.py`` for
requirement identifiers (FR-XX / QR-XX, and FR-INTEGRITY-XXX /
QR-INTEGRITY-XXX for agent-team pipeline requirements) and renders a Markdown
+ HTML matrix under ``tests/reports/``. The CI ``test`` job runs this to
produce the artifact that the "Comment traceability report" step publishes on
the pull request; completeness of the matrix is asserted separately by
``tests/ci-pipeline/test_generate_traceability_matrix.py``.

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
AGENT_REQUIREMENTS = ROOT / ".opencode" / "docs" / "REQUIREMENTS.md"
ARCHITECTURE = ROOT / "doc" / "ARCHITECTURE.md"
SOURCE = ROOT / "src_timesheetalgo" / "TimeSheetAlgo.py"
CI_SCRIPTS = [
    ROOT / ".github" / "scripts",
]
REPORT_PATH = ROOT / "tests" / "reports" / "traceability-matrix.md"


@dataclass
class TraceabilityData:
    """Requirement identifiers discovered in each traceability source."""

    script_ids: list[str]
    agent_ids: list[str]
    architecture_ids: set[str]
    code_ids: set[str]

    @property
    def all_ids(self) -> list[str]:
        return self.script_ids + self.agent_ids

    @property
    def missing_in_architecture(self) -> list[str]:
        """Requirements absent from the architecture document."""
        return [r for r in self.all_ids if r not in self.architecture_ids]

    @property
    def missing_in_code(self) -> list[str]:
        """Requirements absent from the implementation references."""
        return [r for r in self.all_ids if r not in self.code_ids]

    @property
    def script_missing_in_architecture(self) -> list[str]:
        return [r for r in self.script_ids if r not in self.architecture_ids]

    @property
    def agent_missing_in_architecture(self) -> list[str]:
        return [r for r in self.agent_ids if r not in self.architecture_ids]

    @property
    def script_missing_in_code(self) -> list[str]:
        return [r for r in self.script_ids if r not in self.code_ids]

    @property
    def agent_missing_in_code(self) -> list[str]:
        return [r for r in self.agent_ids if r not in self.code_ids]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_requirement_ids(text: str) -> list[str]:
    """Return every FR-XX / QR-XX (and FR-INTEGRITY-XXX / QR-INTEGRITY-XXX)
    identifier found in ``text`` (in order)."""
    return re.findall(
        r"\b(FR-(?:\d{2}|INTEGRITY-\d{3})|QR-(?:\d{2}|INTEGRITY-\d{3}))\b", text
    )


def _dedup_preserve_order(items: list[str]) -> list[str]:
    """Remove duplicates while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def collect_ids() -> TraceabilityData:
    """Read the sources and collect their requirement identifiers."""
    code_text = _read_text(SOURCE)
    for script_dir in CI_SCRIPTS:
        for script in script_dir.iterdir():
            if script.suffix in (".py",):
                code_text += "\n" + _read_text(script)
    return TraceabilityData(
        script_ids=_dedup_preserve_order(
            extract_requirement_ids(_read_text(REQUIREMENTS))
        ),
        agent_ids=_dedup_preserve_order(
            extract_requirement_ids(_read_text(AGENT_REQUIREMENTS))
        ),
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

    # ---- Script requirements (TimeSheetAlgo application) ----
    lines.append("## Script Requirements (TimeSheetAlgo / `doc/REQUIREMENTS.md`)")
    groups = _group_by_type(data.script_ids)
    for label, reqs in (
        ("Functional Requirements", groups["FR"]),
        ("Quality Requirements", groups["QR"]),
    ):
        if not reqs:
            continue
        lines.append(f"### {label}")
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
            f"{_coverage_percent(reqs, data.architecture_ids)}%"
        )
        lines.append(f"- Code coverage: {_coverage_percent(reqs, data.code_ids)}%")

    # ---- Agent team requirements ----
    lines.append("## Agent Team Requirements (`.opencode/docs/REQUIREMENTS.md`)")
    groups = _group_by_type(data.agent_ids)
    for label, reqs in (
        ("Functional Requirements", groups["FR"]),
        ("Quality Requirements", groups["QR"]),
    ):
        if not reqs:
            continue
        lines.append(f"### {label}")
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
            f"{_coverage_percent(reqs, data.architecture_ids)}%"
        )
        lines.append(f"- Code coverage: {_coverage_percent(reqs, data.code_ids)}%")

    return "\n".join(lines)


def build_html(data: TraceabilityData) -> str:
    """Render the compact HTML traceability matrix for richer PR artifacts."""

    def cell(val: str) -> str:
        return f"<td>{val}</td>"

    def section_title(text: str) -> str:
        return f"<h2>{text}</h2>"

    def sub_section(text: str) -> str:
        return f"<h3>{text}</h3>"

    def group_reqs(requirement_ids: list[str]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {"FR": [], "QR": []}
        for req in requirement_ids:
            groups["FR" if req.startswith("FR-") else "QR"].append(req)
        return groups

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

    for section_name, requirement_ids in (
        ("Script Requirements (TimeSheetAlgo)", data.script_ids),
        ("Agent Team Requirements (opencode)", data.agent_ids),
    ):
        groups = group_reqs(requirement_ids)
        for title, reqs in (
            ("Functional Requirements", groups["FR"]),
            ("Quality Requirements", groups["QR"]),
        ):
            if not reqs:
                continue
            html_lines.append(section_name)
            html_lines.append(sub_section(title))
            html_lines.append("<table>")
            html_lines.append(
                "<thead><tr>"
                + "".join(
                    f"<th>{c}</th>"
                    for c in ["Requirement", "Type", "In Architecture", "In Code"]
                )
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
                html_lines.append(
                    "<tr>" + "".join(cell(c) for c in row_cells) + "</tr>"
                )
            html_lines.append("</tbody></table>")
            arch_cov = _coverage_percent(reqs, data.architecture_ids)
            code_cov = _coverage_percent(reqs, data.code_ids)
            html_lines.append(
                f"<p>Architecture coverage: {arch_cov}%<br/>"
                f"Code coverage: {code_cov}%</p>"
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
    if not data.script_ids and not data.agent_ids:
        problems.append("No requirement identifiers were discovered")
    if data.missing_in_architecture:
        problems.append(
            f"Missing from architecture: script={data.script_missing_in_architecture}, "
            f"agent={data.agent_missing_in_architecture}"
        )
    if data.missing_in_code:
        script_missing = data.script_missing_in_code
        agent_missing = data.agent_missing_in_code
        problems.append(
            f"Missing from implementation references: "
            f"script={script_missing}, agent={agent_missing}"
        )

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        sys.exit(1)

    print(build_markdown(data))


if __name__ == "__main__":
    main()
