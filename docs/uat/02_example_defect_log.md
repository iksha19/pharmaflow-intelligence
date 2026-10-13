# Example Defect Log (derived from data-quality findings)

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

| Defect | Description | Object | Severity | Records affected | Status |
|---|---|---|---|---|---|
| DEF-001 | Material master attribute 'shelf_life_days' populated | materials | High | 4 of 120 | Open |
| DEF-002 | Material master attribute 'storage_condition' populated | materials | High | 3 of 120 | Open |
| DEF-003 | Material master attribute 'abc_class' populated | materials | Medium | 3 of 120 | Open |
| DEF-004 | Material master attribute 'gmp_relevant' populated | materials | Medium | 2 of 120 | Open |
| DEF-005 | Material master attribute 'net_weight_kg' populated | materials | Medium | 11 of 120 | Open |
| DEF-006 | Material UoM in valid list | materials | High | 2 of 120 | Open |
| DEF-007 | Putaway not before quality release (simulated rule) | inbound_deliveries | High | 105 of 3248 | Open |
| DEF-008 | Stock status transition allowed | warehouse_movements | Critical | 25 of 3229 | Open |
| DEF-009 | Recorded vs physical within 2% tolerance | inventory_batches | Medium | 194 of 3274 | Open |
