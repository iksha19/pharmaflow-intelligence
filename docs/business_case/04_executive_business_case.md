# Executive Business Case

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.


**Problem.** Stockout rate 13.1% (target 5%), supplier OTD 74.1%, receiving-to-putaway 35.3 h, deviation 5.1%.

**Modelled impact of proposed warehouse improvements** (modelled estimates on synthetic data; not causal evidence):

| metric | baseline | scenario_value | abs_change | rel_change |
|---|---|---|---|---|
| stockout_risk | 0.1314 | 0.0845 | -0.0469 | -0.3567 |
| service_level | 0.9854 | 0.9915 | 0.0061 | 0.0062 |
| avg_order_delay_h | 12.9331 | 5.8649 | -7.0682 | -0.5465 |
| warehouse_utilisation | 0.8000 | 0.5016 | -0.2984 | -0.3730 |
| operating_cost | 999399.2913 | 778440.5460 | -220958.7453 | -0.2211 |

Modelled annual operating cost moves from 999,399 to 778,441 (fictional currency). Costs of implementation are not modelled; a real business case needs them.

**Recommendation.** Approve REC-01..REC-03 for design validation, with KPI verification at 90 days.

| rec_id | problem | evidence | intervention | kpi | stakeholder | verification |
|---|---|---|---|---|---|---|
| REC-01 | Stockouts and backorders on key finished goods | Stockout rate is 13.1% (target 5%); worst materials: MAT0101, MAT0110, MAT0056. Stage most associated with late orders: wait_allocation (+92 h vs on-time orders). | Review reorder points and safety stock for exposed materials (see Scenario Simulator); weekly shortage review with Supply Planning. | stockout_rate | Supply Planning Lead | Stockout rate and backorder volume by material; modelled vs observed service level. |
| REC-02 | Slow receiving-to-putaway in the slowest zone | Receiving-to-putaway averages 35.3 h (target 24 h); zone CTRL is slowest at 47.1 h (n=757). | Review release-to-putaway handover, add putaway task prioritisation and staffing for the slowest zone. | receiving_to_putaway_hours | Warehouse Operations Manager | Zone-level GR-to-putaway distribution before/after; p90 below target. |
| REC-03 | Process deviations and rework | Inbound deviation rate 6.5%, outbound 3.7%; 105 deliveries put away before quality release (simulated rule); rework rate 6.8%. | System-enforced status gate (no putaway before release), mandatory verification step, re-pick root-cause review in COLD zone. | process_rework_rate | Business Process Architect | Conformance rate monthly; zero out-of-order putaway; rework rate <= 5%. |
| REC-04 | Extended quality holds | Closed holds average 60.3 h (target 48 h). | Prioritise holds by stock criticality; standard reason codes and daily QA/warehouse hold review; escalate holds older than the target. | quality_hold_hours | QA Release Manager | Hold-hours distribution by category; count of holds older than target. |
| REC-05 | Inbound supplier delays | Supplier on-time delivery is 74.1%; top 3 suppliers (SUP012, SUP004, SUP018) account for 31% of delay days. | Supplier scorecards, lead-time re-baselining in the material/info record, and escalation plans for chronic late suppliers. | supplier_on_time_delivery | Head of Procurement | Monthly OTD by supplier trend; target >= 90% for 3 consecutive months. |
| REC-06 | Expiry exposure | 100 batches listed within the 90-day window (top 100 shown); recorded-value exposure 84,143,359 (fictional currency). | FEFO enforcement, near-expiry alerts at 90/60/30 days, and consumption planning for short-life materials. | expiry_exposure_value | Inventory Control Lead | Expiry exposure value and expired-stock write-offs per month. |
| REC-07 | Material master-data defects drive process deviations | Master-data completeness is 96.8%; deliveries for materials with invalid UoM show 24.0% process deviation (3.7x average); materials missing storage condition show 26.2% rework. | Mandatory-field and UoM validation at material creation; remediation backlog ranked by downstream impact (query q7). | master_data_completeness | Master Data Steward | Completeness >= 98%; zero invalid UoM; deviation rate for remediated materials. |
| REC-08 | Inventory record inaccuracy | Record accuracy is 94.1% (target 98%). | Cycle-count programme targeted at mismatched batches; root-cause adjustments by zone. | inventory_record_accuracy | Inventory Control Lead | Accuracy by zone after each count cycle. |

