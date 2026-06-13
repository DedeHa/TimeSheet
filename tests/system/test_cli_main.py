"""System tests for the CLI entry points run() and main().

These exercise the orchestration that the ``__main__`` block used to inline:
run() (load -> request dates -> select -> store -> save) and main() (config
load + logging + run). Time is frozen by the autouse fixture, so default-date
logic is deterministic in-process.
"""

import csv

import openpyxl
import pytest

import src_timesheetalgo.TimeSheetAlgo as tsa
from src_timesheetalgo.TimeSheetAlgo import ROW_OFFSET

pytestmark = pytest.mark.system

_DEV_CONFIG = """\
year: 2025
environments:
  development:
    file_paths:
      timelog_path: "timelog_copy.csv"
      timesheet_path: "timesheet_copy.xlsm"
    logging:
      level: "INFO"
      format: "%(message)s"
default_environment: "development"
"""


def _first_january_entry(csv_path):
    """Return the first January ``[date, start, end]`` row, or None."""
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    for row in rows:
        if len(row) >= 3 and row[0].endswith(".01.2025"):
            return row
    return None


def test_run_writes_expected_cell(cli_runner, real_resource_copy):
    """run() with explicit dates stores the CSV entry into the saved workbook."""
    entry = _first_january_entry(real_resource_copy["timelog_path"])
    if entry is None:
        pytest.skip("No January 2025 entry in the real CSV")
    date_str, start, _ = entry[0], entry[1], entry[2]
    day = int(date_str.split(".")[0])

    saved = cli_runner([date_str, date_str, "y"])

    wb = openpyxl.load_workbook(saved, keep_vba=True)
    assert wb.worksheets[0].cell(row=ROW_OFFSET + day, column=5).value == start


def test_run_with_default_dates_completes(cli_runner):
    """run() with empty input uses default dates and still produces a workbook."""
    saved = cli_runner(["", ""])
    wb = openpyxl.load_workbook(saved, keep_vba=True)
    assert len(wb.worksheets) >= 12


def test_main_with_tmp_config(real_resource_copy, tmp_path, monkeypatch):
    """main() loads a real config, configures logging, and runs the pipeline."""
    if real_resource_copy is None:
        pytest.skip("Real resource files not available")

    config_path = tmp_path / "config.yaml"  # same dir as the copied resources
    config_path.write_text(_DEV_CONFIG)

    entry = _first_january_entry(real_resource_copy["timelog_path"])
    if entry is None:
        pytest.skip("No January 2025 entry in the real CSV")
    date_str, start, _ = entry[0], entry[1], entry[2]
    day = int(date_str.split(".")[0])

    real_load = tsa.load_config
    monkeypatch.setattr(tsa, "load_config", lambda: real_load(str(config_path)))
    answers = iter([date_str, date_str, "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers, "y"))

    tsa.main()

    wb = openpyxl.load_workbook(real_resource_copy["timesheet_path"], keep_vba=True)
    assert wb.worksheets[0].cell(row=ROW_OFFSET + day, column=5).value == start


def test_main_config_error_exits(tmp_path, monkeypatch):
    """A config missing 'year' makes main() exit with status 1."""
    bad_config = tmp_path / "bad_config.yaml"
    bad_config.write_text(
        "environments:\n"
        "  development:\n"
        "    file_paths:\n"
        "      timelog_path: x.csv\n"
        "      timesheet_path: y.xlsm\n"
    )

    real_load = tsa.load_config
    monkeypatch.setattr(tsa, "load_config", lambda: real_load(str(bad_config)))

    with pytest.raises(SystemExit) as excinfo:
        tsa.main()
    assert excinfo.value.code == 1
