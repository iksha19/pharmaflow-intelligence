import copy
import pandas as pd
from src.data.generator import generate, VALID_UOM
from src.data.validation import PK, run_checks, material_exceptions


def test_reproducible_with_same_seed(small_cfg):
    a, b = generate(small_cfg), generate(small_cfg)
    for n in a:
        pd.testing.assert_frame_equal(a[n], b[n])


def test_different_seed_differs(small_cfg):
    c = copy.deepcopy(small_cfg); c["data"]["seed"] = 7
    assert not generate(c)["inbound_deliveries"].equals(generate(small_cfg)["inbound_deliveries"])


def test_all_entities_present_and_nonempty(tables):
    for n in ["suppliers", "materials", "purchase_orders", "po_lines", "inbound_deliveries", "inventory_batches", "warehouse_bins", "warehouse_movements",
              "quality_inspections", "production_requests", "customer_orders", "outbound_deliveries", "event_log", "kpi_targets", "scenario_assumptions"]:
        assert len(tables[n]) > 0, n


def test_primary_keys_unique(tables):
    for t, pk in PK.items():
        assert tables[t][pk].is_unique, t


def test_schema_foreign_keys_hold(db):
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"materials", "event_log", "inventory_batches"} <= names


def test_row_counts_match_between_frames_and_db(db, tables):
    for n in ["materials", "inbound_deliveries", "event_log"]:
        assert db.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] == len(tables[n])


def test_timestamps_not_after_snapshot(tables, small_cfg):
    snap = pd.Timestamp(small_cfg["data"]["start_date"]) + pd.DateOffset(months=small_cfg["data"]["months"])
    assert pd.to_datetime(tables["event_log"].event_ts).max() <= snap


def test_event_log_valid(tables):
    ev = tables["event_log"]
    assert ev[["case_id", "activity", "event_ts"]].notna().all().all()
    ts = pd.to_datetime(ev.event_ts)
    assert (ev.assign(ts=ts).groupby("case_id").ts.apply(lambda s: s.is_monotonic_increasing)).all()
    assert set(ev.case_type) == {"INBOUND", "OUTBOUND"}


def test_inventory_concepts_consistent(tables):
    b = tables["inventory_batches"]
    assert (b[["recorded_qty", "physical_qty", "available_qty", "quality_restricted_qty"]] >= 0).all().all()
    assert (b.available_qty + b.quality_restricted_qty <= b.recorded_qty + 1e-6).all()


def test_validation_detects_injected_defects(tables, small_cfg):
    res = run_checks(tables, pd.Timestamp(small_cfg["data"]["start_date"]) + pd.DateOffset(months=small_cfg["data"]["months"]))
    r = res[res.rule == "Stock status transition allowed"].iloc[0]
    assert r.violations > 0
    assert res[(res.rule_id == "DQ-02")].violations.sum() == 0      # no referential breaks


def test_validation_flags_duplicates_and_bad_uom(tables, small_cfg):
    t = {k: v.copy() for k, v in tables.items()}
    t["materials"] = pd.concat([t["materials"], t["materials"].iloc[[0]]], ignore_index=True)
    t["materials"].loc[1, "uom"] = "XX"
    res = run_checks(t)
    assert res[(res.rule_id == "DQ-01") & (res.table == "materials")].violations.iloc[0] == 2
    assert res[(res.rule_id == "DQ-04") & (res.rule.str.startswith("Material UoM"))].violations.iloc[0] >= 1
    assert "invalid_uom" in material_exceptions(t["materials"]).columns
