"""Transparent process-mining engine (pure pandas). PM4Py is intentionally not required.

Rules below are SIMULATED business rules for demonstration; a deviation is not a confirmed regulatory/GMP violation.
"""
from __future__ import annotations
import sqlite3
import numpy as np
import pandas as pd
from src.data.generator import VALID_UOM

RANK_IN = {"Purchase Order Created": 0, "Inbound Delivery Created": 1, "Goods Receipt": 2, "Batch & Quantity Verification": 3,
           "Quality Inspection": 4, "Quality Hold": 5, "Quality Release": 6, "Quality Rejection": 6, "Putaway": 7, "Return to Supplier": 7, "Inventory Available": 8}
RANK_OUT = {"Customer Order Created": 0, "Backorder Created": 1, "Inventory Allocation": 2, "Picking": 3, "Packing": 4, "Dispatch": 5, "Reconciliation": 6, "Order Cancelled": 9}
MANDATORY = {
    "IN_RELEASED": ["Purchase Order Created", "Inbound Delivery Created", "Goods Receipt", "Batch & Quantity Verification", "Quality Inspection", "Quality Release", "Putaway", "Inventory Available"],
    "IN_REJECTED": ["Purchase Order Created", "Inbound Delivery Created", "Goods Receipt", "Batch & Quantity Verification", "Quality Inspection", "Quality Rejection", "Return to Supplier"],
    "OUT_FULL": ["Customer Order Created", "Inventory Allocation", "Picking", "Packing", "Dispatch", "Reconciliation"],
    "OUT_CANCELLED": ["Customer Order Created", "Order Cancelled"],
}
EXPECTED_MAP = {"INBOUND": MANDATORY["IN_RELEASED"], "OUTBOUND": MANDATORY["OUT_FULL"]}


def load_events(con: sqlite3.Connection) -> pd.DataFrame:
    ev = pd.read_sql("SELECT * FROM event_log", con, parse_dates=["event_ts"])
    return ev.sort_values(["case_id", "event_ts", "event_id"], kind="mergesort").reset_index(drop=True)


def _path(case_type: str, acts: set) -> str:
    if case_type == "INBOUND":
        if "Quality Rejection" in acts: return "IN_REJECTED"
        if "Quality Release" in acts: return "IN_RELEASED"
        return "IN_OPEN"
    return "OUT_CANCELLED" if "Order Cancelled" in acts else "OUT_FULL"


def case_table(ev: pd.DataFrame) -> pd.DataFrame:
    g = ev.groupby("case_id")
    c = g.agg(case_type=("case_type", "first"), start=("event_ts", "min"), end=("event_ts", "max"), n_events=("activity", "size"),
              supplier_id=("supplier_id", "first"), material_id=("material_id", "first"), zone=("zone", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
              priority=("priority", "first"), reference_id=("reference_id", "first"))
    c["duration_h"] = (c["end"] - c["start"]).dt.total_seconds() / 3600
    c["variant"] = g["activity"].agg(lambda s: " > ".join(s))
    c["path"] = [_path(t, set(v.split(" > "))) for t, v in zip(c["case_type"], c["variant"])]
    c["status"] = c["path"].map({"IN_RELEASED": "Completed", "IN_REJECTED": "Rejected", "IN_OPEN": "Open", "OUT_FULL": "Completed", "OUT_CANCELLED": "Cancelled"})
    return c.reset_index()


def conformance(ev: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    """Per-case: missing mandatory activities, out-of-order consecutive activities, repeated activities."""
    first = ev.groupby(["case_id", "activity"])["event_ts"].min()
    cnt = ev.groupby(["case_id", "activity"]).size()
    rows = []
    for r in cases.itertuples():
        ranks = RANK_IN if r.case_type == "INBOUND" else RANK_OUT
        ts = first.loc[r.case_id]
        present = ts.index.tolist()
        mand = MANDATORY.get(r.path, [])
        missing = [a for a in mand if a not in present] if r.status != "Open" else []
        ordered = sorted(present, key=lambda a: (ranks[a], ts[a]))
        ooo = [f"{b} before {a}" for a, b in zip(ordered[:-1], ordered[1:]) if ranks[a] < ranks[b] and ts[b] < ts[a]]
        rep = [a for a in present if cnt.loc[(r.case_id, a)] > 1]
        nmand = max(len(mand), 1)
        fitness = 1 - (len(missing) + len(ooo)) / (nmand + max(len(ordered) - 1, 0)) if r.status != "Open" else np.nan
        rows.append(dict(case_id=r.case_id, case_type=r.case_type, status=r.status, missing="; ".join(missing), out_of_order="; ".join(ooo),
                         repeated="; ".join(rep), has_missing=bool(missing), has_out_of_order=bool(ooo), has_rework=bool(rep),
                         deviation=bool(missing or ooo) and r.status != "Open", fitness=fitness))
    return pd.DataFrame(rows)


def variants(cases: pd.DataFrame, case_type: str) -> pd.DataFrame:
    c = cases[cases.case_type == case_type]
    v = c.groupby("variant").agg(cases=("case_id", "size"), median_h=("duration_h", "median"), p90_h=("duration_h", lambda s: s.quantile(.9))).reset_index()
    v = v.sort_values("cases", ascending=False).reset_index(drop=True)
    v["share"] = v["cases"] / v["cases"].sum(); v["cum_share"] = v["share"].cumsum(); v["variant_id"] = [f"V{i + 1:02d}" for i in range(len(v))]
    return v[["variant_id", "variant", "cases", "share", "cum_share", "median_h", "p90_h"]]


def transitions(ev: pd.DataFrame, case_type: str) -> pd.DataFrame:
    e = ev[ev.case_type == case_type].copy()
    e["next_activity"] = e.groupby("case_id")["activity"].shift(-1)
    e["next_ts"] = e.groupby("case_id")["event_ts"].shift(-1)
    e = e.dropna(subset=["next_activity"])
    e["wait_h"] = (e["next_ts"] - e["event_ts"]).dt.total_seconds() / 3600
    t = e.groupby(["activity", "next_activity"])["wait_h"].agg(count="size", mean_h="mean", median_h="median", p90_h=lambda s: s.quantile(.9), total_h="sum").reset_index()
    t["segment"] = np.where(t["activity"].isin(["Purchase Order Created", "Inbound Delivery Created"]), "Procurement / supplier lead time", "Internal handover")
    t["share_of_total_wait"] = t["total_h"] / t.groupby("segment")["total_h"].transform("sum")
    return t.sort_values("total_h", ascending=False).reset_index(drop=True)


def cycle_time_summary(cases: pd.DataFrame) -> pd.DataFrame:
    c = cases[cases.status == "Completed"]
    return c.groupby("case_type")["duration_h"].describe(percentiles=[.5, .9, .95]).reset_index()


def rework_loops(ev: pd.DataFrame) -> pd.DataFrame:
    r = ev.groupby(["case_id", "case_type", "activity"]).agg(n=("event_id", "size"), zone=("zone", "first")).reset_index()
    r = r[r.n > 1]
    total = ev.groupby("case_type")["case_id"].nunique()
    out = r.groupby(["case_type", "activity"]).agg(cases=("case_id", "size"), extra_executions=("n", lambda s: int((s - 1).sum()))).reset_index()
    out["pct_of_cases"] = out.apply(lambda x: x.cases / total[x.case_type], axis=1)
    return out.sort_values("cases", ascending=False)


def deviation_summary(conf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t, g in conf[conf.status != "Open"].groupby("case_type"):
        rows.append(dict(case_type=t, cases=len(g), deviation_cases=int(g.deviation.sum()), deviation_rate=g.deviation.mean(),
                         missing_rate=g.has_missing.mean(), out_of_order_rate=g.has_out_of_order.mean(), rework_rate=g.has_rework.mean(), mean_fitness=g.fitness.mean()))
    return pd.DataFrame(rows)


def deviation_detail(conf: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for col, label in (("missing", "Missing mandatory activity"), ("out_of_order", "Out-of-order activity"), ("repeated", "Repeated activity (rework)")):
        s = conf[conf[col] != ""][col].str.split("; ").explode()
        parts.append(s.value_counts().rename_axis("detail").reset_index(name="cases").assign(deviation_type=label))
    return pd.concat(parts)[["deviation_type", "detail", "cases"]]


def root_cause(cases: pd.DataFrame, conf: pd.DataFrame, con: sqlite3.Connection) -> pd.DataFrame:
    mats = pd.read_sql("SELECT material_id, category, storage_condition, uom FROM materials", con)
    mats["storage_condition_missing"] = mats.storage_condition.isna().map({True: "missing", False: "present"})
    mats["uom_valid"] = mats.uom.isin(VALID_UOM).map({True: "valid", False: "invalid"})
    orders = pd.read_sql("SELECT order_id, requested_dispatch_ts FROM customer_orders", con, parse_dates=["requested_dispatch_ts"])
    od = pd.read_sql("SELECT order_id, dispatch_ts, stockout_flag FROM outbound_deliveries", con, parse_dates=["dispatch_ts"])
    d = cases.merge(conf[["case_id", "deviation", "has_rework"]], on="case_id").merge(mats, on="material_id", how="left")
    d = d[d.status != "Open"]
    out = []
    ib = d[(d.case_type == "INBOUND") & (d.status != "Cancelled")]
    for dim in ["supplier_id", "category", "zone", "storage_condition_missing", "uom_valid"]:
        for val, g in ib.groupby(dim):
            out.append(dict(case_type="INBOUND", dimension=dim, value=val, cases=len(g), deviation_rate=g.deviation.mean(), rework_rate=g.has_rework.mean(),
                            mean_duration_h=g.duration_h.mean(), outcome="deviation_rate"))
    ob = d[(d.case_type == "OUTBOUND") & (d.status == "Completed")].merge(orders, left_on="reference_id", right_on="order_id").merge(od, on="order_id")
    ob["late"] = ob.dispatch_ts > ob.requested_dispatch_ts
    ob["backorder"] = ob.stockout_flag.map({1: "backorder", 0: "no backorder"})
    for dim in ["backorder", "zone", "priority"]:
        for val, g in ob.groupby(dim):
            out.append(dict(case_type="OUTBOUND", dimension=dim, value=val, cases=len(g), deviation_rate=g.late.mean(), rework_rate=g.has_rework.mean(),
                            mean_duration_h=g.duration_h.mean(), outcome="late_dispatch_rate"))
    r = pd.DataFrame(out)
    base = r.groupby("case_type").apply(lambda g: np.average(g.deviation_rate, weights=g.cases) if len(g) else np.nan, include_groups=False)
    r["rate_vs_group_avg"] = r.apply(lambda x: x.deviation_rate / base[x.case_type] if base[x.case_type] else np.nan, axis=1)
    return r.sort_values(["case_type", "rate_vs_group_avg"], ascending=[True, False])


def analyze(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    ev = load_events(con); cases = case_table(ev); conf = conformance(ev, cases)
    return dict(cases=cases, conformance=conf, variants_inbound=variants(cases, "INBOUND"), variants_outbound=variants(cases, "OUTBOUND"),
                transitions_inbound=transitions(ev, "INBOUND"), transitions_outbound=transitions(ev, "OUTBOUND"), cycle_times=cycle_time_summary(cases),
                rework_loops=rework_loops(ev), deviation_summary=deviation_summary(conf), deviation_detail=deviation_detail(conf), root_cause=root_cause(cases, conf, con))
