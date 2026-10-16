"""Unit tests for the CLI orchestration: ``run()``, ``main()`` and the
remaining branches of ``detect_environment`` / ``check_file_existence``.

The multi-step pipeline itself (load -> request dates -> select -> store ->
save) is covered at the integration / system level against real resources.
This file closes the unit-level gaps so the application coverage gate is met
without depending on the resource files:

* ``detect_environment`` development branch when the folder is named ``src``
  (the production branch needs a ``Timealarm`` subfolder, the fallback is
  already covered).
* ``check_file_existence`` fall-through when ``filetype`` is neither ``csv``
  nor ``excel`` (the function then returns ``None`` implicitly).
* ``run()`` happy path (all six pipeline steps) and its error handler, which
  logs and swallows exceptions so a bad date range / missing file ends the
  run gracefully (FR-14).
* ``main()`` success path: config load, logging configuration, the six
  ``logging.info`` diagnostics and the ``run(config)`` call.
"""

import logging

import pytest

import src.TimeSheetAlgo as tsa
from src.TimeSheetAlgo import check_file_existence, detect_environment, run

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# detect_environment
# ---------------------------------------------------------------------------


def test_detect_environment_src_folder(tmp_path):
    """A folder literally named 'src' maps to development.

    The basename check matches 'src' (the packaged application directory),
    which is distinct from the 'src_timesheetalgo' case already covered.
    """
    src_folder = tmp_path / "src"
    src_folder.mkdir()
    assert detect_environment(str(src_folder)) == "development"


# ---------------------------------------------------------------------------
# check_file_existence fall-through
# ---------------------------------------------------------------------------


def test_check_file_existence_unknown_filetype_returns_none(tmp_path):
    """An unknown filetype skips both branches and returns ``None``.

    The function has no ``else`` clause, so an unrecognised ``filetype``
    silently yields ``None`` rather than raising. This pins that contract.
    """
    some_file = tmp_path / "data.bin"
    some_file.write_bytes(b"\x00\x01\x02")
    assert check_file_existence(str(some_file), "unknown") is None


# ---------------------------------------------------------------------------
# run() — happy path and error handler
# ---------------------------------------------------------------------------


def test_run_happy_path(monkeypatch):
    """run() executes all six pipeline steps in order when nothing raises."""
    calls = []

    class FakeProcessor:
        def __init__(self, config):
            self.config = config

        def load_files(self):
            calls.append("load_files")

        def check_year_consistency(self):
            calls.append("check_year_consistency")

        def request_date_input(self):
            calls.append("request_date_input")

        def select_timelog_data(self):
            calls.append("select_timelog_data")

        def store_data(self):
            calls.append("store_data")

        def save_timesheet(self):
            calls.append("save_timesheet")

    monkeypatch.setattr(tsa, "TimeSheetProcessor", FakeProcessor)

    config = {
        "timelog_path": "timelog.csv",
        "timesheet_path": "timesheet.xlsm",
        "year": 2025,
    }

    # run() must not raise and must not return anything meaningful.
    assert run(config) is None
    assert calls == [
        "load_files",
        "check_year_consistency",
        "request_date_input",
        "select_timelog_data",
        "store_data",
        "save_timesheet",
    ]


def test_run_swallows_exception(caplog):
    """run() logs and swallows any exception raised mid-pipeline (FR-14)."""
    config = {
        "timelog_path": "/nonexistent/timelog.csv",
        "timesheet_path": "/nonexistent/timesheet.xlsm",
        "year": 2025,
    }

    with caplog.at_level(logging.ERROR):
        result = run(config)

    assert result is None
    assert "An error occurred" in caplog.text


# ---------------------------------------------------------------------------
# main() — success path
# ---------------------------------------------------------------------------


def test_main_success_path(monkeypatch, caplog):
    """main() loads config, configures logging, logs diagnostics, runs."""
    captured = {}

    fake_config = {
        "environment": "development",
        "timelog_path": "timelog.csv",
        "timesheet_path": "timesheet.xlsm",
        "year": 2025,
        "logging": {"level": "INFO", "format": "%(message)s"},
    }

    def fake_load_config():
        return fake_config

    def fake_run(config):
        captured["config"] = config

    monkeypatch.setattr(tsa, "load_config", fake_load_config)
    monkeypatch.setattr(tsa, "run", fake_run)

    with caplog.at_level(logging.INFO):
        tsa.main()

    assert captured["config"] is fake_config
    # The six diagnostic logging.info calls must have fired.
    assert "CWD:" in caplog.text
    assert "Environment: development" in caplog.text
    assert "Timelog path: timelog.csv" in caplog.text
    assert "Timesheet path: timesheet.xlsm" in caplog.text
    assert "Work year: 2025" in caplog.text
