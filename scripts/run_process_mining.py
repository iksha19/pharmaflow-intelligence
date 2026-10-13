#!/usr/bin/env python
"""Run process mining; export CSVs (data/processed/pm_*.csv) and Plotly HTML charts (reports/)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plotly.express as px
from src.data.db import ROOT, connect, load_config
from src.process_mining.analysis import analyze

cfg = load_config(); con = connect(cfg)
res = analyze(con)
out = ROOT / cfg["paths"]["processed"]; rep = ROOT / cfg["paths"]["reports"]; out.mkdir(parents=True, exist_ok=True); rep.mkdir(parents=True, exist_ok=True)
for k, df in res.items():
    df.to_csv(out / f"pm_{k}.csv", index=False)
v = res["variants_inbound"].head(10)
px.bar(v, x="variant_id", y="cases", hover_data=["variant"], title="Inbound process variants (top 10, synthetic data)").write_html(rep / "pm_variants_inbound.html")
t = res["transitions_inbound"].query("segment == 'Internal handover'").head(10).copy(); t["step"] = t.activity + " → " + t.next_activity
px.bar(t, x="mean_h", y="step", orientation="h", title="Inbound handover wait (mean hours, top 10 by total wait)").write_html(rep / "pm_bottlenecks_inbound.html")
c = res["cases"]; c = c[c.status == "Completed"]
px.box(c, x="case_type", y="duration_h", points=False, title="Completed case cycle time (h)").write_html(rep / "pm_cycle_times.html")
print(res["deviation_summary"].round(3).to_string(index=False)); print(res["transitions_inbound"].head(5).round(2).to_string(index=False))
print(res["root_cause"].head(8).round(3).to_string(index=False)); print(res["rework_loops"].round(3).to_string(index=False))
