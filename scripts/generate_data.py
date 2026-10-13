#!/usr/bin/env python
"""Generate synthetic CSVs and build the SQLite database. Usage: python scripts/generate_data.py [--seed N] [--scale F]"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.generator import generate
from src.data.db import ROOT, load_config, write_csvs, build_database, db_path

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int); ap.add_argument("--scale", type=float, default=1.0, help="multiplier on record counts")
a = ap.parse_args()
cfg = load_config()
if a.seed is not None:
    cfg["data"]["seed"] = a.seed
for k in ("n_purchase_orders", "n_customer_orders", "n_production_requests"):
    cfg["data"][k] = max(10, int(cfg["data"][k] * a.scale))
t = generate(cfg)
write_csvs(t, ROOT / cfg["paths"]["raw"])
build_database(t, db_path(cfg))
for n, df in t.items():
    print(f"{n:24s}{len(df):>8d} rows")
