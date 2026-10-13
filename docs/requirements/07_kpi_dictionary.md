# KPI Dictionary

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

| kpi_id | name | numerator | denominator | exclusions | window | limitation |
|---|---|---|---|---|---|---|
| inventory_record_accuracy | Inventory record accuracy | Batches with /recorded - physical/ <= 2% of recorded | Batches with recorded or physical qty > 0 | Rejected and fully consumed batches | Snapshot (end of data); date filter not applicable | Physical quantity is a synthetic cycle-count proxy; tolerance of 2% is an assumption. |
| supplier_on_time_delivery | Supplier on-time delivery | Deliveries arriving on or before requested delivery date | All received deliveries (cancelled POs excluded) | Cancelled purchase orders | Delivery arrival timestamp | Day-level comparison; partial deliveries each counted as one delivery. |
| receiving_to_putaway_hours | Receiving-to-putaway time (h) | Sum of hours from goods receipt to final putaway | Deliveries with a putaway | Rejected / open-hold deliveries; negative durations (putaway before release is flagged separately, not excluded) | GR timestamp | Includes quality inspection/hold time because release gates putaway. |
| quality_hold_hours | Quality-hold duration (h) | Sum of hold hours | Closed inspections that were on hold | Still-open holds (duration unknown) | Inspection start | Open holds are right-censored and excluded, which understates average duration. |
| order_fulfilment_rate | Order fulfilment rate (first-pass, no backorder) | Dispatched orders with zero backordered quantity | Non-cancelled orders | Cancelled orders | Order timestamp | Binary per order; ignores partial coverage depth (see backorder volume). |
| stockout_rate | Stockout frequency | Orders hitting a stockout/backorder | Non-cancelled orders | Cancelled orders | Order timestamp | Stockouts are flagged at order level; stock levels over time are not simulated. |
| backorder_volume | Backorder volume (units) | Sum of backordered quantity | 1 (total) | Cancelled orders | Order timestamp | Mixed units of measure (EA/BOX); interpret as indicative volume. |
| on_time_dispatch_rate | On-time dispatch rate | Orders dispatched on/before requested dispatch time | Dispatched orders | Cancelled orders | Order timestamp | Requested time is SLA-derived by priority (24/72/120h + up to 24h). |
| order_to_dispatch_hours | Order-to-dispatch cycle time (h) | Sum of hours from order to dispatch | Dispatched orders | Cancelled orders | Order timestamp | Calendar hours; no working-calendar adjustment. |
| picking_hours | Average picking duration (h) | Sum of pick_end - pick_start | Dispatched orders | None | Order timestamp | Re-picks extend the same measure. |
| packing_hours | Average packing duration (h) | Sum of pack_end - pack_start | Dispatched orders | None | Order timestamp | None material. |
| warehouse_throughput_per_day | Warehouse throughput (movements/day) | Movements of type GOODS_RECEIPT, PUTAWAY, TRANSFER, PICK, DISPATCH | Calendar days in window | STATUS_CHANGE (not physical) | Movement timestamp | Counts movements, not units or lines. |
| process_rework_rate | Process rework rate | Cases containing a repeated activity (re-receipt, putaway retry, re-pick) | Cases | Cases without events in window | Case start (first event) | Repetition is treated as rework; legitimate split deliveries are separate cases so are not counted. |
| master_data_completeness | Master-data completeness | Populated required attributes | Materials x 6 required attributes | None | Snapshot | Checks presence, not correctness (see UoM rule DQ-04). |
| expiry_exposure_value | Expiry exposure value (90d, fictional currency) | Recorded qty x unit cost for batches expired or expiring within 90 days of snapshot | 1 (total) | Rejected batches, zero stock | Snapshot (:e used as snapshot date) | Assumes recorded stock is saleable/usable until expiry; no demand forecast applied. |
| inventory_turnover | Inventory turnover (annualised) | Annualised cost of dispatched goods (qty x unit cost) | Average FG inventory value at snapshot (recorded qty x unit cost) | Non-finished goods | Dispatch timestamp | Denominator is a single snapshot, not a time-average; indicative only. |
