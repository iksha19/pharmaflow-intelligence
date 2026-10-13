# Business Requirements Document (BRD)

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

- **BR-01** (REC-01) Stockouts and backorders on key finished goods: Review reorder points and safety stock for exposed materials (see Scenario Simulator); weekly shortage review with Supply Planning. KPI: `stockout_rate`. Owner: Supply Planning Lead.
- **BR-02** (REC-02) Slow receiving-to-putaway in the slowest zone: Review release-to-putaway handover, add putaway task prioritisation and staffing for the slowest zone. KPI: `receiving_to_putaway_hours`. Owner: Warehouse Operations Manager.
- **BR-03** (REC-03) Process deviations and rework: System-enforced status gate (no putaway before release), mandatory verification step, re-pick root-cause review in COLD zone. KPI: `process_rework_rate`. Owner: Business Process Architect.
- **BR-04** (REC-04) Extended quality holds: Prioritise holds by stock criticality; standard reason codes and daily QA/warehouse hold review; escalate holds older than the target. KPI: `quality_hold_hours`. Owner: QA Release Manager.
- **BR-05** (REC-05) Inbound supplier delays: Supplier scorecards, lead-time re-baselining in the material/info record, and escalation plans for chronic late suppliers. KPI: `supplier_on_time_delivery`. Owner: Head of Procurement.
- **BR-06** (REC-06) Expiry exposure: FEFO enforcement, near-expiry alerts at 90/60/30 days, and consumption planning for short-life materials. KPI: `expiry_exposure_value`. Owner: Inventory Control Lead.
- **BR-07** (REC-07) Material master-data defects drive process deviations: Mandatory-field and UoM validation at material creation; remediation backlog ranked by downstream impact (query q7). KPI: `master_data_completeness`. Owner: Master Data Steward.
- **BR-08** (REC-08) Inventory record inaccuracy: Cycle-count programme targeted at mismatched batches; root-cause adjustments by zone. KPI: `inventory_record_accuracy`. Owner: Inventory Control Lead.
