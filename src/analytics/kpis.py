"""KPI definitions + SQL implementation. Every KPI returns numerator, denominator, value; zero denominators give NULL (never 0)."""
from __future__ import annotations
import sqlite3
import pandas as pd

# :s / :e are inclusive start / exclusive end of the aggregation window (ISO timestamps) applied to the KPI's anchor event.
KPI_DEFS = [
    dict(kpi_id="inventory_record_accuracy", name="Inventory record accuracy", unit="ratio",
         numerator="Batches with |recorded - physical| <= 2% of recorded", denominator="Batches with recorded or physical qty > 0",
         exclusions="Rejected and fully consumed batches", window="Snapshot (end of data); date filter not applicable",
         limitation="Physical quantity is a synthetic cycle-count proxy; tolerance of 2% is an assumption.",
         sql="""SELECT SUM(CASE WHEN ABS(recorded_qty-physical_qty) <= 0.02*recorded_qty THEN 1 ELSE 0 END) AS num, COUNT(*) AS den
                FROM inventory_batches WHERE recorded_qty>0 OR physical_qty>0""", windowed=False),
    dict(kpi_id="supplier_on_time_delivery", name="Supplier on-time delivery", unit="ratio",
         numerator="Deliveries arriving on or before requested delivery date", denominator="All received deliveries (cancelled POs excluded)",
         exclusions="Cancelled purchase orders", window="Delivery arrival timestamp",
         limitation="Day-level comparison; partial deliveries each counted as one delivery.",
         sql="""SELECT SUM(CASE WHEN date(d.arrival_ts) <= date(p.requested_delivery_date) THEN 1 ELSE 0 END) AS num, COUNT(*) AS den
                FROM inbound_deliveries d JOIN po_lines l USING(po_line_id) JOIN purchase_orders p USING(po_id)
                WHERE d.arrival_ts >= :s AND d.arrival_ts < :e""", windowed=True),
    dict(kpi_id="receiving_to_putaway_hours", name="Receiving-to-putaway time (h)", unit="hours",
         numerator="Sum of hours from goods receipt to final putaway", denominator="Deliveries with a putaway",
         exclusions="Rejected / open-hold deliveries; negative durations (putaway before release is flagged separately, not excluded)", window="GR timestamp",
         limitation="Includes quality inspection/hold time because release gates putaway.",
         sql="""SELECT SUM((julianday(putaway_ts)-julianday(gr_ts))*24) AS num, COUNT(*) AS den FROM inbound_deliveries
                WHERE putaway_ts IS NOT NULL AND gr_ts >= :s AND gr_ts < :e""", windowed=True),
    dict(kpi_id="quality_hold_hours", name="Quality-hold duration (h)", unit="hours",
         numerator="Sum of hold hours", denominator="Closed inspections that were on hold",
         exclusions="Still-open holds (duration unknown)", window="Inspection start",
         limitation="Open holds are right-censored and excluded, which understates average duration.",
         sql="""SELECT SUM(hold_hours) AS num, COUNT(*) AS den FROM quality_inspections
                WHERE hold_flag=1 AND hold_hours IS NOT NULL AND start_ts >= :s AND start_ts < :e""", windowed=True),
    dict(kpi_id="order_fulfilment_rate", name="Order fulfilment rate (first-pass, no backorder)", unit="ratio",
         numerator="Dispatched orders with zero backordered quantity", denominator="Non-cancelled orders",
         exclusions="Cancelled orders", window="Order timestamp",
         limitation="Binary per order; ignores partial coverage depth (see backorder volume).",
         sql="""SELECT SUM(CASE WHEN o.stockout_flag=0 THEN 1 ELSE 0 END) AS num, COUNT(*) AS den
                FROM outbound_deliveries o JOIN customer_orders c USING(order_id) WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="stockout_rate", name="Stockout frequency", unit="ratio",
         numerator="Orders hitting a stockout/backorder", denominator="Non-cancelled orders", exclusions="Cancelled orders", window="Order timestamp",
         limitation="Stockouts are flagged at order level; stock levels over time are not simulated.",
         sql="""SELECT SUM(o.stockout_flag) AS num, COUNT(*) AS den FROM outbound_deliveries o JOIN customer_orders c USING(order_id)
                WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="backorder_volume", name="Backorder volume (units)", unit="units",
         numerator="Sum of backordered quantity", denominator="1 (total)", exclusions="Cancelled orders", window="Order timestamp",
         limitation="Mixed units of measure (EA/BOX); interpret as indicative volume.",
         sql="""SELECT SUM(o.qty_backordered) AS num, 1 AS den FROM outbound_deliveries o JOIN customer_orders c USING(order_id)
                WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="on_time_dispatch_rate", name="On-time dispatch rate", unit="ratio",
         numerator="Orders dispatched on/before requested dispatch time", denominator="Dispatched orders", exclusions="Cancelled orders",
         window="Order timestamp", limitation="Requested time is SLA-derived by priority (24/72/120h + up to 24h).",
         sql="""SELECT SUM(CASE WHEN o.dispatch_ts <= c.requested_dispatch_ts THEN 1 ELSE 0 END) AS num, COUNT(*) AS den
                FROM outbound_deliveries o JOIN customer_orders c USING(order_id) WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="order_to_dispatch_hours", name="Order-to-dispatch cycle time (h)", unit="hours",
         numerator="Sum of hours from order to dispatch", denominator="Dispatched orders", exclusions="Cancelled orders", window="Order timestamp",
         limitation="Calendar hours; no working-calendar adjustment.",
         sql="""SELECT SUM((julianday(o.dispatch_ts)-julianday(c.order_ts))*24) AS num, COUNT(*) AS den
                FROM outbound_deliveries o JOIN customer_orders c USING(order_id) WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="picking_hours", name="Average picking duration (h)", unit="hours",
         numerator="Sum of pick_end - pick_start", denominator="Dispatched orders", exclusions="None", window="Order timestamp",
         limitation="Re-picks extend the same measure.",
         sql="""SELECT SUM((julianday(pick_end_ts)-julianday(pick_start_ts))*24) AS num, COUNT(*) AS den FROM outbound_deliveries o
                JOIN customer_orders c USING(order_id) WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="packing_hours", name="Average packing duration (h)", unit="hours",
         numerator="Sum of pack_end - pack_start", denominator="Dispatched orders", exclusions="None", window="Order timestamp", limitation="None material.",
         sql="""SELECT SUM((julianday(pack_end_ts)-julianday(pack_start_ts))*24) AS num, COUNT(*) AS den FROM outbound_deliveries o
                JOIN customer_orders c USING(order_id) WHERE c.order_ts >= :s AND c.order_ts < :e""", windowed=True),
    dict(kpi_id="warehouse_throughput_per_day", name="Warehouse throughput (movements/day)", unit="movements/day",
         numerator="Movements of type GOODS_RECEIPT, PUTAWAY, TRANSFER, PICK, DISPATCH", denominator="Calendar days in window",
         exclusions="STATUS_CHANGE (not physical)", window="Movement timestamp", limitation="Counts movements, not units or lines.",
         sql="""SELECT COUNT(*) AS num, MAX(1.0, julianday(:e)-julianday(:s)) AS den FROM warehouse_movements
                WHERE movement_type<>'STATUS_CHANGE' AND movement_ts >= :s AND movement_ts < :e""", windowed=True),
    dict(kpi_id="process_rework_rate", name="Process rework rate", unit="ratio",
         numerator="Cases containing a repeated activity (re-receipt, putaway retry, re-pick)", denominator="Cases",
         exclusions="Cases without events in window", window="Case start (first event)",
         limitation="Repetition is treated as rework; legitimate split deliveries are separate cases so are not counted.",
         sql="""WITH c AS (SELECT case_id, MIN(event_ts) AS st FROM event_log GROUP BY case_id),
                r AS (SELECT DISTINCT case_id FROM (SELECT case_id, activity FROM event_log GROUP BY case_id, activity HAVING COUNT(*)>1))
                SELECT SUM(CASE WHEN r.case_id IS NOT NULL THEN 1 ELSE 0 END) AS num, COUNT(*) AS den
                FROM c LEFT JOIN r USING(case_id) WHERE c.st >= :s AND c.st < :e""", windowed=True),
    dict(kpi_id="master_data_completeness", name="Master-data completeness", unit="ratio",
         numerator="Populated required attributes", denominator="Materials x 6 required attributes", exclusions="None",
         window="Snapshot", limitation="Checks presence, not correctness (see UoM rule DQ-04).",
         sql="""SELECT SUM((uom IS NOT NULL)+(shelf_life_days IS NOT NULL)+(storage_condition IS NOT NULL)+(abc_class IS NOT NULL)
                +(gmp_relevant IS NOT NULL)+(net_weight_kg IS NOT NULL)) AS num, COUNT(*)*6 AS den FROM materials""", windowed=False),
    dict(kpi_id="expiry_exposure_value", name="Expiry exposure value (90d, fictional currency)", unit="currency",
         numerator="Recorded qty x unit cost for batches expired or expiring within 90 days of snapshot", denominator="1 (total)",
         exclusions="Rejected batches, zero stock", window="Snapshot (:e used as snapshot date)",
         limitation="Assumes recorded stock is saleable/usable until expiry; no demand forecast applied.",
         sql="""SELECT SUM(b.recorded_qty*m.unit_cost) AS num, 1 AS den FROM inventory_batches b JOIN materials m USING(material_id)
                WHERE b.recorded_qty>0 AND b.stock_status<>'Rejected' AND date(b.expiry_date) <= date(:e, '+90 day')""", windowed=False),
    dict(kpi_id="inventory_turnover", name="Inventory turnover (annualised)", unit="turns/yr",
         numerator="Annualised cost of dispatched goods (qty x unit cost)", denominator="Average FG inventory value at snapshot (recorded qty x unit cost)",
         exclusions="Non-finished goods", window="Dispatch timestamp",
         limitation="Denominator is a single snapshot, not a time-average; indicative only.",
         sql="""SELECT SUM(o.qty_shipped*m.unit_cost)*365.0/MAX(1.0, julianday(:e)-julianday(:s)) AS num,
                (SELECT SUM(b.recorded_qty*m2.unit_cost) FROM inventory_batches b JOIN materials m2 USING(material_id) WHERE m2.category='Finished Good') AS den
                FROM outbound_deliveries o JOIN customer_orders c USING(order_id) JOIN materials m ON m.material_id=c.material_id
                WHERE o.dispatch_ts >= :s AND o.dispatch_ts < :e""", windowed=True),
]
DEFS = {d["kpi_id"]: d for d in KPI_DEFS}


def compute_kpis(con: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    rows = []
    for d in KPI_DEFS:
        num, den = con.execute(d["sql"], {"s": start, "e": end}).fetchone()
        val = (num / den) if (num is not None and den not in (None, 0)) else None
        rows.append(dict(kpi_id=d["kpi_id"], name=d["name"], unit=d["unit"], numerator=num, denominator=den, value=val))
    return pd.DataFrame(rows)


def kpi_dictionary() -> pd.DataFrame:
    return pd.DataFrame([{k: v for k, v in d.items() if k not in ("sql", "windowed")} for d in KPI_DEFS])
