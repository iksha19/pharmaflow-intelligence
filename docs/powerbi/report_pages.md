# Power BI report page specifications (6 pages)

1. **Executive Overview** - KPI cards (OTD, fulfilment, accuracy, deviation) vs `fact_kpi_target`; monthly trend of On-Time Dispatch %; top-5 issues table.
2. **Warehouse Operations** - throughput by month (fact_warehouse_movement), GR-to-putaway by zone (dim_bin / dim_material storage condition), picking/packing duration, re-pick rate.
3. **Inventory and Expiry Risk** - expiry_bucket by value, near-expiry batch table, recorded vs physical mismatch list, stock status split (available / restricted / physical / recorded).
4. **Supplier and Inbound Performance** - OTD by supplier, delay-days Pareto, partial delivery rate, quality hold duration by category.
5. **Process Mining** - variant table (fact_case_conformance), deviation by type, top handover waits, rework loops (Power BI visuals: matrix + decomposition tree).
6. **Improvement Tracking** - KPI vs target, scenario comparison (fact_scenario_assumption), recommendation status (manual table / SharePoint list).
