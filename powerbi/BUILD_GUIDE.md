# Power BI report notes and rebuild guide

The [Power BI service report](https://app.powerbi.com/groups/me/reports/1b968d56-f28b-4835-8f77-d6d0dac681f2) has three pages. It is saved in a private workspace, so the link requires access to that workspace. The [page images](images/) and [PDF](NHS-Emergency-Demand-Capacity-Analytics.pdf) are public previews. To rebuild the report, import `monthly_demand.csv`, `quarterly_beds.csv`, `trust_beds_2026q2.csv`, `admissions_forecast_backtest.csv`, and `admissions_forecast_summary.csv` from the checked-in [`data/`](data/) snapshot or run the pipeline for fresh exports in `outputs/powerbi/`. The one-row `source_summary.csv` is for validation, not a report table. Set month and quarter-end fields to Date and counts, beds, percentages, and forecast values to numeric types.

Keep the monthly demand, quarterly beds, trust snapshot, backtest, and summary tables **disconnected**. They represent different time grains or populations. A cross-table relationship or shared slicer would imply a match the source publications do not establish.

## Emergency demand

- Line chart: `monthly_demand.month` against `total_emergency_admissions`, February 2016–August 2026.
- Line chart: `monthly_demand.month` against `dta_wait_over_12h`. These are **counts of patients waiting over 12 hours after a decision to admit**, not average ED waits.

## Bed pressure

- Line chart: `quarterly_beds.quarter_end` against `occupancy_pct` for general-and-acute overnight beds, June 2015–June 2026.
- Trust table: `organisation_name`, `available_beds`, `occupied_beds`, and `occupancy_pct` from the April–June 2026 snapshot, sorted by occupancy descending. The sum of trust occupancy percentages is meaningless, so table totals are disabled.

The admissions series and bed series are shown separately. They come from different NHS collections and populations; the report does not calculate an admissions-per-bed rate.

## Admission forecast

- Line chart: `admissions_forecast_backtest.month` against `actual_admissions`, `seasonal_baseline`, and `model_forecast` across the 24 held-out months, September 2024–August 2026.
- Cards: the preferred September 2026 forecast, baseline MAE, and random-forest MAE from `admissions_forecast_summary`.

The preferred method is the lower-MAE same-month-last-year baseline: 9,874.21 admissions per month versus 15,501.42 for the random forest. Its September 2026 forecast was **535,580 admissions as of August 2026**. This is a historical as-of forecast, not a live prediction for today's month. Power BI cards abbreviate these numbers in the current report.

The saved report was checked in reading view after the semantic model completed its refresh. Its charts display rows from the imported tables, and its three pages and metric labels were verified against the local exports.

The [three-page PDF export](NHS-Emergency-Demand-Capacity-Analytics.pdf) is a static preview. Its trust table shows only the visible top rows; the live report scrolls through the full trust snapshot.
