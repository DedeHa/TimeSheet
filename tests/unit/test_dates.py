"""Unit tests for date parsing and default-date logic.

Covers parse_date, TimeSheetProcessor._get_date, set_default_start_date and
set_default_end_date. All time-dependent behaviour relies on the autouse
``frozen_time`` fixture (2025-12-23).
"""

import logging
from datetime import datetime, timedelta

import pytest

from src.TimeSheetAlgo import DATE_FORMAT, ROW_OFFSET, parse_date

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------


def test_parse_date_valid(monkeypatch):
    """A valid date string is parsed into a datetime."""
    monkeypatch.setattr("builtins.input", lambda prompt: "15.03.2025")
    assert parse_date("Enter date: ") == datetime.strptime("15.03.2025", DATE_FORMAT)


def test_parse_date_retries_exhausted(monkeypatch):
    """Repeated invalid input raises ValueError after the retry budget."""
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")
    with pytest.raises(ValueError, match="Maximum retries reached"):
        parse_date("Enter date: ")


def test_parse_date_retries_zero(monkeypatch):
    """retries=0 raises ValueError immediately."""
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")
    with pytest.raises(ValueError, match="Maximum retries reached"):
        parse_date("Enter date: ", retries=0)


def test_parse_date_invalid_then_valid(monkeypatch):
    """An invalid entry followed by a valid one returns the parsed date."""
    inputs = iter(["invalid", "15.03.2025"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    assert parse_date("Enter date: ", retries=3) == datetime(2025, 3, 15)


# ---------------------------------------------------------------------------
# TimeSheetProcessor._get_date
# ---------------------------------------------------------------------------


def test_get_date_success(mock_processor, monkeypatch):
    """Valid input returns the parsed date and never calls the fallback."""
    monkeypatch.setattr("builtins.input", lambda prompt: "15.03.2025")
    result = mock_processor._get_date("Enter date: ", lambda: datetime(2025, 1, 1))
    assert result == datetime(2025, 3, 15)


def test_get_date_fallback_on_exception(mock_processor, monkeypatch, caplog):
    """When parsing fails, the fallback value is returned and a warning logged."""
    monkeypatch.setattr("builtins.input", lambda prompt: "invalid")
    fallback = datetime(2025, 12, 31)
    with caplog.at_level(logging.WARNING):
        result = mock_processor._get_date("Enter date: ", lambda: fallback)
    assert result == fallback
    assert "Error parsing date" in caplog.text


# ---------------------------------------------------------------------------
# set_default_start_date / set_default_end_date
# ---------------------------------------------------------------------------


def test_set_default_start_date_with_data(mock_processor):
    """The latest worked day in the workbook becomes the default start date."""
    mock_processor.timesheet.worksheets[5].cell(
        row=ROW_OFFSET + 15, column=5, value="09:00"
    )
    result = mock_processor.set_default_start_date()
    assert (result.year, result.month, result.day) == (2025, 6, 15)


def test_set_default_start_date_no_data(mock_processor, caplog):
    """With no worked days, the default start date falls back to Jan 1 + warns."""
    with caplog.at_level(logging.WARNING):
        result = mock_processor.set_default_start_date()
    assert result == datetime(2025, 1, 1)
    assert "No valid date found" in caplog.text


def test_set_default_end_date_is_yesterday(mock_processor):
    """The default end date is yesterday relative to 'now'.

    Under the frozen clock (2025-12-23) that is 2025-12-22; the assertion is
    written relative to ``now()`` so it also holds when freezegun is absent and
    the autouse ``frozen_time`` fixture degrades to a no-op.
    """
    result = mock_processor.set_default_end_date()
    assert result.date() == (datetime.now() - timedelta(days=1)).date()


# ---------------------------------------------------------------------------
# PRO-262: boundary / equivalence-class additions
# ---------------------------------------------------------------------------
#
# parse_date currently distinguishes only "format-malformed" input. These cases
# add the second invalid equivalence class - strings that match the DD.MM.YYYY
# format but are not real calendar dates - and the leap-year boundary.


@pytest.mark.parametrize("bad_date", ["32.01.2025", "30.02.2025", "31.04.2025"])
def test_parse_date_calendar_invalid_is_rejected(monkeypatch, bad_date):
    """A well-formatted but non-existent calendar date is rejected."""
    monkeypatch.setattr("builtins.input", lambda prompt: bad_date)
    with pytest.raises(ValueError, match="Maximum retries reached"):
        parse_date("Enter date: ", retries=1)


def test_parse_date_leap_day_valid(monkeypatch):
    """29 February in a leap year (2024) parses successfully."""
    monkeypatch.setattr("builtins.input", lambda prompt: "29.02.2024")
    assert parse_date("Enter date: ") == datetime(2024, 2, 29)


def test_parse_date_leap_day_non_leap_year_rejected(monkeypatch):
    """29 February in a non-leap year (2025) is rejected as calendar-invalid."""
    monkeypatch.setattr("builtins.input", lambda prompt: "29.02.2025")
    with pytest.raises(ValueError, match="Maximum retries reached"):
        parse_date("Enter date: ", retries=1)


def test_set_default_start_date_day_31_boundary(mock_processor):
    """A worked day on the 31st should become the default start date.

    PRO-262: set_default_start_date scans rows ROW_OFFSET+31..+1, so a worked
    day on the 31st is detected. See tests/boundary_equivalence_analysis.md.
    """
    mock_processor.timesheet.worksheets[0].cell(
        row=ROW_OFFSET + 31, column=5, value="09:00"
    )
    result = mock_processor.set_default_start_date()
    assert (result.year, result.month, result.day) == (2025, 1, 31)
