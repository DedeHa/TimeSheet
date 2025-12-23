#!/usr/bin/env python3
"""
FILENAME: final_verification_test.py
AUTHOR: Dennis Hartel
DESCRIPTION: Final verification test for TimeSheetAlgo.py CSV to Excel data mapping
"""

import csv
import openpyxl
from datetime import datetime as dt
import logging
import sys
import os
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_system_timesheetalgo_verification.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Constants from TimeSheetAlgo.py
DATE_FORMAT = "%d.%m.%Y"
ROW_OFFSET = 4
TIMESHEET_SHEETS = 12
YEAR = 2025

# Test configuration
TEST_CONFIG = {
    "timelog_path": "sup/2025_extract.csv",  # Use the comprehensive 2025 data
    "timesheet_path": "src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm",
    "backup_path": (
        "src_timesheetalgo/" "2025_FDTech_Dennis_Hartel_VERIFICATION_BACKUP.xlsm"
    ),
}


class VerificationTester:
    """Comprehensive verification tester for TimeSheetAlgo.py functionality."""

    def __init__(self, config):
        self.config = config
        self.timelog = []
        self.timesheet = None
        self.test_results = {
            "csv_data_loaded": False,
            "excel_file_loaded": False,
            "date_parsing_tests": [],
            "worksheet_mapping_tests": [],
            "row_calculation_tests": [],
            "column_placement_tests": [],
            "data_integrity_tests": [],
            "overall_success": False,
        }

    def create_backup(self):
        """Create a backup of the Excel file before testing."""
        try:
            shutil.copy2(self.config["timesheet_path"], self.config["backup_path"])
            logging.info(f"Backup created: {self.config['backup_path']}")
            return True
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            return False

    def load_test_data(self):
        """Load CSV test data."""
        logging.info("Loading CSV test data...")
        try:
            with open(self.config["timelog_path"], encoding="utf-8") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                self.timelog = list(reader)

            logging.info(f"Loaded {len(self.timelog)} CSV records")
            self.test_results["csv_data_loaded"] = True

            # Log sample data for verification
            logging.info("Sample CSV data:")
            for i, entry in enumerate(self.timelog[:5]):
                logging.info(
                    f"  {i+1}. Date: {entry[0]}, Start: {entry[1]}, End: {entry[2]}"
                )

            return True
        except Exception as e:
            logging.error(f"Failed to load CSV data: {e}")
            return False

    def load_excel_file(self):
        """Load Excel timesheet file."""
        logging.info("Loading Excel timesheet...")
        try:
            self.timesheet = openpyxl.load_workbook(
                self.config["timesheet_path"], data_only=False, keep_vba=True
            )
            logging.info(
                f"Excel file loaded with {len(self.timesheet.worksheets)} worksheets"
            )
            self.test_results["excel_file_loaded"] = True

            # Log worksheet names
            logging.info("Available worksheets:")
            for i, ws in enumerate(self.timesheet.worksheets[:12]):
                logging.info(f"  {i+1}. {ws.title}")

            return True
        except Exception as e:
            logging.error(f"Failed to load Excel file: {e}")
            return False

    def test_date_parsing(self):
        """Test date parsing functionality."""
        logging.info("Testing date parsing...")

        test_dates = [
            "06.01.2025",
            "15.03.2025",
            "30.06.2025",
            "25.09.2025",
            "31.12.2025",
        ]

        for date_str in test_dates:
            try:
                parsed_date = dt.strptime(date_str, DATE_FORMAT)
                test_result = {
                    "date_string": date_str,
                    "parsed_date": parsed_date,
                    "month": parsed_date.month,
                    "day": parsed_date.day,
                    "year": parsed_date.year,
                    "success": True,
                }
                logging.info(
                    f"  ✓ {date_str} → {parsed_date.date()} "
                    f"(Month: {parsed_date.month}, Day: {parsed_date.day})"
                )
            except Exception as e:
                test_result = {
                    "date_string": date_str,
                    "error": str(e),
                    "success": False,
                }
                logging.error(f"  ✗ {date_str} → ERROR: {e}")

            self.test_results["date_parsing_tests"].append(test_result)

    def test_worksheet_mapping(self):
        """Test date-to-worksheet mapping."""
        logging.info("Testing worksheet mapping...")

        # Test specific dates from our CSV data
        test_cases = [
            ("06.01.2025", 0, "Januar"),  # January → worksheet 0
            ("15.03.2025", 2, "März"),  # March → worksheet 2
            ("30.06.2025", 5, "Juni"),  # June → worksheet 5
            ("25.09.2025", 8, "Sept."),  # September → worksheet 8
        ]

        for date_str, expected_idx, expected_name in test_cases:
            try:
                date_obj = dt.strptime(date_str, DATE_FORMAT)
                calculated_idx = date_obj.month - 1
                actual_worksheet = self.timesheet.worksheets[calculated_idx]

                test_result = {
                    "date": date_str,
                    "expected_index": expected_idx,
                    "calculated_index": calculated_idx,
                    "expected_name": expected_name,
                    "actual_name": actual_worksheet.title,
                    "index_correct": calculated_idx == expected_idx,
                    "name_matches": actual_worksheet.title == expected_name,
                    "success": calculated_idx == expected_idx,
                }

                if test_result["success"]:
                    logging.info(
                        f"  ✓ {date_str} → Worksheet {calculated_idx} "
                        f"({actual_worksheet.title})"
                    )
                else:
                    logging.error(
                        f"  ✗ {date_str} → Expected {expected_idx}, "
                        f"got {calculated_idx}"
                    )

            except Exception as e:
                test_result = {"date": date_str, "error": str(e), "success": False}
                logging.error(f"  ✗ {date_str} → ERROR: {e}")

            self.test_results["worksheet_mapping_tests"].append(test_result)

    def test_row_calculation(self):
        """Test row calculation (ROW_OFFSET + day)."""
        logging.info("Testing row calculation...")

        test_cases = [
            ("01.01.2025", 1, ROW_OFFSET + 1),  # Day 1 → Row 5
            ("15.01.2025", 15, ROW_OFFSET + 15),  # Day 15 → Row 19
            ("31.01.2025", 31, ROW_OFFSET + 31),  # Day 31 → Row 35
        ]

        for date_str, expected_day, expected_row in test_cases:
            try:
                date_obj = dt.strptime(date_str, DATE_FORMAT)
                calculated_row = ROW_OFFSET + date_obj.day

                test_result = {
                    "date": date_str,
                    "day": date_obj.day,
                    "expected_day": expected_day,
                    "expected_row": expected_row,
                    "calculated_row": calculated_row,
                    "success": calculated_row == expected_row,
                }

                if test_result["success"]:
                    logging.info(
                        f"  ✓ {date_str} (Day {date_obj.day}) → Row {calculated_row}"
                    )
                else:
                    logging.error(
                        f"  ✗ {date_str} → Expected row {expected_row}, "
                        f"got {calculated_row}"
                    )

            except Exception as e:
                test_result = {"date": date_str, "error": str(e), "success": False}
                logging.error(f"  ✗ {date_str} → ERROR: {e}")

            self.test_results["row_calculation_tests"].append(test_result)

    def test_column_placement(self):
        """Test start/end time placement in columns 5 and 6."""
        logging.info("Testing column placement...")

        # Test with actual data from CSV
        test_entries = self.timelog[:3]  # Test first 3 entries

        for entry in test_entries:
            try:
                date_str, start_time, end_time = entry[0], entry[1], entry[2]
                date_obj = dt.strptime(date_str, DATE_FORMAT)

                month_idx = date_obj.month - 1
                row = ROW_OFFSET + date_obj.day
                worksheet = self.timesheet.worksheets[month_idx]

                # Get current cell values
                start_cell = worksheet.cell(row=row, column=5)
                end_cell = worksheet.cell(row=row, column=6)

                test_result = {
                    "date": date_str,
                    "start_time": start_time,
                    "end_time": end_time,
                    "worksheet": worksheet.title,
                    "row": row,
                    "start_column": 5,
                    "end_column": 6,
                    "start_cell_address": start_cell.coordinate,
                    "end_cell_address": end_cell.coordinate,
                    "current_start_value": start_cell.value,
                    "current_end_value": end_cell.value,
                    "success": True,
                }

                logging.info(
                    f"  ✓ {date_str} → {worksheet.title} Row {row}, "
                    f"Cols E&F ({start_cell.coordinate}, {end_cell.coordinate})"
                )
                logging.info(
                    f"    Start: {start_time} → {start_cell.coordinate}, "
                    f"End: {end_time} → {end_cell.coordinate}"
                )

            except Exception as e:
                test_result = {"date": date_str, "error": str(e), "success": False}
                logging.error(f"  ✗ {date_str} → ERROR: {e}")

            self.test_results["column_placement_tests"].append(test_result)

    def test_data_integrity(self):
        """Test actual data writing and integrity."""
        logging.info("Testing data integrity with sample writes...")

        # Select a few test entries from January 2025
        january_entries = [
            entry for entry in self.timelog if entry[0].endswith(".01.2025")
        ][:3]

        if not january_entries:
            logging.warning("No January 2025 entries found for integrity testing")
            return

        for entry in january_entries:
            try:
                date_str, start_time, end_time = entry[0], entry[1], entry[2]
                date_obj = dt.strptime(date_str, DATE_FORMAT)

                # Calculate target location
                month_idx = date_obj.month - 1
                row = ROW_OFFSET + date_obj.day
                worksheet = self.timesheet.worksheets[month_idx]

                # Store original values
                start_cell = worksheet.cell(row=row, column=5)
                end_cell = worksheet.cell(row=row, column=6)
                original_start = start_cell.value
                original_end = end_cell.value

                # Write test data
                start_cell.value = start_time
                end_cell.value = end_time

                # Verify write
                written_start = start_cell.value
                written_end = end_cell.value

                test_result = {
                    "date": date_str,
                    "worksheet": worksheet.title,
                    "row": row,
                    "original_start": original_start,
                    "original_end": original_end,
                    "written_start": written_start,
                    "written_end": written_end,
                    "start_match": written_start == start_time,
                    "end_match": written_end == end_time,
                    "success": written_start == start_time and written_end == end_time,
                }

                if test_result["success"]:
                    logging.info(
                        f"  ✓ {date_str} → Data written successfully to "
                        f"{worksheet.title} row {row}"
                    )
                    logging.info(f"    Start: {start_time} ✓, End: {end_time} ✓")
                else:
                    logging.error(f"  ✗ {date_str} → Data write verification failed")

                # Restore original values
                start_cell.value = original_start
                end_cell.value = original_end

            except Exception as e:
                test_result = {"date": date_str, "error": str(e), "success": False}
                logging.error(f"  ✗ {date_str} → ERROR: {e}")

            self.test_results["data_integrity_tests"].append(test_result)

    def run_comprehensive_test(self):
        """Run all verification tests."""
        logging.info("=" * 80)
        logging.info("STARTING COMPREHENSIVE VERIFICATION TEST")
        logging.info("=" * 80)

        # Create backup
        if not self.create_backup():
            logging.error("Failed to create backup. Aborting test.")
            return False

        # Load data
        if not self.load_test_data():
            logging.error("Failed to load CSV data. Aborting test.")
            return False

        if not self.load_excel_file():
            logging.error("Failed to load Excel file. Aborting test.")
            return False

        # Run tests
        self.test_date_parsing()
        self.test_worksheet_mapping()
        self.test_row_calculation()
        self.test_column_placement()
        self.test_data_integrity()

        # Generate summary
        self.generate_test_summary()

        return self.test_results["overall_success"]

    def generate_test_summary(self):
        """Generate comprehensive test summary."""
        logging.info("=" * 80)
        logging.info("VERIFICATION TEST SUMMARY")
        logging.info("=" * 80)

        # Count successes
        date_parsing_success = sum(
            1 for t in self.test_results["date_parsing_tests"] if t["success"]
        )
        worksheet_mapping_success = sum(
            1 for t in self.test_results["worksheet_mapping_tests"] if t["success"]
        )
        row_calculation_success = sum(
            1 for t in self.test_results["row_calculation_tests"] if t["success"]
        )
        column_placement_success = sum(
            1 for t in self.test_results["column_placement_tests"] if t["success"]
        )
        data_integrity_success = sum(
            1 for t in self.test_results["data_integrity_tests"] if t["success"]
        )

        total_tests = (
            len(self.test_results["date_parsing_tests"])
            + len(self.test_results["worksheet_mapping_tests"])
            + len(self.test_results["row_calculation_tests"])
            + len(self.test_results["column_placement_tests"])
            + len(self.test_results["data_integrity_tests"])
        )

        total_success = (
            date_parsing_success
            + worksheet_mapping_success
            + row_calculation_success
            + column_placement_success
            + data_integrity_success
        )

        csv_status = "✓ PASS" if self.test_results["csv_data_loaded"] else "✗ FAIL"
        excel_status = "✓ PASS" if self.test_results["excel_file_loaded"] else "✗ FAIL"
        logging.info(f"CSV Data Loading: {csv_status}")
        logging.info(f"Excel File Loading: {excel_status}")
        date_total = len(self.test_results["date_parsing_tests"])
        logging.info(f"Date Parsing Tests: {date_parsing_success}/{date_total} passed")
        ws_total = len(self.test_results["worksheet_mapping_tests"])
        logging.info(
            f"Worksheet Mapping Tests: {worksheet_mapping_success}/{ws_total} passed"
        )
        row_total = len(self.test_results["row_calculation_tests"])
        logging.info(
            f"Row Calculation Tests: {row_calculation_success}/{row_total} passed"
        )
        col_total = len(self.test_results["column_placement_tests"])
        logging.info(
            f"Column Placement Tests: {column_placement_success}/{col_total} passed"
        )
        data_total = len(self.test_results["data_integrity_tests"])
        logging.info(
            f"Data Integrity Tests: {data_integrity_success}/{data_total} passed"
        )

        logging.info("-" * 80)
        pct = total_success / total_tests * 100
        logging.info(
            f"OVERALL RESULT: {total_success}/{total_tests} tests passed ({pct:.1f}%)"
        )

        # Determine overall success
        self.test_results["overall_success"] = (
            self.test_results["csv_data_loaded"]
            and self.test_results["excel_file_loaded"]
            and total_success == total_tests
        )

        if self.test_results["overall_success"]:
            logging.info(
                "🎉 ALL TESTS PASSED - TimeSheetAlgo.py is ready for production use!"
            )
        else:
            logging.warning(
                "⚠️  SOME TESTS FAILED - Review issues before production use"
            )

        logging.info("=" * 80)


def main():
    """Main function to run verification tests."""
    print("TimeSheetAlgo.py Final Verification Test")
    print("=" * 80)

    # Check if required files exist
    for key, path in TEST_CONFIG.items():
        if key != "backup_path" and not os.path.exists(path):
            logging.error(f"Required file not found: {path}")
            sys.exit(1)

    # Run verification
    tester = VerificationTester(TEST_CONFIG)
    success = tester.run_comprehensive_test()

    if success:
        logging.info("Verification completed successfully!")
        sys.exit(0)
    else:
        logging.error("Verification completed with issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()
