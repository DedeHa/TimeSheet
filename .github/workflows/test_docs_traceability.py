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


def _build_traceability_matrix(
    requirement_ids: list[str], architecture_ids: set[str], code_ids: set[str]
) -> str:
    rows = []
    for requirement_id in requirement_ids:
        in_architecture = requirement_id in architecture_ids
        in_code = requirement_id in code_ids
        status = "Covered" if in_architecture and in_code else "Missing mapping"
        rows.append(
            f"| {requirement_id} | "
            f"{'✅' if requirement_id in requirement_ids else '❌'} | "
            f"{'✅' if in_architecture else '❌'} | "
            f"{'✅' if in_code else '❌'} | {status} |"
        )

    architecture_coverage = round(
        100
        * sum(1 for req in requirement_ids if req in architecture_ids)
        / len(requirement_ids),
        1,
    )
    code_coverage = round(
        100
        * sum(1 for req in requirement_ids if req in code_ids)
        / len(requirement_ids),
        1,
    )

    header = [
        "# Traceability Matrix",
        "",
        "| Requirement | In Requirements | In Architecture | In Code | Status |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        f"- Architecture coverage: {architecture_coverage}%",
        f"- Code coverage: {code_coverage}%",
    ]
    return "\n".join(header)


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

    report = _build_traceability_matrix(requirement_ids, architecture_ids, code_ids)
    _publish_report(report)

    print(report)
