"""Unit tests for the injected Clock.

``set_default_end_date`` now uses ``self._clock()`` instead of
``datetime.now()`` directly, so tests can inject a fixed clock without
``freezegun``.
"""

from datetime import datetime

import pytest

from src_timesheetalgo.TimeSheetAlgo import (
    _default_clock,
)

pytestmark = pytest.mark.unit


def _fixed_clock(fixed_dt):
    def _clock():
        return fixed_dt

    return _clock


# ---------------------------------------------------------------------------
# Clock type alias and default
# ---------------------------------------------------------------------------


def test_clock_is_callable():
    """Clock is a Callable alias usable as a type hint."""
    assert callable(_default_clock)


def test_default_clock_returns_datetime():
    """The default Clock returns a datetime instance."""
    assert isinstance(_default_clock(), datetime)


# ---------------------------------------------------------------------------
# set_default_end_date with injected clock
# ---------------------------------------------------------------------------


def test_set_default_end_date_uses_injected_clock(mock_processor):
    """The default end date is yesterday relative to the injected clock."""
    fixed = datetime(2025, 12, 23, 12, 0, 0)
    mock_processor._clock = _fixed_clock(fixed)
    result = mock_processor.set_default_end_date()
    assert result == datetime(2025, 12, 22, 12, 0, 0)


def test_set_default_end_date_injected_clock_midnight(mock_processor):
    """The injected clock at midnight still yields yesterday."""
    fixed = datetime(2026, 1, 1, 0, 0, 0)
    mock_processor._clock = _fixed_clock(fixed)
    result = mock_processor.set_default_end_date()
    assert result == datetime(2025, 12, 31)


def test_set_default_end_date_does_not_call_real_now(mock_processor, monkeypatch):
    """The injected clock prevents any call to ``datetime.now``."""
    called = {"now": False}
    real_now = datetime.now

    def spy_now():
        called["now"] = True
        return real_now()

    monkeypatch.setattr("src_timesheetalgo.TimeSheetAlgo.dt.now", spy_now)
    mock_processor._clock = _fixed_clock(datetime(2025, 6, 15))
    mock_processor.set_default_end_date()
    assert called["now"] is False
