"""Integration-level fixtures."""

from datetime import datetime

import pytest

from src_timesheetalgo.TimeSheetAlgo import DATE_FORMAT


@pytest.fixture
def processor_with_timelog(make_processor):
    """Build a processor with a timelog and an explicit date range set.

    Wraps the shared ``make_processor`` factory for the common integration
    setup: an in-memory dummy workbook, an assigned timelog, and the
    start/end boundaries already parsed.

    Returns a callable ``build(timelog, start, end, timesheet_cells=None,
    year=2025)`` where ``start``/``end`` are ``DD.MM.YYYY`` strings.
    """

    def _build(timelog, start, end, timesheet_cells=None, year=2025):
        processor = make_processor(
            timelog=timelog, timesheet_cells=timesheet_cells, year=year
        )
        processor.obj_date_startpoint = datetime.strptime(start, DATE_FORMAT)
        processor.obj_date_endpoint = datetime.strptime(end, DATE_FORMAT)
        return processor

    return _build
