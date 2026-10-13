"""PharmaFlow Intelligence - Streamlit UI. Presentation only; all calculations live in src/. DATA IS SYNTHETIC (fictional company)."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.db import ROOT, connect, db_path, load_config
from src.data.validation import MASTER_ATTRS, material_exceptions, run_checks, PK
from src.analytics import metrics as M
from src.analytics.kpis import compute_kpis, kpi_dictionary
from src.analytics.queries import run_all, TITLES
from src.process_mining.analysis import analyze
from src.reporting.recommendations import build as build_recs
from src.simulation.model import PARAMS, build_baseline, compare, simulate, scenario_table

st.set_page_config(page_title="PharmaFlow Intelligence", page_icon="💊", layout="wide")
st.markdown("<style>.block-container{padding-top:1.5rem} [data-testid=stMetricValue]{font-size:1.6rem}</style>", unsafe_allow_html=True)
CFG = load_config()
DB = db_path(CFG)
START = pd.Timestamp(CFG["data"]["start_date"]); END = START + pd.DateOffset(months=CFG["data"]["months"])
FMT = "%Y-%m-%d %H:%M:%S"
if not DB.exists():
    st.error("Database not found. Build it from a terminal:  `bash scripts/run_pipeline.sh`")
    st.stop()
MT = DB.stat().st_mtime


@st.cache_data(show_spinner="Loading data...")
def load(_mt):
    con = connect(CFG)
    out = dict(inb=M.inbound_frame(con), out=M.outbound_frame(con), inv=M.inventory_frame(con, END.strftime("%Y-%m-%d")),
               mov=pd.read_sql("SELECT movement_type, zone, movement_ts FROM warehouse_movements", con, parse_dates=["movement_ts"]),
               mats=pd.read_sql("SELECT * FROM materials", con), targets=pd.read_sql("SELECT * FROM kpi_targets", con),
               queries=run_all(con, END.strftime("%Y-%m-%d")), pm=analyze(con),
               tables={n: pd.read_sql(f"SELECT * FROM {n}", con) for n in PK})
    out["dq"] = run_checks(out["tables"], END)
    con.close()
    return out


@st.cache_data(show_spinner=False)
def kpis_for(_mt, s, e):
    con = connect(CFG); k = compute_kpis(con, s, e); con.close()
    pm = D["pm"]["deviation_summary"]
    dn, dd = int(pm.deviation_cases.sum()), int(pm.cases.sum())
    k = pd.concat([k, pd.DataFrame([dict(kpi_id="process_deviation_rate", name="Process deviation rate", unit="ratio", numerator=dn, denominator=dd, value=dn / dd)])], ignore_index=True)
    return _attach_targets(k)


def _attach_targets(k):
    t = D["targets"]
    k = k.drop(columns=[c for c in ("target_value", "direction") if c in k.columns]).merge(t[["kpi_id", "target_value", "direction"]], on="kpi_id", how="left")
    return k


D = load(MT)
KD = kpi_dictionary().set_index("kpi_id")


def fmt(v, unit):
    if v is None or pd.isna(v): return "n/a"
    return f"{v:.1%}" if unit == "ratio" else f"{v:,.1f} h" if unit == "hours" else f"{v:,.0f}"


def card(col, row):
    v, t = row.value, row.target_value
    delta, dc = None, "off"
    if pd.notna(v) and pd.notna(t):
        diff = v - t
        delta = (f"{diff:+.1%}" if row.unit == "ratio" else f"{diff:+.1f} h") + " vs target"
        dc = "normal" if row.direction == "higher" else "inverse"
    col.metric(row["name"], fmt(v, row.unit), delta, delta_color=dc, help=KD.loc[row.kpi_id, "numerator"] + " / " + KD.loc[row.kpi_id, "denominator"] if row.kpi_id in KD.index else None)


def dl(df, name, label="Download CSV"):
    st.download_button(label, df.to_csv(index=False).encode(), file_name=name, mime="text/csv", key=f"dl_{name}")


def date_range(key):
    a, b = st.slider("Date window", START.date(), END.date(), (START.date(), END.date()), key=key)
    return pd.Timestamp(a), pd.Timestamp(b) + pd.Timedelta(days=1)


# ------------------------------------------------------------------ pages
def page_exec():
    st.title("Executive Overview")
    s, e = date_range("exec_dates")
    k = kpis_for(MT, s.strftime(FMT), e.strftime(FMT))
    show = ["supplier_on_time_delivery", "on_time_dispatch_rate", "order_fulfilment_rate", "stockout_rate", "inventory_record_accuracy",
            "receiving_to_putaway_hours", "quality_hold_hours", "process_rework_rate", "master_data_completeness", "process_deviation_rate"]
    cols = st.columns(5)
    for i, kid in enumerate(show):
        card(cols[i % 5], k[k.kpi_id == kid].iloc[0])
    st.caption("Snapshot KPIs (inventory accuracy, master data), process KPIs (rework/deviation) use the full dataset; other KPIs use the date window.")
    inb = D["inb"][(D["inb"].arrival_ts >= s) & (D["inb"].arrival_ts < e)]; out = D["out"][(D["out"].order_ts >= s) & (D["out"].order_ts < e)]
    tr = M.monthly_trend(inb, out)
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.line(tr, x="month", y=["supplier_otd", "on_time_dispatch"], markers=True, title="On-time performance by month").update_yaxes(tickformat=".0%", title=None), width="stretch")
    c2.plotly_chart(px.line(tr, x="month", y=["stockout_rate"], markers=True, title="Stockout rate by month").update_yaxes(tickformat=".0%", title=None), width="stretch")
    recs = build_recs(_attach_targets(k), D["queries"], D["pm"], D["dq"])
    st.subheader("Top priorities")
    st.dataframe(recs.head(5)[["rec_id", "problem", "evidence", "stakeholder"]], hide_index=True, width="stretch")
    with st.expander("All KPIs (numerator / denominator / value)"):
        st.dataframe(k[["kpi_id", "numerator", "denominator", "value", "target_value"]], hide_index=True, width="stretch")
        dl(k, "kpis.csv")


def page_wh():
    st.title("Warehouse Operations")
    zones = st.multiselect("Zone", ["AMB", "COLD", "CTRL"], default=["AMB", "COLD", "CTRL"])
    pri = st.multiselect("Order priority", ["High", "Standard", "Low"], default=["High", "Standard", "Low"])
    inb = D["inb"][D["inb"].zone.isin(zones)]; out = D["out"][D["out"].zone.isin(zones) & D["out"].priority.isin(pri) & D["out"].dispatch_ts.notna()]
    if inb.empty or out.empty:
        st.warning("No records match the current filters."); return
    c = st.columns(4)
    c[0].metric("Avg GR to putaway", f"{inb.gr_to_putaway_h.mean():.1f} h"); c[1].metric("Avg picking", f"{out.picking_h.mean():.2f} h")
    c[2].metric("Re-pick rate", f"{out.repick_flag.mean():.1%}"); c[3].metric("On-time dispatch", f"{1 - out.late.mean():.1%}")
    a, b = st.columns(2)
    a.plotly_chart(px.box(inb.dropna(subset=["gr_to_putaway_h"]), x="zone", y="gr_to_putaway_h", points=False, title="GR to putaway (h) by zone"), width="stretch")
    b.plotly_chart(px.box(out, x="zone", y="picking_h", points=False, title="Picking duration (h) by zone"), width="stretch")
    sd = M.stage_delay(out)
    st.plotly_chart(px.bar(sd, x="stage", y=["avg_on_time", "avg_late"], barmode="group", title="Average hours per outbound stage: on-time vs late orders"), width="stretch")
    mv = D["mov"][D["mov"].movement_type != "STATUS_CHANGE"].assign(month=lambda d: d.movement_ts.dt.to_period("M").astype(str))
    st.plotly_chart(px.bar(mv.groupby(["month", "movement_type"]).size().reset_index(name="movements"), x="month", y="movements", color="movement_type", title="Warehouse throughput (movements per month)"), width="stretch")
    st.subheader("Exceptions")
    ex = out[out.repick_flag == 1][["order_id", "material_id", "zone", "priority", "picking_h", "order_to_dispatch_h"]].round(2)
    st.write(f"Re-picked orders ({len(ex)})"); st.dataframe(ex, hide_index=True, width="stretch"); dl(ex, "repick_orders.csv")
    pb = inb[inb.putaway_before_release][["delivery_id", "supplier_id", "material_id", "zone", "decision_ts", "putaway_ts"]]
    st.write(f"Putaway before quality release ({len(pb)}) - simulated rule"); st.dataframe(pb, hide_index=True, width="stretch"); dl(pb, "putaway_before_release.csv")


def page_inv():
    st.title("Inventory and Expiry Risk")
    inv = D["inv"]
    cats = st.multiselect("Material category", sorted(inv.category.unique()), default=sorted(inv.category.unique()))
    win = st.slider("Expiry window (days from snapshot)", 30, 365, 90, 15)
    inv = inv[inv.category.isin(cats)]
    if inv.empty: st.warning("No records match the current filters."); return
    pos = M.inventory_position(inv)
    st.plotly_chart(px.bar(pos, x="concept", y="value", text_auto=".3s", title="Four inventory concepts (value at unit cost, fictional currency)"), width="stretch")
    ex = M.expiry_exposure(inv, win)
    c = st.columns(3); c[0].metric("Batches in window", f"{len(ex):,}"); c[1].metric("Exposure value", f"{ex.recorded_value.sum():,.0f}")
    c[2].metric("Record accuracy", f"{1 - inv[inv.recorded_qty > 0].mismatch.mean():.1%}")
    st.plotly_chart(px.bar(ex.groupby(["category", "bucket"]).recorded_value.sum().reset_index(), x="category", y="recorded_value", color="bucket", title="Expiry exposure by category"), width="stretch")
    st.subheader("Near-expiry / expired batches"); t = ex[["batch_id", "material_id", "category", "stock_status", "recorded_qty", "recorded_value", "days_to_expiry", "bucket"]].round(1)
    st.dataframe(t.head(200), hide_index=True, width="stretch"); dl(t, "expiry_batches.csv")
    st.subheader("Recorded vs physical mismatches (>2%)"); mm = inv[inv.mismatch][["batch_id", "material_id", "category", "recorded_qty", "physical_qty", "abs_diff_qty"]].sort_values("abs_diff_qty", ascending=False).round(1)
    st.dataframe(mm, hide_index=True, width="stretch"); dl(mm, "inventory_mismatches.csv")


def page_sup():
    st.title("Supplier Performance")
    s, e = date_range("sup_dates")
    inb = D["inb"][(D["inb"].arrival_ts >= s) & (D["inb"].arrival_ts < e)]
    sel = st.multiselect("Suppliers (empty = all)", sorted(inb.supplier_id.unique()))
    if sel: inb = inb[inb.supplier_id.isin(sel)]
    if inb.empty: st.warning("No records match the current filters."); return
    sc = M.supplier_scorecard(inb)
    c = st.columns(4); c[0].metric("Deliveries", f"{len(inb):,}"); c[1].metric("On-time delivery", f"{inb.on_time.mean():.1%}")
    c[2].metric("Avg delay (late only)", f"{inb[inb.delay_days > 0].delay_days.mean():.1f} d" if (inb.delay_days > 0).any() else "n/a"); c[3].metric("Partial deliveries", f"{inb.partial_flag.mean():.1%}")
    a, b = st.columns(2)
    a.plotly_chart(px.bar(sc.head(15), x="supplier_id", y="total_delay_days", hover_data=["otd", "pct_of_delay_days"], title="Delay days by supplier (Pareto, top 15)"), width="stretch")
    b.plotly_chart(px.box(inb.dropna(subset=["hold_hours"]), x="category", y="hold_hours", points=False, title="Quality-hold hours by material category"), width="stretch")
    st.dataframe(sc.round(3), hide_index=True, width="stretch"); dl(sc, "supplier_scorecard.csv")


def page_pm():
    st.title("Process Mining")
    pm = D["pm"]; ct = st.radio("Process", ["INBOUND", "OUTBOUND"], horizontal=True)
    ds = pm["deviation_summary"].set_index("case_type").loc[ct]
    c = st.columns(4); c[0].metric("Cases (closed)", f"{int(ds.cases):,}"); c[1].metric("Deviation rate", f"{ds.deviation_rate:.1%}"); c[2].metric("Rework rate", f"{ds.rework_rate:.1%}"); c[3].metric("Mean fitness", f"{ds.mean_fitness:.3f}")
    st.caption("Deviations are breaches of SIMULATED rules (missing mandatory step / out-of-order step), not confirmed regulatory violations.")
    v = pm["variants_inbound" if ct == "INBOUND" else "variants_outbound"]
    st.subheader("Process variants"); st.dataframe(v.head(15).round(3), hide_index=True, width="stretch"); st.plotly_chart(px.bar(v.head(10), x="variant_id", y="cases", hover_data=["variant"], title="Top variants"), width="stretch")
    tr = pm["transitions_inbound" if ct == "INBOUND" else "transitions_outbound"]
    if "segment" in tr.columns:
        seg = st.selectbox("Segment", sorted(tr.segment.unique()), index=sorted(tr.segment.unique()).index("Internal handover")); tr = tr[tr.segment == seg]
    tr = tr.assign(step=tr.activity + " → " + tr.next_activity).head(12)
    st.plotly_chart(px.bar(tr, x="mean_h", y="step", orientation="h", hover_data=["count", "p90_h", "total_h"], title="Handover waits (mean hours) - bottlenecks").update_yaxes(autorange="reversed"), width="stretch")
    cs = pm["cases"]; cs = cs[(cs.case_type == ct) & (cs.status == "Completed")]
    st.plotly_chart(px.histogram(cs, x="duration_h", nbins=50, title="Cycle-time distribution, completed cases (h)"), width="stretch")
    a, b = st.columns(2)
    a.subheader("Deviations"); a.dataframe(pm["deviation_detail"], hide_index=True, width="stretch")
    b.subheader("Rework loops"); b.dataframe(pm["rework_loops"][pm["rework_loops"].case_type == ct].round(3), hide_index=True, width="stretch")
    st.subheader("Root-cause investigation (rate vs group average)")
    rc = pm["root_cause"]; rc = rc[rc.case_type == ct]; st.dataframe(rc.round(3).head(25), hide_index=True, width="stretch")
    conf = pm["conformance"]; conf = conf[(conf.case_type == ct) & (conf.deviation)]
    st.write(f"Deviating cases ({len(conf)})"); st.dataframe(conf[["case_id", "status", "missing", "out_of_order", "repeated", "fitness"]].round(3), hide_index=True, width="stretch"); dl(conf, f"deviating_cases_{ct.lower()}.csv")


def page_dq():
    st.title("Material Master Data Quality")
    dq = D["dq"]; sev = st.multiselect("Severity", ["Critical", "High", "Medium"], default=["Critical", "High", "Medium"])
    f = dq[dq.severity.isin(sev) & (dq.violations > 0)]
    c = st.columns(3); c[0].metric("Rules evaluated", len(dq)); c[1].metric("Rules failing", int((dq.violations > 0).sum())); c[2].metric("Critical failing", int(((dq.severity == "Critical") & (dq.violations > 0)).sum()))
    st.dataframe(f, hide_index=True, width="stretch"); dl(dq, "dq_findings.csv")
    comp = M.completeness_by_attribute(D["mats"], MASTER_ATTRS)
    st.plotly_chart(px.bar(comp, x="attribute", y="populated", text_auto=".1%", title="Completeness by attribute").update_yaxes(tickformat=".0%", range=[0, 1.02]), width="stretch")
    me = material_exceptions(D["mats"]); st.subheader(f"Materials with defects ({len(me)})"); st.dataframe(me, hide_index=True, width="stretch"); dl(me, "material_exceptions.csv")
    st.subheader("Remediation priority (ranked by downstream impact)"); st.dataframe(D["queries"]["q7_data_quality_priority"].head(25), hide_index=True, width="stretch")


def page_sim():
    st.title("Supply-Chain Scenario Simulator")
    st.caption("Modelled estimates on SYNTHETIC data; no causal claims. Baseline lead time is calibrated to the observed stockout rate. See Methodology.")
    base = build_baseline_cached(MT)
    names = {k: v["label"] for k, v in CFG["scenarios"].items()}
    preset = st.selectbox("Start from preset", list(names), format_func=lambda k: names[k], index=1)
    spec = dict(supplier_lead_time_mult=("Supplier lead-time multiplier", .5, 2.5, .05), demand_growth=("Demand growth", -.2, .6, .01), receiving_hours=("Receiving duration (h)", .5, 8., .25),
                putaway_hours=("Putaway duration (h)", 1., 16., .5), picking_hours=("Picking duration (h)", .3, 2., .05), warehouse_capacity_mult=("Warehouse capacity multiplier", .6, 1.6, .05),
                reorder_point_mult=("Reorder-point multiplier", .5, 2., .05), safety_stock_mult=("Safety-stock multiplier", .5, 2.5, .05),
                holding_cost_rate=("Holding cost rate (annual)", .05, .4, .01), expiry_window_days=("Expiry window (days)", 30, 180, 5))
    p, cols = {}, st.columns(2)
    for i, (k, (lab, lo, hi, stp)) in enumerate(spec.items()):
        v = CFG["scenarios"][preset][k]
        p[k] = cols[i % 2].slider(lab, float(lo), float(hi), float(v), float(stp), key=f"{preset}_{k}")
    custom = simulate(base, p, CFG)
    tbl = scenario_table(base, CFG); tbl.loc["custom"] = custom
    cmp = compare(tbl.loc[["baseline", "custom"]], "baseline")
    show = ["stockout_risk", "service_level", "avg_order_delay_h", "expiry_exposure_value", "throughput_capacity_orders_per_day", "warehouse_utilisation", "operating_cost"]
    st.dataframe(cmp[cmp.metric.isin(show)].round(4), hide_index=True, width="stretch")
    st.plotly_chart(px.bar(tbl.reset_index().melt(id_vars="index", value_vars=["stockout_risk", "avg_order_delay_h", "warehouse_utilisation"]), x="variable", y="value", color="index", barmode="group",
                           title="Scenario comparison (modelled)").update_layout(legend_title="scenario"), width="stretch")
    st.subheader("All scenarios"); st.dataframe(tbl.round(3).T, width="stretch"); dl(tbl.reset_index().rename(columns={"index": "scenario"}), "scenario_results.csv")


@st.cache_data(show_spinner="Calibrating model...")
def build_baseline_cached(_mt):
    con = connect(CFG); b = build_baseline(con, CFG); con.close(); return b


def page_rec():
    st.title("Recommendations and Improvement Tracking")
    k = kpis_for(MT, START.strftime(FMT), END.strftime(FMT))
    recs = build_recs(_attach_targets(k), D["queries"], D["pm"], D["dq"])
    if "tracking" not in st.session_state:
        st.session_state["tracking"] = recs.assign(status="Proposed", owner="", notes="")
    st.caption("Edit status/owner/notes below (session only). Each recommendation links problem -> evidence -> intervention -> KPI -> stakeholder -> verification.")
    ed = st.data_editor(st.session_state["tracking"], hide_index=True, width="stretch", disabled=[c for c in recs.columns],
                        column_config={"status": st.column_config.SelectboxColumn("status", options=["Proposed", "Approved", "In progress", "Verified", "Rejected"])})
    st.session_state["tracking"] = ed
    dl(ed, "recommendations_tracking.csv")


def page_method():
    st.title("Methodology and Data Limitations")
    st.warning("All data, the company (Nordvale Pharmaceuticals), results and cost assumptions are FICTIONAL and synthetic. No Merck systems or data were accessed. This is process design, not SAP configuration.")
    st.markdown("""
**Scope.** Supplier PO → delivery → goods receipt → verification → quality inspection → release/hold → putaway → availability → allocation → pick → pack → dispatch → reconciliation.
**Process mining.** Pure-pandas discovery (variants, directly-follows waits), conformance against simulated rules, rework (repeated activities), root-cause by dimension. Inbound cycle time starts at PO creation, so it includes supplier lead time (shown separately from internal handovers).
**Simulator.** Reorder-point policy with normal lead-time demand and a loss-function shortage estimate; labour-hour utilisation with an M/M/1-style queue. Baseline replenishment lead time is calibrated to the observed stockout rate. Results are modelled estimates, not causal improvements.
**Key limitations.** Single-line orders; stockouts flagged per order (no daily stock simulation); inventory snapshot only; day-level OTD; open quality holds are right-censored; units mix EA/BOX/KG.""")
    d = kpi_dictionary(); st.dataframe(d, hide_index=True, width="stretch"); dl(d, "kpi_dictionary.csv")


PAGES = {"Executive Overview": page_exec, "Warehouse Operations": page_wh, "Inventory and Expiry Risk": page_inv, "Supplier Performance": page_sup,
         "Process Mining": page_pm, "Material Master Data Quality": page_dq, "Scenario Simulator": page_sim, "Recommendations and Tracking": page_rec,
         "Methodology and Limitations": page_method}
st.sidebar.title("💊 PharmaFlow Intelligence")
st.sidebar.caption("Synthetic data · fictional company")
choice = st.sidebar.radio("Section", list(PAGES))
PAGES[choice]()
