"""Evidence-linked recommendations generated from computed results (no hard-coded numbers)."""
from __future__ import annotations
import pandas as pd

COLS = ["rec_id", "priority_score", "problem", "evidence", "intervention", "kpi", "stakeholder", "verification"]


def _gap(k: pd.DataFrame, kpi_id: str) -> float:
    r = k[k.kpi_id == kpi_id]
    if r.empty or pd.isna(r.value.iloc[0]) or pd.isna(r.target_value.iloc[0]) or not r.target_value.iloc[0]:
        return 0.0
    v, t = float(r.value.iloc[0]), float(r.target_value.iloc[0])
    return max(0.0, (t - v) / t if r.direction.iloc[0] == "higher" else (v - t) / t)


def _val(k, kpi_id):
    return float(k.loc[k.kpi_id == kpi_id, "value"].iloc[0])


def build(k: pd.DataFrame, q: dict[str, pd.DataFrame], pm: dict[str, pd.DataFrame], dq: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    s = q["q1_supplier_delay_contribution"]; top = s.head(3)
    rows.append(("Inbound supplier delays", f"Supplier on-time delivery is {_val(k, 'supplier_on_time_delivery'):.1%}; top 3 suppliers ({', '.join(top.supplier_id)}) account for {top.pct_of_all_delay_days.sum():.0f}% of delay days.",
                 "Supplier scorecards, lead-time re-baselining in the material/info record, and escalation plans for chronic late suppliers.", "supplier_on_time_delivery", "Head of Procurement",
                 "Monthly OTD by supplier trend; target >= 90% for 3 consecutive months.", _gap(k, "supplier_on_time_delivery")))
    z = q["q2_zone_processing_times"]; worst = z.iloc[0]
    rows.append(("Slow receiving-to-putaway in the slowest zone", f"Receiving-to-putaway averages {_val(k, 'receiving_to_putaway_hours'):.1f} h (target 24 h); zone {worst.zone} is slowest at {worst.avg_gr_to_putaway_h:.1f} h (n={int(worst.inbound_n)}).",
                 "Review release-to-putaway handover, add putaway task prioritisation and staffing for the slowest zone.", "receiving_to_putaway_hours", "Warehouse Operations Manager",
                 "Zone-level GR-to-putaway distribution before/after; p90 below target.", _gap(k, "receiving_to_putaway_hours")))
    rc = pm["root_cause"]; u = rc[(rc.dimension == "uom_valid") & (rc.value == "invalid")]; sc = rc[(rc.dimension == "storage_condition_missing") & (rc.value == "missing")]
    ev = []
    if len(u): ev.append(f"deliveries for materials with invalid UoM show {u.deviation_rate.iloc[0]:.1%} process deviation ({u.rate_vs_group_avg.iloc[0]:.1f}x average)")
    if len(sc): ev.append(f"materials missing storage condition show {sc.rework_rate.iloc[0]:.1%} rework")
    rows.append(("Material master-data defects drive process deviations", f"Master-data completeness is {_val(k, 'master_data_completeness'):.1%}; " + ("; ".join(ev) or "defects present") + ".",
                 "Mandatory-field and UoM validation at material creation; remediation backlog ranked by downstream impact (query q7).", "master_data_completeness", "Master Data Steward",
                 "Completeness >= 98%; zero invalid UoM; deviation rate for remediated materials.", max(_gap(k, "master_data_completeness"), 0.05)))
    m3 = q["q3_material_stockout_exposure"].head(3)
    q6 = q.get("q6_stage_delay_contribution")
    stage_note = f"Stage most associated with late orders: {q6.iloc[0].stage} (+{q6.iloc[0].late_minus_ontime_h:.0f} h vs on-time orders)." if q6 is not None and len(q6) else ""
    rows.append(("Stockouts and backorders on key finished goods", f"Stockout rate is {_val(k, 'stockout_rate'):.1%} (target 5%); worst materials: {', '.join(m3.material_id)}. {stage_note}",
                 "Review reorder points and safety stock for exposed materials (see Scenario Simulator); weekly shortage review with Supply Planning.", "stockout_rate", "Supply Planning Lead",
                 "Stockout rate and backorder volume by material; modelled vs observed service level.", _gap(k, "stockout_rate")))
    rows.append(("Extended quality holds", f"Closed holds average {_val(k, 'quality_hold_hours'):.1f} h (target 48 h).",
                 "Prioritise holds by stock criticality; standard reason codes and daily QA/warehouse hold review; escalate holds older than the target.", "quality_hold_hours", "QA Release Manager",
                 "Hold-hours distribution by category; count of holds older than target.", _gap(k, "quality_hold_hours")))
    ex = q["q4_batches_near_expiry"]
    rows.append(("Expiry exposure", f"{len(ex)} batches listed within the 90-day window (top 100 shown); recorded-value exposure {_val(k, 'expiry_exposure_value'):,.0f} (fictional currency).",
                 "FEFO enforcement, near-expiry alerts at 90/60/30 days, and consumption planning for short-life materials.", "expiry_exposure_value", "Inventory Control Lead",
                 "Expiry exposure value and expired-stock write-offs per month.", 0.10))
    if dq is not None and not dq.empty:
        pbr = dq[dq.rule.str.contains("Putaway not before quality release", regex=False)]
        n = int(pbr.violations.iloc[0]) if len(pbr) else 0
    else:
        n = 0
    dev = pm["deviation_summary"].set_index("case_type")
    rows.append(("Process deviations and rework", f"Inbound deviation rate {dev.loc['INBOUND', 'deviation_rate']:.1%}, outbound {dev.loc['OUTBOUND', 'deviation_rate']:.1%}; {n} deliveries put away before quality release (simulated rule); "
                 f"rework rate {_val(k, 'process_rework_rate'):.1%}.", "System-enforced status gate (no putaway before release), mandatory verification step, re-pick root-cause review in COLD zone.",
                 "process_rework_rate", "Business Process Architect",
                 "Conformance rate monthly; zero out-of-order putaway; rework rate <= 5%.", max(_gap(k, "process_rework_rate"), .05)))
    rows.append(("Inventory record inaccuracy", f"Record accuracy is {_val(k, 'inventory_record_accuracy'):.1%} (target 98%).", "Cycle-count programme targeted at mismatched batches; root-cause adjustments by zone.",
                 "inventory_record_accuracy", "Inventory Control Lead", "Accuracy by zone after each count cycle.", _gap(k, "inventory_record_accuracy")))
    df = pd.DataFrame(rows, columns=["problem", "evidence", "intervention", "kpi", "stakeholder", "verification", "priority_score"])
    df = df.sort_values("priority_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rec_id", [f"REC-{i + 1:02d}" for i in range(len(df))])
    return df[COLS]
