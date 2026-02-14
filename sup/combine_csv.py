import os

import pandas as pd

# Dateipfade
csv_files = [
    "/workspaces/TimeSheet/sup/2023_extract.csv",
    "/workspaces/TimeSheet/sup/2024_extract.csv",
    "/workspaces/TimeSheet/sup/2025_extract.csv",
    "/workspaces/TimeSheet/sup/fdtech_timelog_2.csv",
]

# Leere Liste für DataFrames
dfs = []

# Lese jede CSV-Datei
for file in csv_files:
    if os.path.exists(file):
        # Lese CSV ohne quote character
        df = pd.read_csv(file, quoting=3)  # QUOTE_NONE

        # Standardisiere die Spaltenamen
        if "Remark" in df.columns:
            df.rename(columns={"Remark": "Remark (!! only one line !!)"}, inplace=True)

        # Stelle sicher, dass die Remark-Spalte existiert
        if "Remark (!! only one line !!)" not in df.columns:
            df["Remark (!! only one line !!)"] = '""'

        # Behandle leere Werte und NaN
        df["Remark (!! only one line !!)"] = df["Remark (!! only one line !!)"].fillna(
            '""'
        )

        # Konvertiere das Datum
        df["Date"] = pd.to_datetime(df["Date"], format="%d.%m.%Y", dayfirst=True)
        dfs.append(df)

# Kombiniere alle DataFrames
combined_df = pd.concat(dfs, ignore_index=True)

# Sortiere nach Datum aufsteigend
combined_df = combined_df.sort_values("Date")

# Konvertiere das Datum zurück in das deutsche Format
combined_df["Date"] = combined_df["Date"].dt.strftime("%d.%m.%Y")

# Speichere das Ergebnis ohne quote character
combined_df.to_csv(
    "/workspaces/TimeSheet/sup/timelog_all.csv", index=False, quoting=3
)  # QUOTE_NONE
print("Kombinierte CSV-Datei wurde erstellt!")
