# PharmaFlow Intelligence

End-to-end pharmaceutical warehouse and supply-chain **process intelligence** platform: SQL KPI analytics, process mining, master-data quality, scenario simulation, Power BI-ready exports and a Business Process Architecture documentation pack.

> **All data is synthetic.** The company (Nordvale Pharmaceuticals), records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.

## Business problem
Flow from supplier PO to dispatch suffers delays, rework, quality holds, stockouts, expiry exposure and master-data defects. The project measures them reproducibly, finds root causes, models improvements and documents requirements.

## Architecture
generate_data.py -> CSV + SQLite (database/schema.sql) -> validate_data.py -> calculate_kpis.py -> run_process_mining.py -> export_powerbi.py -> generate_docs.py -> app.py (Streamlit, presentation only). Logic lives in src/.
Stack: Python 3.12, pandas, SQLite, Plotly, Streamlit, SciPy, pytest. PM4Py is not used; a transparent pandas engine is.

## Quick start (Bash)
```bash
cd pharmaflow-intelligence
bash scripts/run_pipeline.sh
source .venv/bin/activate
streamlit run app.py     # http://localhost:8501 (remote: --server.address 0.0.0.0 and port-forward)
```
Options: `python scripts/generate_data.py --seed 7 --scale 0.5`. Defaults: config/settings.yaml.

## Dataset
15 tables incl. a ~44k-event log. Exceptions: supplier delays, partial deliveries, damage/rejection, quality holds, missing attributes, repeated handling, putaway delays, inventory mismatch, stockouts, near-expiry, late dispatch, cancellations. Physical, recorded, quality-restricted and available stock are distinct.

## KPIs
Each has numerator, denominator, exclusions, window, limitation (docs/requirements/07_kpi_dictionary.md). Zero denominators return NULL, never 0.

## Process mining
Variants, handover waits (supplier lead time separated from internal handovers), cycle times, rework loops, missing/out-of-order conformance, root cause. Deviations breach simulated rules, not confirmed GMP violations.

## App sections
Executive Overview, Warehouse Operations, Inventory and Expiry Risk, Supplier Performance, Process Mining, Master Data Quality, Scenario Simulator, Recommendations and Tracking, Methodology.

## Scenario results
See docs/business_case/04_executive_business_case.md. Modelled estimates only; baseline calibrated to the observed stockout rate; no causal claims.

## Power BI
data/exports/powerbi/ (6 dimensions, 9 facts) and docs/powerbi/ (relationships, DAX, 6 page specs, refresh). No .pbix shipped.

## Testing
```bash
python -m pytest -q
```

## Limitations
Single-line orders; per-order stockout flags; one inventory snapshot; day-level OTD; mixed units; embedded synthetic effects mean findings demonstrate method, not real operations.

## Screenshots
_Add after launching the app._
