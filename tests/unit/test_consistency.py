"""Unit tests for TimeSheetProcessor.check_year_consistency.

Verifies the input check that compares the configured year with the year
stored in the timesheet (cell ``Januar!B3``): the OK path (year as a date and
as a plain string), a year mismatch, and an empty/unreadable cell. All run on
the in-memory dummy workbook in isolation.
"""

import pytest

from src.TimeSheetAlgo import (
    YEAR_CHECK_CELL,
    YEAR_CHECK_SHEET,
    ConsistencyError,
)

pytestmark = pytest.mark.unit


def _name_january(processor):
    """Rename the dummy workbook's first sheet to the expected 'Januar' tab."""
    processor.timesheet.worksheets[0].title = YEAR_CHECK_SHEET
    return processor


def test_check_year_consistency_match(make_processor):
    """Matching config year and a date in Januar!B3 pass without raising."""
    processor = _name_january(make_processor(year=2025))  # B3 = datetime(2025, 1, 1)

    processor.check_year_consistency()  # must not raise


def test_check_year_consistency_year_as_text(make_processor):
    """A plain year string in B3 (e.g. '2025') is parsed and matched."""
    processor = _name_january(make_processor(year=2025))
    processor.timesheet[YEAR_CHECK_SHEET][YEAR_CHECK_CELL] = "2025"

    processor.check_year_consistency()  # must not raise


def test_check_year_consistency_mismatch_raises(make_processor):
    """A differing config year raises ConsistencyError naming both years."""
    processor = _name_january(make_processor(year=2024))  # B3 stays 2025

    with pytest.raises(ConsistencyError, match="Year mismatch"):
        processor.check_year_consistency()


def test_check_year_consistency_missing_value_raises(make_processor):
    """An empty B3 cell yields no usable year and raises ConsistencyError."""
    processor = _name_january(make_processor(year=2025))
    processor.timesheet[YEAR_CHECK_SHEET][YEAR_CHECK_CELL] = None

    with pytest.raises(ConsistencyError, match="Year mismatch"):
        processor.check_year_consistency()
