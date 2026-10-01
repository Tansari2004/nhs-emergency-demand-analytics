"""Load published NHS England aggregate statistics into SQLite."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "nhs-ae-monthly-aug-2026.xls": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/09/Monthly-AE-Time-Series-August-2026-YG43sd.xls",
        "267d1983202388e5ac5a913cf3ac0ff9100103603b771ac99f2aa543c1bb8f7a",
    ),
    "kh03-available-overnight.csv": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/09/KH03-Available-Overnight-only.csv",
        "de58388b736d555b122a764cbad79524d27476fe50a4071f85e8ce19a7fd1147",
    ),
    "kh03-occupied-overnight.csv": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/09/KH03-Occupied-Overnight-only.csv",
        "d00891eacbee972fd8def2e43dda4a2e01e37af20b957a395e1b386aa84a8bc6",
    ),
    "kh03-2026q2-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/08/NHS-organisations-in-England-Quarter-1-2026-27-Overnight.xlsx",
        "aa467766825324802649b75c2ea4a842282281dcf28951e95556a2dcaf7f0a2f",
    ),
    "kh03-2024q3-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/11/Beds-Open-Overnight-Web_File-Q2-2024-25.xlsx",
        "a049f5469d0be4c2794b231b8a986780ceee24e723939ed3f308ae077c99a281",
    ),
    "kh03-2024q4-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/Beds-Open-Overnight-Web_File-Q3-2024-25-revised.xlsx",
        "af3f561ce0d0d87bbdce5f58dced1e32c16485c4727ccad51bdc7a10906d349f",
    ),
    "kh03-2025q1-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/05/Beds-Open-Overnight-Web_File-Q4-2024-25.xlsx",
        "b46bc0379b52d2462de779b17bb679db0c08cc0a8960e43c6dd06ee4481dc7b8",
    ),
    "kh03-2025q2-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/Beds-Open-Overnight-Web_File-Q1-2025-26-revised.xlsx",
        "d104ef32c376d379b55d740c31bc5e5692af6cb60a073a233170e0f53716b5f1",
    ),
    "kh03-2025q3-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/11/Beds-Open-Overnight-Web_File-Q2-2025-26.xlsx",
        "466336afe00cde2c67eed898d5163c861b5d0f0a85bda49467229a863fd2fe2b",
    ),
    "kh03-2025q4-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Beds-Open-Overnight-Web_File-Q3-2025-26.xlsx",
        "cd6e7b001243d652d046715b11615f9ac0ca0c5b58f15d2c7149c3884bf61527",
    ),
    "kh03-2026q1-overnight.xlsx": (
        "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Beds-Open-Overnight-Web_File-Q4-2025-26.xlsx",
        "6be516436644adbff1f3f3ead64df1c33e62bfc5559daeb7fc4a7eeafad845e7",
    ),
}


def get_sources(raw: Path) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    for name, (url, expected_hash) in SOURCES.items():
        path = raw / name
        if not path.exists():
            subprocess.run(["curl", "-L", "--fail", "--silent", "--show-error", url, "-o", str(path)], check=True)
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"Source hash mismatch: {name}; check the NHS publication for a revision")


def parse_activity(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Activity", header=None)
    expected = {1: "Period", 5: "Total Attendances", 9: "Total Emergency Admissions via A&E",
                10: "Other Emergency Admissions (i.e not via A&E)", 11: "Total Emergency Admissions"}
    if any(raw.iat[13, col] != label for col, label in expected.items()):
        raise ValueError("NHS activity workbook layout changed")
    frame = raw.iloc[14:, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]].copy()
    frame.columns = ["month", "type1_attendances", "type2_attendances", "type3_attendances",
                     "total_attendances", "type1_admissions", "type2_admissions",
                     "type3_admissions", "ae_admissions", "other_emergency_admissions",
                     "total_emergency_admissions", "dta_wait_over_4h", "dta_wait_over_12h"]
    frame["month"] = pd.to_datetime(frame.month, errors="coerce")
    # Several earlier workbook rows contain estimated fractional attendances.
    # This reporting window contains whole-number published monthly counts.
    frame = frame.loc[frame.month.between("2016-02-01", "2026-08-01")].copy()
    for col in frame.columns.drop("month"):
        frame[col] = pd.to_numeric(frame[col], errors="raise")
        if frame[col].isna().any() or (frame[col] < 0).any() or not ((frame[col] - frame[col].round()).abs() < 1e-6).all():
            raise ValueError(f"Unexpected non-count value in {col}")
        frame[col] = frame[col].astype("int64")
    frame["month"] = frame.month.dt.strftime("%Y-%m-%d")
    if frame.month.duplicated().any() or len(frame) != 127:
        raise ValueError("Unexpected NHS monthly coverage")
    return frame


def parse_kh03_csv(path: Path, measure: str) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str).dropna(subset=["Organisation_Code", "Sector", "Effective_Snapshot_Date"])
    frame = frame.loc[frame.Sector == "General & Acute"].copy()
    frame["quarter_end"] = pd.to_datetime(frame.Effective_Snapshot_Date, dayfirst=True, errors="raise")
    frame[measure] = pd.to_numeric(frame.Number_Of_Beds.str.replace(",", "", regex=False), errors="raise")
    frame = frame.loc[frame.quarter_end.between("2015-06-30", "2024-06-30")]
    if frame.duplicated(["Organisation_Code", "quarter_end"]).any():
        raise ValueError(f"Duplicate KH03 {measure} provider-quarter")
    return frame[["Organisation_Code", "quarter_end", measure]]


def parse_bed_history(available: Path, occupied: Path, recent: list[Path]) -> pd.DataFrame:
    left = parse_kh03_csv(available, "available_beds")
    right = parse_kh03_csv(occupied, "occupied_beds")
    joined = left.merge(right, on=["Organisation_Code", "quarter_end"], validate="one_to_one")
    if len(joined) != len(left) or len(joined) != len(right):
        raise ValueError("KH03 available and occupied providers do not match")
    national = joined.groupby("quarter_end", as_index=False).agg(
        available_beds=("available_beds", "sum"), occupied_beds=("occupied_beds", "sum"),
        reporting_organisations=("Organisation_Code", "size"),
    )
    national["occupancy_pct"] = 100 * national.occupied_beds / national.available_beds
    national["quarter_end"] = national.quarter_end.dt.strftime("%Y-%m-%d")
    recent_rows = []
    for path in recent:
        raw = pd.read_excel(path, sheet_name="NHS Trust by Sector", header=None)
        england = raw.iloc[15]
        if england.iat[5] != "England":
            raise ValueError(f"England total row missing in {path.name}")
        quarter = path.name.split("-")[1]
        year, number = int(quarter[:4]), int(quarter[-1])
        quarter_end = pd.Period(f"{year}Q{number}", freq="Q").end_time.strftime("%Y-%m-%d")
        recent_rows.append({
            "quarter_end": quarter_end,
            "available_beds": float(england.iat[7]),
            "occupied_beds": float(england.iat[13]),
            "reporting_organisations": int(raw.iloc[17:, 4].notna().sum()),
            "occupancy_pct": 100 * float(england.iat[13]) / float(england.iat[7]),
        })
    combined = pd.concat([national, pd.DataFrame(recent_rows)], ignore_index=True).sort_values("quarter_end")
    if combined.quarter_end.duplicated().any() or len(combined) != 45:
        raise ValueError("Unexpected quarterly bed coverage")
    return combined


def parse_latest_snapshot(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_excel(path, sheet_name="NHS Trust by Sector", header=None)
    if raw.iat[14, 4] != "Org Code" or raw.iat[14, 7] != "General & Acute":
        raise ValueError("Latest KH03 workbook layout changed")
    england = raw.iloc[15]
    if england.iat[5] != "England":
        raise ValueError("England total row missing")
    frame = raw.iloc[17:, [3, 4, 5, 7, 13]].copy()
    frame.columns = ["region_code", "organisation_code", "organisation_name", "available_beds", "occupied_beds"]
    frame = frame.dropna(subset=["organisation_code"]).copy()
    frame["available_beds"] = pd.to_numeric(frame.available_beds, errors="raise")
    frame["occupied_beds"] = pd.to_numeric(frame.occupied_beds, errors="raise")
    frame["occupancy_pct"] = 100 * frame.occupied_beds / frame.available_beds.replace(0, float("nan"))
    frame.insert(0, "quarter_end", "2026-06-30")
    frame = frame.loc[frame.available_beds > 0]
    total = {"available_beds": float(england.iat[7]), "occupied_beds": float(england.iat[13])}
    return frame, total


def main(raw: Path, database: Path) -> None:
    get_sources(raw)
    activity = parse_activity(raw / "nhs-ae-monthly-aug-2026.xls")
    recent = sorted(raw / name for name in SOURCES if name.startswith("kh03-20") and name.endswith("-overnight.xlsx"))
    beds = parse_bed_history(raw / "kh03-available-overnight.csv", raw / "kh03-occupied-overnight.csv", recent)
    snapshot, england = parse_latest_snapshot(raw / "kh03-2026q2-overnight.xlsx")
    if abs(snapshot.available_beds.sum() - england["available_beds"]) > 1 or abs(snapshot.occupied_beds.sum() - england["occupied_beds"]) > 1:
        raise ValueError("Trust bed totals do not match published England row")
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as db:
        activity.to_sql("national_monthly", db, if_exists="replace", index=False)
        beds.to_sql("national_beds_quarterly", db, if_exists="replace", index=False)
        snapshot.to_sql("trust_bed_snapshot", db, if_exists="replace", index=False)
        db.executescript("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_month ON national_monthly(month);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_quarter ON national_beds_quarterly(quarter_end);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_trust ON trust_bed_snapshot(organisation_code);
        """)
    print(f"Loaded {len(activity)} monthly demand rows, {len(beds)} capacity quarters, and {len(snapshot)} trusts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/nhs.sqlite")
    args = parser.parse_args()
    main(args.raw, args.database)
