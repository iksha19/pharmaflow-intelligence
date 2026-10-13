# DAX measures

```DAX
Supplier OTD % = DIVIDE(SUM(fact_inbound_delivery[on_time_flag]), COUNTROWS(fact_inbound_delivery))
Avg GR to Putaway (h) = AVERAGE(fact_inbound_delivery[gr_to_putaway_h])
Quality Hold Avg (h) = CALCULATE(AVERAGE(fact_quality_inspection[hold_hours]), fact_quality_inspection[hold_flag] = 1)
Fulfilment Rate % = DIVIDE(CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[stockout_flag] = 0, fact_outbound_order[status] = "Dispatched"), CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[status] = "Dispatched"))
Stockout Rate % = DIVIDE(SUM(fact_outbound_order[stockout_flag]), CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[status] = "Dispatched"))
On-Time Dispatch % = DIVIDE(SUM(fact_outbound_order[on_time_flag]), CALCULATE(COUNTROWS(fact_outbound_order), fact_outbound_order[status] = "Dispatched"))
Avg Order-to-Dispatch (h) = AVERAGE(fact_outbound_order[order_to_dispatch_h])
Backorder Qty = SUM(fact_outbound_order[qty_backordered])
Inventory Record Accuracy % = DIVIDE(CALCULATE(COUNTROWS(fact_inventory_snapshot), fact_inventory_snapshot[mismatch_flag] = 0, fact_inventory_snapshot[recorded_qty] > 0), CALCULATE(COUNTROWS(fact_inventory_snapshot), fact_inventory_snapshot[recorded_qty] > 0))
Expiry Exposure Value = CALCULATE(SUM(fact_inventory_snapshot[recorded_value]), fact_inventory_snapshot[expiry_bucket] <> "OK", fact_inventory_snapshot[stock_status] <> "Rejected")
Process Deviation % = DIVIDE(CALCULATE(COUNTROWS(fact_case_conformance), fact_case_conformance[deviation] = TRUE()), CALCULATE(COUNTROWS(fact_case_conformance), fact_case_conformance[status] <> "Open"))
Process Rework % = DIVIDE(CALCULATE(COUNTROWS(fact_case_conformance), fact_case_conformance[has_rework] = TRUE()), COUNTROWS(fact_case_conformance))
```
