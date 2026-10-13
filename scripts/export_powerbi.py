#!/usr/bin/env python
"""Export a star-schema model for Power BI (CSV) + documentation (relationships, DAX, pages, refresh)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data.db import ROOT, connect, load_config
from src.analytics.kpis import kpi_dictionary
from src.process_mining.analysis import analyze

cfg = load_config(); con = connect(cfg)
out = ROOT / cfg["paths"]["exports"] / "powerbi"; out.mkdir(parents=True, exist_ok=True)
q = lambda s: pd.read_sql(s, con)
start = pd.Timestamp(cfg["data"]["start_date"]); end = start + pd.DateOffset(months=cfg["data"]["months"])
dd = pd.DataFrame({"date": pd.date_range(start, end + pd.Timedelta(days=60))})
dd["date_key"] = dd.date.dt.strftime("%Y%m%d").astype(int); dd["year"] = dd.date.dt.year; dd["quarter"] = "Q" + dd.date.dt.quarter.astype(str)
dd["month"] = dd.date.dt.month; dd["month_name"] = dd.date.dt.strftime("%b"); dd["year_month"] = dd.date.dt.strftime("%Y-%m"); dd["week"] = dd.date.dt.isocalendar().week.astype(int)
dd["date"] = dd.date.dt.strftime("%Y-%m-%d")
dim = {
    "dim_date": dd,
    "dim_material": q("SELECT * FROM materials"),
    "dim_supplier": q("SELECT * FROM suppliers"),
    "dim_bin": q("SELECT bin_id, zone, capacity_units FROM warehouse_bins"),
    "dim_priority": pd.DataFrame({"priority": ["High", "Standard", "Low"], "sla_hours": [24, 72, 120]}),
    "dim_scenario": q("SELECT DISTINCT scenario FROM scenario_assumptions"),
}
dk = lambda col: f"CAST(strftime('%Y%m%d', {col}) AS INTEGER)"
fact = {
    "fact_inbound_delivery": q(f"""SELECT d.delivery_id, p.supplier_id, l.material_id, {dk('d.arrival_ts')} AS arrival_date_key, p.requested_delivery_date,
        d.arrival_ts, d.gr_ts, d.putaway_ts, d.delivered_qty, d.damaged_qty, d.partial_flag, d.rework_flag, d.status,
        MAX(0, julianday(date(d.arrival_ts))-julianday(date(p.requested_delivery_date))) AS delay_days,
        CASE WHEN date(d.arrival_ts) <= date(p.requested_delivery_date) THEN 1 ELSE 0 END AS on_time_flag,
        (julianday(d.putaway_ts)-julianday(d.gr_ts))*24 AS gr_to_putaway_h
        FROM inbound_deliveries d JOIN po_lines l USING(po_line_id) JOIN purchase_orders p USING(po_id)"""),
    "fact_quality_inspection": q(f"SELECT q.*, {dk('q.start_ts')} AS start_date_key FROM quality_inspections q"),
    "fact_outbound_order": q(f"""SELECT c.order_id, c.material_id, c.priority, c.customer_id, {dk('c.order_ts')} AS order_date_key, c.order_ts, c.requested_dispatch_ts, c.status,
        c.order_qty, o.zone, o.dispatch_ts, o.qty_backordered, o.stockout_flag, o.repick_flag,
        (julianday(o.dispatch_ts)-julianday(c.order_ts))*24 AS order_to_dispatch_h,
        (julianday(o.pick_end_ts)-julianday(o.pick_start_ts))*24 AS picking_h, (julianday(o.pack_end_ts)-julianday(o.pack_start_ts))*24 AS packing_h,
        CASE WHEN o.dispatch_ts <= c.requested_dispatch_ts THEN 1 WHEN o.dispatch_ts IS NULL THEN NULL ELSE 0 END AS on_time_flag
        FROM customer_orders c LEFT JOIN outbound_deliveries o USING(order_id)"""),
    "fact_inventory_snapshot": q("""SELECT b.*, m.unit_cost, b.recorded_qty*m.unit_cost AS recorded_value,
        CASE WHEN date(b.expiry_date) <= date(:s) THEN 'Expired' WHEN date(b.expiry_date) <= date(:s,'+90 day') THEN 'Expiring <=90d' ELSE 'OK' END AS expiry_bucket,
        CASE WHEN b.recorded_qty>0 AND ABS(b.recorded_qty-b.physical_qty) > 0.02*b.recorded_qty THEN 1 ELSE 0 END AS mismatch_flag
        FROM inventory_batches b JOIN materials m USING(material_id)""".replace(":s", f"'{end.strftime('%Y-%m-%d')}'")),
    "fact_warehouse_movement": q(f"SELECT w.*, {dk('w.movement_ts')} AS movement_date_key FROM warehouse_movements w"),
    "fact_event_log": q(f"SELECT e.*, {dk('e.event_ts')} AS event_date_key FROM event_log e"),
    "fact_kpi_target": q("SELECT * FROM kpi_targets"),
    "fact_scenario_assumption": q("SELECT * FROM scenario_assumptions"),
}
pm = analyze(con)
fact["fact_case_conformance"] = pm["conformance"].merge(pm["cases"][["case_id", "start", "end", "duration_h", "variant", "supplier_id", "material_id", "zone"]], on="case_id")
for n, df in {**dim, **fact}.items():
    df.to_csv(out / f"{n}.csv", index=False)
kpi_dictionary().to_csv(out / "kpi_dictionary.csv", index=False)

docs = ROOT / "docs" / "powerbi"; docs.mkdir(parents=True, exist_ok=True)
(docs / "relationships.md").write_text("""# Power BI model relationships (star schema)

All relationships are single-direction, many-to-one (fact -> dimension). Data is **synthetic**.

| From (fact) | Column | To (dimension) | Column |
|---|---|---|---|
| fact_inbound_delivery | arrival_date_key | dim_date | date_key |
| fact_inbound_delivery | supplier_id | dim_supplier | supplier_id |
| fact_inbound_delivery | material_id | dim_material | material_id |
| fact_quality_inspection | start_date_key | dim_date | date_key |
| fact_outbound_order | order_date_key | dim_date | date_key |
| fact_outbound_order | material_id | dim_material | material_id |
| fact_outbound_order | priority | dim_priority | priority |
| fact_inventory_snapshot | material_id | dim_material | material_id |
| fact_inventory_snapshot | bin_id | dim_bin | bin_id |
| fact_warehouse_movement | movement_date_key | dim_date | date_key |
| fact_warehouse_movement | material_id | dim_material | material_id |
| fact_event_log | event_date_key | dim_date | date_key |
| fact_event_log | material_id | dim_material | material_id |
| fact_case_conformance | material_id | dim_material | material_id |
| fact_scenario_assumption | scenario | dim_scenario | scenario |

Mark `dim_date` as the date table. Hide key columns in report view.
""")
(docs / "dax_measures.md").write_text("""# DAX measures

```DAX
Supplier OTD % = DIVIDE(SUM(fact_inbound_delivery[on_time_flag]), COUNTROWS(fact_inbound_delivery))
Avg GR to Putaway (h) = AVERAGE(fact_inbound_delivery[gr_to_putaway_h])
Quality Hold Avg (h) = CALCULATE(AVERAGE(fact_quality_inspection[hold_hours]), fact_quality_inspection[hold_flag] = 1)
Fulfilment Rate % = DIVIDE(CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[stockout_flag] = 0, fact_outbound_order[status] = "Dispatched"), CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[status] = "Dispatched"))
Stockout Rate % = DIVIDE(SUM(fact_outbound_order[stockout_flag]), CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[status] = "Dispatched"))
On-Time Dispatch % = DIVIDE(SUM(fact_outbound_order[on_time_flag]), CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[status] = "Dispatched"))
Avg Order-to-Dispatch (h) = AVERAGE(fact_outbound_order[order_to_dispatch_h])
Backorder Qty = SUM(fact_outbound_order[backordered_qty_placeholder])
Inventory Record Accuracy % = DIVIDE(CALCULATE(COUNTROWS(fact_inventory_snapshot), fact_inventory_snapshot[mismatch_flag] = 0, fact_inventory_snapshot[recorded_qty] > 0), CALCULATE(COUNTROWS(fact_inventory_snapshot), fact_inventory_snapshot[recorded_qty] > 0))
Expiry Exposure Value = CALCULATE(SUM(fact_inventory_snapshot[recorded_value]), fact_inventory_snapshot[expiry_bucket] <> "OK", fact_inventory_snapshot[stock_status] <> "Rejected")
Process Deviation % = DIVIDE(CALCULATE(COUNTROWS(fact_case_conformance), fact_case_conformance[deviation] = TRUE()), CALCULATE(COUNTROWS(fact_case_conformance), fact_case_conformance[status] <> "Open"))
Process Rework % = DIVIDE(CALCULATE(COUNTROWS(fact_case_conformance), fact_case_conformance[has_rework] = TRUE()), COUNTROWS(fact_case_conformance))
```
""".replace("Backorder Qty = SUM(fact_outbound_order[backordered_qty_placeholder])", "Backorder Qty = SUM(fact_outbound_order[qty_backordered])"))
(docs / "report_pages.md").write_text("""# Power BI report page specifications (6 pages)

1. **Executive Overview** - KPI cards (OTD, fulfilment, accuracy, deviation) vs `fact_kpi_target`; monthly trend of On-Time Dispatch %; top-5 issues table.
2. **Warehouse Operations** - throughput by month (fact_warehouse_movement), GR-to-putaway by zone (dim_bin / dim_material storage condition), picking/packing duration, re-pick rate.
3. **Inventory and Expiry Risk** - expiry_bucket by value, near-expiry batch table, recorded vs physical mismatch list, stock status split (available / restricted / physical / recorded).
4. **Supplier and Inbound Performance** - OTD by supplier, delay-days Pareto, partial delivery rate, quality hold duration by category.
5. **Process Mining** - variant table (fact_case_conformance), deviation by type, top handover waits, rework loops (Power BI visuals: matrix + decomposition tree).
6. **Improvement Tracking** - KPI vs target, scenario comparison (fact_scenario_assumption), recommendation status (manual table / SharePoint list).
""")
(docs / "refresh.md").write_text("""# Data refresh

```bash
bash scripts/run_pipeline.sh          # regenerates data/exports/powerbi/*.csv
```
In Power BI Desktop: Get Data > Folder (or Text/CSV) > `data/exports/powerbi/`, then Refresh. No `.pbix` file is shipped; build it from the CSVs
following `relationships.md`, `dax_measures.md` and `report_pages.md`. All data is synthetic.
""")
print({n: len(df) for n, df in {**dim, **fact}.items()})
