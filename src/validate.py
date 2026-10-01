"""Reconcile published NHS source totals with dashboard and forecast exports."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FILES = ("monthly_demand.csv", "quarterly_beds.csv", "trust_beds_2026q2.csv",
         "source_summary.csv", "admissions_forecast_backtest.csv", "admissions_forecast_summary.csv")


def validate(database: Path, output: Path) -> dict:
    missing = [name for name in FILES if not (output / name).is_file()]
    if missing:
        raise AssertionError(f"Missing exports: {missing}")
    with sqlite3.connect(database) as db:
        source_months = db.execute("SELECT COUNT(*) FROM national_monthly").fetchone()[0]
        source_quarters = db.execute("SELECT COUNT(*) FROM national_beds_quarterly").fetchone()[0]
        source_trusts = db.execute("SELECT COUNT(*) FROM trust_bed_snapshot").fetchone()[0]
    monthly = pd.read_csv(output / "monthly_demand.csv", parse_dates=["month"])
    beds = pd.read_csv(output / "quarterly_beds.csv", parse_dates=["quarter_end"])
    trusts = pd.read_csv(output / "trust_beds_2026q2.csv")
    summary = pd.read_csv(output / "source_summary.csv").iloc[0]
    backtest = pd.read_csv(output / "admissions_forecast_backtest.csv", parse_dates=["month"])
    forecast = pd.read_csv(output / "admissions_forecast_summary.csv").iloc[0]
    if (source_months, source_quarters, source_trusts) != (127, 45, 153):
        raise AssertionError("Unexpected source coverage")
    if (len(monthly), len(beds), len(trusts)) != (source_months, source_quarters, source_trusts):
        raise AssertionError("Output rows differ from SQLite")
    if not monthly.month.is_unique or not monthly.month.equals(pd.Series(pd.date_range("2016-02-01", "2026-08-01", freq="MS"), name="month")):
        raise AssertionError("Missing or out-of-order demand months")
    if not beds.quarter_end.is_unique or not beds.quarter_end.equals(pd.Series(pd.date_range("2015-06-30", "2026-06-30", freq="QE"), name="quarter_end")):
        raise AssertionError("Missing or out-of-order bed quarters")
    if not (monthly.total_emergency_admissions == monthly.ae_admissions + monthly.other_emergency_admissions).all():
        raise AssertionError("Emergency admission routes do not reconcile")
    if not (monthly.ae_admissions == monthly.type1_admissions + monthly.type2_admissions + monthly.type3_admissions).all():
        raise AssertionError("A&E admission types do not reconcile")
    if not (monthly.total_attendances == monthly.type1_attendances + monthly.type2_attendances + monthly.type3_attendances).all():
        raise AssertionError("A&E attendance types do not reconcile")
    if (monthly.dta_wait_over_12h > monthly.dta_wait_over_4h).any():
        raise AssertionError("12-hour waits exceed 4-hour waits")
    if (beds.available_beds <= 0).any() or (beds.occupied_beds < 0).any():
        raise AssertionError("Invalid bed totals")
    if not np.allclose(beds.occupancy_pct, 100 * beds.occupied_beds / beds.available_beds):
        raise AssertionError("Incorrect quarterly occupancy percentage")
    if trusts.organisation_code.duplicated().any() or not (trusts.quarter_end == "2026-06-30").all():
        raise AssertionError("Invalid latest trust snapshot")
    latest = beds.iloc[-1]
    if not np.isclose(trusts.available_beds.sum(), latest.available_beds) or not np.isclose(trusts.occupied_beds.sum(), latest.occupied_beds):
        raise AssertionError("Trust beds do not reconcile to national latest quarter")
    if forecast.as_of_month != monthly.month.iloc[-1].strftime("%Y-%m-%d") or forecast.forecast_month != "2026-09-01":
        raise AssertionError("Forecast is not for the next reporting month")
    if forecast.final_training_end != forecast.as_of_month or len(backtest) != int(forecast.test_months):
        raise AssertionError("Forecast fit or backtest coverage is wrong")
    if not np.isclose(abs(backtest.actual_admissions - backtest.seasonal_baseline).mean(), forecast.baseline_mae, atol=0.1):
        raise AssertionError("Baseline MAE does not match backtest")
    if not np.isclose(abs(backtest.actual_admissions - backtest.model_forecast).mean(), forecast.model_mae, atol=0.1):
        raise AssertionError("Model MAE does not match backtest")
    if int(summary.total_emergency_admissions_latest_month) != int(monthly.total_emergency_admissions.iloc[-1]):
        raise AssertionError("Headline admission count does not match")
    return {"demand_months": len(monthly), "capacity_quarters": len(beds), "trusts": len(trusts), "backtest_months": len(backtest)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/nhs.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/powerbi")
    args = parser.parse_args()
    print("Validation passed:", validate(args.database, args.output))
