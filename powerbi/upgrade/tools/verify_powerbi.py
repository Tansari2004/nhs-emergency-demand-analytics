"""Verify NHS snapshot/model arithmetic and source structure, not native DAX."""
from __future__ import annotations
import base64
import json
from pathlib import Path
import re
import zlib

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi/upgrade"
if not OUT.exists():
    OUT = ROOT
DATA = ROOT / "powerbi/data"
if not DATA.exists():
    DATA = ROOT / "data"


def main():
    model = json.loads((OUT / "NHS_Analytics.SemanticModel/model.bim").read_text())["model"]
    check_results = []
    def check(name, condition):
        if not condition:
            raise ValueError(name)
        check_results.append({"check": name, "passed": True})
    tables = {t["name"]: t for t in model["tables"]}
    decoded = {}
    for name, table in tables.items():
        partition = table["partitions"][0]
        expression = "\n".join(partition["source"]["expression"])
        check(name + ": embedded import only", partition["mode"] == "import" and not re.search(r"Web\.Contents|File\.Contents|PostgreSQL\.Database|Sql\.Database|Odbc\.|OleDb\.", expression))
        raw = expression.split("Encoded = Text.Combine({", 1)[1].split("}),", 1)[0]
        chunks = re.findall(r'"([A-Za-z0-9+/=]+)"', raw)
        rows = json.loads(zlib.decompress(base64.b64decode("".join(chunks)), -15))
        names = [c["name"] for c in table["columns"]]
        check(name + ": row widths", all(len(row) == len(names) for row in rows))
        check(name + ": no implicit summation", all(c["summarizeBy"] == "none" for c in table["columns"]))
        decoded[name] = pd.DataFrame(rows, columns=names)
    check("no external model data sources", not model.get("dataSources") and not model.get("expressions"))
    monthly = pd.read_csv(DATA / "monthly_demand.csv")
    beds = pd.read_csv(DATA / "quarterly_beds.csv")
    trusts = pd.read_csv(DATA / "trust_beds_2026q2.csv")
    forecast = pd.read_csv(DATA / "admissions_forecast_backtest.csv")
    summary = pd.read_csv(DATA / "admissions_forecast_summary.csv").iloc[0]
    rebuilt = ROOT / "outputs/powerbi"
    if rebuilt.exists():
        for source in DATA.glob("*.csv"):
            pd.testing.assert_frame_equal(pd.read_csv(source), pd.read_csv(rebuilt / source.name),
                                          check_exact=False, rtol=1e-9, atol=0.05)
            check(source.name + ": checked snapshot matches pipeline rebuild", True)
    check("127 demand observations retained exactly", decoded["MonthlyDemand"].values.tolist() == monthly[["month", "total_emergency_admissions", "dta_wait_over_12h"]].values.tolist() and len(monthly) == 127)
    check("45 bed quarters retained", len(decoded["QuarterlyBeds"]) == len(beds) == 45 and np.allclose(decoded["QuarterlyBeds"][["Available beds", "Occupied beds"]], beds[["available_beds", "occupied_beds"]]))
    check("153 trust snapshots retained", len(decoded["TrustSnapshot"]) == len(trusts) == 153 and decoded["TrustSnapshot"].values.tolist() == trusts[["organisation_code", "available_beds", "occupied_beds"]].values.tolist())
    forecast_cols = ["month", "actual_admissions", "seasonal_baseline", "model_forecast", "fixed_fit_model_forecast", "training_end", "training_rows"]
    check("24 targets and origins retained exactly", len(forecast) == 24 and decoded["Forecast"].values.tolist() == forecast[forecast_cols].values.tolist())
    expected_relationships = {("MonthlyDemand", "DemandMonth"), ("QuarterlyBeds", "BedQuarter"), ("TrustSnapshot", "DimTrust"), ("Forecast", "ForecastMonth")}
    check("four separate filtering domains", {(r["fromTable"], r["toTable"]) for r in model["relationships"]} == expected_relationships)
    for rel in model["relationships"]:
        keys = decoded[rel["toTable"]][rel["toColumn"]]
        check(rel["fromTable"] + ": valid one-way dimension relationship", keys.is_unique and decoded[rel["fromTable"]][rel["fromColumn"]].isin(keys).all() and rel["crossFilteringBehavior"] == "oneDirection")
    current = monthly.iloc[-1]
    previous = monthly.iloc[-13]
    admissions_yoy = current.total_emergency_admissions / previous.total_emergency_admissions - 1
    delays_yoy = current.dta_wait_over_12h / previous.dta_wait_over_12h - 1
    check("fixed admissions finding", round(100 * admissions_yoy, 1) == -1.6)
    check("fixed delay-count finding", round(100 * delays_yoy, 1) == 25.2)
    selected = decoded["QuarterlyBeds"]
    days = selected["Quarter days"]
    expected_days = (pd.to_datetime(selected["Quarter end"]) - pd.to_datetime(selected["Quarter end"]).dt.to_period("Q").dt.start_time).dt.days + 1
    check("calendar day weights", days.equals(expected_days))
    weighted = (selected["Occupied beds"] * days).sum() / (selected["Available beds"] * days).sum()
    latest_occupancy = selected["Occupied beds"].iloc[-1] / selected["Available beds"].iloc[-1]
    trust_occupancy = decoded["TrustSnapshot"]["Occupied beds"].sum() / decoded["TrustSnapshot"]["Available beds"].sum()
    check("single-quarter occupancy matches public finding", round(100 * latest_occupancy, 2) == 90.85)
    check("latest trust totals reconcile to national quarter", np.isclose(trust_occupancy, latest_occupancy))
    # Unequal capacities and quarter lengths must not be averaged as percentages.
    adversarial = (90 * 91 + 20 * 92) / (100 * 91 + 200 * 92)
    check("weighted occupancy differs from arithmetic mean", not np.isclose(adversarial, (0.9 + 0.1) / 2))
    check("multi-quarter percentage remains a ratio", 0 <= weighted <= 1)
    for col, metric in [("seasonal_baseline", "baseline_mae"), ("model_forecast", "model_mae"), ("fixed_fit_model_forecast", "fixed_fit_model_mae")]:
        check(col + ": full-period MAE", np.isclose(abs(forecast.actual_admissions - forecast[col]).mean(), summary[metric], atol=0.1))
    check("training cutoff precedes every target", (pd.to_datetime(forecast.training_end) == pd.to_datetime(forecast.month) - pd.offsets.MonthBegin(1)).all())
    check("expanding rather than fixed training pool", (forecast.training_rows.diff().dropna() == 1).all())
    cols = {name: {c["name"] for c in t["columns"]} for name, t in tables.items()}
    measures = {name: {m["name"] for m in t.get("measures", [])} for name, t in tables.items()}
    def bindings(node):
        if isinstance(node, dict):
            for kind in ("Column", "Measure"):
                if kind in node:
                    f = node[kind]
                    t = f.get("Expression", {}).get("SourceRef", {}).get("Entity")
                    if t:
                        check("visual resolves " + t + "." + f["Property"], f["Property"] in (cols if kind == "Column" else measures)[t])
            for value in node.values():bindings(value)
        elif isinstance(node, list):
            for value in node:bindings(value)
    layout = json.loads((OUT / "verification/layout_manifest.json").read_text())
    for page in layout["pages"]:
        visuals = page["visuals"]
        for v in visuals:
            check("visual within page " + v["name"], v["x"] >= 0 and v["y"] >= 0 and v["x"] + v["width"] <= page["width"] and v["y"] + v["height"] <= page["height"])
        for i, a in enumerate(visuals):
            for b in visuals[i+1:]:
                overlap = min(a["x"]+a["width"], b["x"]+b["width"])-max(a["x"],b["x"]) > 0 and min(a["y"]+a["height"], b["y"]+b["height"])-max(a["y"],b["y"]) > 0
                check("no overlap " + a["name"] + "/" + b["name"], not overlap)
    for file in (OUT / "NHS_Analytics.Report/definition/pages").glob("*/visuals/*/visual.json"):
        bindings(json.loads(file.read_text()))
    binding = json.loads((OUT / "NHS_Analytics.Report/definition.pbir").read_text())["datasetReference"]
    check("relative local model connection", binding == {"byPath": {"path": "../NHS_Analytics.SemanticModel"}})
    result = {"status": "passed", "checks": check_results, "check_count": len(check_results),
              "native_runtime_verified": False,
              "reference_values": {"august_2026_admissions_yoy_percent": float(100 * admissions_yoy), "august_2026_delay_yoy_percent": float(100 * delays_yoy), "latest_quarter_occupancy": float(latest_occupancy), "all_quarters_bed_day_weighted_occupancy": float(weighted), "trust_snapshot_occupancy": float(trust_occupancy), "single_quarter_card_with_multiple_quarters": None},
              "note": "Reference arithmetic, data fidelity and source checks do not execute native DAX, Power Query refresh or report rendering."}
    write_path = OUT / "verification/offline_checks.json"
    write_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "passed", "checks": len(check_results), "native_runtime_verified": False}))


if __name__ == "__main__":main()
