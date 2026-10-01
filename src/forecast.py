"""Evaluate a next-month national emergency-admissions forecast."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ["month_sin", "month_cos", "year", "days_in_month", "lag_1", "lag_2", "lag_3", "lag_12", "rolling_3"]
TEST_START = pd.Timestamp("2024-09-01")


def make_features(series: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"actual": series.astype(float)})
    frame["month_sin"] = np.sin(2 * np.pi * frame.index.month / 12)
    frame["month_cos"] = np.cos(2 * np.pi * frame.index.month / 12)
    frame["year"] = frame.index.year
    frame["days_in_month"] = frame.index.days_in_month
    for lag in (1, 2, 3, 12):
        frame[f"lag_{lag}"] = frame.actual.shift(lag)
    frame["rolling_3"] = frame.actual.shift(1).rolling(3).mean()
    return frame


def run_forecast(series: pd.Series) -> tuple[pd.DataFrame, dict]:
    if series.isna().any() or not series.index.equals(pd.date_range(series.index.min(), series.index.max(), freq="MS")):
        raise ValueError("Admissions must have one observation for every consecutive month")
    next_month = series.index.max() + pd.offsets.MonthBegin(1)
    extended = pd.concat([series, pd.Series([np.nan], index=[next_month])])
    frame = make_features(extended).dropna(subset=FEATURES)
    train = frame.loc[frame.index < TEST_START].dropna(subset="actual")
    test = frame.loc[frame.index >= TEST_START].dropna(subset="actual")
    if len(train) < 80 or len(test) != 24:
        raise ValueError("Unexpected chronological forecast split")
    model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=3, max_features=0.8, random_state=42, n_jobs=1
    )
    model.fit(train[FEATURES], train.actual)
    predicted = model.predict(test[FEATURES])
    baseline = test.lag_12.to_numpy()
    backtest = pd.DataFrame({
        "month": test.index.strftime("%Y-%m-%d"),
        "actual_admissions": test.actual.astype(int).to_numpy(),
        "seasonal_baseline": np.round(baseline, 1),
        "model_forecast": np.round(predicted, 1),
    })
    baseline_mae = float(mean_absolute_error(test.actual, baseline))
    model_mae = float(mean_absolute_error(test.actual, predicted))
    final_train = frame.loc[:series.index.max()].dropna(subset="actual")
    final_model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=3, max_features=0.8, random_state=42, n_jobs=1
    )
    final_model.fit(final_train[FEATURES], final_train.actual)
    next_model = float(final_model.predict(frame.loc[[next_month], FEATURES])[0])
    next_baseline = float(frame.loc[next_month, "lag_12"])
    preferred = "seasonal_baseline" if baseline_mae <= model_mae else "random_forest"
    summary = {
        "as_of_month": series.index.max().strftime("%Y-%m-%d"),
        "forecast_month": next_month.strftime("%Y-%m-%d"),
        "training_end": train.index.max().strftime("%Y-%m-%d"),
        "test_start": test.index.min().strftime("%Y-%m-%d"),
        "test_end": test.index.max().strftime("%Y-%m-%d"),
        "test_months": len(test),
        "baseline_mae": baseline_mae,
        "model_mae": model_mae,
        "final_training_end": final_train.index.max().strftime("%Y-%m-%d"),
        "next_month_baseline": next_baseline,
        "next_month_model": next_model,
        "preferred_method": preferred,
        "preferred_next_month_forecast": next_baseline if preferred == "seasonal_baseline" else next_model,
    }
    return backtest, summary


def main(source: Path, output: Path) -> None:
    monthly = pd.read_csv(source, parse_dates=["month"]).set_index("month")
    backtest, summary = run_forecast(monthly.total_emergency_admissions.asfreq("MS"))
    output.mkdir(parents=True, exist_ok=True)
    backtest.to_csv(output / "admissions_forecast_backtest.csv", index=False)
    pd.DataFrame([summary]).to_csv(output / "admissions_forecast_summary.csv", index=False)
    print(pd.DataFrame([summary]).round(2).to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs/powerbi/monthly_demand.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/powerbi")
    args = parser.parse_args()
    main(args.source, args.output)
