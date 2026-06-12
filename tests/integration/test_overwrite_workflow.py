"""Integration tests for store_data acting on overwrite decisions.

Each test pre-populates a target cell, then drives select -> store with a
simulated user answer, verifying how the overwrite state machine
(overwrite_all / skip_all / abort, plus the empty and EOF defaults) is applied
across the workbook.
"""

import logging

import pytest

from src_timesheetalgo.TimeSheetAlgo import ROW_OFFSET

pytestmark = pytest.mark.integration

# Jan 5 entry colliding with an existing cell at January day 5.
_NEW = [["05.01.2025", "09:00", "17:00"]]
_EXISTING = [(0, 5, "08:00", "16:00")]
_ROW = ROW_OFFSET + 5


def _build(processor_with_timelog):
    return processor_with_timelog(
        _NEW, "05.01.2025", "05.01.2025", timesheet_cells=_EXISTING
    )


def test_overwrite_all_replaces_existing(processor_with_timelog, monkeypatch):
    """Answering 'y' overwrites the existing cell with the new times."""
    processor = _build(processor_with_timelog)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    processor.select_timelog_data()
    processor.store_data()

    sheet = processor.timesheet.worksheets[0]
    assert sheet.cell(row=_ROW, column=5).value == "09:00"
    assert sheet.cell(row=_ROW, column=6).value == "17:00"


def test_skip_all_preserves_existing(processor_with_timelog, monkeypatch, caplog):
    """Answering 's' keeps the existing data and logs a skip."""
    processor = _build(processor_with_timelog)
    monkeypatch.setattr("builtins.input", lambda prompt: "s")

    processor.select_timelog_data()
    with caplog.at_level(logging.INFO):
        processor.store_data()

    assert processor.timesheet.worksheets[0].cell(row=_ROW, column=5).value == "08:00"
    assert "Skipping existing data" in caplog.text


def test_abort_preserves_existing(processor_with_timelog, monkeypatch, caplog):
    """Answering 'n' aborts storage and logs it; existing data is preserved."""
    processor = _build(processor_with_timelog)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    processor.select_timelog_data()
    with caplog.at_level(logging.INFO):
        processor.store_data()

    assert processor.timesheet.worksheets[0].cell(row=_ROW, column=5).value == "08:00"
    assert "Aborting due to user request" in caplog.text


def test_empty_answer_overwrites(processor_with_timelog, monkeypatch):
    """An empty answer defaults to overwrite_all through the full pipeline."""
    processor = _build(processor_with_timelog)
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    processor.select_timelog_data()
    processor.store_data()

    assert processor.timesheet.worksheets[0].cell(row=_ROW, column=5).value == "09:00"


def test_eof_answer_overwrites(processor_with_timelog, monkeypatch):
    """An EOF at the overwrite prompt defaults to overwrite_all."""
    processor = _build(processor_with_timelog)
    monkeypatch.setattr(
        "builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError())
    )

    processor.select_timelog_data()
    processor.store_data()

    assert processor.timesheet.worksheets[0].cell(row=_ROW, column=5).value == "09:00"
