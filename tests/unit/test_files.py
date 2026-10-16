"""Unit tests for check_file_existence (CSV + Excel loading)."""

import logging

import openpyxl
import pytest

from src.TimeSheetAlgo import check_file_existence

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_csv_loads_without_header(mock_csv_file):
    """A CSV is parsed into rows with the header line stripped."""
    data = check_file_existence(str(mock_csv_file), "csv")
    assert data == [["15.03.2025", "09:00", "17:00"]]


def test_excel_loads_workbook(mock_excel_file):
    """An Excel file is loaded into an openpyxl Workbook."""
    wb = check_file_existence(str(mock_excel_file), "excel")
    assert isinstance(wb, openpyxl.Workbook)


# ---------------------------------------------------------------------------
# Missing files
# ---------------------------------------------------------------------------


def test_csv_not_found(tmp_path):
    """A missing CSV raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(tmp_path / "nope.csv"), "csv")


def test_excel_not_found(tmp_path):
    """A missing Excel file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        check_file_existence(str(tmp_path / "nope.xlsx"), "excel")


# ---------------------------------------------------------------------------
# Permission / lock handling
# ---------------------------------------------------------------------------


def test_csv_permission_denied_logs_and_reraises(tmp_path, monkeypatch, caplog):
    """A PermissionError opening the CSV is logged and re-raised."""
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text("Date,Start,End\n15.03.2025,09:00,17:00\n")

    def raise_perm(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("builtins.open", raise_perm)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(PermissionError):
            check_file_existence(str(csv_file), "csv")
    assert "Permission denied accessing file" in caplog.text
    assert "Error details" in caplog.text


def test_excel_permission_denied_logs_and_reraises(
    mock_excel_file, monkeypatch, caplog
):
    """A PermissionError from load_workbook is logged and re-raised."""

    def raise_perm(*args, **kwargs):
        raise PermissionError("Permission denied from load_workbook")

    monkeypatch.setattr(
        "src.TimeSheetAlgo.openpyxl.load_workbook", raise_perm
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(PermissionError):
            check_file_existence(str(mock_excel_file), "excel")
    assert "Permission denied accessing file" in caplog.text


def test_excel_locked_warns_but_returns_workbook(mock_excel_file, monkeypatch, caplog):
    """A locked file (PermissionError on the r+b probe) warns but still loads."""
    orig_open = open

    def fake_open(filepath, mode="r", *args, **kwargs):
        if mode == "r+b":
            raise PermissionError("File is locked")
        return orig_open(filepath, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    with caplog.at_level(logging.WARNING):
        wb = check_file_existence(str(mock_excel_file), "excel")
    assert isinstance(wb, openpyxl.Workbook)
    assert "Excel file may be locked" in caplog.text
    assert "Lock error" in caplog.text
    assert "Please close the Excel file" in caplog.text


# ---------------------------------------------------------------------------
# PRO-262: CSV column-count equivalence
# ---------------------------------------------------------------------------


def test_csv_preserves_remark_column(tmp_path):
    """A 4-column row (Date,Start,End,Remark) is loaded intact, header stripped.

    The real timelog carries a free-text Remark column; the loader must keep
    it (store_data later ignores everything past End).
    """
    csv_file = tmp_path / "timelog.csv"
    csv_file.write_text(
        "Date,Start,End,Remark\n15.03.2025,09:00,17:00,Project A\n",
        encoding="utf-8",
    )
    data = check_file_existence(str(csv_file), "csv")
    assert data == [["15.03.2025", "09:00", "17:00", "Project A"]]
