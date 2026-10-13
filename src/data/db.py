"""Config loading, CSV export and SQLite database build."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
LOAD_ORDER = ["suppliers", "materials", "warehouse_bins", "purchase_orders", "po_lines", "inbound_deliveries", "inventory_batches",
              "quality_inspections", "warehouse_movements", "production_requests", "customer_orders", "outbound_deliveries",
              "event_log", "kpi_targets", "scenario_assumptions"]


def load_config(path: str | Path | None = None) -> dict:
    with open(path or ROOT / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


def db_path(cfg: dict) -> Path:
    return ROOT / cfg["paths"]["database"]


def connect(cfg: dict | None = None) -> sqlite3.Connection:
    cfg = cfg or load_config()
    con = sqlite3.connect(db_path(cfg))
    con.execute("PRAGMA foreign_keys = ON")
    return con


def write_csvs(tables: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)


def build_database(tables: dict[str, pd.DataFrame], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript((ROOT / "database" / "schema.sql").read_text())
        con.execute("PRAGMA foreign_keys = ON")
        for name in LOAD_ORDER:
            tables[name].to_sql(name, con, if_exists="append", index=False)
        con.commit()
        bad = con.execute("PRAGMA foreign_key_check").fetchall()
        if bad:
            raise RuntimeError(f"Foreign key violations: {bad[:5]}")
    finally:
        con.close()
