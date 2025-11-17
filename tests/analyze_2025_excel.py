#!/usr/bin/env python3
"""
FILENAME: analyze_2025_excel.py
AUTHOR: Dennis Hartel
DESCRIPTION: Analyze 2025 Excel timesheet structure and compare with TimeSheetAlgo.py expectations
"""

import openpyxl
from datetime import datetime
import sys
import os

# Constants from TimeSheetAlgo.py
ROW_OFFSET = 4
EXPECTED_TIMESHEET_SHEETS = 12
EXPECTED_YEAR = 2025
TIME_COLUMNS = [5, 6]  # Columns E and F for start/end times


def analyze_excel_structure(filepath):
    """
    Analyze the Excel file structure in READ-ONLY mode and compare with expectations.

    Args:
        filepath (str): Path to the Excel file

    Returns:
        dict: Analysis results
    """
    print(f"Analyzing Excel file: {filepath}")
    print("=" * 80)

    try:
        # Load workbook in READ-ONLY mode to prevent any modifications
        workbook = openpyxl.load_workbook(filepath, read_only=True, data_only=False)
        print("[OK] Successfully loaded workbook in READ-ONLY mode")

        analysis_results = {
            "file_path": filepath,
            "total_worksheets": len(workbook.worksheets),
            "worksheet_names": [ws.title for ws in workbook.worksheets],
            "monthly_sheets": [],
            "compatibility_issues": [],
            "recommendations": [],
        }

        print(f"Total worksheets found: {analysis_results['total_worksheets']}")
        print(f"Expected worksheets: {EXPECTED_TIMESHEET_SHEETS}")

        if analysis_results["total_worksheets"] < EXPECTED_TIMESHEET_SHEETS:
            analysis_results["compatibility_issues"].append(
                f"Insufficient worksheets: Found {analysis_results['total_worksheets']}, expected {EXPECTED_TIMESHEET_SHEETS}"
            )

        print("\nWorksheet Names:")
        for i, name in enumerate(analysis_results["worksheet_names"], 1):
            print(f"  {i:2d}. {name}")

        # Analyze first 12 worksheets (assumed to be monthly sheets)
        monthly_sheet_names = [
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ]

        print(
            f"\nAnalyzing Monthly Worksheets (first {min(EXPECTED_TIMESHEET_SHEETS, len(workbook.worksheets))}):"
        )
        print("-" * 80)

        for month_idx in range(
            min(EXPECTED_TIMESHEET_SHEETS, len(workbook.worksheets))
        ):
            worksheet = workbook.worksheets[month_idx]
            month_analysis = analyze_monthly_worksheet(
                worksheet, month_idx + 1, monthly_sheet_names[month_idx]
            )
            analysis_results["monthly_sheets"].append(month_analysis)

            print(f"\nMonth {month_idx + 1} - {worksheet.title}:")
            print(f"  Expected name: {monthly_sheet_names[month_idx]}")
            print(f"  Actual name: {worksheet.title}")

            if worksheet.title != monthly_sheet_names[month_idx]:
                issue = f"Month {month_idx + 1}: Expected '{monthly_sheet_names[month_idx]}', found '{worksheet.title}'"
                analysis_results["compatibility_issues"].append(issue)
                print("  [WARNING] Name mismatch!")
            else:
                print("  [OK] Name matches expectation")

            # Check year in header (row 3, column 2 as per TimeSheetAlgo.py)
            try:
                year_cell = worksheet.cell(row=3, column=2).value
                if year_cell and hasattr(year_cell, "year"):
                    found_year = year_cell.year
                    print(f"  Year found in header: {found_year}")
                    if found_year != EXPECTED_YEAR:
                        issue = f"Month {month_idx + 1}: Expected year {EXPECTED_YEAR}, found {found_year}"
                        analysis_results["compatibility_issues"].append(issue)
                        print("  [WARNING] Year mismatch!")
                    else:
                        print("  [OK] Year matches expectation")
                else:
                    print("  [WARNING] No valid year found in header (row 3, column 2)")
                    analysis_results["compatibility_issues"].append(
                        f"Month {month_idx + 1}: No valid year found in expected header position"
                    )
            except Exception as e:
                print(f"  [WARNING] Error reading year from header: {e}")

            # Analyze date entries and time columns
            print("  Date entries analysis:")
            date_entries = 0
            time_entries = 0

            for day in range(1, 32):  # Check up to 31 days
                row = ROW_OFFSET + day
                try:
                    # Check date column (column 5 as per TimeSheetAlgo.py)
                    date_cell = worksheet.cell(row=row, column=5).value
                    start_time_cell = worksheet.cell(row=row, column=5).value
                    end_time_cell = worksheet.cell(row=row, column=6).value

                    if date_cell:
                        date_entries += 1

                    if start_time_cell or end_time_cell:
                        time_entries += 1

                except Exception:
                    # Skip if row doesn't exist
                    continue

            print(f"    - Date entries found: {date_entries}")
            print(f"    - Time entries found: {time_entries}")
            print(f"    - Row offset used: {ROW_OFFSET} (as expected)")
            print(f"    - Time columns: {TIME_COLUMNS} (E & F as expected)")

        # Generate compatibility assessment
        print(f"\n{'='*80}")
        print("COMPATIBILITY ASSESSMENT")
        print(f"{'='*80}")

        if not analysis_results["compatibility_issues"]:
            print(
                "[OK] FULLY COMPATIBLE: No issues found with current TimeSheetAlgo.py expectations"
            )
        else:
            print(
                f"[WARNING] COMPATIBILITY ISSUES FOUND: {len(analysis_results['compatibility_issues'])} issues"
            )
            for i, issue in enumerate(analysis_results["compatibility_issues"], 1):
                print(f"  {i}. {issue}")

        # Generate recommendations
        print("\nRECOMMENDATIONS:")
        print("-" * 40)

        if analysis_results["total_worksheets"] != EXPECTED_TIMESHEET_SHEETS:
            analysis_results["recommendations"].append(
                f"Update TIMESHEET_SHEETS constant from {EXPECTED_TIMESHEET_SHEETS} to {analysis_results['total_worksheets']}"
            )

        # Check if year needs updating
        year_issues = [
            issue
            for issue in analysis_results["compatibility_issues"]
            if "year" in issue.lower()
        ]
        if year_issues:
            analysis_results["recommendations"].append(
                f"Update YEAR constant from 2023 to {EXPECTED_YEAR} in TimeSheetAlgo.py"
            )

        # Check file path
        current_path = "src_timesheetalgo/2023_FDTech_Dennis_Hartel.xlsm"
        new_path = "src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm"
        analysis_results["recommendations"].append(
            f"Update timesheet_path in CONFIG from '{current_path}' to '{new_path}'"
        )

        if not analysis_results["recommendations"]:
            print("  No specific recommendations needed.")
        else:
            for i, rec in enumerate(analysis_results["recommendations"], 1):
                print(f"  {i}. {rec}")

        workbook.close()
        return analysis_results

    except FileNotFoundError:
        print(f"[ERROR] Error: File not found: {filepath}")
        return None
    except Exception as e:
        print(f"[ERROR] Error analyzing file: {e}")
        return None


def analyze_monthly_worksheet(worksheet, month_number, expected_name):
    """
    Analyze a single monthly worksheet structure.

    Args:
        worksheet: openpyxl worksheet object
        month_number (int): Month number (1-12)
        expected_name (str): Expected worksheet name

    Returns:
        dict: Analysis results for the worksheet
    """
    analysis = {
        "month_number": month_number,
        "actual_name": worksheet.title,
        "expected_name": expected_name,
        "name_matches": worksheet.title == expected_name,
        "date_entries": 0,
        "time_entries": 0,
        "max_row_with_data": 0,
        "structure_issues": [],
    }

    # Check structure from ROW_OFFSET onwards
    for day in range(1, 32):
        row = ROW_OFFSET + day
        try:
            # Check if row has any data
            for col in range(1, 10):  # Check first 9 columns
                cell_value = worksheet.cell(row=row, column=col).value
                if cell_value:
                    analysis["max_row_with_data"] = max(
                        analysis["max_row_with_data"], row
                    )
                    break

            # Check date column (column 5)
            date_cell = worksheet.cell(row=row, column=5).value
            if date_cell:
                analysis["date_entries"] += 1

            # Check time columns (columns 5 & 6)
            start_time = worksheet.cell(row=row, column=5).value
            end_time = worksheet.cell(row=row, column=6).value
            if start_time or end_time:
                analysis["time_entries"] += 1

        except Exception:
            # Row might not exist, continue
            continue

    return analysis


def main():
    """Main function to run the analysis."""
    excel_file_path = "src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm"

    # Check if file exists
    if not os.path.exists(excel_file_path):
        print(f"[ERROR] Error: Excel file not found at {excel_file_path}")
        print("Please ensure the file exists in the correct location.")
        sys.exit(1)

    print("2025 Excel Timesheet Structure Analysis")
    print("=" * 80)
    print(f"Target file: {excel_file_path}")
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Mode: READ-ONLY (no modifications will be made)")
    print()

    # Perform analysis
    results = analyze_excel_structure(excel_file_path)

    if results:
        print(f"\n{'='*80}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"File analyzed successfully: {excel_file_path}")
        print(f"Total worksheets: {results['total_worksheets']}")
        print(f"Compatibility issues found: {len(results['compatibility_issues'])}")
        print(f"Recommendations generated: {len(results['recommendations'])}")

        if results["compatibility_issues"]:
            print(
                "\n[WARNING] TimeSheetAlgo.py may need updates to work with the 2025 file."
            )
        else:
            print(
                "\n[OK] TimeSheetAlgo.py should work with the 2025 file without modifications."
            )
    else:
        print("\n[ERROR] Analysis failed. Please check the file path and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
