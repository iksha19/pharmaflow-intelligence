# Data refresh

```bash
bash scripts/run_pipeline.sh          # regenerates data/exports/powerbi/*.csv
```
In Power BI Desktop: Get Data > Folder (or Text/CSV) > `data/exports/powerbi/`, then Refresh. No `.pbix` file is shipped; build it from the CSVs
following `relationships.md`, `dax_measures.md` and `report_pages.md`. All data is synthetic.
