"""Data-quality rules. Each rule returns a finding row; nothing is silently coerced."""
from __future__ import annotations
import pandas as pd
from .generator import VALID_UOM

MASTER_ATTRS = ["uom", "shelf_life_days", "storage_condition", "abc_class", "gmp_relevant", "net_weight_kg"]
ALLOWED_TRANSITIONS = {
    "Quality Hold": {"Released", "Rejected", "Blocked"},
    "Blocked": {"Released", "Rejected", "Quality Hold"},
    "Released": {"Blocked", "Quality Hold"},
    "Rejected": set(),
}
PK = {"suppliers": "supplier_id", "materials": "material_id", "warehouse_bins": "bin_id", "purchase_orders": "po_id", "po_lines": "po_line_id",
      "inbound_deliveries": "delivery_id", "inventory_batches": "batch_id", "quality_inspections": "inspection_id",
      "warehouse_movements": "movement_id", "production_requests": "request_id", "customer_orders": "order_id",
      "outbound_deliveries": "outbound_id", "event_log": "event_id"}


def _row(rule_id, rule, table, severity, bad: int, total: int, sample=None):
    return dict(rule_id=rule_id, rule=rule, table=table, severity=severity, violations=int(bad), total=int(total),
                violation_pct=round(bad / total, 4) if total else None, sample_ids=",".join(map(str, list(sample)[:5])) if sample is not None else "")


def run_checks(t: dict[str, pd.DataFrame], snapshot: pd.Timestamp | None = None) -> pd.DataFrame:
    out = []
    # DQ-01 duplicate IDs
    for tb, pk in PK.items():
        dup = t[tb][t[tb][pk].duplicated(keep=False)][pk]
        out.append(_row("DQ-01", "Primary key unique", tb, "Critical", len(dup), len(t[tb]), dup))
    # DQ-02 referential integrity
    refs = [("po_lines", "po_id", "purchase_orders", "po_id"), ("po_lines", "material_id", "materials", "material_id"),
            ("purchase_orders", "supplier_id", "suppliers", "supplier_id"), ("inbound_deliveries", "po_line_id", "po_lines", "po_line_id"),
            ("inventory_batches", "material_id", "materials", "material_id"), ("quality_inspections", "batch_id", "inventory_batches", "batch_id"),
            ("warehouse_movements", "batch_id", "inventory_batches", "batch_id"), ("outbound_deliveries", "order_id", "customer_orders", "order_id"),
            ("customer_orders", "material_id", "materials", "material_id")]
    for ct, ck, pt, pk in refs:
        bad = t[ct][~t[ct][ck].isin(t[pt][pk])][ck]
        out.append(_row("DQ-02", f"{ct}.{ck} -> {pt}.{pk}", ct, "Critical", len(bad), len(t[ct]), bad))
    # DQ-03 missing values in material master
    m = t["materials"]
    for a in MASTER_ATTRS:
        bad = m[m[a].isna()]["material_id"]
        out.append(_row("DQ-03", f"Material master attribute '{a}' populated", "materials", "High" if a in ("storage_condition", "uom", "shelf_life_days") else "Medium", len(bad), len(m), bad))
    # DQ-04 unit of measure
    bad = m[~m["uom"].isin(VALID_UOM)]["material_id"]
    out.append(_row("DQ-04", "Material UoM in valid list", "materials", "High", len(bad), len(m), bad))
    pl = t["po_lines"].merge(m[["material_id", "uom"]], on="material_id", suffixes=("", "_m"))
    bad = pl[pl["uom"] != pl["uom_m"]]["po_line_id"]
    out.append(_row("DQ-04", "PO-line UoM equals material UoM", "po_lines", "High", len(bad), len(pl), bad))
    # DQ-05 timestamp validation
    snap = snapshot or pd.Timestamp.max
    d = t["inbound_deliveries"].copy()
    for c in ["arrival_ts", "gr_ts", "verification_ts", "putaway_ts"]:
        d[c] = pd.to_datetime(d[c])
    bad = d[d["gr_ts"] < d["arrival_ts"]]["delivery_id"]
    out.append(_row("DQ-05", "GR timestamp not before arrival", "inbound_deliveries", "High", len(bad), len(d), bad))
    bad = d[d["verification_ts"].notna() & (d["verification_ts"] < d["gr_ts"])]["delivery_id"]
    out.append(_row("DQ-05", "Verification not before GR", "inbound_deliveries", "High", len(bad), len(d), bad))
    q = t["quality_inspections"].merge(d[["delivery_id", "putaway_ts"]], on="delivery_id")
    q["decision_ts"] = pd.to_datetime(q["decision_ts"])
    bad = q[q["decision_ts"].notna() & q["putaway_ts"].notna() & (q["putaway_ts"] < q["decision_ts"])]["delivery_id"]
    out.append(_row("DQ-05", "Putaway not before quality release (simulated rule)", "inbound_deliveries", "High", len(bad), len(q), bad))
    o = t["outbound_deliveries"].copy()
    cols = ["allocation_ts", "pick_start_ts", "pick_end_ts", "pack_start_ts", "pack_end_ts", "dispatch_ts"]
    for c in cols:
        o[c] = pd.to_datetime(o[c])
    seqbad = pd.Series(False, index=o.index)
    for a, b in zip(cols[:-1], cols[1:]):
        seqbad |= o[b] < o[a]
    out.append(_row("DQ-05", "Outbound timestamps monotonic", "outbound_deliveries", "High", seqbad.sum(), len(o), o[seqbad]["outbound_id"]))
    ev = pd.to_datetime(t["event_log"]["event_ts"], errors="coerce")
    out.append(_row("DQ-05", "Event timestamps parse", "event_log", "Critical", ev.isna().sum(), len(ev)))
    out.append(_row("DQ-05", "Event timestamps not after snapshot", "event_log", "High", (ev > snap).sum(), len(ev)))
    # DQ-06 invalid stock transitions
    mv = t["warehouse_movements"]
    sc = mv[mv["movement_type"] == "STATUS_CHANGE"]
    inval = sc[[(f not in ALLOWED_TRANSITIONS) or (to not in ALLOWED_TRANSITIONS[f]) for f, to in zip(sc["status_from"], sc["status_to"])]]
    # GR sets initial status; only STATUS_CHANGE with Quality Hold -> Released/Rejected/On Hold(not a change) are checked
    inval = inval[inval["status_from"].notna()]
    out.append(_row("DQ-06", "Stock status transition allowed", "warehouse_movements", "Critical", len(inval), len(sc), inval["movement_id"]))
    # DQ-07 inventory arithmetic / negative quantities
    b = t["inventory_batches"]
    neg = b[(b[["recorded_qty", "physical_qty", "available_qty", "quality_restricted_qty"]] < 0).any(axis=1)]["batch_id"]
    out.append(_row("DQ-07", "No negative stock quantities", "inventory_batches", "Critical", len(neg), len(b), neg))
    over = b[b["available_qty"] + b["quality_restricted_qty"] > b["recorded_qty"] + 1e-6]["batch_id"]
    out.append(_row("DQ-07", "Available + restricted <= recorded", "inventory_batches", "High", len(over), len(b), over))
    mism = b[(b["recorded_qty"] > 0) & ((b["recorded_qty"] - b["physical_qty"]).abs() / b["recorded_qty"] > .02)]["batch_id"]
    out.append(_row("DQ-07", "Recorded vs physical within 2% tolerance", "inventory_batches", "Medium", len(mism), int((b["recorded_qty"] > 0).sum()), mism))
    return pd.DataFrame(out)


def material_exceptions(materials: pd.DataFrame) -> pd.DataFrame:
    """One row per material with at least one master-data defect."""
    m = materials.copy()
    for a in MASTER_ATTRS:
        m[f"missing_{a}"] = m[a].isna().astype(int)
    m["invalid_uom"] = (~m["uom"].isin(VALID_UOM) & m["uom"].notna()).astype(int)
    flag_cols = [c for c in m.columns if c.startswith("missing_")] + ["invalid_uom"]
    m["defect_count"] = m[flag_cols].sum(axis=1)
    return m[m["defect_count"] > 0].sort_values(["defect_count", "material_id"], ascending=[False, True])[["material_id", "category", "defect_count"] + flag_cols]
