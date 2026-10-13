#!/usr/bin/env python
"""Run data-quality rules against the database. Exit code 1 if any Critical rule is violated."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data.db import ROOT, connect, load_config
from src.data.validation import run_checks, material_exceptions, PK

cfg = load_config(); con = connect(cfg)
tables = {n: pd.read_sql(f"SELECT * FROM {n}", con) for n in PK}
snap = pd.Timestamp(cfg["data"]["start_date"]) + pd.DateOffset(months=cfg["data"]["months"])
res = run_checks(tables, snap)
out = ROOT / cfg["paths"]["processed"]; out.mkdir(parents=True, exist_ok=True)
res.to_csv(out / "dq_findings.csv", index=False)
material_exceptions(tables["materials"]).to_csv(out / "material_exceptions.csv", index=False)
pd.set_option("display.width", 200, "display.max_colwidth", 60)
print(res[res.violations > 0][["rule_id", "rule", "table", "severity", "violations", "total", "violation_pct"]].to_string(index=False))
crit = res[(res.severity == "Critical") & (res.violations > 0)]
print(f"\nrules={len(res)} failing={int((res.violations > 0).sum())} critical_failing={len(crit)}")
sys.exit(1 if len(crit) else 0)
