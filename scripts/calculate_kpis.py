#!/usr/bin/env python
"""Compute KPIs vs targets and run the management queries. Writes CSVs to data/processed/."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data.db import ROOT, connect, load_config
from src.analytics.kpis import compute_kpis, kpi_dictionary
from src.analytics.queries import run_all
from src.process_mining.analysis import analyze
from src.reporting.recommendations import build as build_recs

cfg = load_config(); con = connect(cfg)
start = pd.Timestamp(cfg["data"]["start_date"]); end = start + pd.DateOffset(months=cfg["data"]["months"])
k = compute_kpis(con, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"))
pm = analyze(con)
ds = pm["deviation_summary"]
dev_n, dev_d = int(ds.deviation_cases.sum()), int(ds.cases.sum())
k = pd.concat([k, pd.DataFrame([dict(kpi_id="process_deviation_rate", name="Process deviation rate", unit="ratio", numerator=dev_n, denominator=dev_d, value=dev_n / dev_d if dev_d else None)])], ignore_index=True)
tg = pd.read_sql("SELECT kpi_id, target_value, direction FROM kpi_targets", con)
k = k.merge(tg, on="kpi_id", how="left")
k["meets_target"] = [None if (v is None or pd.isna(v) or pd.isna(t)) else (v >= t if d == "higher" else v <= t) for v, t, d in zip(k.value, k.target_value, k.direction)]
out = ROOT / cfg["paths"]["processed"]; out.mkdir(parents=True, exist_ok=True)
k.to_csv(out / "kpis.csv", index=False); kpi_dictionary().to_csv(out / "kpi_dictionary.csv", index=False)
qs = run_all(con, end.strftime("%Y-%m-%d"))
for n, df in qs.items():
    df.to_csv(out / f"{n}.csv", index=False)
dq_path = out / "dq_findings.csv"
recs = build_recs(k, qs, pm, pd.read_csv(dq_path) if dq_path.exists() else None)
recs.to_csv(out / "recommendations.csv", index=False)
pd.set_option("display.width", 200)
print(k[["kpi_id", "numerator", "denominator", "value", "target_value", "meets_target"]].round(3).to_string(index=False))
