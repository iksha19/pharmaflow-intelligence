"""Runs the reusable management SQL in database/queries/."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

QDIR = Path(__file__).resolve().parents[2] / "database" / "queries"
TITLES = {"q1_supplier_delay_contribution": "Suppliers contributing most to inbound delay", "q2_zone_processing_times": "Zone processing times",
          "q3_material_stockout_exposure": "Materials with highest stockout exposure", "q4_batches_near_expiry": "Batches approaching expiry",
          "q5_rework_hotspots": "Rework hotspots", "q6_stage_delay_contribution": "Outbound stage contribution to delay",
          "q7_data_quality_priority": "Data-quality remediation priority"}


def run_query(con: sqlite3.Connection, name: str, snapshot: str) -> pd.DataFrame:
    sql = (QDIR / f"{name}.sql").read_text()
    return pd.read_sql(sql, con, params={"snapshot": snapshot} if ":snapshot" in sql else None)


def run_all(con: sqlite3.Connection, snapshot: str) -> dict[str, pd.DataFrame]:
    return {n: run_query(con, n, snapshot) for n in TITLES}
