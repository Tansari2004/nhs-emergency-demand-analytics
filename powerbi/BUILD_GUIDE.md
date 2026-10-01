# Power BI report build guide

Run the project pipeline, then import the six CSV files from `outputs/powerbi/`. Set `month` and `quarter_end` to **Date** and all counts and bed measures to numeric types. Display **England aggregate, 2016–2026** and each metric's reporting period prominently.

Keep the monthly demand, quarterly beds, and trust snapshot tables **disconnected**. They come from different NHS collections and have different time grains and provider populations. Do not create a single shared slicer that implies a direct match between monthly admissions and quarterly beds.

## Page 1 — Emergency demand

- Cards: latest published month, total emergency admissions, A&E attendances.
- Monthly line chart: total emergency admissions, split into via-A&E and other routes.
- Monthly line chart: attendances by A&E department type.
- Year-over-year percentage chart, with pandemic and reporting-change context in a note.

## Page 2 — Admission pressure and capacity

- Monthly bars: `dta_wait_over_4h` and `dta_wait_over_12h`. Label them **counts after decision to admit**, not average waiting time.
- Quarterly line chart: general-and-acute `occupancy_pct`; show available and occupied average beds as tooltips.
- Trust table for April–June 2026: organisation, available beds, occupied beds, occupancy percentage. Filter out zero-bed trusts, as the export already does.
- State that monthly admissions and quarterly beds are separate NHS populations and cannot be combined into an admissions-per-bed rate here.

## Page 3 — Next-month admissions forecast

- Cards: as-of month, forecast month, preferred next-month forecast, seasonal baseline MAE, random-forest MAE.
- Backtest line chart: actual admissions versus both methods across September 2024–August 2026.
- Note: the preferred method is the lower-MAE **same-month-last-year baseline** for this evaluation.
- Label September 2026 as a historical as-of forecast, not today's live prediction.

Before claiming a Power BI dashboard on a resume, save the native report, check these three pages, and reconcile headline figures with `source_summary.csv` and `admissions_forecast_summary.csv`.
