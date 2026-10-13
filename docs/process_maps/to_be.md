# To-Be Process Map (proposed design)

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.


```mermaid
flowchart LR
  A[PO with validated lead time] --> B[ASN / delivery] --> C[Goods receipt - mandatory UoM/batch check] --> D[Quality inspection]
  D --> R{Release gate}
  R -->|released| F[Auto putaway task, priority by zone] --> H[Available]
  R -->|hold| I[Daily hold review, aging alert] --> R
  R -->|reject| J[Return]
  H --> L[Allocation with shortage alert at ROP] --> M[Pick] --> N[Pack] --> O[Dispatch] --> P[Auto reconciliation]
```
**Design changes:** system-enforced status gate (no putaway before release); mandatory verification step; master-data validation at creation; hold aging alerts; replenishment parameter review; FEFO picking and near-expiry alerts.
