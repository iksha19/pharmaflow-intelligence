# Master-Data Quality Rules

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

| rule_id | rule | table | severity | violations | total | violation_pct |
|---|---|---|---|---|---|---|
| DQ-01 | Primary key unique | suppliers | Critical | 0 | 25 | 0.000 |
| DQ-01 | Primary key unique | materials | Critical | 0 | 120 | 0.000 |
| DQ-01 | Primary key unique | warehouse_bins | Critical | 0 | 260 | 0.000 |
| DQ-01 | Primary key unique | purchase_orders | Critical | 0 | 1200 | 0.000 |
| DQ-01 | Primary key unique | po_lines | Critical | 0 | 2982 | 0.000 |
| DQ-01 | Primary key unique | inbound_deliveries | Critical | 0 | 3248 | 0.000 |
| DQ-01 | Primary key unique | inventory_batches | Critical | 0 | 3353 | 0.000 |
| DQ-01 | Primary key unique | quality_inspections | Critical | 0 | 3248 | 0.000 |
| DQ-01 | Primary key unique | warehouse_movements | Critical | 0 | 15472 | 0.000 |
| DQ-01 | Primary key unique | production_requests | Critical | 0 | 800 | 0.000 |
| DQ-01 | Primary key unique | customer_orders | Critical | 0 | 3000 | 0.000 |
| DQ-01 | Primary key unique | outbound_deliveries | Critical | 0 | 2861 | 0.000 |
| DQ-01 | Primary key unique | event_log | Critical | 0 | 44272 | 0.000 |
| DQ-02 | po_lines.po_id -> purchase_orders.po_id | po_lines | Critical | 0 | 2982 | 0.000 |
| DQ-02 | po_lines.material_id -> materials.material_id | po_lines | Critical | 0 | 2982 | 0.000 |
| DQ-02 | purchase_orders.supplier_id -> suppliers.supplier_id | purchase_orders | Critical | 0 | 1200 | 0.000 |
| DQ-02 | inbound_deliveries.po_line_id -> po_lines.po_line_id | inbound_deliveries | Critical | 0 | 3248 | 0.000 |
| DQ-02 | inventory_batches.material_id -> materials.material_id | inventory_batches | Critical | 0 | 3353 | 0.000 |
| DQ-02 | quality_inspections.batch_id -> inventory_batches.batch_id | quality_inspections | Critical | 0 | 3248 | 0.000 |
| DQ-02 | warehouse_movements.batch_id -> inventory_batches.batch_id | warehouse_movements | Critical | 0 | 15472 | 0.000 |
| DQ-02 | outbound_deliveries.order_id -> customer_orders.order_id | outbound_deliveries | Critical | 0 | 2861 | 0.000 |
| DQ-02 | customer_orders.material_id -> materials.material_id | customer_orders | Critical | 0 | 3000 | 0.000 |
| DQ-03 | Material master attribute 'uom' populated | materials | High | 0 | 120 | 0.000 |
| DQ-03 | Material master attribute 'shelf_life_days' populated | materials | High | 4 | 120 | 0.033 |
| DQ-03 | Material master attribute 'storage_condition' populated | materials | High | 3 | 120 | 0.025 |
| DQ-03 | Material master attribute 'abc_class' populated | materials | Medium | 3 | 120 | 0.025 |
| DQ-03 | Material master attribute 'gmp_relevant' populated | materials | Medium | 2 | 120 | 0.017 |
| DQ-03 | Material master attribute 'net_weight_kg' populated | materials | Medium | 11 | 120 | 0.092 |
| DQ-04 | Material UoM in valid list | materials | High | 2 | 120 | 0.017 |
| DQ-04 | PO-line UoM equals material UoM | po_lines | High | 0 | 2982 | 0.000 |
| DQ-05 | GR timestamp not before arrival | inbound_deliveries | High | 0 | 3248 | 0.000 |
| DQ-05 | Verification not before GR | inbound_deliveries | High | 0 | 3248 | 0.000 |
| DQ-05 | Putaway not before quality release (simulated rule) | inbound_deliveries | High | 105 | 3248 | 0.032 |
| DQ-05 | Outbound timestamps monotonic | outbound_deliveries | High | 0 | 2861 | 0.000 |
| DQ-05 | Event timestamps parse | event_log | Critical | 0 | 44272 | 0.000 |
| DQ-05 | Event timestamps not after snapshot | event_log | High | 0 | 44272 | 0.000 |
| DQ-06 | Stock status transition allowed | warehouse_movements | Critical | 25 | 3229 | 0.008 |
| DQ-07 | No negative stock quantities | inventory_batches | Critical | 0 | 3353 | 0.000 |
| DQ-07 | Available + restricted <= recorded | inventory_batches | High | 0 | 3353 | 0.000 |
| DQ-07 | Recorded vs physical within 2% tolerance | inventory_batches | Medium | 194 | 3274 | 0.059 |
