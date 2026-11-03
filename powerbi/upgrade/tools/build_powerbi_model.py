"""Build an editable, self-contained NHS snapshot model; native refresh is separate."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import uuid
import zlib

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi/upgrade"
if not OUT.exists():
    OUT = ROOT
MODEL = OUT / "NHS_Analytics.SemanticModel"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def m_query(names, rows, types):
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    encoded = base64.b64encode(compressor.compress(raw) + compressor.flush()).decode()
    chunks = ",\n".join(json.dumps(encoded[i:i+16000]) for i in range(0, len(encoded), 16000))
    columns = "{" + ",".join(json.dumps(n) for n in names) + "}"
    mapping = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date"}
    changes = ",".join("{" + json.dumps(n) + "," + mapping[t] + "}" for n, t in zip(names, types))
    return ["let", "    Encoded = Text.Combine({" + chunks + "}),",
            "    Data = Json.Document(Binary.Decompress(Binary.FromText(Encoded, BinaryEncoding.Base64), Compression.Deflate)),",
            "    Rows = Table.FromRows(Data, " + columns + "),",
            "    Typed = Table.TransformColumnTypes(Rows, {" + changes + '}, "en-US")',
            "in", "    Typed"]


def table(name, columns, rows, description, hidden=False):
    names, types = zip(*columns)
    fields = []
    for n, t in columns:
        field = {"name": n, "dataType": t, "sourceColumn": n, "summarizeBy": "none", "isHidden": hidden}
        if t == "dateTime":
            field["formatString"] = "dd MMM yyyy"
            field["annotations"] = [{"name": "UnderlyingDateTimeDataType", "value": "Date"}]
        elif t in ("int64", "double"):
            field["formatString"] = "#,0" if t == "int64" else "#,0.00"
        fields.append(field)
    return {"name": name, "description": description, "columns": fields,
            "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": m_query(names, rows, types)}}]}


def previous_year(measure):
    return f'''VAR Months = VALUES(DemandMonth[Month])
VAR PriorMonths = SELECTCOLUMNS(Months, "PriorMonth", EDATE(DemandMonth[Month], -12))
VAR PriorCount = CALCULATE(COUNTROWS(MonthlyDemand), REMOVEFILTERS(DemandMonth), TREATAS(PriorMonths, DemandMonth[Month]))
RETURN IF(COUNTROWS(Months) > 0 && PriorCount = COUNTROWS(Months),
    CALCULATE([{measure}], REMOVEFILTERS(DemandMonth), TREATAS(PriorMonths, DemandMonth[Month])))'''


MEASURES = [
    ("Admissions", "SUM(MonthlyDemand[Admissions])", "#,0", "Demand", "Total across selected monthly observations."),
    ("Admissions Previous Year", previous_year("Admissions"), "#,0", "Demand", "Matching months one year earlier; blank if any prior month is missing."),
    ("Admissions YoY Change", "IF(NOT ISBLANK([Admissions Previous Year]), [Admissions] - [Admissions Previous Year])", "#,0;-#,0", "Demand", "Count difference for matched month selections."),
    ("Admissions YoY Percent", "DIVIDE([Admissions YoY Change], [Admissions Previous Year])", "0.0%;-0.0%", "Demand", "Relative change; missing/zero comparison stays blank."),
    ("Over 12 Hour Delays", "SUM(MonthlyDemand[Over 12 hour delays])", "#,0", "Demand", "Count after decision to admit, not an average wait or all ED waits."),
    ("Delays Previous Year", previous_year("Over 12 Hour Delays"), "#,0", "Demand", "All selected months must have corresponding prior-year observations."),
    ("Delays YoY Change", "IF(NOT ISBLANK([Delays Previous Year]), [Over 12 Hour Delays] - [Delays Previous Year])", "#,0;-#,0", "Demand", "Change in threshold counts, not hours of waiting."),
    ("Delays YoY Percent", "DIVIDE([Delays YoY Change], [Delays Previous Year])", "0.0%;-0.0%", "Demand", "Relative change in delay counts."),
    ("Selected Quarter Occupancy", "IF(HASONEVALUE(BedQuarter[Quarter end]), DIVIDE(SUM(QuarterlyBeds[Occupied beds]), SUM(QuarterlyBeds[Available beds])))", "0.00%", "Beds", "A single national quarter only; blank when multiple quarters are selected."),
    ("Bed Day Weighted Occupancy", "DIVIDE(SUMX(QuarterlyBeds, QuarterlyBeds[Occupied beds] * QuarterlyBeds[Quarter days]), SUMX(QuarterlyBeds, QuarterlyBeds[Available beds] * QuarterlyBeds[Quarter days]))", "0.00%", "Beds", "Across complete selected quarters, occupied bed-days / available bed-days. Never sum percentages."),
    ("Trust Available Beds", "SUM(TrustSnapshot[Available beds])", "#,0.0", "Trusts", "Average available overnight beds in the fixed Apr-Jun 2026 snapshot."),
    ("Trust Occupied Beds", "SUM(TrustSnapshot[Occupied beds])", "#,0.0", "Trusts", "Average occupied beds for selected trusts; not admissions."),
    ("Trust Snapshot Occupancy", "DIVIDE([Trust Occupied Beds], [Trust Available Beds])", "0.00%", "Trusts", "Ratio of totals for selected trusts, not an average or sum of trust percentages."),
    ("Observed Admissions", "SUM(Forecast[Actual admissions])", "#,0", "Forecast", "Observed target over selected evaluation months."),
    ("Seasonal Forecast", "SUM(Forecast[Seasonal baseline])", "#,0", "Forecast", "Same month one year earlier."),
    ("Expanding Forest Forecast", "SUM(Forecast[Expanding forest])", "#,0", "Forecast", "Re-fitted before each target using earlier monthly observations."),
    ("Seasonal Absolute Error", "SUMX(Forecast, ABS(Forecast[Actual admissions] - Forecast[Seasonal baseline]))", "#,0", "Forecast", "Absolute errors summed over selected months."),
    ("Forest Absolute Error", "SUMX(Forecast, ABS(Forecast[Actual admissions] - Forecast[Expanding forest]))", "#,0", "Forecast", "Absolute errors summed over selected months."),
    ("Seasonal MAE", "AVERAGEX(Forecast, ABS(Forecast[Actual admissions] - Forecast[Seasonal baseline]))", "#,0.0", "Forecast", "Mean over selected test months; recomputes with the evaluation-date filter."),
    ("Expanding Forest MAE", "AVERAGEX(Forecast, ABS(Forecast[Actual admissions] - Forecast[Expanding forest]))", "#,0.0", "Forecast", "One-month-ahead expanding-window error, admissions/month."),
    ("Fixed Fit Forest MAE", "AVERAGEX(Forecast, ABS(Forecast[Actual admissions] - Forecast[Fixed fit forest]))", "#,0.0", "Forecast", "Original forest held fixed after Aug 2024; comparison, not the expanding model."),
    ("Evaluation Months", "COUNTROWS(Forecast)", "#,0", "Forecast", "Number of selected test months."),
    ("Historical Next Forecast", "MAX(Summary[Next forecast])", "#,0", "Forecast", "Full-period preferred September 2026 forecast as of August 2026; unaffected by evaluation slicer."),
]


def main():
    data = ROOT / "powerbi/data"
    if not data.exists():
        data = ROOT / "data"
    monthly = pd.read_csv(data / "monthly_demand.csv")
    beds = pd.read_csv(data / "quarterly_beds.csv")
    trusts = pd.read_csv(data / "trust_beds_2026q2.csv")
    forecasts = pd.read_csv(data / "admissions_forecast_backtest.csv")
    summary = pd.read_csv(data / "admissions_forecast_summary.csv").iloc[0]
    end = pd.to_datetime(beds.quarter_end)
    days = (end - end.dt.to_period("Q").dt.start_time).dt.days + 1
    tables = [
        table("DemandMonth", [("Month", "dateTime")], [[d] for d in monthly.month], "Monthly demand selector; no link to bed or trust populations."),
        table("MonthlyDemand", [("Month", "dateTime"), ("Admissions", "int64"), ("Over 12 hour delays", "int64")], monthly[["month", "total_emergency_admissions", "dta_wait_over_12h"]].values.tolist(), "England aggregate monthly demand and decision-to-admit threshold counts.", True),
        table("BedQuarter", [("Quarter end", "dateTime")], [[d] for d in beds.quarter_end], "Quarter selector for national bed history only."),
        table("QuarterlyBeds", [("Quarter end", "dateTime"), ("Available beds", "double"), ("Occupied beds", "double"), ("Quarter days", "int64")], [[r.quarter_end, float(r.available_beds), float(r.occupied_beds), int(d)] for (_, r), d in zip(beds.iterrows(), days)], "National quarterly average beds, with calendar-day weights.", True),
        table("DimTrust", [("Trust code", "string"), ("Trust", "string"), ("Region code", "string")], trusts[["organisation_code", "organisation_name", "region_code"]].values.tolist(), "Provider filter for the fixed latest trust snapshot only."),
        table("TrustSnapshot", [("Trust code", "string"), ("Available beds", "double"), ("Occupied beds", "double")], trusts[["organisation_code", "available_beds", "occupied_beds"]].values.tolist(), "Apr-Jun 2026 trust snapshot; not a trust-level admissions series.", True),
        table("ForecastMonth", [("Month", "dateTime")], [[d] for d in forecasts.month], "Evaluation dates only; independent of the other date selectors."),
        table("Forecast", [("Month", "dateTime"), ("Actual admissions", "int64"), ("Seasonal baseline", "double"), ("Expanding forest", "double"), ("Fixed fit forest", "double"), ("Training through", "dateTime"), ("Training rows", "int64")], forecasts[["month", "actual_admissions", "seasonal_baseline", "model_forecast", "fixed_fit_model_forecast", "training_end", "training_rows"]].values.tolist(), "Shared 24-month target; origin cutoff and training size retained."),
        table("Summary", [("As of month", "dateTime"), ("Forecast month", "dateTime"), ("Preferred method", "string"), ("Next forecast", "double")], [[summary.as_of_month, summary.forecast_month, summary.preferred_method, float(summary.preferred_next_month_forecast)]], "Historical as-of forecast, not a current live prediction."),
    ]
    metrics = tables[-1]
    metrics["measures"] = [{"name": n, "expression": e.splitlines(), "formatString": f,
                            "displayFolder": folder, "description": d} for n, e, f, folder, d in MEASURES]
    relationships = []
    for fact, col, dim in [("MonthlyDemand", "Month", "DemandMonth"), ("QuarterlyBeds", "Quarter end", "BedQuarter"),
                           ("TrustSnapshot", "Trust code", "DimTrust"), ("Forecast", "Month", "ForecastMonth")]:
        relationships.append({"name": str(uuid.uuid5(uuid.NAMESPACE_URL, f"nhs:{fact}:{dim}")),
                              "fromTable": fact, "fromColumn": col, "fromCardinality": "many",
                              "toTable": dim, "toColumn": col, "toCardinality": "one",
                              "crossFilteringBehavior": "oneDirection", "isActive": True})
    write(MODEL / "model.bim", {"name": "NHS_Analytics", "compatibilityLevel": 1600,
          "model": {"culture": "en-US", "sourceQueryCulture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3",
                    "tables": tables, "relationships": relationships,
                    "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                                    {"name": "RuntimeVerification", "value": "Native Power BI refresh, DAX and rendering unverified."}]}})
    write(MODEL / "definition.pbism", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "1.0", "settings": {}})
    write(MODEL / ".platform", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json", "metadata": {"type": "SemanticModel", "displayName": "NHS Analytics"}, "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, "tarik-nhs-analytics-upgrade"))}})
    (OUT / "Measures.dax").write_text("\n\n".join("// " + d + "\n" + n + " =\n" + e for n, e, f, folder, d in MEASURES) + "\n")
    (OUT / "PowerQuery.m").write_text("\n\n".join("// " + t["name"] + "\n" + "\n".join(t["partitions"][0]["source"]["expression"]) for t in tables) + "\n")
    write(OUT / "verification/model_inventory.json", {"tables": {t["name"]: len(t["columns"]) for t in tables}, "relationships": relationships, "measures": len(MEASURES), "native_runtime_verified": False})
    print(json.dumps({"tables": len(tables), "relationships": len(relationships), "measures": len(MEASURES)}))


if __name__ == "__main__":
    main()
