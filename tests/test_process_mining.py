import pandas as pd
from src.process_mining.analysis import case_table, conformance, transitions, variants, rework_loops, MANDATORY


def _ev(rows):
    df = pd.DataFrame(rows, columns=["case_id", "activity", "event_ts"])
    df["case_type"] = "INBOUND"; df["event_id"] = [f"E{i}" for i in range(len(df))]
    for c in ("supplier_id", "material_id", "zone", "priority", "reference_id", "resource"): df[c] = None
    df["event_ts"] = pd.to_datetime(df["event_ts"])
    return df.sort_values(["case_id", "event_ts"]).reset_index(drop=True)


def _full(case, t0="2025-01-01"):
    acts = MANDATORY["IN_RELEASED"]
    return [(case, a, pd.Timestamp(t0) + pd.Timedelta(hours=i)) for i, a in enumerate(acts)]


def test_conforming_case_has_no_deviation():
    ev = _ev(_full("C1")); c = case_table(ev); r = conformance(ev, c).iloc[0]
    assert not r.deviation and r.fitness == 1.0 and c.status.iloc[0] == "Completed"


def test_missing_activity_detected():
    rows = [x for x in _full("C1") if x[1] != "Batch & Quantity Verification"]
    ev = _ev(rows); r = conformance(ev, case_table(ev)).iloc[0]
    assert r.has_missing and "Batch & Quantity Verification" in r.missing and r.deviation and r.fitness < 1


def test_out_of_order_detected():
    rows = _full("C1"); rows = [(c, a, (t - pd.Timedelta(hours=5)) if a == "Putaway" else t) for c, a, t in rows]   # putaway before release
    ev = _ev(rows); r = conformance(ev, case_table(ev)).iloc[0]
    assert r.has_out_of_order and "Putaway before Quality Release" in r.out_of_order


def test_rework_is_repetition_not_deviation():
    rows = _full("C1") + [("C1", "Putaway", pd.Timestamp("2025-01-01") + pd.Timedelta(hours=20))]
    ev = _ev(rows); r = conformance(ev, case_table(ev)).iloc[0]
    assert r.has_rework and not r.deviation
    assert rework_loops(ev).iloc[0].activity == "Putaway"


def test_open_hold_case_excluded_from_deviation():
    rows = [x for x in _full("C1") if x[1] not in ("Quality Release", "Putaway", "Inventory Available")] + [("C1", "Quality Hold", pd.Timestamp("2025-01-01") + pd.Timedelta(hours=9))]
    ev = _ev(rows); c = case_table(ev); r = conformance(ev, c).iloc[0]
    assert c.status.iloc[0] == "Open" and not r.deviation


def test_variants_and_transitions_counts():
    ev = _ev(_full("C1") + _full("C2", "2025-02-01"))
    v = variants(case_table(ev), "INBOUND"); assert v.cases.iloc[0] == 2 and abs(v.cum_share.iloc[-1] - 1) < 1e-9
    t = transitions(ev, "INBOUND"); assert (t["count"] == 2).all() and (t.mean_h == 1.0).all()


def test_real_log_conformance_runs(db):
    from src.process_mining.analysis import analyze
    res = analyze(db)
    assert (res["conformance"].fitness.dropna().between(0, 1)).all()
    assert set(res["deviation_summary"].case_type) == {"INBOUND", "OUTBOUND"}
    assert len(res["root_cause"]) > 0
