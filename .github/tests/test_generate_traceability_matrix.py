"""Unit tests for the traceability matrix generator (PRO-368).

These validate the completeness gate and the rendering of
``.github/scripts/generate_traceability_matrix.py`` in isolation. Like
``test_generate_pr_summary.py`` this file lives under ``.github/tests/`` (not in
``tests/``), so it does not change the 103-test application suite or the
coverage gate. The CI pipeline enforces the completeness gate inside the script
itself (``generate_traceability_matrix.py`` exits non-zero on an untraced
requirement); this developer unit test covers the same logic and can be run
with::

    pytest -q .github/tests/test_generate_traceability_matrix.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "scripts"
    / "generate_traceability_matrix.py"
)
_spec = importlib.util.spec_from_file_location(
    "generate_traceability_matrix", _MODULE_PATH
)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["generate_traceability_matrix"] = mod
_spec.loader.exec_module(mod)


def test_every_requirement_is_traced():
    """Quality gate: every requirement appears in architecture and in code."""
    data = mod.collect_ids()
    assert data.requirement_ids, "No requirement identifiers were discovered"
    assert (
        not data.missing_in_architecture
    ), f"Requirements missing from architecture: {data.missing_in_architecture}"
    assert (
        not data.missing_in_code
    ), f"Requirements missing from implementation references: {data.missing_in_code}"


def test_extract_requirement_ids_matches_fr_and_qr():
    """The extractor picks up FR-XX / QR-XX tokens and ignores other text."""
    ids = mod.extract_requirement_ids("FR-01 blah QR-08 nope AB-12 FR-99")
    assert ids == ["FR-01", "QR-08", "FR-99"]


def test_build_markdown_renders_sections_and_coverage():
    """The Markdown matrix contains the section headers and coverage footer."""
    data = mod.TraceabilityData(
        requirement_ids=["FR-01", "QR-08"],
        architecture_ids={"FR-01", "QR-08"},
        code_ids={"FR-01"},
    )
    md = mod.build_markdown(data)
    assert "# Traceability Matrix" in md
    assert "## Functional Requirements" in md
    assert "## Quality Requirements" in md
    assert "Architecture coverage: 100.0%" in md
    assert "Code coverage: 50.0%" in md


def test_write_reports_creates_markdown_and_html(tmp_path, monkeypatch):
    """write_reports emits both the .md and .html artifacts."""
    report_md = tmp_path / "reports" / "traceability-matrix.md"
    monkeypatch.setattr(mod, "REPORT_PATH", report_md)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    data = mod.TraceabilityData(
        requirement_ids=["FR-01"], architecture_ids={"FR-01"}, code_ids={"FR-01"}
    )
    written = mod.write_reports(data)
    assert written.is_file()
    assert report_md.with_suffix(".html").is_file()
    assert "Traceability Matrix" in report_md.read_text(encoding="utf-8")


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
