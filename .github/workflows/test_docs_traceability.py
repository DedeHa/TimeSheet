import os
import re
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "doc" / "REQUIREMENTS.md"
ARCHITECTURE = ROOT / "doc" / "ARCHITECTURE.md"
SOURCE = ROOT / "src_timesheetalgo" / "TimeSheetAlgo.py"
REPORT_PATH = ROOT / "tests" / "reports" / "traceability-matrix.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_requirement_ids(text: str) -> list[str]:
    return re.findall(r"\b(FR-\d{2}|QR-\d{2})\b", text)


def _discover_test_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.py") if "tests" in p.parts]


def _map_tests_to_requirements(test_files: List[Path]) -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = {}
    for tf in test_files:
        text = tf.read_text(encoding="utf-8")
        ids = set(_extract_requirement_ids(text))
        for req in ids:
            mapping.setdefault(req, set()).add(tf.name)
    return mapping


def _build_traceability_matrix(
    requirement_ids: list[str], architecture_ids: set[str], code_ids: set[str], test_map: Dict[str, Set[str]], test_files: List[Path]
) -> str:
    # Prepare per-test columns (all discovered tests)
    tests = sorted({p.name for p in test_files})

    def indicator(req_id: str, present: bool) -> str:
        return "🟢" if present else "◯"

    lines: List[str] = ["# Traceability Matrix", ""]

    # Group by requirement type
    groups = {"FR": [], "QR": []}
    for req in requirement_ids:
        if req.startswith("FR-"):
            groups["FR"].append(req)
        else:
            groups["QR"].append(req)

    for label, reqs in (("Functional Requirements", groups["FR"]), ("Quality Requirements", groups["QR"])):
        if not reqs:
            continue
        lines.append(f"## {label}")
        # Header
        header_cols = ["Requirement", "Type", "Spec count", "In Architecture", "In Code"] + tests
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

        for req in reqs:
            in_arch = req in architecture_ids
            in_code = req in code_ids
            specs = sorted(test_map.get(req, set()))
            spec_count = len(specs)
            row = [
                req,
                "Functional" if req.startswith("FR-") else "Quality",
                str(spec_count),
                indicator(req, in_arch),
                indicator(req, in_code),
            ]
            for t in tests:
                row.append(indicator(req, t in specs))
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    # Coverage summary
    total = len(requirement_ids)
    arch_cov = round(100 * sum(1 for r in requirement_ids if r in architecture_ids) / max(1, total), 1)
    code_cov = round(100 * sum(1 for r in requirement_ids if r in code_ids) / max(1, total), 1)
    lines.append(f"- Architecture coverage: {arch_cov}%")
    lines.append(f"- Code coverage: {code_cov}%")

    return "\n".join(lines)


def _build_traceability_html(
    requirement_ids: list[str], architecture_ids: set[str], code_ids: set[str], test_map: Dict[str, Set[str]], test_files: List[Path]
) -> str:
    # The HTML view will not include per-test columns — only a compact matrix
    # showing Requirement, Type, Spec count, In Architecture and In Code.
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

    groups = {"FR": [], "QR": []}
    for req in requirement_ids:
        if req.startswith("FR-"):
            groups["FR"].append(req)
        else:
            groups["QR"].append(req)

    for title, reqs in (("Functional Requirements", groups["FR"]), ("Quality Requirements", groups["QR"])):
        if not reqs:
            continue
        html_lines.append(f"<h2>{title}</h2>")
        html_lines.append("<table>")
        header_cols = ["Requirement", "Type", "Spec count", "In Architecture", "In Code"]
        html_lines.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in header_cols) + "</tr></thead>")
        html_lines.append("<tbody>")

        for req in reqs:
            in_arch = req in architecture_ids
            in_code = req in code_ids
            specs = sorted(test_map.get(req, set()))
            spec_count = len(specs)
            row_cells = [
                req,
                ("Functional" if req.startswith("FR-") else "Quality"),
                str(spec_count),
                ("✅" if in_arch else "◯"),
                ("✅" if in_code else "◯"),
            ]
            html_lines.append("<tr>" + "".join(cell(c) for c in row_cells) + "</tr>")

        html_lines.append("</tbody></table>")

    total = len(requirement_ids)
    arch_cov = round(100 * sum(1 for r in requirement_ids if r in architecture_ids) / max(1, total), 1)
    code_cov = round(100 * sum(1 for r in requirement_ids if r in code_ids) / max(1, total), 1)
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


def test_requirements_use_unique_requirement_identifiers():
    text = _read_text(REQUIREMENTS)
    ids = _extract_requirement_ids(text)

    assert ids, "Expected functional and quality requirements to be labeled"
    assert len(ids) == len(set(ids)), "Requirement identifiers must be unique"
    assert "FR-01" in ids
    assert "QR-01" in ids


def test_architecture_documents_traceability_to_source_modules():
    text = _read_text(ARCHITECTURE)

    assert "## Traceability Matrix" in text
    assert "src_timesheetalgo/TimeSheetAlgo.py" in text
    assert "FR-01" in text
    assert "QR-01" in text


def test_source_code_references_requirements_where_implemented():
    text = _read_text(SOURCE)

    assert "FR-01" in text
    assert "FR-03" in text
    assert "FR-04" in text
    assert "FR-06" in text
    assert "QR-01" in text


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

    # discover tests and map requirements -> test filenames
    test_files = _discover_test_files(ROOT)
    test_map = _map_tests_to_requirements(test_files)

    report = _build_traceability_matrix(requirement_ids, architecture_ids, code_ids, test_map, test_files)
    _publish_report(report)
    # also produce HTML report for richer display in PR artifacts
    html = _build_traceability_html(requirement_ids, architecture_ids, code_ids, test_map, test_files)
    html_path = REPORT_PATH.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n---\n")
            handle.write(f"Generated traceability HTML: {html_path}\n")

    print(report)
