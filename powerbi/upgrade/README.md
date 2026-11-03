# NHS Analytics: editable Power BI source preview

**Status: source/data checks pass; native Power BI refresh, DAX execution,
interaction and rendering checks remain pending.** This is a new editable
snapshot project, not a claim that the saved workspace report has been updated.

Download and extract the complete `NHS_Analytics_Source_Preview.zip`, keeping
`NHS_Analytics.pbip`, `NHS_Analytics.Report` and `NHS_Analytics.SemanticModel`
together. Open the PBIP in a recent Power BI Desktop for Windows and refresh.
Its nine queries load included compressed data. No database login, external
connector, local CSV path or workspace access is required for that initial
refresh. Power BI Desktop does not run natively on macOS.

## What changed

Three pages contain 26 native visual definitions and 23 explicit DAX measures:

- **Emergency demand:** a between-dates month selector, admissions and
  over-12-hour delay counts, matching-month prior-year changes, two trends and a
  fixed interpretation panel. All selected months must have prior-year matches
  or YoY measures return blank; missing comparisons are not silently dropped.
- **Bed pressure and trust capacity:** a national-quarter range selector, a
  separate trust dropdown, national occupancy history, trust capacity table and
  explicit occupancy measures. The quarter selector does not filter the fixed
  trust snapshot, and the trust selector does not filter national history.
- **Forecast evaluation:** its own evaluation-month range, MAEs for the seasonal,
  expanding-window and original fixed-fit methods, actual-versus-forecast and
  error charts, and auditable training-cutoff/training-size rows.

Four one-direction dimension-to-fact relationships define independent filtering
domains. There is no demand-to-beds join, shared cross-population slicer or
admissions-per-bed rate. Report notes explain which controls affect each visual.

The embedded source is the published aggregate snapshot: 127 demand months,
45 bed quarters, 153 trusts and 24 forecast evaluation months. It has no patient
records. `Measures.dax` and `PowerQuery.m` contain the actual model definitions.

## Occupancy rules

- **One national quarter:** occupied average beds / available average beds.
- **Single-quarter card with several quarters selected:** blank, rather than
  adding the percentages or choosing an arbitrary quarter.
- **Multiple complete quarters:** sum(occupied average beds × calendar days) /
  sum(available average beds × calendar days). This is bed-day weighted occupancy.
- **Selected trusts in the fixed Apr-Jun 2026 snapshot:** sum(occupied average
  beds) / sum(available average beds). Trust percentages are not added or averaged.

All raw columns use `summarizeBy: none`; report calculations use explicit
measures. Native totals and filter behaviour still need the runtime checks below.

## Forecast findings and scope

The same 24 targets (Sep 2024-Aug 2026) are used by all three methods:

| Method | MAE, admissions/month |
| --- | ---: |
| Same month last year | 9,874.21 |
| Forest, expanding window with 24 refits | 13,134.67 |
| Original forest, fitted once through Aug 2024 | 15,501.42 |

Refitting improves the forest but does not beat the seasonal baseline. The
baseline has 24.8% lower error than the expanding forest on this period. Model
parameters are unchanged; the only training-protocol change is expanding the
training pool before each target. Every row records its preceding-month cutoff.

This is an observation-time backtest. NHS publication delays are not simulated.
The evaluation period was examined previously, so the updated protocol is a
retrospective comparison, not a fresh prospective test or evidence of clinical
benefit. September 2026's preferred 535,580 forecast remains a historical as-of
estimate, not a current live forecast. Prediction intervals are not implemented.

## Fixed interpretation panels

- August 2026 admissions fell 1.6% year on year while over-12-hour delay counts
  rose 25.2%. Lower admissions did not coincide with fewer long delays.
- Apr-Jun 2026 national occupancy was 90.85%, down 0.60 percentage points from
  the same quarter a year earlier. This does not establish hospital-level spare
  capacity or explain why delay counts changed.
- The panels are labelled full-snapshot findings and do not change with
  selectors. The charts and measure cards respond to their stated filters.

## Verification

`verification/offline_checks.json` records reference arithmetic, exact embedded
data checks, independent dimension scopes, valid field bindings and page
geometry. Microsoft's PBIR validator reports zero errors/warnings and Microsoft's
Power Query parser successfully parses all nine queries. Neither tool executes
native M refresh or DAX, or proves that controls render and interact correctly.

Required Desktop checks before replacing the existing report:

1. Open the project and refresh every table without errors.
2. Select August 2026 demand: verify 517,868 admissions, 44,951 long delays,
   -1.6% admissions YoY and +25.2% delay-count YoY. Select a month lacking a
   prior-year match and verify blank YoY results.
3. Select one bed quarter, then several: verify the single-quarter card's
   blank behaviour and compare weighted occupancy with the reference JSON.
4. Select one trust and several trusts: verify ratio-of-totals occupancy and
   that national history is unchanged. Use the dropdown's search option if
   needed; search rendering has not been verified here.
5. Change the forecast date range: verify MAE and observation counts recompute.
6. Inspect all three pages, filter clear/reset behaviour, date sorting, text,
   tables, card labels and legends at normal zoom; then publish if satisfactory.

The original PBIX, PDF and screenshots remain in the repository as the
fixed-fit version and are not labelled as screenshots of this upgrade.

## Rebuild

From the repository root after the pipeline exports are current:

```sh
python scripts/build_powerbi_model.py
python scripts/build_powerbi_report.py
python scripts/verify_powerbi.py
```

For the extracted package, the same scripts are under `tools/` and the public
CSV snapshots are in `data/`. Source rebuilding needs the Python dependencies;
opening and refreshing the embedded Power BI model does not.

Data attribution: NHS England, aggregate A&E activity and overnight bed
statistics, under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Code and documentation: this repository's MIT licence. Format:
[Microsoft PBIP documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview).
