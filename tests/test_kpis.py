import numpy as np
import pandas as pd
from src.analytics.kpis import KPI_DEFS, compute_kpis, kpi_dictionary
from src.analytics.metrics import safe_div, inbound_frame, supplier_scorecard, expiry_exposure, inventory_frame
from src.analytics.queries import run_all

S, E = "2024-01-01 00:00:00", "2026-01-01 00:00:00"


def test_every_kpi_returns_num_den(db):
    k = compute_kpis(db, S, E)
    assert len(k) == len(KPI_DEFS) and k.denominator.notna().all()


def test_supplier_otd_matches_pandas(db):
    k = compute_kpis(db, S, E).set_index("kpi_id")
    inb = inbound_frame(db)
    assert abs(k.loc["supplier_on_time_delivery", "value"] - inb.on_time.mean()) < 1e-9


def test_zero_denominator_gives_null_not_zero(db):
    k = compute_kpis(db, "1990-01-01 00:00:00", "1990-02-01 00:00:00").set_index("kpi_id")
    assert pd.isna(k.loc["supplier_on_time_delivery", "value"]) and pd.isna(k.loc["on_time_dispatch_rate"].value)


def test_safe_div_edge_cases():
    assert np.isnan(safe_div(5, 0)) and np.isnan(safe_div(5, None)) and safe_div(1, 4) == .25


def test_ratios_between_0_and_1(db):
    k = compute_kpis(db, S, E)
    r = k[k.unit == "ratio"].value.dropna()
    assert ((r >= 0) & (r <= 1)).all()


def test_dictionary_complete():
    d = kpi_dictionary()
    assert d[["numerator", "denominator", "exclusions", "window", "limitation"]].notna().all().all()


def test_management_queries_run(db):
    res = run_all(db, "2026-01-01")
    assert len(res) == 7 and len(res["q1_supplier_delay_contribution"]) > 0
    assert abs(res["q1_supplier_delay_contribution"].pct_of_all_delay_days.sum() - 100) < 0.5


def test_scorecard_delay_shares_sum_to_one(db):
    sc = supplier_scorecard(inbound_frame(db))
    assert abs(sc.pct_of_delay_days.sum() - 1) < 1e-9


def test_expiry_window_monotonic(db):
    inv = inventory_frame(db, "2026-01-01")
    assert len(expiry_exposure(inv, 30)) <= len(expiry_exposure(inv, 90)) <= len(expiry_exposure(inv, 365))
