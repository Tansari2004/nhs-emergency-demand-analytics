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


def compare_frames(actual: pd.DataFrame, expected: pd.DataFrame, label: str) -> None:
    """Compare all values, with only CSV floating-point round-trip tolerance."""
    try:
        pd.testing.assert_frame_equal(actual.reset_index(drop=True), expected.reset_index(drop=True),
                                      check_dtype=False, check_exact=False, rtol=0, atol=1e-7)
    except AssertionError as exc:
        raise AssertionError(f"{label} differs from its reference: {exc}") from exc


def validate(database: Path, output: Path, snapshot: Path | None = None) -> dict:
    missing = [name for name in FILES if not (output / name).is_file()]
    if missing:
        raise AssertionError(f"Missing exports: {missing}")
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as db:
        source_months = db.execute("SELECT COUNT(*) FROM national_monthly").fetchone()[0]
        source_quarters = db.execute("SELECT COUNT(*) FROM national_beds_quarterly").fetchone()[0]
        source_trusts = db.execute("SELECT COUNT(*) FROM trust_bed_snapshot").fetchone()[0]
        sources = {
            "monthly_demand.csv": (pd.read_sql_query("SELECT * FROM national_monthly ORDER BY month", db, parse_dates=["month"]), "month"),
            "quarterly_beds.csv": (pd.read_sql_query("SELECT * FROM national_beds_quarterly ORDER BY quarter_end", db, parse_dates=["quarter_end"]), "quarter_end"),
            "trust_beds_2026q2.csv": (pd.read_sql_query("SELECT * FROM trust_bed_snapshot ORDER BY organisation_code", db), "organisation_code"),
        }
    monthly = pd.read_csv(output / "monthly_demand.csv", parse_dates=["month"])
    beds = pd.read_csv(output / "quarterly_beds.csv", parse_dates=["quarter_end"])
    trusts = pd.read_csv(output / "trust_beds_2026q2.csv")
    headlines = pd.read_csv(output / "source_summary.csv")
    if len(headlines) != 1:
        raise AssertionError("Expected one source summary row")
    summary = headlines.iloc[0]
    backtest = pd.read_csv(output / "admissions_forecast_backtest.csv", parse_dates=["month"])
    forecasts = pd.read_csv(output / "admissions_forecast_summary.csv")
    if len(forecasts) != 1:
        raise AssertionError("Expected one forecast summary row")
    forecast = forecasts.iloc[0]
    for name, frame in [("monthly", monthly.drop(columns=["admissions_yoy_pct", "attendances_yoy_pct"])),
                        ("beds", beds), ("trusts", trusts), ("headlines", headlines),
                        ("backtest", backtest), ("forecast", forecasts)]:
        if frame.isna().any().any() or not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
            raise AssertionError(f"Missing or nonfinite {name} values")
    for filename, frame in [("monthly_demand.csv", monthly), ("quarterly_beds.csv", beds),
                            ("trust_beds_2026q2.csv", trusts)]:
        source, key = sources[filename]
        compare_frames(frame.sort_values(key)[source.columns], source, filename)
    for value, total in [("admissions_yoy_pct", "total_emergency_admissions"),
                         ("attendances_yoy_pct", "total_attendances")]:
        expected = 100 * (monthly[total] / monthly[total].shift(12) - 1)
        if not np.allclose(monthly[value], expected, rtol=0, atol=1e-7, equal_nan=True):
            raise AssertionError(f"Incorrect {value}")
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
    expected_test = pd.date_range("2024-09-01", "2026-08-01", freq="MS")
    if not backtest.month.equals(pd.Series(expected_test, name="month")):
        raise AssertionError("Backtest dates differ from the chronological holdout")
    indexed = monthly.set_index("month").total_emergency_admissions
    if not np.array_equal(backtest.actual_admissions, indexed.loc[expected_test]):
        raise AssertionError("Backtest actual admissions differ from source months")
    if not np.array_equal(backtest.seasonal_baseline, indexed.loc[expected_test - pd.DateOffset(years=1)]):
        raise AssertionError("Seasonal baseline differs from same month last year")
    if (backtest[["actual_admissions", "seasonal_baseline", "model_forecast"]] < 0).any().any():
        raise AssertionError("Negative admissions or forecasts")
    expected_metadata = {"training_end": "2024-08-01", "test_start": "2024-09-01",
                         "test_end": "2026-08-01", "test_months": 24,
                         "next_month_baseline": indexed.loc["2025-09-01"]}
    if any(forecast[key] != value for key, value in expected_metadata.items()):
        raise AssertionError("Incorrect forecast split or next seasonal baseline")
    preferred = "seasonal_baseline" if forecast.baseline_mae <= forecast.model_mae else "random_forest"
    preferred_value = forecast.next_month_baseline if preferred == "seasonal_baseline" else forecast.next_month_model
    if forecast.preferred_method != preferred or forecast.preferred_next_month_forecast != preferred_value:
        raise AssertionError("Preferred forecast does not match lower-MAE method")
    if not np.isclose(abs(backtest.actual_admissions - backtest.seasonal_baseline).mean(), forecast.baseline_mae, rtol=0, atol=0.051):
        raise AssertionError("Baseline MAE does not match backtest")
    if not np.isclose(abs(backtest.actual_admissions - backtest.model_forecast).mean(), forecast.model_mae, rtol=0, atol=0.051):
        raise AssertionError("Model MAE does not match backtest")
    if int(summary.total_emergency_admissions_latest_month) != int(monthly.total_emergency_admissions.iloc[-1]):
        raise AssertionError("Headline admission count does not match")
    expected_headlines = {
        "demand_first_month": "2016-02-01", "demand_last_month": "2026-08-01", "demand_months": 127,
        "total_emergency_admissions_latest_month": monthly.total_emergency_admissions.iloc[-1],
        "dta_wait_over_4h_latest_month": monthly.dta_wait_over_4h.iloc[-1],
        "dta_wait_over_12h_latest_month": monthly.dta_wait_over_12h.iloc[-1],
        "historical_beds_last_quarter": "2026-06-30", "latest_bed_snapshot_quarter": "2026-06-30",
        "latest_general_acute_occupancy_pct": 100 * trusts.occupied_beds.sum() / trusts.available_beds.sum(),
        "trusts_with_general_acute_beds": 153,
    }
    for key, expected in expected_headlines.items():
        valid = summary[key] == expected if isinstance(expected, str) else np.isclose(summary[key], expected, rtol=0, atol=1e-7)
        if not valid:
            raise AssertionError(f"Source summary {key} does not match")
    if snapshot is not None:
        for name in FILES:
            compare_frames(pd.read_csv(output / name), pd.read_csv(snapshot / name), f"Published snapshot {name}")
    return {"demand_months": len(monthly), "capacity_quarters": len(beds), "trusts": len(trusts), "backtest_months": len(backtest)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT / "data/processed/nhs.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/powerbi")
    parser.add_argument("--snapshot", type=Path, help="Also reconcile checked-in report CSVs against rebuilt outputs")
    args = parser.parse_args()
    print("Validation passed:", validate(args.database, args.output, snapshot=args.snapshot))
