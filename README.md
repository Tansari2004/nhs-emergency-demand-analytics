# NHS England Emergency Demand & Capacity Analytics

An end-to-end SQL, Python, forecasting, and Power BI preparation project using **published NHS England aggregate statistics**. It studies emergency demand, long waits after a decision to admit, and general-and-acute overnight bed occupancy. The pipeline is **NHS workbooks and CSVs → SQLite → Python analysis and backtest → Power BI import tables**.

This project contains **no patient-level records**. It does not estimate individual length of stay or an individual's ED-to-ward transfer time.

## Sources and scope

| NHS England publication | Used for | Coverage in this project |
| --- | --- | --- |
| [A&E Attendances and Emergency Admissions](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/) | Monthly attendances, emergency admissions, and numbers waiting over 4 or 12 hours **after a decision to admit** | February 2016–August 2026, England total |
| [Bed Availability and Occupancy Data – Overnight](https://www.england.nhs.uk/statistics/statistical-work-areas/bed-availability-and-occupancy/bed-data-overnight/) | Average available and occupied general-and-acute beds | June 2015–June 2026, 45 calendar quarters |
| Same bed publication, Q1 2026–27 workbook | Latest trust-level general-and-acute bed snapshot | April–June 2026, 153 trusts with beds |

The monthly [A&E time-series workbook](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/09/Monthly-AE-Time-Series-August-2026-YG43sd.xls) was published 10 September 2026. The first months in that workbook include estimated fractional attendances, so the project begins with February 2016, when the selected counts are whole numbers. The bed CSVs end in June 2024; the importer continues the series with the individual [quarterly workbooks](https://www.england.nhs.uk/statistics/statistical-work-areas/bed-availability-and-occupancy/bed-data-overnight/) through June 2026. File URLs and SHA-256 hashes are pinned in `src/ingest.py` so a later NHS revision cannot silently change the reproduced results.

NHS England makes these publications available under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). The MIT licence here covers this project's original code and documentation, not NHS source files.

## Build and verify

Use Python 3.9 or newer and `curl`. From the repository directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/ingest.py
.venv/bin/python src/analyze.py
.venv/bin/python src/forecast.py
.venv/bin/python src/validate.py
.venv/bin/python -m unittest discover -s tests -v
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. The importer downloads the official files into `data/raw/` and verifies their hashes. It creates `data/processed/nhs.sqlite`; dashboard import CSVs appear in `outputs/powerbi/`. These generated files are excluded from Git. If a hash fails, review the updated NHS publication before changing the pinned version.

## Measures and limits

| Measure | What it means |
| --- | --- |
| Emergency admissions | NHS England's monthly England total, split into admissions via A&E and other emergency admissions. |
| Decision-to-admit waits over 4 or 12 hours | Number of patients crossing the stated threshold after the decision to admit. These are **counts**, not average wait times or all ED waits. |
| General-and-acute bed occupancy | Published average occupied overnight beds divided by average available overnight beds for each quarter. |
| Latest trust capacity | General-and-acute available and occupied overnight bed averages in the April–June 2026 workbook. Trust snapshots are **not** admission volumes by trust. |

The admissions time series includes NHS and independent-sector organisations, while the KH03 bed series covers NHS organisations. They have different populations and time grains and are **displayed separately**, never added together or used to calculate a combined rate. The [NHS A&E data-quality notes](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/data-quality/) describe changes in provider coverage and reporting; comparisons around the pandemic and reporting changes need care.

## Verified example results

| Result | Value |
| --- | ---: |
| Emergency admissions, August 2026 | 517,868 |
| Decision-to-admit waits over 4 hours, August 2026 | 118,550 |
| Decision-to-admit waits over 12 hours, August 2026 | 44,951 |
| General-and-acute overnight occupancy, April–June 2026 | 90.85% |

The August 2026 monthly figures and the April–June 2026 bed figures are separate reporting periods.

## Forecast evaluation

The target is **next-month England emergency admissions**. The model uses month-of-year, month length, and admissions from previous months only. A random forest is tested against a simple seasonal baseline: use the admissions count from the same month one year earlier. The first fit ends August 2024; the chronological test is September 2024–August 2026 (24 months). Each test row uses actual prior-month admissions, simulating a one-month-ahead update. After evaluation, both methods use all observations through August 2026 to forecast September 2026.

| Method | Test MAE, admissions/month |
| --- | ---: |
| Same month last year | 9,874.21 |
| Random forest | 15,501.42 |

The baseline performed better and is the preferred demonstration forecast: **535,580 emergency admissions for September 2026** as of August 2026. This is a historical as-of forecast; it is not a live prediction for the current month. MAE measures absolute forecast error; neither method is claimed to improve hospital outcomes.

## Outputs and Power BI

`outputs/powerbi/` contains `monthly_demand.csv`, `quarterly_beds.csv`, `trust_beds_2026q2.csv`, `source_summary.csv`, `admissions_forecast_backtest.csv`, and `admissions_forecast_summary.csv`. The [Power BI build guide](powerbi/BUILD_GUIDE.md) defines three report pages and metric labels. A native Power BI report has not yet been added; the dashboard claim should be made only after the actual report is built and checked against these exports.

**Accurate resume wording now:** “Analyzed NHS England emergency-admission trends, decision-to-admit delay counts, and published bed occupancy; compared next-month admission forecasts with a seasonal baseline.”
