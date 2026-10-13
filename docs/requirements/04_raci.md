# RACI Matrix

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

R=Responsible, A=Accountable, C=Consulted, I=Informed

| Activity | Process Architect | Warehouse Ops | QA Release | Master Data | Supply Planning | Procurement |
|---|---|---|---|---|---|---|
| Define KPI dictionary | A/R | C | C | C | I | C |
| Receiving & verification process | C | A/R | C | I | I | C |
| Quality release / hold decision | I | C | A/R | I | I | I |
| Putaway & storage rules | C | A/R | C | I | C | C |
| Material master remediation | C | I | I | A/R | I | C |
| Reorder point / safety stock | C | I | I | C | A/R | I |
| Supplier performance review | C | I | C | I | I | A/R |
| UAT sign-off | A | R | R | R | R | R |
