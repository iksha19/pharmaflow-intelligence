import numpy as np
import pytest
from src.simulation.model import build_baseline, simulate, scenario_table, compare, PARAMS


@pytest.fixture(scope="module")
def base(db, small_cfg):
    return build_baseline(db, small_cfg)


def P(cfg, name="baseline", **kw):
    p = {k: float(cfg["scenarios"][name][k]) for k in PARAMS}; p.update(kw); return p


def test_baseline_calibrated_to_observed_stockout(base, small_cfg):
    r = simulate(base, P(small_cfg), small_cfg)
    assert abs(r["stockout_risk"] - base.observed_stockout_rate) < 0.01


def test_more_safety_stock_lowers_stockout_risk(base, small_cfg):
    a = simulate(base, P(small_cfg), small_cfg); b = simulate(base, P(small_cfg, safety_stock_mult=2.0), small_cfg)
    assert b["stockout_risk"] < a["stockout_risk"] and b["avg_inventory_value"] > a["avg_inventory_value"]


def test_longer_lead_time_and_demand_raise_risk(base, small_cfg):
    a = simulate(base, P(small_cfg), small_cfg)
    assert simulate(base, P(small_cfg, supplier_lead_time_mult=1.5), small_cfg)["stockout_risk"] > a["stockout_risk"]
    assert simulate(base, P(small_cfg, demand_growth=.3), small_cfg)["stockout_risk"] > a["stockout_risk"]


def test_utilisation_rises_with_demand_and_falls_with_capacity(base, small_cfg):
    a = simulate(base, P(small_cfg), small_cfg)
    assert simulate(base, P(small_cfg, demand_growth=.3), small_cfg)["warehouse_utilisation"] > a["warehouse_utilisation"]
    assert simulate(base, P(small_cfg, warehouse_capacity_mult=1.5), small_cfg)["warehouse_utilisation"] < a["warehouse_utilisation"]


def test_saturation_capped_not_infinite(base, small_cfg):
    r = simulate(base, P(small_cfg, warehouse_capacity_mult=.6, demand_growth=.6), small_cfg)
    assert r["warehouse_utilisation"] > 1 and np.isfinite(r["avg_order_delay_h"]) and r["avg_order_delay_h"] <= 240 + 1e4


def test_probabilities_bounded_and_compare_math(base, small_cfg):
    t = scenario_table(base, small_cfg)
    assert t.stockout_risk.between(0, 1).all() and t.service_level.between(0, 1).all()
    c = compare(t).query("scenario=='disruption' and metric=='stockout_risk'").iloc[0]
    assert abs(c.abs_change - (c.scenario_value - c.baseline)) < 1e-12 and abs(c.rel_change - c.abs_change / c.baseline) < 1e-12


def test_overrides_change_results(base, small_cfg):
    t0 = scenario_table(base, small_cfg); t1 = scenario_table(base, small_cfg, {"baseline": {"demand_growth": .2}})
    assert t1.loc["baseline", "stockout_risk"] > t0.loc["baseline", "stockout_risk"]
