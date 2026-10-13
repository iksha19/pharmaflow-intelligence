# UAT Test Cases

> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

| ID | Test | Steps | Expected |
|---|---|---|---|
| UAT-01 | Rebuild dataset from scratch | bash scripts/run_pipeline.sh | Exit 0; all steps ok |
| UAT-02 | KPI values reproducible with same seed | Run generate twice; compare kpis.csv | Identical |
| UAT-03 | Putaway-before-release is detected | Open Warehouse Operations > exceptions | Listed deliveries equal DQ-05 count |
| UAT-04 | Scenario controls recalculate | Change demand growth slider | Stockout risk and utilisation change |
| UAT-05 | Master-data exceptions listed | Open Material Master Data Quality | Defective materials match completeness KPI |
| UAT-06 | Process variants & bottlenecks visible | Open Process Mining | Variants, handover waits, rework loops shown |
| UAT-07 | Power BI export complete | ls data/exports/powerbi | 6 dimensions, 9 facts, KPI dictionary |
| UAT-08 | Zero-denominator handling | Select empty filter / window | Message or n/a - never silent 0 |
| UAT-09 | Automated tests pass | python -m pytest -q | All pass |
