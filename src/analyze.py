"""Export SQL-based NHS demand and capacity tables for Power BI."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main(database: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as db:
        db.executescript((ROOT / "sql/analytics.sql").read_text())
        monthly = pd.read_sql_query("SELECT * FROM monthly_pressure ORDER BY month", db)
        beds = pd.read_sql_query("SELECT * FROM quarterly_beds ORDER BY quarter_end", db)
        trusts = pd.read_sql_query(
            "SELECT * FROM trust_bed_snapshot ORDER BY occupancy_pct DESC", db
        )
    monthly["month_number"] = pd.to_datetime(monthly.month).dt.month
    monthly["year"] = pd.to_datetime(monthly.month).dt.year
    monthly["admissions_yoy_pct"] = (
        100 * (monthly.total_emergency_admissions / monthly.total_emergency_admissions.shift(12) - 1)
    )
    monthly["attendances_yoy_pct"] = (
        100 * (monthly.total_attendances / monthly.total_attendances.shift(12) - 1)
    )
    monthly.to_csv(output / "monthly_demand.csv", index=False)
    beds.to_csv(output / "quarterly_beds.csv", index=False)
    trusts.to_csv(output / "trust_beds_2026q2.csv", index=False)
    summary = pd.DataFrame([{
        "demand_first_month": monthly.month.min(),
        "demand_last_month": monthly.month.max(),
        "demand_months": len(monthly),
        "total_emergency_admissions_latest_month": int(monthly.total_emergency_admissions.iloc[-1]),
        "dta_wait_over_4h_latest_month": int(monthly.dta_wait_over_4h.iloc[-1]),
        "dta_wait_over_12h_latest_month": int(monthly.dta_wait_over_12h.iloc[-1]),
        "historical_beds_last_quarter": beds.quarter_end.max(),
        "latest_bed_snapshot_quarter": trusts.quarter_end.iloc[0],
        "latest_general_acute_occupancy_pct": 100 * trusts.occupied_beds.sum() / trusts.available_beds.sum(),
        "trusts_with_general_acute_beds": len(trusts),
    }])
    summary.to_csv(output / "source_summary.csv", index=False)
    print(summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/nhs.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/powerbi")
    args = parser.parse_args()
    main(args.database, args.output)
