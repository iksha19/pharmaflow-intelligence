# Project Charter - PharmaFlow Intelligence

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.


**Purpose.** Give Healthcare Business Process Architecture a fact-based view of the end-to-end warehouse and inventory process (supplier PO to dispatch) and a quantified improvement backlog.

**Objectives.** (1) Measure process KPIs reproducibly from event data. (2) Find bottlenecks, rework and deviations through process mining. (3) Raise master-data quality. (4) Model improvement scenarios before change. (5) Hand over requirements and UAT criteria.

**Success measures (targets from `config/settings.yaml`).**

| kpi_id | value | target_value | direction |
|---|---|---|---|
| inventory_record_accuracy | 0.941 | 0.980 | higher |
| supplier_on_time_delivery | 0.741 | 0.900 | higher |
| receiving_to_putaway_hours | 35.338 | 24.000 | lower |
| quality_hold_hours | 60.288 | 48.000 | lower |
| order_fulfilment_rate | 0.869 | 0.950 | higher |
| stockout_rate | 0.131 | 0.050 | lower |
| on_time_dispatch_rate | 0.917 | 0.920 | higher |
| order_to_dispatch_hours | 29.715 | 72.000 | lower |
| process_rework_rate | 0.068 | 0.050 | lower |
| master_data_completeness | 0.968 | 0.980 | higher |
| process_deviation_rate | 0.051 | 0.080 | lower |


**Sponsor / owner.** Head of Healthcare Supply Chain (fictional role). **Business Process Architect:** accountable for process design and requirements.
