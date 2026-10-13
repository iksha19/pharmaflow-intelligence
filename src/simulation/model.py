"""Analytical supply-chain scenario model (modelled estimates on SYNTHETIC data; not causal evidence).

Per finished-good material: normal lead-time demand, reorder-point policy, normal loss function for shortage.
Warehouse: labour-hour utilisation with an M/M/1-style queue delay. The replenishment lead time is CALIBRATED so the
baseline modelled stockout risk equals the observed order-level stockout rate in the dataset.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.stats import norm

PARAMS = ["supplier_lead_time_mult", "demand_growth", "receiving_hours", "putaway_hours", "picking_hours", "warehouse_capacity_mult",
          "reorder_point_mult", "safety_stock_mult", "holding_cost_rate", "expiry_window_days"]


@dataclass
class Baseline:
    items: pd.DataFrame          # per FG material: mu, sigma, unit_cost, shelf_life_days, reorder_point, safety_stock
    inbound_per_day: float
    orders_per_day: float
    rework_rate: float
    packing_hours: float
    observed_stockout_rate: float
    base_lead_days: float
    base_labour_hours: float


def _loss(z):  # standard normal loss function G(z) = phi(z) - z(1-Phi(z))
    return norm.pdf(z) - z * (1 - norm.cdf(z))


def _stockout_prob(items, L, growth, rop_mult, ss_mult):
    mu, sig = items.mu * (1 + growth), items.sigma * np.sqrt(1 + growth)
    ss = items.safety_stock * ss_mult
    rop = items.reorder_point * rop_mult + (ss - items.safety_stock)   # safety-stock change shifts the reorder point 1:1
    s = np.maximum(sig * np.sqrt(L), 1e-9)
    z = (rop - mu * L) / s
    return 1 - norm.cdf(z), z, s, mu, rop


def build_baseline(con: sqlite3.Connection, cfg: dict) -> Baseline:
    m = cfg["model"]
    o = pd.read_sql("""SELECT c.material_id, date(c.order_ts) AS d, SUM(c.order_qty) AS q FROM customer_orders c WHERE c.status='Dispatched' GROUP BY 1,2""", con)
    days = pd.date_range(cfg["data"]["start_date"], periods=int(cfg["data"]["months"] * 30.4), freq="D")
    items = pd.read_sql("SELECT material_id, unit_cost, shelf_life_days, reorder_point, safety_stock FROM materials WHERE category='Finished Good'", con)
    piv = o.pivot_table(index="d", columns="material_id", values="q", aggfunc="sum").reindex(days.strftime("%Y-%m-%d")).fillna(0)
    items["mu"] = items.material_id.map(piv.mean()).fillna(0.0)
    items["sigma"] = items.material_id.map(piv.std()).fillna(0.0)
    items["shelf_life_days"] = items["shelf_life_days"].fillna(730)
    items = items[items.mu > 0].reset_index(drop=True)
    n_days = len(days)
    inb = pd.read_sql("SELECT COUNT(*) n FROM inbound_deliveries", con).n[0] / n_days
    ords = len(o) and pd.read_sql("SELECT COUNT(*) n FROM outbound_deliveries", con).n[0] / n_days
    rew = pd.read_sql("SELECT AVG(repick_flag) r, AVG(stockout_flag) s FROM outbound_deliveries", con)
    pack = pd.read_sql("SELECT AVG((julianday(pack_end_ts)-julianday(pack_start_ts))*24) h FROM outbound_deliveries", con).h[0]
    obs = float(rew.s[0])
    bs = cfg["scenarios"]["baseline"]; off = (bs["receiving_hours"] + bs["putaway_hours"]) / 24
    lo, hi = 0.5, 90.0
    for _ in range(60):                                   # bisection calibration of base lead time
        mid = (lo + hi) / 2
        p = _stockout_prob(items, mid + off, 0, 1, 1)[0]
        avg = float(np.average(p, weights=items.mu))
        lo, hi = (mid, hi) if avg < obs else (lo, mid)
    base_L = (lo + hi) / 2
    b = Baseline(items, float(inb), float(ords), float(rew.r[0]), float(pack), obs, base_L, 0.0)
    bp = {k: cfg["scenarios"]["baseline"][k] for k in PARAMS}
    b.base_labour_hours = _labour_hours(b, bp)
    return b


def _labour_hours(b: Baseline, p: dict) -> float:
    return b.inbound_per_day * (p["receiving_hours"] + p["putaway_hours"]) + \
        b.orders_per_day * (1 + p["demand_growth"]) * (p["picking_hours"] * (1 + b.rework_rate) + b.packing_hours)


def simulate(b: Baseline, p: dict, cfg: dict) -> dict:
    m = cfg["model"]; it = b.items
    L = b.base_lead_days * p["supplier_lead_time_mult"] + (p["receiving_hours"] + p["putaway_hours"]) / 24
    prob, z, s, mu, rop = _stockout_prob(it, L, p["demand_growth"], p["reorder_point_mult"], p["safety_stock_mult"])
    Q = np.maximum(mu * m["order_cycle_days"], 1.0)
    short = s * _loss(z)                                                # expected shortage per cycle (units)
    fill = float(np.average(np.clip(1 - short / Q, 0, 1), weights=mu))
    ss_units = np.maximum(rop - mu * L, 0)
    avg_inv = Q / 2 + ss_units
    inv_value = float((avg_inv * it.unit_cost).sum())
    holding = inv_value * p["holding_cost_rate"]
    usable_days = np.maximum(m["expiry_remaining_shelf_share"] * it.shelf_life_days - p["expiry_window_days"], 0)
    at_risk = np.maximum(avg_inv - mu * usable_days, 0)
    expiry = float((at_risk * it.unit_cost).sum())
    cycles = m["horizon_days"] / m["order_cycle_days"]
    penalty = float((short * it.unit_cost).sum() * cycles * m["stockout_penalty_rate"])
    req = _labour_hours(b, p); cap = b.base_labour_hours * m["capacity_headroom"] * p["warehouse_capacity_mult"]
    rho = req / cap
    cycle_h = p["picking_hours"] * (1 + b.rework_rate) + b.packing_hours
    queue_h = min(240.0, cycle_h * rho ** 2 / (1 - rho)) if rho < 1 else 240.0
    stockout_wait_h = float(np.average(prob, weights=mu)) * (L / 2) * 24
    orders_day = b.orders_per_day * (1 + p["demand_growth"])
    capacity_orders = orders_day / rho
    thr = min(orders_day, capacity_orders)
    labour = req * m["labor_cost_per_hour"] * m["horizon_days"]
    return dict(stockout_risk=float(np.average(prob, weights=mu)), service_level=fill, avg_inventory_value=inv_value, holding_cost=holding,
                expiry_exposure_value=expiry, avg_order_delay_h=stockout_wait_h + queue_h, warehouse_utilisation=rho, throughput_orders_per_day=thr, throughput_capacity_orders_per_day=capacity_orders,
                labour_cost=labour, stockout_penalty_cost=penalty, operating_cost=holding + labour + penalty, replenishment_lead_days=L)


def scenario_table(b: Baseline, cfg: dict, overrides: dict[str, dict] | None = None) -> pd.DataFrame:
    rows = {}
    for name, sc in cfg["scenarios"].items():
        p = {k: float(sc[k]) for k in PARAMS}
        p.update((overrides or {}).get(name, {}))
        rows[name] = simulate(b, p, cfg)
    return pd.DataFrame(rows).T


def compare(table: pd.DataFrame, base: str = "baseline") -> pd.DataFrame:
    out = []
    for sc in table.index:
        if sc == base:
            continue
        for metric in table.columns:
            bv, sv = table.loc[base, metric], table.loc[sc, metric]
            out.append(dict(scenario=sc, metric=metric, baseline=bv, scenario_value=sv, abs_change=sv - bv, rel_change=(sv - bv) / bv if bv else np.nan))
    return pd.DataFrame(out)
