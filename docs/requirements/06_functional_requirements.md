# Functional Requirements and Acceptance Criteria

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-01 | System blocks putaway while stock status is Quality Hold/unreleased | Test: attempt putaway on held batch -> rejected; 0 'putaway before release' events in 30 days |
| FR-02 | Receiving requires batch, quantity and UoM verification before inspection can start | 0 cases missing verification; invalid-UoM materials cannot be received |
| FR-03 | Material creation enforces mandatory fields (UoM, shelf life, storage condition, ABC, GMP flag, net weight) | Master-data completeness >= 98% |
| FR-04 | Quality hold aging report with alerts at target hours | Holds older than 48 h listed daily; avg hold <= 48 h |
| FR-05 | Shortage alert when available stock falls below reorder point | Alert raised before backorder; stockout rate trending to <= 5% |
| FR-06 | Near-expiry alerts at 90/60/30 days with FEFO pick suggestion | Expiry exposure value reported monthly and declining |
| FR-07 | Event log captured for every process step with case id, timestamp, resource | Event-log completeness check passes in pipeline |
| FR-08 | Dashboards refresh from the reproducible pipeline | `bash scripts/run_pipeline.sh` exit code 0 |
