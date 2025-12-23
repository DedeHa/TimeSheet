import os
import pytest
import openpyxl
from TimeSheetAlgo import check_file_existence

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_load_real_csv():
    path = "sup/2025_extract.csv"
    if not os.path.exists(path):
        pytest.skip("Real timelog CSV not present")
    data = check_file_existence(path, "csv")
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.integration
def test_load_real_excel():
    path = "src_timesheetalgo/2025_FDTech_Dennis_Hartel.xlsm"
    if not os.path.exists(path):
        pytest.skip("Real timesheet Excel not present")
    wb = check_file_existence(path, "excel")
    assert isinstance(wb, openpyxl.Workbook)