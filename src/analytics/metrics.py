"""Pure-pandas frame builders and metrics used by the app, reports and tests (no Streamlit imports)."""
from __future__ import annotations
import sqlite3
import numpy as np
import pandas as pd

ZONE_SQL = "CASE m.storage_condition WHEN 'Cold' THEN 'COLD' WHEN 'Controlled' THEN 'CTRL' ELSE 'AMB' END"
HOURS = lambda a, b: (pd.to_datetime(a) - pd.to_datetime(b)).dt.total_seconds() / 3600


def safe_div(n, d):
    """Ratio or NaN on zero/missing denominator (never a silent 0)."""
    return np.nan if (d is None or pd.isna(d) or d == 0) else n / d


def inbound_frame(con: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(f"""SELECT d.delivery_id, p.supplier_id, l.material_id, m.category, {ZONE_SQL} AS zone, m.storage_condition,
        d.arrival_ts, d.gr_ts, d.verification_ts, d.putaway_ts, p.requested_delivery_date, d.delivered_qty, d.damaged_qty, d.partial_flag, d.rework_flag, d.status,
        q.start_ts AS insp_start_ts, q.decision_ts, q.result, q.hold_flag, q.hold_hours
        FROM inbound_deliveries d JOIN po_lines l USING(po_line_id) JOIN purchase_orders p USING(po_id) JOIN materials m ON m.material_id=l.material_id
        JOIN quality_inspections q USING(delivery_id)""", con)
    for c in ["arrival_ts", "gr_ts", "verification_ts", "putaway_ts", "requested_delivery_date", "insp_start_ts", "decision_ts"]:
        df[c] = pd.to_datetime(df[c])
    df["delay_days"] = np.maximum(0, (df.arrival_ts.dt.normalize() - df.requested_delivery_date.dt.normalize()).dt.days)
    df["on_time"] = (df.delay_days == 0).astype(int)
    df["gr_to_putaway_h"] = HOURS(df.putaway_ts, df.gr_ts)
    df["putaway_before_release"] = (df.putaway_ts.notna() & df.decision_ts.notna() & (df.putaway_ts < df.decision_ts))
    return df


def outbound_frame(con: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(f"""SELECT c.order_id, c.material_id, m.category, o.zone, c.priority, c.order_ts, c.requested_dispatch_ts, c.status, c.order_qty,
        o.allocation_ts, o.pick_start_ts, o.pick_end_ts, o.pack_start_ts, o.pack_end_ts, o.dispatch_ts, o.qty_backordered, o.stockout_flag, o.repick_flag
        FROM customer_orders c JOIN materials m USING(material_id) LEFT JOIN outbound_deliveries o USING(order_id)""", con)
    for c in ["order_ts", "requested_dispatch_ts", "allocation_ts", "pick_start_ts", "pick_end_ts", "pack_start_ts", "pack_end_ts", "dispatch_ts"]:
        df[c] = pd.to_datetime(df[c])
    df["order_to_dispatch_h"] = HOURS(df.dispatch_ts, df.order_ts)
    df["wait_allocation_h"] = HOURS(df.allocation_ts, df.order_ts); df["wait_pick_h"] = HOURS(df.pick_start_ts, df.allocation_ts)
    df["picking_h"] = HOURS(df.pick_end_ts, df.pick_start_ts); df["wait_pack_h"] = HOURS(df.pack_start_ts, df.pick_end_ts)
    df["packing_h"] = HOURS(df.pack_end_ts, df.pack_start_ts); df["wait_dispatch_h"] = HOURS(df.dispatch_ts, df.pack_end_ts)
    df["late"] = (df.dispatch_ts > df.requested_dispatch_ts).where(df.dispatch_ts.notna())
    return df


def inventory_frame(con: sqlite3.Connection, snapshot: str) -> pd.DataFrame:
    df = pd.read_sql("""SELECT b.*, m.category, m.unit_cost, m.storage_condition FROM inventory_batches b JOIN materials m USING(material_id)""", con)
    df["expiry_date"] = pd.to_datetime(df.expiry_date); snap = pd.Timestamp(snapshot)
    df["days_to_expiry"] = (df.expiry_date.dt.normalize() - snap.normalize()).dt.days
    df["recorded_value"] = df.recorded_qty * df.unit_cost
    df["abs_diff_qty"] = (df.recorded_qty - df.physical_qty).abs()
    df["mismatch"] = (df.recorded_qty > 0) & (df.abs_diff_qty > .02 * df.recorded_qty)
    return df


def expiry_exposure(inv: pd.DataFrame, window_days: int) -> pd.DataFrame:
    x = inv[(inv.recorded_qty > 0) & (inv.stock_status != "Rejected") & (inv.days_to_expiry <= window_days)].copy()
    x["bucket"] = np.where(x.days_to_expiry <= 0, "Expired", np.where(x.days_to_expiry <= 30, "<=30d", "31+ d"))
    return x.sort_values("recorded_value", ascending=False)


def inventory_position(inv: pd.DataFrame) -> pd.DataFrame:
    """Four inventory concepts: physical, recorded, quality-restricted, available-to-use (quantities and value)."""
    cols = {"Physical": "physical_qty", "Recorded (book)": "recorded_qty", "Quality-restricted": "quality_restricted_qty", "Available-to-use": "available_qty"}
    return pd.DataFrame([dict(concept=k, units=inv[c].sum(), value=(inv[c] * inv.unit_cost).sum()) for k, c in cols.items()])


def supplier_scorecard(inb: pd.DataFrame) -> pd.DataFrame:
    g = inb.groupby("supplier_id")
    s = g.agg(deliveries=("delivery_id", "size"), otd=("on_time", "mean"), avg_delay_days=("delay_days", "mean"), total_delay_days=("delay_days", "sum"),
              partial_rate=("partial_flag", "mean"), reject_rate=("result", lambda r: (r == "Rejected").mean()), avg_hold_h=("hold_hours", "mean")).reset_index()
    tot = s.total_delay_days.sum()
    s["pct_of_delay_days"] = s.total_delay_days / tot if tot else np.nan
    return s.sort_values("total_delay_days", ascending=False).reset_index(drop=True)


def stage_delay(out: pd.DataFrame) -> pd.DataFrame:
    stages = ["wait_allocation_h", "wait_pick_h", "picking_h", "wait_pack_h", "packing_h", "wait_dispatch_h"]
    o = out[out.dispatch_ts.notna()]
    rows = [dict(stage=s.replace("_h", ""), avg_all=o[s].mean(), avg_late=o.loc[o.late == True, s].mean(), avg_on_time=o.loc[o.late == False, s].mean()) for s in stages]
    r = pd.DataFrame(rows); r["late_minus_on_time"] = r.avg_late - r.avg_on_time
    return r.sort_values("late_minus_on_time", ascending=False)


def monthly_trend(inb: pd.DataFrame, out: pd.DataFrame) -> pd.DataFrame:
    a = inb.assign(m=inb.arrival_ts.dt.to_period("M").astype(str)).groupby("m").agg(supplier_otd=("on_time", "mean"))
    o = out[out.dispatch_ts.notna()]
    b = o.assign(m=o.order_ts.dt.to_period("M").astype(str)).groupby("m").agg(on_time_dispatch=("late", lambda s: 1 - s.mean()), stockout_rate=("stockout_flag", "mean"),
                                                                                  avg_order_to_dispatch_h=("order_to_dispatch_h", "mean"))
    return a.join(b, how="outer").reset_index().rename(columns={"m": "month"})


def completeness_by_attribute(materials: pd.DataFrame, attrs: list[str]) -> pd.DataFrame:
    return pd.DataFrame([dict(attribute=a, populated=materials[a].notna().mean(), missing=int(materials[a].isna().sum())) for a in attrs])
