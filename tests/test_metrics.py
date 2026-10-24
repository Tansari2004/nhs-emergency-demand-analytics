import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from forecast import make_features, run_forecast  # noqa: E402


class ForecastTests(unittest.TestCase):
    def test_features_do_not_use_target_month(self):
        dates = pd.date_range("2016-01-01", periods=60, freq="MS")
        series = pd.Series(np.arange(60), index=dates)
        features = make_features(series)
        target = dates[-1]
        self.assertEqual(features.loc[target, "lag_1"], 58)
        self.assertEqual(features.loc[target, "lag_12"], 47)
        self.assertEqual(features.loc[target, "rolling_3"], 57)

    def test_invalid_counts_are_rejected(self):
        dates = pd.date_range("2016-02-01", "2026-08-01", freq="MS")
        for bad in (-1, float("inf"), float("nan"), 1.5):
            series = pd.Series(450000.0, index=dates)
            series.iloc[0] = bad
            with self.subTest(value=bad), self.assertRaises(ValueError):
                run_forecast(series)
        with self.assertRaises(ValueError):
            run_forecast(pd.Series([], index=pd.DatetimeIndex([]), dtype=float))

    def test_future_values_do_not_change_earlier_features(self):
        dates = pd.date_range("2016-01-01", periods=60, freq="MS")
        series = pd.Series(100.0, index=dates)
        before = make_features(series)
        series.iloc[-2:] = 999999
        after = make_features(series)
        pd.testing.assert_frame_equal(before.iloc[:-2], after.iloc[:-2])

    def test_forecast_uses_chronological_holdout_and_refits(self):
        dates = pd.date_range("2016-02-01", "2026-08-01", freq="MS")
        series = pd.Series(450000 + 1000 * dates.month + np.arange(len(dates)) * 30, index=dates)
        backtest, summary = run_forecast(series)
        self.assertEqual(summary["training_end"], "2024-08-01")
        self.assertEqual(summary["test_start"], "2024-09-01")
        self.assertEqual(summary["final_training_end"], "2026-08-01")
        self.assertEqual(summary["forecast_month"], "2026-09-01")
        self.assertEqual(len(backtest), 24)
        self.assertEqual(summary["next_month_baseline"], series.loc["2025-09-01"])


if __name__ == "__main__":
    unittest.main()
