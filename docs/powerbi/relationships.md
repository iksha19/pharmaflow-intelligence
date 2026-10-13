# Power BI model relationships (star schema)

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
