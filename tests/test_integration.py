"""Integration tests for TimeSheetAlgo - testing complete workflows.

These tests verify that multiple components of the system work together
correctly to process timelog data and store it in Excel timesheet files.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta

import openpyxl
import pytest
from src_timesheetalgo.TimeSheetAlgo import (
    DATE_FORMAT,
    ROW_OFFSET,
    TimeSheetProcessor,
    check_file_existence,
)

pytestmark = pytest.mark.integration


class TestLoadRealResources:
    """Test loading real CSV and Excel files if available."""

    def test_load_real_csv(self):
        """Integration test: Load real timelog CSV file.

        Tests that the check_file_existence function can load and parse
        a real CSV file with multiple entries.
        """
        path = "sup/2025_extract.csv"
        if not os.path.exists(path):
            pytest.skip("Real timelog CSV not present")
        data = check_file_existence(path, "csv")
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify CSV structure: each row should have date, start, end
        for entry in data:
            assert len(entry) >= 3
            assert isinstance(entry[0], str)  # date string
            assert isinstance(entry[1], str)  # start time
            assert isinstance(entry[2], str)  # end time

    def test_load_real_excel(self):
        """Integration test: Load real timesheet Excel file.

        Tests that the check_file_existence function can load
        a real Excel workbook with proper structure.
        """
        path = "src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm"
        if not os.path.exists(path):
            pytest.skip("Real timesheet Excel not present")
        wb = check_file_existence(path, "excel")
        assert isinstance(wb, openpyxl.Workbook)
        assert len(wb.worksheets) >= 12  # Should have 12 month sheets


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows: load → select → store → save."""

    def test_e2e_load_and_select_data(self, mock_processor):
        """Integration test: Load files and select data for date range.

        Tests the complete workflow of:
        1. Loading CSV and Excel files
        2. Setting date boundaries
        3. Filtering timelog data by date range
        """
        # Setup: Configure processor with test data
        mock_processor.timelog = [
            ["05.01.2025", "09:00", "17:00"],
            ["10.01.2025", "08:30", "16:30"],
            ["15.01.2025", "09:15", "17:15"],
            ["20.01.2025", "08:00", "16:00"],
        ]

        # Set date range
        mock_processor.obj_date_startpoint = datetime.strptime(
            "08.01.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "18.01.2025", DATE_FORMAT
        )

        # Execute: Select timelog data for the date range
        mock_processor.select_timelog_data()

        # Verify: Correct entries are selected (10.01 and 15.01)
        assert len(mock_processor.timedata) == 2
        assert mock_processor.timedata[0][0] == "10.01.2025"
        assert mock_processor.timedata[1][0] == "15.01.2025"

    def test_e2e_load_select_and_store_single_entry(self, mock_processor):
        """Integration test: Load, select, and store a single timesheet entry.

        Tests the complete workflow of:
        1. Loading files
        2. Selecting data for a specific date
        3. Writing data to the Excel workbook
        4. Verifying data is correctly placed
        """
        # Setup: Configure processor with single entry
        mock_processor.timelog = [["15.01.2025", "09:00", "17:00"]]
        mock_processor.obj_date_startpoint = datetime.strptime(
            "15.01.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "15.01.2025", DATE_FORMAT
        )

        # Execute: Select data
        mock_processor.select_timelog_data()
        assert len(mock_processor.timedata) == 1

        # Execute: Store data to Excel
        mock_processor.store_data()

        # Verify: Data is written to correct location
        # January (month 0), day 15 → row ROW_OFFSET + 15, columns 5 & 6
        sheet = mock_processor.timesheet.worksheets[0]  # January
        start_cell = sheet.cell(row=ROW_OFFSET + 15, column=5)
        end_cell = sheet.cell(row=ROW_OFFSET + 15, column=6)

        assert start_cell.value == "09:00"
        assert end_cell.value == "17:00"

    def test_e2e_load_select_and_store_multiple_months(self, mock_processor):
        """Integration test: Store entries across multiple months.

        Tests that the system correctly distributes entries
        across different month worksheets.
        """
        # Setup: Entries in different months
        mock_processor.timelog = [
            ["15.01.2025", "09:00", "17:00"],  # January
            ["20.02.2025", "08:30", "16:30"],  # February
            ["10.06.2025", "10:00", "18:00"],  # June
        ]
        mock_processor.obj_date_startpoint = datetime.strptime(
            "01.01.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "30.06.2025", DATE_FORMAT
        )

        # Execute: Select and store
        mock_processor.select_timelog_data()
        assert len(mock_processor.timedata) == 3
        mock_processor.store_data()

        # Verify: Each entry is in the correct month/row
        january_sheet = mock_processor.timesheet.worksheets[0]
        january_start = january_sheet.cell(row=ROW_OFFSET + 15, column=5)
        assert january_start.value == "09:00"

        february_sheet = mock_processor.timesheet.worksheets[1]
        february_start = february_sheet.cell(row=ROW_OFFSET + 20, column=5)
        assert february_start.value == "08:30"

        june_sheet = mock_processor.timesheet.worksheets[5]
        june_start = june_sheet.cell(row=ROW_OFFSET + 10, column=5)
        assert june_start.value == "10:00"

    def test_e2e_full_workflow_with_save(self, mock_processor, monkeypatch):
        """Integration test: Complete workflow including file save.

        Tests the entire pipeline:
        1. Load CSV and Excel
        2. Select data for date range
        3. Store data in workbook
        4. Save workbook to file
        """
        # Setup: Configure full workflow
        mock_processor.timelog = [
            ["12.03.2025", "09:00", "17:00"],
            ["15.03.2025", "08:30", "16:30"],
        ]
        mock_processor.obj_date_startpoint = datetime.strptime(
            "10.03.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "20.03.2025", DATE_FORMAT
        )

        # Execute: Full workflow
        mock_processor.select_timelog_data()
        mock_processor.store_data()

        # Verify: Data is in memory before save
        march_sheet = mock_processor.timesheet.worksheets[2]
        assert march_sheet.cell(row=ROW_OFFSET + 12, column=5).value == "09:00"
        assert march_sheet.cell(row=ROW_OFFSET + 15, column=5).value == "08:30"

        # Execute: Save workbook
        save_called = False

        def mock_save(path):
            nonlocal save_called
            save_called = True

        monkeypatch.setattr(mock_processor.timesheet, "save", mock_save)
        mock_processor.save_timesheet()

        # Verify: Save was called
        assert save_called is True


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_scenario_week_of_entries_with_various_times(self, mock_processor):
        """Integration test: Process a full week of variable work hours.

        Simulates a realistic scenario where an employee works different
        hours each day across a week, testing the system's ability to
        handle multiple entries with varying durations.
        """
        # Setup: Full week of March 2025
        mock_processor.timelog = [
            ["10.03.2025", "08:00", "17:00"],  # Monday, 9 hours
            ["11.03.2025", "09:00", "17:30"],  # Tuesday, 8.5 hours
            ["12.03.2025", "07:30", "16:00"],  # Wednesday, 8.5 hours
            ["13.03.2025", "09:30", "18:00"],  # Thursday, 8.5 hours
            ["14.03.2025", "08:00", "15:00"],  # Friday, 7 hours (short day)
        ]
        mock_processor.obj_date_startpoint = datetime.strptime(
            "10.03.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "14.03.2025", DATE_FORMAT
        )

        # Execute: Select and store all week's entries
        mock_processor.select_timelog_data()
        assert len(mock_processor.timedata) == 5

        mock_processor.store_data()

        # Verify: All entries are correctly stored
        march_sheet = mock_processor.timesheet.worksheets[2]  # March is index 2

        test_cases = [
            (10, "08:00", "17:00"),
            (11, "09:00", "17:30"),
            (12, "07:30", "16:00"),
            (13, "09:30", "18:00"),
            (14, "08:00", "15:00"),
        ]

        for day, expected_start, expected_end in test_cases:
            row = ROW_OFFSET + day
            start_cell = march_sheet.cell(row=row, column=5)
            end_cell = march_sheet.cell(row=row, column=6)
            assert start_cell.value == expected_start, (
                f"Mismatch on March {day}: "
                f"expected start {expected_start}, got {start_cell.value}"
            )
            assert end_cell.value == expected_end, (
                f"Mismatch on March {day}: "
                f"expected end {expected_end}, got {end_cell.value}"
            )

    def test_scenario_data_overwrite_workflow(
        self, mock_processor, monkeypatch, caplog
    ):
        """Integration test: Handle overwriting existing data with user confirmation.

        Tests the scenario where timesheet cells already contain data
        and the user decides whether to overwrite or skip.
        """
        # Setup: Add existing data to target cells
        march_sheet = mock_processor.timesheet.worksheets[2]
        march_sheet.cell(row=ROW_OFFSET + 15, column=5, value="14:00")
        march_sheet.cell(row=ROW_OFFSET + 15, column=6, value="18:00")

        mock_processor.timelog = [["15.03.2025", "09:00", "17:00"]]
        mock_processor.obj_date_startpoint = datetime.strptime(
            "15.03.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "15.03.2025", DATE_FORMAT
        )

        # Scenario A: User chooses to overwrite
        mock_processor.select_timelog_data()
        monkeypatch.setattr("builtins.input", lambda prompt: "y")

        with caplog.at_level(logging.INFO):
            mock_processor.store_data()

        # Verify: Data was overwritten
        start_cell = march_sheet.cell(row=ROW_OFFSET + 15, column=5)
        end_cell = march_sheet.cell(row=ROW_OFFSET + 15, column=6)
        assert start_cell.value == "09:00"
        assert end_cell.value == "17:00"

    def test_scenario_cross_year_boundary_not_supported(self, mock_processor):
        """Integration test: Verify system behavior at year boundaries.

        Ensures that the system correctly handles (or rejects) requests
        that cross year boundaries, as each instance is typically tied
        to a specific year.
        """
        # Setup: Try to select dates that span years (should fail gracefully)
        mock_processor.timelog = [
            ["30.12.2024", "09:00", "17:00"],  # Previous year
            ["15.01.2025", "08:30", "16:30"],  # Current year
        ]

        # Try to select both - system should only find 2025 data
        mock_processor.obj_date_startpoint = datetime.strptime(
            "01.01.2025", DATE_FORMAT
        )
        mock_processor.obj_date_endpoint = datetime.strptime(
            "31.12.2025", DATE_FORMAT
        )

        # Only 2025 entry should be selected
        mock_processor.select_timelog_data()
        assert len(mock_processor.timedata) == 1
        assert mock_processor.timedata[0][0] == "15.01.2025"


class TestRealResourceIntegration:
    """Integration tests using actual project resources (if available)."""

    def test_integration_with_real_resources(self, real_resource_copy):
        """Integration test: Process real timelog and Excel files.

        This test requires the actual project resources to be present.
        It tests the complete workflow with real data.
        """
        if real_resource_copy is None:
            pytest.skip("Real resource files not available")

        # Verify resources were copied
        assert os.path.exists(real_resource_copy["timelog_path"])
        assert os.path.exists(real_resource_copy["timesheet_path"])

        # Load resources
        timelog_data = check_file_existence(
            real_resource_copy["timelog_path"], "csv"
        )
        timesheet = check_file_existence(
            real_resource_copy["timesheet_path"], "excel"
        )

        # Verify data structures
        assert isinstance(timelog_data, list)
        assert len(timelog_data) > 0
        assert isinstance(timesheet, openpyxl.Workbook)
        assert len(timesheet.worksheets) >= 12

        # Process with TimeSheetProcessor
        config = real_resource_copy.copy()
        config["year"] = 2025
        processor = TimeSheetProcessor(config)
        processor.load_files()

        # Verify processor loaded data
        assert len(processor.timelog) > 0
        assert processor.timesheet is not None

        # Clean up backup
        if os.path.exists(config["backup_path"]):
            os.remove(config["backup_path"])
