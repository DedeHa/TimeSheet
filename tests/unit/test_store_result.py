"""Unit tests for the StoreResult enum and store_data return value (PRO-339).

``store_data`` now returns a :class:`StoreResult` instead of using implicit
``break`` / ``continue`` control flow, so tests can assert on the outcome.
"""

import pytest

from src_timesheetalgo.TimeSheetAlgo import StoreResult

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# StoreResult enum
# ---------------------------------------------------------------------------


def test_store_result_values():
    """StoreResult members carry the expected string values."""
    assert StoreResult.STORED.value == "stored"
    assert StoreResult.SKIPPED.value == "skipped"
    assert StoreResult.ABORTED.value == "abort"


def test_store_result_is_enum():
    """StoreResult is an enum member."""
    assert StoreResult.STORED is not StoreResult.SKIPPED
    assert StoreResult("stored") is StoreResult.STORED


# ---------------------------------------------------------------------------
# store_data return value (integration-level behaviour, unit-tested here)
# ---------------------------------------------------------------------------


def test_store_data_returns_stored_on_overwrite(make_processor, caplog):
    """store_data returns STORED when data is written (overwrite_all)."""
    processor = make_processor(
        timelog=[["15.03.2025", "09:00", "17:00"]],
        timesheet_cells=[(2, 15, "08:00", "16:00")],  # existing data -> conflict
    )
    processor.obj_date_startpoint = __import__(
        "datetime"
    ).datetime(2025, 3, 1)
    processor.obj_date_endpoint = __import__(
        "datetime"
    ).datetime(2025, 3, 31)
    processor.select_timelog_data()

    # Force overwrite_all by injecting a provider that answers "y"
    processor._input_provider = lambda prompt: "y"
    result = processor.store_data()
    assert result is StoreResult.STORED


def test_store_data_returns_skipped_on_skip_all(make_processor):
    """store_data returns SKIPPED when the user chooses skip_all."""
    processor = make_processor(
        timelog=[["15.03.2025", "09:00", "17:00"]],
        timesheet_cells=[(2, 15, "08:00", "16:00")],
    )
    processor.obj_date_startpoint = __import__("datetime").datetime(2025, 3, 1)
    processor.obj_date_endpoint = __import__("datetime").datetime(2025, 3, 31)
    processor.select_timelog_data()

    processor._input_provider = lambda prompt: "s"  # skip
    result = processor.store_data()
    assert result is StoreResult.SKIPPED


def test_store_data_returns_aborted_on_abort(make_processor):
    """store_data returns ABORTED when the user chooses abort."""
    processor = make_processor(
        timelog=[["15.03.2025", "09:00", "17:00"]],
        timesheet_cells=[(2, 15, "08:00", "16:00")],
    )
    processor.obj_date_startpoint = __import__("datetime").datetime(2025, 3, 1)
    processor.obj_date_endpoint = __import__("datetime").datetime(2025, 3, 31)
    processor.select_timelog_data()

    processor._input_provider = lambda prompt: "n"  # abort
    result = processor.store_data()
    assert result is StoreResult.ABORTED


def test_store_data_returns_stored_no_conflict(make_processor):
    """store_data returns STORED when there is no existing data."""
    processor = make_processor(
        timelog=[["15.03.2025", "09:00", "17:00"]],
        timesheet_cells=[],
    )
    processor.obj_date_startpoint = __import__("datetime").datetime(2025, 3, 1)
    processor.obj_date_endpoint = __import__("datetime").datetime(2025, 3, 31)
    processor.select_timelog_data()

    result = processor.store_data()
    assert result is StoreResult.STORED