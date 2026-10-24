"""Reject plausible-looking exports that no longer match their source/evaluation."""
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from validate import validate


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / 'output'
        shutil.copytree(ROOT / 'powerbi/data', self.output)
        self.database = Path(self.tmp.name) / 'source.sqlite'
        with sqlite3.connect(self.database) as db:
            for filename, table, drop in [
                ('monthly_demand.csv', 'national_monthly', ['month_number', 'year', 'admissions_yoy_pct', 'attendances_yoy_pct']),
                ('quarterly_beds.csv', 'national_beds_quarterly', []),
                ('trust_beds_2026q2.csv', 'trust_bed_snapshot', []),
            ]:
                frame = pd.read_csv(self.output / filename).drop(columns=drop)
                frame.to_sql(table, db, index=False)

    def change(self, filename, column, value, row=0):
        path = self.output / filename
        frame = pd.read_csv(path)
        frame.loc[row, column] = value
        frame.to_csv(path, index=False)

    def test_valid_snapshot(self):
        self.assertEqual(validate(self.database, self.output)['backtest_months'], 24)

    def test_altered_historical_count(self):
        self.change('monthly_demand.csv', 'dta_wait_over_12h', 1)
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_backtest_dates_must_match_holdout(self):
        self.change('admissions_forecast_backtest.csv', 'month', '1900-01-01')
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_backtest_actuals_must_match_source(self):
        path = self.output / 'admissions_forecast_backtest.csv'
        frame = pd.read_csv(path)
        frame['actual_admissions'] += 100
        frame.to_csv(path, index=False)
        # Keep the aggregate errors internally consistent to expose source mismatch.
        self.change('admissions_forecast_summary.csv', 'baseline_mae', abs(frame.actual_admissions-frame.seasonal_baseline).mean())
        self.change('admissions_forecast_summary.csv', 'model_mae', abs(frame.actual_admissions-frame.model_forecast).mean())
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_false_baseline_with_consistent_mae(self):
        path = self.output / 'admissions_forecast_backtest.csv'
        frame = pd.read_csv(path)
        frame['seasonal_baseline'] += 100
        frame.to_csv(path, index=False)
        self.change('admissions_forecast_summary.csv', 'baseline_mae', abs(frame.actual_admissions-frame.seasonal_baseline).mean())
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_wrong_split_metadata(self):
        self.change('admissions_forecast_summary.csv', 'training_end', '2026-08-01')
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_wrong_preferred_forecast(self):
        self.change('admissions_forecast_summary.csv', 'preferred_next_month_forecast', 1)
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_missing_model_predictions_cannot_be_skipped_by_mean(self):
        self.change('admissions_forecast_backtest.csv', 'model_forecast', float('nan'))
        frame = pd.read_csv(self.output / 'admissions_forecast_backtest.csv')
        self.change('admissions_forecast_summary.csv', 'model_mae', abs(frame.actual_admissions-frame.model_forecast).mean())
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_trust_occupancy_must_be_recomputed(self):
        self.change('trust_beds_2026q2.csv', 'occupancy_pct', 1)
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_all_headlines_reconcile(self):
        self.change('source_summary.csv', 'dta_wait_over_12h_latest_month', 1)
        with self.assertRaises(AssertionError):
            validate(self.database, self.output)

    def test_snapshot_drift(self):
        snapshot = Path(self.tmp.name) / 'snapshot'
        shutil.copytree(self.output, snapshot)
        path = snapshot / 'admissions_forecast_summary.csv'
        frame = pd.read_csv(path)
        frame.loc[0, 'next_month_model'] += 100
        frame.to_csv(path, index=False)
        with self.assertRaises(AssertionError):
            validate(self.database, self.output, snapshot=snapshot)


if __name__ == '__main__':
    unittest.main()
