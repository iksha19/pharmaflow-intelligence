#!/usr/bin/env python
"""Generate the Business Process Architecture pack (Markdown + Mermaid) from computed results. All numbers come from the pipeline outputs.
Everything here is process DESIGN on SYNTHETIC data - not SAP configuration and not Merck data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data.db import ROOT, connect, load_config
from src.analytics.kpis import kpi_dictionary
from src.simulation.model import build_baseline, scenario_table, compare

cfg = load_config(); P = ROOT / cfg["paths"]["processed"]; DOCS = ROOT / "docs"
rd = lambda n: pd.read_csv(P / n)
k = rd("kpis.csv").set_index("kpi_id"); recs = rd("recommendations.csv"); dq = rd("dq_findings.csv"); rc = rd("pm_root_cause.csv")
dev = rd("pm_deviation_summary.csv").set_index("case_type"); rw = rd("pm_rework_loops.csv"); tr = rd("pm_transitions_inbound.csv")
con = connect(cfg); base = build_baseline(con, cfg); sim = scenario_table(base, cfg); cmp = compare(sim)
DISCLAIMER = "> **Synthetic data disclaimer:** Nordvale Pharmaceuticals, all records, results and costs are fictional. No Merck systems or data were accessed. This is process design, not SAP configuration.\n\n"


def md(df, floatfmt=3):
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]): df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:.{floatfmt}f}")
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "".join("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in r) + " |\n" for r in df.itertuples(index=False))


def w(path, title, body):
    p = DOCS / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(f"# {title}\n\n{DISCLAIMER}{body}")


pct = lambda i: f"{k.loc[i, 'value']:.1%}"
hrs = lambda i: f"{k.loc[i, 'value']:.1f} h"

w("requirements/01_project_charter.md", "Project Charter - PharmaFlow Intelligence", f"""
**Purpose.** Give Healthcare Business Process Architecture a fact-based view of the end-to-end warehouse and inventory process (supplier PO to dispatch) and a quantified improvement backlog.

**Objectives.** (1) Measure process KPIs reproducibly from event data. (2) Find bottlenecks, rework and deviations through process mining. (3) Raise master-data quality. (4) Model improvement scenarios before change. (5) Hand over requirements and UAT criteria.

**Success measures (targets from `config/settings.yaml`).**

{md(rd('kpis.csv')[['kpi_id','value','target_value','direction']].dropna(subset=['target_value']))}

**Sponsor / owner.** Head of Healthcare Supply Chain (fictional role). **Business Process Architect:** accountable for process design and requirements.
""")
w("requirements/02_scope_and_assumptions.md", "Scope and Assumptions", """
**In scope:** supplier PO, inbound delivery, goods receipt, batch/quantity verification, quality inspection/release/hold, putaway, inventory availability, production staging requests, customer-order allocation, pick, pack, dispatch, reconciliation.

**Out of scope:** SAP configuration, GxP validation, serialisation, transport management, finance postings, real Merck data.

**Assumptions.** Single-line customer orders; stockouts flagged per order; inventory only as an end-of-period snapshot; day-level on-time comparison; SLA by priority 24/72/120 h; 2% inventory tolerance; fictional currency.
""")
w("requirements/03_stakeholder_map.md", "Stakeholder Map", md(pd.DataFrame([
    ("Head of Healthcare Supply Chain", "Sponsor", "High", "High", "Monthly steering"), ("Business Process Architect", "Process owner (design)", "High", "High", "Weekly"),
    ("Warehouse Operations Manager", "Process executor", "High", "Medium", "Weekly"), ("QA Release Manager", "Quality gate owner", "High", "Medium", "Bi-weekly"),
    ("Head of Procurement", "Supplier owner", "Medium", "High", "Monthly"), ("Master Data Steward", "Data owner", "Medium", "Medium", "Bi-weekly"),
    ("Supply Planning Lead", "Replenishment parameters", "Medium", "High", "Weekly"), ("IT / SAP EWM-MM Product Owner", "Enabler", "Medium", "Medium", "Bi-weekly"),
    ("Inventory Control Lead", "Stock accuracy, expiry", "Medium", "Medium", "Weekly")], columns=["Stakeholder", "Role", "Influence", "Interest", "Engagement"])))
w("requirements/04_raci.md", "RACI Matrix", "R=Responsible, A=Accountable, C=Consulted, I=Informed\n\n" + md(pd.DataFrame([
    ("Define KPI dictionary", "A/R", "C", "C", "C", "I", "C"), ("Receiving & verification process", "C", "A/R", "C", "I", "I", "C"), ("Quality release / hold decision", "I", "C", "A/R", "I", "I", "I"),
    ("Putaway & storage rules", "C", "A/R", "C", "I", "C", "C"), ("Material master remediation", "C", "I", "I", "A/R", "I", "C"), ("Reorder point / safety stock", "C", "I", "I", "C", "A/R", "I"),
    ("Supplier performance review", "C", "I", "C", "I", "I", "A/R"), ("UAT sign-off", "A", "R", "R", "R", "R", "R")],
    columns=["Activity", "Process Architect", "Warehouse Ops", "QA Release", "Master Data", "Supply Planning", "Procurement"])))
w("process_maps/as_is.md", "As-Is Process Map (observed)", f"""
```mermaid
flowchart LR
  A[PO created] --> B[Inbound delivery created] --> C[Goods receipt] --> D[Batch & qty verification] --> E[Quality inspection]
  E -->|release| F[Quality release] --> G[Putaway] --> H[Inventory available]
  E -->|hold| I[Quality hold] --> F
  E -->|reject| J[Rejection] --> K[Return to supplier]
  H --> L[Order allocation] --> M[Pick] --> N[Pack] --> O[Dispatch] --> P[Reconciliation]
  L -.stockout.-> Q[Backorder] -.wait.-> L
  G -.retry.-> G
  M -.re-pick.-> M
```
**Observed pain points (from data):** inbound deviation rate {dev.loc['INBOUND','deviation_rate']:.1%}, outbound {dev.loc['OUTBOUND','deviation_rate']:.1%}; rework rate {pct('process_rework_rate')}; supplier OTD {pct('supplier_on_time_delivery')}; receiving-to-putaway {hrs('receiving_to_putaway_hours')}; quality hold {hrs('quality_hold_hours')}; stockout rate {pct('stockout_rate')}.

**Largest internal handover waits (inbound):**

{md(tr[tr.segment=='Internal handover'].head(5)[['activity','next_activity','count','mean_h','p90_h','share_of_total_wait']])}
""")
w("process_maps/to_be.md", "To-Be Process Map (proposed design)", """
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
""")
w("requirements/05_business_requirements.md", "Business Requirements Document (BRD)", "\n".join(f"- **BR-{i+1:02d}** ({r.rec_id}) {r.problem}: {r.intervention} KPI: `{r.kpi}`. Owner: {r.stakeholder}." for i, r in enumerate(recs.itertuples())) + "\n")
w("requirements/06_functional_requirements.md", "Functional Requirements and Acceptance Criteria", md(pd.DataFrame([
    ("FR-01", "System blocks putaway while stock status is Quality Hold/unreleased", "Test: attempt putaway on held batch -> rejected; 0 'putaway before release' events in 30 days"),
    ("FR-02", "Receiving requires batch, quantity and UoM verification before inspection can start", "0 cases missing verification; invalid-UoM materials cannot be received"),
    ("FR-03", "Material creation enforces mandatory fields (UoM, shelf life, storage condition, ABC, GMP flag, net weight)", "Master-data completeness >= 98%"),
    ("FR-04", "Quality hold aging report with alerts at target hours", "Holds older than 48 h listed daily; avg hold <= 48 h"),
    ("FR-05", "Shortage alert when available stock falls below reorder point", "Alert raised before backorder; stockout rate trending to <= 5%"),
    ("FR-06", "Near-expiry alerts at 90/60/30 days with FEFO pick suggestion", "Expiry exposure value reported monthly and declining"),
    ("FR-07", "Event log captured for every process step with case id, timestamp, resource", "Event-log completeness check passes in pipeline"),
    ("FR-08", "Dashboards refresh from the reproducible pipeline", "`bash scripts/run_pipeline.sh` exit code 0")], columns=["ID", "Requirement", "Acceptance criterion"])))
kd = kpi_dictionary(); w("requirements/07_kpi_dictionary.md", "KPI Dictionary", md(kd[["kpi_id", "name", "numerator", "denominator", "exclusions", "window", "limitation"]]))
w("requirements/08_master_data_quality_rules.md", "Master-Data Quality Rules", md(dq[["rule_id", "rule", "table", "severity", "violations", "total", "violation_pct"]]))
fails = dq[dq.violations > 0].reset_index(drop=True)
w("uat/01_uat_test_cases.md", "UAT Test Cases", md(pd.DataFrame([
    ("UAT-01", "Rebuild dataset from scratch", "bash scripts/run_pipeline.sh", "Exit 0; all steps ok"), ("UAT-02", "KPI values reproducible with same seed", "Run generate twice; compare kpis.csv", "Identical"),
    ("UAT-03", "Putaway-before-release is detected", "Open Warehouse Operations > exceptions", "Listed deliveries equal DQ-05 count"),
    ("UAT-04", "Scenario controls recalculate", "Change demand growth slider", "Stockout risk and utilisation change"),
    ("UAT-05", "Master-data exceptions listed", "Open Material Master Data Quality", "Defective materials match completeness KPI"),
    ("UAT-06", "Process variants & bottlenecks visible", "Open Process Mining", "Variants, handover waits, rework loops shown"),
    ("UAT-07", "Power BI export complete", "ls data/exports/powerbi", "6 dimensions, 9 facts, KPI dictionary"),
    ("UAT-08", "Zero-denominator handling", "Select empty filter / window", "Message or n/a - never silent 0"),
    ("UAT-09", "Automated tests pass", "python -m pytest -q", "All pass")], columns=["ID", "Test", "Steps", "Expected"])))
w("uat/02_example_defect_log.md", "Example Defect Log (derived from data-quality findings)", md(pd.DataFrame([
    (f"DEF-{i+1:03d}", r.rule, r.table, r.severity, f"{r.violations} of {r.total}", "Open") for i, r in fails.iterrows()], columns=["Defect", "Description", "Object", "Severity", "Records affected", "Status"])))
risks = pd.DataFrame([("R1", "Master-data remediation slower than planned", "Medium", "High", "Prioritise by impact (q7); steward capacity"), ("R2", "Users bypass status gate", "Medium", "High", "System-enforced gate; audit report"),
    ("R3", "KPI definitions disputed", "Medium", "Medium", "Signed-off KPI dictionary"), ("R4", "Simulation read as forecast", "Medium", "Medium", "Label as modelled estimates; calibrate with real data"),
    ("R5", "Synthetic findings do not transfer to real systems", "High", "High", "Re-run pipeline on real extracts; validate rules with QA")], columns=["ID", "Risk", "Likelihood", "Impact", "Mitigation"])
w("business_case/01_risk_register.md", "Risk Register", md(risks))
w("business_case/02_root_cause_analysis.md", "Root-Cause Analysis", "Rate vs group average, by dimension (inbound: deviation rate; outbound: late dispatch rate).\n\n" + md(rc.groupby("case_type").head(8)[["case_type", "dimension", "value", "cases", "deviation_rate", "rework_rate", "rate_vs_group_avg"]]) +
  "\nAssociation, not proof of causation; confirm through process walk-throughs.\n")
w("business_case/03_improvement_roadmap.md", "Improvement Roadmap", "\n".join(f"- **{'Now (0-3 mo)' if i < 3 else 'Next (3-6 mo)' if i < 6 else 'Later (6-12 mo)'}** {r.rec_id}: {r.problem} -> {r.kpi}" for i, r in enumerate(recs.itertuples())) + "\n")
b, i_ = sim.loc["baseline"], sim.loc["improvement"]
w("business_case/04_executive_business_case.md", "Executive Business Case", f"""
**Problem.** Stockout rate {pct('stockout_rate')} (target {k.loc['stockout_rate','target_value']:.0%}), supplier OTD {pct('supplier_on_time_delivery')}, receiving-to-putaway {hrs('receiving_to_putaway_hours')}, deviation {pct('process_deviation_rate')}.

**Modelled impact of proposed warehouse improvements** (modelled estimates on synthetic data; not causal evidence):

{md(cmp[(cmp.scenario=='improvement') & cmp.metric.isin(['stockout_risk','service_level','avg_order_delay_h','warehouse_utilisation','operating_cost'])][['metric','baseline','scenario_value','abs_change','rel_change']], 4)}
Modelled annual operating cost moves from {b.operating_cost:,.0f} to {i_.operating_cost:,.0f} (fictional currency). Costs of implementation are not modelled; a real business case needs them.

**Recommendation.** Approve REC-01..REC-03 for design validation, with KPI verification at 90 days.

{md(recs[['rec_id','problem','evidence','intervention','kpi','stakeholder','verification']])}
""")
w("business_case/05_limitations_and_assumptions.md", "Limitations and Assumptions", """
- Data are synthetic; embedded effects (e.g. slow controlled-zone putaway, chronic late suppliers) were designed into the generator, so findings demonstrate method, not real operations.
- Deviation = breach of simulated rules; not a confirmed regulatory or GMP violation.
- Simulation: normal lead-time demand, calibrated lead time, simplified queue; no causal claims.
- Inventory is a single snapshot; turnover uses that snapshot as denominator.
- Mixed units of measure in volume KPIs; fictional currency.
- Process design only; SAP EWM/MM configuration, validation and data migration are out of scope.
""")
w("recommendations_traceability.md", "Recommendation Traceability", "Each row links observed/simulated problem -> evidence -> intervention -> KPI -> accountable stakeholder -> verification method.\n\n" + md(recs))
print(f"docs written: {len(list(DOCS.rglob('*.md')))} files")
