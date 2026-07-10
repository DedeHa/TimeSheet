import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "doc" / "REQUIREMENTS.md"
ARCHITECTURE = ROOT / "doc" / "ARCHITECTURE.md"
SOURCE = ROOT / "src_timesheetalgo" / "TimeSheetAlgo.py"
REPORT_PATH = ROOT / "tests" / "reports" / "traceability-matrix.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_requirement_ids(text: str) -> list[str]:
    return re.findall(r"\b(FR-\d{2}|QR-\d{2})\b", text)


def _coverage_percent(requirement_ids: list[str], present_ids: set[str]) -> float:
    total = len(requirement_ids)
    return round(100 * sum(1 for r in requirement_ids if r in present_ids) / max(1, total), 1)


def _group_by_type(requirement_ids: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"FR": [], "QR": []}
    for req in requirement_ids:
        groups["FR" if req.startswith("FR-") else "QR"].append(req)
    return groups


def _build_traceability_matrix(
    requirement_ids: list[str], architecture_ids: set[str], code_ids: set[str]
) -> str:
    def indicator(present: bool) -> str:
        return "🟢" if present else "◯"

    lines: list[str] = ["# Traceability Matrix", ""]

    groups = _group_by_type(requirement_ids)
    for label, reqs in (
        ("Functional Requirements", groups["FR"]),
        ("Quality Requirements", groups["QR"]),
    ):
        if not reqs:
            continue
        lines.append(f"## {label}")
        # Header (compact: no spec count, no per-test columns)
        header_cols = ["Requirement", "Type", "In Architecture", "In Code"]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

        for req in reqs:
            row = [
                req,
                "Functional" if req.startswith("FR-") else "Quality",
                indicator(req in architecture_ids),
                indicator(req in code_ids),
            ]
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    lines.append(f"- Architecture coverage: {_coverage_percent(requirement_ids, architecture_ids)}%")
    lines.append(f"- Code coverage: {_coverage_percent(requirement_ids, code_ids)}%")

    return "\n".join(lines)


def _build_traceability_html(
    requirement_ids: list[str], architecture_ids: set[str], code_ids: set[str]
) -> str:
    # Compact matrix only: Requirement, Type, In Architecture, In Code.
    def cell(val: str) -> str:
        return f"<td>{val}</td>"

    html_lines = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        "<title>Traceability Matrix</title>",
        "<style>",
        "body{font-family:Arial,Helvetica,sans-serif;margin:16px;background:#0f1724;color:#e6eef8}",
        "table{border-collapse:collapse;width:100%;overflow:auto}",
        "th,td{border:1px solid #2b3350;padding:8px;text-align:left}",
        "th{background:#111827;color:#9fb4ff}",
        "tr:nth-child(even){background:#071026}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Traceability Matrix</h1>",
    ]

    groups = _group_by_type(requirement_ids)
    for title, reqs in (
        ("Functional Requirements", groups["FR"]),
        ("Quality Requirements", groups["QR"]),
    ):
        if not reqs:
            continue
        html_lines.append(f"<h2>{title}</h2>")
        html_lines.append("<table>")
        header_cols = ["Requirement", "Type", "In Architecture", "In Code"]
        html_lines.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in header_cols) + "</tr></thead>")
        html_lines.append("<tbody>")

        for req in reqs:
            row_cells = [
                req,
                ("Functional" if req.startswith("FR-") else "Quality"),
                ("✅" if req in architecture_ids else "◯"),
                ("✅" if req in code_ids else "◯"),
            ]
            html_lines.append("<tr>" + "".join(cell(c) for c in row_cells) + "</tr>")

        html_lines.append("</tbody></table>")

    arch_cov = _coverage_percent(requirement_ids, architecture_ids)
    code_cov = _coverage_percent(requirement_ids, code_ids)
    html_lines.append(f"<p>Architecture coverage: {arch_cov}%<br/>Code coverage: {code_cov}%</p>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def _publish_report(report: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(report)
            handle.write("\n")


def test_traceability_matrix_is_complete_and_published():
    requirement_ids = _extract_requirement_ids(_read_text(REQUIREMENTS))
    architecture_ids = set(_extract_requirement_ids(_read_text(ARCHITECTURE)))
    code_ids = set(_extract_requirement_ids(_read_text(SOURCE)))

    assert requirement_ids, "No requirement identifiers were discovered"
    missing_in_architecture = [
        req_id for req_id in requirement_ids if req_id not in architecture_ids
    ]
    missing_in_code = [req_id for req_id in requirement_ids if req_id not in code_ids]

    assert (
        not missing_in_architecture
    ), f"Requirements missing from architecture traceability: {missing_in_architecture}"
    assert (
        not missing_in_code
    ), f"Requirements missing from implementation references: {missing_in_code}"

    report = _build_traceability_matrix(requirement_ids, architecture_ids, code_ids)
    _publish_report(report)
    # also produce HTML report for richer display in PR artifacts
    html = _build_traceability_html(requirement_ids, architecture_ids, code_ids)
    html_path = REPORT_PATH.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n---\n")
            handle.write(f"Generated traceability HTML: {html_path}\n")

    print(report)
