"""
FILENAME:        excel_data_extractor.py
AUTHOR:         GitHub Copilot
DESCRIPTION:    Extrahiert Zeiterfassungsdaten aus Excel-Arbeitszeittabellen
VERSION:        2.0
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union

import openpyxl
import pandas as pd
import xlrd


class TimeSheetError(Exception):
    """Basisklasse für alle TimeSheet-spezifischen Fehler"""

    pass


class WorkbookLoadError(TimeSheetError):
    """Fehler beim Laden der Excel-Arbeitsmappe"""

    pass


class InvalidTimeFormatError(TimeSheetError):
    """Fehler bei der Zeitwert-Konvertierung"""

    pass


class AbsenceCode(Enum):
    """Abwesenheitscodes in der Excel-Tabelle"""

    HOLIDAY = "g"  # Feiertag
    VACATION = "u"  # Urlaub


# Konstanten für Datumsformate
DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M:%S"
DEFAULT_TIME = "01:00:00"


# Excel Spaltendefinitionen
@dataclass
class ExcelColumns:
    DAY: int = 1  # Spalte A: Tag
    DESC: int = 2  # Spalte B: Beschreibung/Bemerkungen
    CODE: int = 3  # Spalte C: Urlaubscode (G)
    START: int = 5  # Spalte E: Kommen
    END: int = 6  # Spalte F: Gehen
    START2: int = 7  # Spalte G: Zweites Kommen
    END2: int = 8  # Spalte H: Zweites Gehen
    HEADER_ROW: int = 4  # Zeile mit den Spaltenüberschriften


# Globale Excel-Spalten Definition
COLS = ExcelColumns()

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("timesheet.log")],
)

logger = logging.getLogger(__name__)


class TimeSheetExtractor:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.workbook = None
        self.year = self._extract_year_from_filename()

    def _extract_year_from_filename(self) -> int:
        filename = os.path.basename(self.excel_path)
        match = re.search(r"20\d{2}", filename)
        return int(match.group()) if match else datetime.now().year

    def load_workbook(self) -> bool:
        try:
            if not os.path.exists(self.excel_path):
                raise WorkbookLoadError(f"Die Datei existiert nicht: {self.excel_path}")

            if self.excel_path.endswith(".xls"):
                self.workbook = xlrd.open_workbook(self.excel_path)
            else:
                self.workbook = openpyxl.load_workbook(
                    self.excel_path, data_only=True, keep_vba=True
                )

            logger.info(f"Excel-Datei erfolgreich geladen: {self.excel_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Laden: {str(e)}")
            return False

    def _convert_excel_time(
        self, value: Union[str, datetime.time, float, None]
    ) -> Optional[str]:
        """Konvertiert verschiedene Zeitformate in String-Format HH:MM:SS

        Args:
            value: Zeit als String, datetime.time oder Excel-Float

        Returns:
            Formatierte Zeit oder None bei ungültigem Wert
        """
        if value is None:
            return None

        # Wenn bereits datetime.time, direkt formatieren
        if isinstance(value, time):
            if value == time(0, 0, 0):  # Prüfe auf 00:00:00
                return None
            return value.strftime("%H:%M:%S")

        # String parsen
        time_str = str(value)

        # Wenn der String schon das richtige Format hat und nicht 00:00:00 ist
        if isinstance(value, str) and ":" in time_str and time_str != "00:00:00":
            return time_str
        if value is None:
            return None

        try:
            # String-Verarbeitung
            if isinstance(value, str):
                # Entferne eventuelle Leerzeichen
                value = value.strip()
                if not value:
                    return None
                return self._parse_time_string(value)

            # Float-Verarbeitung (Excel Zeitformat)
            elif isinstance(value, float):
                # Prüfe ob der Wert im gültigen Bereich liegt (0-1 für Excel-Zeiten)
                if 0 <= value <= 1:
                    return self._convert_excel_float_to_time(value)
                # Prüfe ob es sich um einen Timestamp handelt
                elif value > 1:
                    try:
                        # Excel-Timestamp zu Python datetime
                        dt = datetime(1899, 12, 30) + timedelta(days=value)
                        return dt.strftime(TIME_FORMAT)
                    except:
                        return None

            # Datetime-Objekt
            elif isinstance(value, datetime):
                return value.strftime(TIME_FORMAT)

            # Time-Objekt
            elif isinstance(value, time):
                return value.strftime(TIME_FORMAT)

        except Exception as e:
            logger.debug(
                f"Fehler bei der Zeitkonvertierung: {str(e)} für Wert: {value} ({type(value)})"
            )
            return None

        return None

    def _parse_time_string(self, time_str: str) -> Optional[str]:
        if ":" not in time_str:
            return None

        parts = time_str.split(":")
        if len(parts) < 2:
            return None

        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0

            if not (0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60):
                return None

            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except ValueError:
            return None

    def _convert_excel_float_to_time(self, excel_time: float) -> Optional[str]:
        """Konvertiert Excel-Zeitwert (Dezimalbruch eines Tages) in Zeitstring

        Args:
            excel_time: Excel-Zeitwert zwischen 0 und 1

        Returns:
            Formatierte Zeit oder None bei ungültigem Wert
        """
        try:
            # Excel speichert Zeiten als Dezimalbruch eines Tages
            if not (0 <= excel_time <= 1):
                logger.debug(
                    f"Excel-Zeit außerhalb des gültigen Bereichs: {excel_time}"
                )
                return None

            # Konvertiere in Sekunden und runde
            total_seconds = round(excel_time * 24 * 3600)

            # Berechne Stunden, Minuten und Sekunden
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # Validiere die Werte
            if hours >= 24:
                logger.debug(f"Ungültiger Stundenwert: {hours}")
                return None

            if not (0 <= minutes < 60 and 0 <= seconds < 60):
                logger.debug(f"Ungültige Minuten/Sekunden: {minutes}:{seconds}")
                return None

            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        except Exception as e:
            logger.debug(
                f"Fehler bei Excel-Zeitkonvertierung: {str(e)} für Wert {excel_time}"
            )
            return None

    def _get_day_from_row(self, sheet, row: int, is_xls: bool) -> Optional[int]:
        """Extrahiert die Tagesnummer aus der ersten Spalte der Excel-Tabelle"""
        try:
            # Hole den Wert aus der ersten Spalte (A)
            day_value = (
                sheet.cell_value(row, COLS.DAY - 1)
                if is_xls
                else sheet.cell(row=row, column=COLS.DAY).value
            )

            # Konvertiere zu String und entferne Whitespace
            if day_value is not None:
                # Konvertiere numerische Werte direkt zu int
                if isinstance(day_value, (int, float)):
                    day = int(day_value)
                    if 1 <= day <= 31:
                        return day
                # Behandle String-Werte
                else:
                    day_str = str(day_value).strip()

                    # Versuche Datumswert zu extrahieren (Format: "YYYY-MM-DD HH:MM:SS")
                    date_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", day_str)
                    if date_match:
                        day = int(date_match.group(3))
                        if 1 <= day <= 31:
                            return day

                    # Versuche numerischen Wert zu extrahieren
                    num_match = re.match(r"^(\d+)", day_str)
                    if num_match:
                        day = int(num_match.group(1))
                        if 1 <= day <= 31:
                            return day

            logger.debug(f"Ungültiger Tag in Spalte A, Zeile {row}: {day_value}")
            return None
        except:
            return None

    def _validate_date(self, day: int, month: int, year: int) -> bool:
        """Prüft ob das Datum gültig ist"""
        try:
            datetime(year, month, day)
            return True
        except ValueError:
            logger.debug(f"Ungültiges Datum: {day}.{month}.{year}")
            return False

    def _process_row(
        self,
        sheet: Union[xlrd.sheet.Sheet, openpyxl.worksheet.worksheet.Worksheet],
        row: int,
        month: int,
        is_xls: bool = False,
    ) -> Optional[Dict[str, str]]:
        try:
            # Hole den Tag aus der Excel-Tabelle
            day = self._get_day_from_row(sheet, row, is_xls)
            if not day:
                logger.debug(f"Kein gültiger Tag in Zeile {row} gefunden")
                return None

            # Validiere das Datum
            if not self._validate_date(day, month, self.year):
                return None

            if is_xls:
                start = sheet.cell_value(row, COLS.START - 1)
                end = sheet.cell_value(row, COLS.END - 1)
                start2 = sheet.cell_value(row, COLS.START2 - 1)
                end2 = sheet.cell_value(row, COLS.END2 - 1)
                desc = sheet.cell_value(row, COLS.DESC - 1)
                code = sheet.cell_value(row, COLS.CODE - 1)
            else:
                start = sheet.cell(row=row, column=COLS.START).value
                end = sheet.cell(row=row, column=COLS.END).value
                start2 = sheet.cell(row=row, column=COLS.START2).value
                end2 = sheet.cell(row=row, column=COLS.END2).value
                desc = sheet.cell(row=row, column=COLS.DESC).value
                code = sheet.cell(row=row, column=COLS.CODE).value

            # Debug logging
            logger.debug(
                f"Verarbeite Zeile {row}: Start={start}, End={end}, Start2={start2}, End2={end2}, Code={code}"
            )

            # Prüfe ob es sich um einen Feiertag oder Urlaub handelt
            if code and str(code).lower() in [
                AbsenceCode.HOLIDAY.value,
                AbsenceCode.VACATION.value,
            ]:
                logger.debug(f"Zeile {row} ist Urlaub/Feiertag: {code}")
                return None

            try:
                date = datetime(self.year, month, day)
            except ValueError:
                logger.debug(f"Ungültiges Datum: {day}.{month}.{self.year}")
                return None

            # Verarbeite erstes Zeitpaar
            start_str = self._convert_excel_time(start)

            if not start_str or start_str == "00:00:00":
                logger.debug(
                    f"Kein gültiger Startzeitwert oder Startzeit ist 00:00:00 in Zeile {row}"
                )
                return None

            # Verarbeite End-Zeit mit Debug-Ausgaben
            logger.debug(f"Rohe Endzeit 1: {end} (Typ: {type(end)})")
            logger.debug(f"Rohe Endzeit 2: {end2} (Typ: {type(end2)})")

            # Prüfe erst end2 (spätere Zeit hat Vorrang)
            end_str2 = self._convert_excel_time(end2)
            end_str = self._convert_excel_time(end)
            final_end = None

            # Bestimme die finale Endzeit
            if end_str2 and end_str2 != DEFAULT_TIME:
                final_end = end_str2
            elif (
                isinstance(end, str) and end != DEFAULT_TIME and ":" in end
            ):  # Direkte Verwendung des String-Formats
                final_end = end
            elif end_str and end_str != DEFAULT_TIME:
                final_end = end_str

            logger.debug(f"Konvertierte Endzeit 1: {end_str}")
            logger.debug(f"Konvertierte Endzeit 2: {end_str2}")

            # Wenn keine Endzeit gefunden, prüfe ob es eine zweite Startzeit gibt
            if not final_end:
                start_str2 = self._convert_excel_time(start2)
                if start_str2 and start_str2 != DEFAULT_TIME:
                    final_end = start_str2

            # Erstelle den Eintrag
            entry = {
                "Date": date.strftime(DATE_FORMAT),
                "Start": start_str,
                "End": (
                    final_end if final_end else DEFAULT_TIME
                ),  # Verwende DEFAULT_TIME wenn keine gültige Zeit gefunden
                "Remark": str(desc) if desc else "",
            }

            # Debug-Logging für Zeitwerte
            logger.debug(
                f"Finale Zeiten für {date.strftime(DATE_FORMAT)}: Start={start_str}, End={final_end}"
            )

            return entry

        except Exception as e:
            logger.debug(f"Fehler in Zeile {row}: {str(e)}")
            return None

    def extract_sheet_data(
        self, sheet: Union[xlrd.sheet.Sheet, openpyxl.worksheet.worksheet.Worksheet]
    ) -> List[Dict[str, str]]:
        data = []
        is_xls = isinstance(sheet, xlrd.sheet.Sheet)
        sheet_name = sheet.name if is_xls else sheet.title

        logger.info(f"Verarbeite Sheet: {sheet_name}")

        current_month = self._get_current_month(sheet)
        if not current_month:
            logger.warning(
                f"Konnte Monat nicht aus Sheet-Namen ermitteln: {sheet_name}"
            )
            return []

        logger.info(f"Erkannter Monat: {current_month}")

        # Bestimme Start- und Endzeile
        start_row = COLS.HEADER_ROW + 1
        max_row = sheet.nrows if is_xls else sheet.max_row

        # Verarbeite jede Zeile
        empty_days = 0

        for row in range(start_row, max_row + 1):
            entry = self._process_row(sheet, row, current_month, is_xls)

            if entry:
                data.append(entry)
                empty_days = 0
            else:
                # Hole den Code-Wert für die aktuelle Zeile
                code = (
                    sheet.cell_value(row, COLS.CODE - 1)
                    if is_xls
                    else sheet.cell(row=row, column=COLS.CODE).value
                )

                if code and str(code).lower() in [
                    AbsenceCode.HOLIDAY.value,
                    AbsenceCode.VACATION.value,
                ]:
                    empty_days = 0

        return data

    def _get_current_month(self, sheet) -> Optional[int]:
        name = sheet.name if isinstance(sheet, xlrd.sheet.Sheet) else sheet.title

        month_map = {
            "jan": 1,
            "januar": 1,
            "feb": 2,
            "februar": 2,
            "mär": 3,
            "märz": 3,
            "mar": 3,
            "apr": 4,
            "april": 4,
            "mai": 5,
            "jun": 6,
            "juni": 6,
            "jul": 7,
            "juli": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "sept": 9,
            "september": 9,
            "okt": 10,
            "oktober": 10,
            "nov": 11,
            "november": 11,
            "dez": 12,
            "dezember": 12,
        }

        name = name.lower()

        for month_pattern, month_num in month_map.items():
            if month_pattern in name:
                return month_num

        if name.isdigit() and 1 <= int(name) <= 12:
            return int(name)

        return None

    def extract_all_data(self):
        if not self.workbook:
            logger.error("Keine Excel-Datei geladen")
            return []

        all_data = []

        sheets = (
            [self.workbook.sheet_by_index(i) for i in range(self.workbook.nsheets)]
            if isinstance(self.workbook, xlrd.book.Book)
            else self.workbook.worksheets
        )

        for sheet in sheets:
            sheet_name = (
                sheet.name if isinstance(sheet, xlrd.sheet.Sheet) else sheet.title
            )
            if any(
                sheet_name.lower().startswith(m)
                for m in [
                    "jan",
                    "feb",
                    "mär",
                    "apr",
                    "mai",
                    "jun",
                    "jul",
                    "aug",
                    "sep",
                    "okt",
                    "nov",
                    "dez",
                ]
            ):
                sheet_data = self.extract_sheet_data(sheet)
                all_data.extend(sheet_data)

        return all_data

    def export_to_csv(self, output_path):
        try:
            data = self.extract_all_data()

            if not data:
                logger.error("Keine Daten zum Exportieren")
                return False

            df = pd.DataFrame(data)
            columns = ["Date", "Start", "End", "Remark"]
            df = df[columns]

            df["Date"] = pd.to_datetime(df["Date"], format=DATE_FORMAT)
            df = df.sort_values("Date")
            df["Date"] = df["Date"].dt.strftime(DATE_FORMAT)

            df.to_csv(output_path, index=False, encoding="utf-8")

            logger.info(f"Daten exportiert nach: {output_path}")
            logger.info(f"Gesamt: {len(df)} Einträge")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Export: {str(e)}")
            return False


def main():
    excel_path = "/workspaces/TimeSheet/sup/2025_FDTech_Dennis_Hartel.xlsm"
    output_csv = "/workspaces/TimeSheet/sup/2025_extract.csv"

    extractor = TimeSheetExtractor(excel_path)
    if extractor.load_workbook():
        if extractor.export_to_csv(output_csv):
            logger.info(f"Export erfolgreich: {output_csv}")
        else:
            logger.error("Export fehlgeschlagen!")


if __name__ == "__main__":
    main()
