PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS event_log; DROP TABLE IF EXISTS outbound_deliveries; DROP TABLE IF EXISTS customer_orders;
DROP TABLE IF EXISTS production_requests; DROP TABLE IF EXISTS warehouse_movements; DROP TABLE IF EXISTS quality_inspections;
DROP TABLE IF EXISTS inventory_batches; DROP TABLE IF EXISTS inbound_deliveries; DROP TABLE IF EXISTS po_lines;
DROP TABLE IF EXISTS purchase_orders; DROP TABLE IF EXISTS warehouse_bins; DROP TABLE IF EXISTS materials;
DROP TABLE IF EXISTS suppliers; DROP TABLE IF EXISTS kpi_targets; DROP TABLE IF EXISTS scenario_assumptions;

CREATE TABLE suppliers (
  supplier_id TEXT PRIMARY KEY, supplier_name TEXT NOT NULL, country TEXT, tier TEXT,
  contract_lead_time_days INTEGER NOT NULL);
CREATE TABLE materials (
  material_id TEXT PRIMARY KEY, material_name TEXT NOT NULL, category TEXT NOT NULL, uom TEXT,
  shelf_life_days INTEGER, storage_condition TEXT, abc_class TEXT, gmp_relevant TEXT, net_weight_kg REAL,
  unit_cost REAL NOT NULL, reorder_point REAL NOT NULL, safety_stock REAL NOT NULL);
CREATE TABLE warehouse_bins (
  bin_id TEXT PRIMARY KEY, zone TEXT NOT NULL, capacity_units REAL NOT NULL);
CREATE TABLE purchase_orders (
  po_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
  po_date TEXT NOT NULL, requested_delivery_date TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE po_lines (
  po_line_id TEXT PRIMARY KEY, po_id TEXT NOT NULL REFERENCES purchase_orders(po_id),
  material_id TEXT NOT NULL REFERENCES materials(material_id), ordered_qty REAL NOT NULL, uom TEXT, unit_price REAL);
CREATE TABLE inbound_deliveries (
  delivery_id TEXT PRIMARY KEY, po_line_id TEXT NOT NULL REFERENCES po_lines(po_line_id),
  delivery_seq INTEGER NOT NULL, scheduled_date TEXT NOT NULL, arrival_ts TEXT NOT NULL, gr_ts TEXT NOT NULL,
  verification_ts TEXT, putaway_ts TEXT, delivered_qty REAL NOT NULL, damaged_qty REAL NOT NULL,
  partial_flag INTEGER NOT NULL, rework_flag INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE inventory_batches (
  batch_id TEXT PRIMARY KEY, material_id TEXT NOT NULL REFERENCES materials(material_id),
  delivery_id TEXT REFERENCES inbound_deliveries(delivery_id), source TEXT NOT NULL,
  bin_id TEXT REFERENCES warehouse_bins(bin_id), received_qty REAL NOT NULL, recorded_qty REAL NOT NULL,
  physical_qty REAL NOT NULL, quality_restricted_qty REAL NOT NULL, available_qty REAL NOT NULL,
  received_date TEXT NOT NULL, expiry_date TEXT, stock_status TEXT NOT NULL);
CREATE TABLE quality_inspections (
  inspection_id TEXT PRIMARY KEY, delivery_id TEXT NOT NULL REFERENCES inbound_deliveries(delivery_id),
  batch_id TEXT NOT NULL REFERENCES inventory_batches(batch_id), start_ts TEXT NOT NULL, decision_ts TEXT,
  result TEXT NOT NULL, hold_flag INTEGER NOT NULL, hold_hours REAL, reason_code TEXT);
CREATE TABLE warehouse_movements (
  movement_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES inventory_batches(batch_id),
  material_id TEXT NOT NULL REFERENCES materials(material_id), movement_type TEXT NOT NULL,
  from_bin TEXT REFERENCES warehouse_bins(bin_id), to_bin TEXT REFERENCES warehouse_bins(bin_id),
  zone TEXT, qty REAL NOT NULL, uom TEXT, movement_ts TEXT NOT NULL, status_from TEXT, status_to TEXT);
CREATE TABLE production_requests (
  request_id TEXT PRIMARY KEY, material_id TEXT NOT NULL REFERENCES materials(material_id),
  requested_qty REAL NOT NULL, request_ts TEXT NOT NULL, required_by_ts TEXT NOT NULL, staged_ts TEXT,
  fulfilled_qty REAL NOT NULL, shortage_flag INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE customer_orders (
  order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, material_id TEXT NOT NULL REFERENCES materials(material_id),
  order_qty REAL NOT NULL, order_ts TEXT NOT NULL, requested_dispatch_ts TEXT NOT NULL, priority TEXT NOT NULL,
  status TEXT NOT NULL);
CREATE TABLE outbound_deliveries (
  outbound_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES customer_orders(order_id), batch_id TEXT REFERENCES inventory_batches(batch_id),
  zone TEXT, allocation_ts TEXT NOT NULL, pick_start_ts TEXT NOT NULL, pick_end_ts TEXT NOT NULL,
  pack_start_ts TEXT NOT NULL, pack_end_ts TEXT NOT NULL, dispatch_ts TEXT NOT NULL, reconciliation_ts TEXT,
  qty_shipped REAL NOT NULL, qty_backordered REAL NOT NULL, stockout_flag INTEGER NOT NULL, repick_flag INTEGER NOT NULL);
CREATE TABLE event_log (
  event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, case_type TEXT NOT NULL, activity TEXT NOT NULL,
  event_ts TEXT NOT NULL, resource TEXT, reference_id TEXT, material_id TEXT, supplier_id TEXT, zone TEXT, priority TEXT);
CREATE TABLE kpi_targets (kpi_id TEXT PRIMARY KEY, target_value REAL NOT NULL, direction TEXT NOT NULL, unit TEXT);
CREATE TABLE scenario_assumptions (scenario TEXT NOT NULL, parameter TEXT NOT NULL, value REAL, PRIMARY KEY (scenario, parameter));

CREATE INDEX ix_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX ix_pol_po ON po_lines(po_id);
CREATE INDEX ix_dlv_pol ON inbound_deliveries(po_line_id);
CREATE INDEX ix_batch_mat ON inventory_batches(material_id);
CREATE INDEX ix_mov_batch ON warehouse_movements(batch_id);
CREATE INDEX ix_ord_mat ON customer_orders(material_id);
CREATE INDEX ix_out_ord ON outbound_deliveries(order_id);
CREATE INDEX ix_evt_case ON event_log(case_id, event_ts);
