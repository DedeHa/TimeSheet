"""Unit tests for the overwrite-decision logic.

Covers confirm_overwrite, _prompt_overwrite_decision and
_check_and_confirm_overwrite in isolation. The way store_data *acts* on these
decisions (skip/abort/overwrite across the workbook) is tested at the
integration level.
"""

import logging

import pytest

from src.TimeSheetAlgo import ROW_OFFSET, TimeSheetProcessor

pytestmark = pytest.mark.unit


def _bare_processor():
    """A processor with no files loaded (enough for input-only methods)."""
    return TimeSheetProcessor(
        {"timelog_path": "dummy.csv", "timesheet_path": "dummy.xlsx", "year": 2025}
    )


# ---------------------------------------------------------------------------
# confirm_overwrite
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "user_input, expected",
    [
        ("y", True),
        ("yes", True),
        ("YES", True),
        (" y ", True),
        ("n", False),
        ("no", False),
        ("NO", False),
        ("", False),
        ("invalid", False),
    ],
)
def test_confirm_overwrite(monkeypatch, user_input, expected):
    """confirm_overwrite maps yes-like answers to True, everything else False."""
    monkeypatch.setattr("builtins.input", lambda prompt: user_input)
    assert _bare_processor().confirm_overwrite() is expected


def test_confirm_overwrite_eof_defaults_true(monkeypatch):
    """An EOFError defaults confirm_overwrite to True."""
    monkeypatch.setattr(
        "builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError())
    )
    assert _bare_processor().confirm_overwrite() is True


# ---------------------------------------------------------------------------
# _prompt_overwrite_decision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "user_input, expected",
    [
        ("s", "skip_all"),
        ("skip", "skip_all"),
        ("y", "overwrite_all"),
        ("", "overwrite_all"),
        ("n", "abort"),
        ("no", "abort"),
    ],
)
def test_prompt_overwrite_decision(monkeypatch, user_input, expected):
    """Each answer maps to the expected overwrite state."""
    monkeypatch.setattr("builtins.input", lambda prompt: user_input)
    assert _bare_processor()._prompt_overwrite_decision(2) == expected


def test_prompt_overwrite_decision_eof_defaults_overwrite(monkeypatch, caplog):
    """An EOFError defaults the decision to overwrite_all and logs it."""
    monkeypatch.setattr(
        "builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError())
    )
    with caplog.at_level(logging.INFO):
        assert _bare_processor()._prompt_overwrite_decision(2) == "overwrite_all"
    assert "No input provided" in caplog.text


# ---------------------------------------------------------------------------
# _check_and_confirm_overwrite
# ---------------------------------------------------------------------------


def test_check_and_confirm_overwrite_no_conflicts(make_processor):
    """With no existing data, overwrite_all is returned without prompting."""
    processor = make_processor(timelog=[["15.03.2025", "09:00", "17:00"]])
    processor.timedata = list(processor.timelog)
    assert processor._check_and_confirm_overwrite() == "overwrite_all"


def test_check_and_confirm_overwrite_with_conflicts(
    make_processor, monkeypatch, caplog
):
    """Existing data triggers a prompt; the user's choice is returned and logged."""
    processor = make_processor(
        timelog=[["05.01.2025", "09:00", "17:00"]],
        timesheet_cells=[(0, 5, "08:00", "16:00")],
    )
    processor.timedata = list(processor.timelog)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    with caplog.at_level(logging.INFO):
        result = processor._check_and_confirm_overwrite()

    assert result == "overwrite_all"
    assert "Found 1 day(s) with existing data" in caplog.text
    # Sanity: the conflict cell really was pre-populated at the expected row.
    assert processor.timesheet.worksheets[0].cell(row=ROW_OFFSET + 5, column=5).value
