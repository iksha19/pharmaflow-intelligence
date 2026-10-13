"""Synthetic data generator. Company, records and results are FICTIONAL (Nordvale Pharmaceuticals)."""
from __future__ import annotations

import numpy as np
import pandas as pd

FMT = "%Y-%m-%d %H:%M:%S"
VALID_UOM = ["EA", "KG", "G", "L", "ML", "BOX"]
ZMAP = {"Ambient": "AMB", "Cold": "COLD", "Controlled": "CTRL"}
PUT_H = {"AMB": 6.0, "COLD": 4.0, "CTRL": 12.0}          # embedded signal: CTRL putaway is the bottleneck
INSP_H = {"API": 18.0, "Excipient": 10.0, "Packaging": 4.0, "Intermediate": 14.0}
REASONS = ["CoA discrepancy", "Out-of-spec result", "Documentation incomplete", "Sample retest", "Packaging integrity"]


def _s(ts):
    return None if ts is None else pd.Timestamp(ts).strftime(FMT)


def generate(cfg: dict) -> dict[str, pd.DataFrame]:
    d = cfg["data"]
    rng = np.random.default_rng(int(d["seed"]))
    start = pd.Timestamp(d["start_date"])
    end = start + pd.DateOffset(months=int(d["months"]))   # snapshot date
    H = lambda x: pd.Timedelta(hours=float(x))
    D = lambda x: pd.Timedelta(days=float(x))
    ln = lambda m, s: float(rng.lognormal(np.log(m), s))
    events: list[tuple] = []

    def ev(case, ctype, act, ts, res, ref, mat, sup=None, zone=None, prio=None):
        events.append((case, ctype, act, ts, res, ref, mat, sup, zone, prio))

    # ---------------- materials ----------------
    cats = rng.choice(["API", "Excipient", "Packaging", "Intermediate", "Finished Good"], size=d["n_materials"],
                      p=[.15, .20, .25, .10, .30])
    mats = []
    for i, c in enumerate(cats, 1):
        c = str(c)
        if c == "API":
            uom, shelf, cond, cost = "KG", int(rng.integers(540, 1460)), rng.choice(["Ambient", "Controlled", "Cold"], p=[.4, .4, .2]), ln(600, .6)
        elif c == "Excipient":
            uom, shelf, cond, cost = "KG", int(rng.integers(540, 1095)), rng.choice(["Ambient", "Controlled"], p=[.8, .2]), ln(25, .6)
        elif c == "Packaging":
            uom, shelf, cond, cost = "EA", int(rng.integers(1095, 1825)), "Ambient", ln(0.8, .6)
        elif c == "Intermediate":
            uom, shelf, cond, cost = str(rng.choice(["L", "KG"])), int(rng.integers(180, 365)), rng.choice(["Controlled", "Cold"]), ln(150, .5)
        else:
            uom, shelf, cond, cost = str(rng.choice(["EA", "BOX"])), int(rng.integers(365, 1095)), rng.choice(["Ambient", "Cold", "Controlled"], p=[.6, .3, .1]), ln(60, .8)
        rp = ln(250 if c == "Finished Good" else 600 if c == "Packaging" else 150, .5)
        mats.append(dict(material_id=f"MAT{i:04d}", material_name=f"{c} item {i:03d}", category=c, uom=uom,
                         shelf_life_days=shelf, storage_condition=str(cond), abc_class=str(rng.choice(["A", "B", "C"], p=[.2, .3, .5])),
                         gmp_relevant="N" if (c == "Packaging" and rng.random() < .3) else "Y",
                         net_weight_kg=round(ln(5, .8), 3), unit_cost=round(cost, 2), reorder_point=round(rp), safety_stock=round(rp * .4)))
    for col, rate in d["master_data_missing_rates"].items():
        for m in mats:
            if rng.random() < rate:
                m[col] = None
    for m in mats:
        if rng.random() < d["invalid_uom_rate"]:
            m["uom"] = str(rng.choice(["BX", "PCS", "UNIT"]))
    mat = {m["material_id"]: m for m in mats}
    purchasable = [m["material_id"] for m in mats if m["category"] != "Finished Good"]
    fg = [m["material_id"] for m in mats if m["category"] == "Finished Good"]

    # ---------------- suppliers (latent behaviour kept internal) ----------------
    n_sup = d["n_suppliers"]
    chronic = set(int(x) for x in rng.choice(n_sup, 3, replace=False))
    sups, lat, catalog = [], {}, {}
    for j in range(n_sup):
        sid = f"SUP{j + 1:03d}"
        sups.append(dict(supplier_id=sid, supplier_name=f"Supplier {j + 1:03d} Ltd (fictional)",
                         country=str(rng.choice(["DE", "IN", "CH", "US", "IE", "SG"])), tier=str(rng.choice(["Strategic", "Preferred", "Approved"], p=[.2, .4, .4])),
                         contract_lead_time_days=int(rng.choice([7, 10, 14, 21, 28, 42]))))
        c = j in chronic
        lat[sid] = dict(delay_prob=.55 if c else rng.uniform(.05, .25), delay_mean=9. if c else 3.,
                        reject=.09 if (c and j % 2 == 0) else rng.uniform(.005, .04), hold_mult=1.6 if c else 1.0)
        catalog[sid] = list(rng.choice(purchasable, size=min(12, len(purchasable)), replace=False))
    sup_w = rng.dirichlet(np.ones(n_sup) * 3)

    # ---------------- bins ----------------
    bins, by_zone = [], {}
    for z, n, cap in [("AMB", 120, 500), ("COLD", 60, 300), ("CTRL", 50, 300), ("QUAR", 20, 400), ("DISP", 10, 800)]:
        by_zone[z] = [f"{z}-{k:03d}" for k in range(1, n + 1)]
        bins += [dict(bin_id=b, zone=z, capacity_units=cap) for b in by_zone[z]]
    pick_bin = lambda z: str(rng.choice(by_zone[z]))

    # ---------------- inbound ----------------
    pos, lines, dlv, batches, insp, moves = [], [], [], [], [], []
    seq = dict(d=0, l=0, m=0, b=0)

    def mv(batch, m, typ, fb, tb, zone, qty, ts, sf=None, st=None):
        seq["m"] += 1
        moves.append(dict(movement_id=f"MOV{seq['m']:07d}", batch_id=batch, material_id=m, movement_type=typ, from_bin=fb, to_bin=tb,
                          zone=zone, qty=round(float(qty), 2), uom=mat[m]["uom"], movement_ts=ts, status_from=sf, status_to=st))

    def inbound(line_id, po_ts, sid, mid, qty, arrival, sched, delivery_seq, partial):
        seq["d"] += 1; seq["b"] += 1
        did, bid = f"DLV{seq['d']:06d}", f"BAT{seq['b']:06d}"
        case = f"IB-{did}"
        m, s = mat[mid], lat[sid]
        cat, cond = m["category"], m["storage_condition"]
        zone = ZMAP.get(cond, "AMB")
        bad_uom = m["uom"] not in VALID_UOM
        ev(case, "INBOUND", "Purchase Order Created", po_ts, "Procurement", line_id, mid, sid)
        ev(case, "INBOUND", "Inbound Delivery Created", min(sched - D(1), arrival - H(2)), "Procurement", line_id, mid, sid)
        gr = arrival + H(rng.uniform(.5, 3))
        ev(case, "INBOUND", "Goods Receipt", gr, "Receiving", line_id, mid, sid)
        rework = False
        if rng.random() < .02:
            ev(case, "INBOUND", "Goods Receipt", gr + H(rng.uniform(1, 4)), "Receiving", line_id, mid, sid); rework = True
        ver = None if rng.random() < (.20 if bad_uom else .03) else gr + H(ln(3, .5))
        if ver is not None:
            ev(case, "INBOUND", "Batch & Quantity Verification", ver, "Receiving", line_id, mid, sid)
        i_start = (ver or gr) + H(ln(4, .5))
        ev(case, "INBOUND", "Quality Inspection", i_start, "Quality Assurance", line_id, mid, sid)
        dur = ln(INSP_H[cat], .5)
        hold = rng.random() < (.22 if cat == "API" else .10)
        open_hold = rng.random() < d["open_hold_rate"]
        hold_h = ln(48, .6) * s["hold_mult"] if hold else 0.0
        reject = (not open_hold) and rng.random() < s["reject"]
        qty_damaged = round(qty * rng.uniform(.02, .15), 2) if rng.random() < .05 else 0.0
        accepted = qty - qty_damaged
        decision, put_final, status, result, mv_dest = None, None, "Completed", "Released", None
        if hold or open_hold:
            ev(case, "INBOUND", "Quality Hold", i_start + H(dur), "Quality Assurance", line_id, mid, sid)
        if open_hold:
            result, status = "On Hold", "Open Hold"
        else:
            decision = i_start + H(dur) + H(hold_h)
            if reject:
                result, status = "Rejected", "Rejected"
                ev(case, "INBOUND", "Quality Rejection", decision, "Quality Assurance", line_id, mid, sid)
                ev(case, "INBOUND", "Return to Supplier", decision + H(rng.uniform(6, 48)), "Logistics", line_id, mid, sid)
            else:
                ev(case, "INBOUND", "Quality Release", decision, "Quality Assurance", line_id, mid, sid)
                put = decision + H(ln(PUT_H[zone], .6))
                if rng.random() < .03:
                    put = decision - H(rng.uniform(1, 6))          # simulated rule violation: putaway before release
                dest = pick_bin(zone)
                ev(case, "INBOUND", "Putaway", put, "Warehouse", line_id, mid, sid, zone)
                put_final = put
                retry_p = .25 if cond is None else .04
                mv_dest = dest
                mv(bid, mid, "PUTAWAY", pick_bin("QUAR"), dest, zone, accepted, _s(put))
                if rng.random() < retry_p:
                    put2 = put + H(rng.uniform(2, 10)); dest2 = pick_bin(zone)
                    ev(case, "INBOUND", "Putaway", put2, "Warehouse", line_id, mid, sid, zone)
                    mv(bid, mid, "TRANSFER", dest, dest2, zone, accepted, _s(put2)); put_final, mv_dest, rework = put2, dest2, True
                ev(case, "INBOUND", "Inventory Available", max(put_final, decision) + H(.5), "Inventory Control", line_id, mid, sid, zone)
        age = max((end - gr).days, 0)
        shelf = m["shelf_life_days"] or 730
        mfg = gr - D(rng.uniform(5, min(200, .6 * shelf)))
        expiry = mfg + D(shelf)
        if result == "Released":
            consumed = min(.97, rng.beta(2, 2) * min(1, age / 180))
            rec = round(accepted * (1 - consumed), 2)
            phys = rec
            if rng.random() < .08:
                phys = round(rec * (1 + rng.uniform(-.10, .10)), 2)
            bstat = "Blocked" if rng.random() < .01 else "Released"
            bbin = mv_dest
            qr = rec if bstat == "Blocked" else 0.0
            avail = min(rec, phys) if (bstat == "Released" and expiry > end) else 0.0
        elif result == "Rejected":
            rec = phys = qr = avail = 0.0; bstat, bbin = "Rejected", pick_bin("QUAR")
        else:
            rec = phys = round(accepted, 2); qr = rec; avail = 0.0; bstat, bbin = "Quality Hold", pick_bin("QUAR")
        batches.append(dict(batch_id=bid, material_id=mid, delivery_id=did, source="PURCHASE", bin_id=bbin, received_qty=round(accepted, 2),
                            recorded_qty=rec, physical_qty=phys, quality_restricted_qty=qr, available_qty=avail,
                            received_date=_s(gr), expiry_date=_s(expiry), stock_status=bstat))
        mv(bid, mid, "GOODS_RECEIPT", None, pick_bin("QUAR"), "QUAR", accepted, _s(gr), None, "Quality Hold")
        if decision is not None:
            mv(bid, mid, "STATUS_CHANGE", None, None, "QUAR", accepted, _s(decision), "Quality Hold", result)
        insp.append(dict(inspection_id=f"QI{seq['d']:06d}", delivery_id=did, batch_id=bid, start_ts=_s(i_start), decision_ts=_s(decision),
                         result=result, hold_flag=int(hold or open_hold), hold_hours=round(hold_h, 2) if hold else None,
                         reason_code=str(rng.choice(REASONS)) if (hold or reject or open_hold) else None))
        dlv.append(dict(delivery_id=did, po_line_id=line_id, delivery_seq=delivery_seq, scheduled_date=_s(sched.normalize()), arrival_ts=_s(arrival),
                        gr_ts=_s(gr), verification_ts=_s(ver), putaway_ts=_s(put_final), delivered_qty=round(qty, 2), damaged_qty=qty_damaged,
                        partial_flag=int(partial), rework_flag=int(rework), status=status))

    last_po = end - D(150)
    span = (last_po - start).total_seconds()
    for k in range(d["n_purchase_orders"]):
        po_ts = (start + pd.Timedelta(seconds=float(rng.random() * span))).floor("h")
        sid = sups[int(rng.choice(n_sup, p=sup_w))]["supplier_id"]
        lead = next(x["contract_lead_time_days"] for x in sups if x["supplier_id"] == sid)
        req = po_ts.normalize() + D(lead)
        po_id = f"PO{k + 1:06d}"
        cancelled = rng.random() < .03
        pos.append(dict(po_id=po_id, supplier_id=sid, po_date=_s(po_ts), requested_delivery_date=_s(req), status="Cancelled" if cancelled else "Closed"))
        for mid in rng.choice(catalog[sid], size=int(rng.integers(1, 5)), replace=False):
            mid = str(mid); seq["l"] += 1; lid = f"POL{seq['l']:06d}"
            u = mat[mid]["uom"]
            qty = round(ln(600, .6), -1) if u in ("KG", "L", "G", "ML") else round(ln(8000, .5), -2)
            qty = max(qty, 10.0)
            lines.append(dict(po_line_id=lid, po_id=po_id, material_id=mid, ordered_qty=qty, uom=u, unit_price=round(mat[mid]["unit_cost"] * rng.uniform(.9, 1.1), 2)))
            if cancelled:
                continue
            s = lat[sid]
            delay = min(40., rng.gamma(2, s["delay_mean"] / 2)) if rng.random() < s["delay_prob"] else rng.normal(-.3, .5)
            arrival = (req + D(delay)).normalize() + H(rng.uniform(7, 16))
            if rng.random() < .12:
                f = rng.uniform(.4, .8)
                inbound(lid, po_ts, sid, mid, round(qty * f, 2), arrival, req, 1, True)
                inbound(lid, po_ts, sid, mid, round(qty * (1 - f), 2), arrival + D(rng.uniform(3, 14)), req, 2, True)
            else:
                inbound(lid, po_ts, sid, mid, qty, arrival, req, 1, False)

    # invalid stock transitions (rejected -> released), injected for the data-quality rules
    rej = [b for b in batches if b["stock_status"] == "Rejected"]
    if rej:
        for idx in rng.choice(len(rej), size=min(int(d["invalid_transitions"]), len(rej)), replace=False):
            b = rej[int(idx)]
            mv(b["batch_id"], b["material_id"], "STATUS_CHANGE", None, None, "QUAR", b["received_qty"],
               _s(pd.Timestamp(b["received_date"]) + H(rng.uniform(60, 400))), "Rejected", "Released")

    # ---------------- finished-goods batches (production source) ----------------
    fg_batches: dict[str, list] = {}
    for mid in fg:
        zone = ZMAP.get(mat[mid]["storage_condition"], "AMB")
        for _ in range(3):
            seq["b"] += 1; bid = f"BAT{seq['b']:06d}"
            mfg = start + D(rng.uniform(0, (end - start).days - 30))
            exp = mfg + D(mat[mid]["shelf_life_days"] or 730)
            rec = float(round(ln(600, .4), 0)); phys = rec if rng.random() > .08 else float(round(rec * rng.uniform(.9, 1.1)))
            stat = "Quality Hold" if rng.random() < .02 else "Released"
            batches.append(dict(batch_id=bid, material_id=mid, delivery_id=None, source="PRODUCTION", bin_id=pick_bin(zone), received_qty=rec,
                                recorded_qty=rec, physical_qty=phys, quality_restricted_qty=rec if stat == "Quality Hold" else 0.0,
                                available_qty=min(rec, phys) if (stat == "Released" and exp > end) else 0.0, received_date=_s(mfg),
                                expiry_date=_s(exp), stock_status=stat))
            fg_batches.setdefault(mid, []).append(batches[-1])

    # ---------------- outbound ----------------
    prop = {m: rng.beta(1, 12) for m in fg}
    for m in rng.choice(fg, size=min(6, len(fg)), replace=False):
        prop[str(m)] = .35                                                  # embedded signal: chronic stockout materials
    orders, outs = [], []
    last_ord = end - D(45)
    ospan = (last_ord - start).total_seconds()
    sla = {"High": 24, "Standard": 72, "Low": 120}
    for k in range(d["n_customer_orders"]):
        oid = f"ORD{k + 1:06d}"; case = f"OB-{oid}"
        mid = str(rng.choice(fg)); zone = ZMAP.get(mat[mid]["storage_condition"], "AMB")
        qty = float(max(1, int(ln(90, .7))))
        pr = str(rng.choice(["High", "Standard", "Low"], p=[.15, .70, .15]))
        ots = (start + pd.Timedelta(seconds=float(rng.random() * ospan))).floor("h")
        req = ots + H(sla[pr] + rng.uniform(0, 24))
        cust = f"CUST{int(rng.integers(1, 61)):03d}"
        ev(case, "OUTBOUND", "Customer Order Created", ots, "Customer Service", oid, mid, None, zone, pr)
        if rng.random() < .04:
            ev(case, "OUTBOUND", "Order Cancelled", ots + H(rng.uniform(2, 48)), "Customer Service", oid, mid, None, zone, pr)
            orders.append(dict(order_id=oid, customer_id=cust, material_id=mid, order_qty=qty, order_ts=_s(ots), requested_dispatch_ts=_s(req), priority=pr, status="Cancelled"))
            continue
        so = rng.random() < prop[mid]
        bo = float(round(qty * rng.uniform(.3, 1.0))) if so else 0.0
        if so:
            ev(case, "OUTBOUND", "Backorder Created", ots + H(rng.uniform(.2, 2)), "Inventory Control", oid, mid, None, zone, pr)
        alloc = ots + H(ln(72, .6) if so else ln(3, .6))
        ev(case, "OUTBOUND", "Inventory Allocation", alloc, "Inventory Control", oid, mid, None, zone, pr)
        ps = alloc + H(ln(4, .7))
        pdur = (ln(35, .4) + qty * .15) / 60 * (1.4 if zone == "COLD" else 1.0) * (.7 if pr == "High" else 1.0)
        pe = ps + H(pdur)
        ev(case, "OUTBOUND", "Picking", ps, "Warehouse", oid, mid, None, zone, pr)
        repick = rng.random() < (.12 if zone == "COLD" else .05)
        if repick:
            ps2 = pe + H(rng.uniform(.5, 3)); pe = ps2 + H(pdur * .6)
            ev(case, "OUTBOUND", "Picking", ps2, "Warehouse", oid, mid, None, zone, pr)
        pks = pe + H(rng.uniform(.2, 2)); pke = pks + H(ln(.5, .4))
        ev(case, "OUTBOUND", "Packing", pks, "Warehouse", oid, mid, None, zone, pr)
        disp = pke + H(ln(6, .7))
        ev(case, "OUTBOUND", "Dispatch", disp, "Logistics", oid, mid, None, zone, pr)
        rr = rng.random()
        rec_ts = disp + H(rng.uniform(4, 36))
        if rr < .015:
            rec_ts = disp - H(rng.uniform(1, 5))                     # simulated deviation: reconciliation posted before dispatch
        if rr >= .97:
            rec_ts = None                                             # simulated deviation: reconciliation never posted
        if rec_ts is not None:
            ev(case, "OUTBOUND", "Reconciliation", rec_ts, "Inventory Control", oid, mid, None, zone, pr)
        cand = [b for b in fg_batches[mid] if b["stock_status"] == "Released"] or fg_batches[mid]
        b = cand[int(rng.integers(len(cand)))]
        outs.append(dict(outbound_id=f"OUT{k + 1:06d}", order_id=oid, batch_id=b["batch_id"], zone=zone, allocation_ts=_s(alloc), pick_start_ts=_s(ps),
                         pick_end_ts=_s(pe), pack_start_ts=_s(pks), pack_end_ts=_s(pke), dispatch_ts=_s(disp), reconciliation_ts=_s(rec_ts),
                         qty_shipped=qty, qty_backordered=bo, stockout_flag=int(so), repick_flag=int(repick)))
        orders.append(dict(order_id=oid, customer_id=cust, material_id=mid, order_qty=qty, order_ts=_s(ots), requested_dispatch_ts=_s(req), priority=pr, status="Dispatched"))
        mv(b["batch_id"], mid, "PICK", b["bin_id"], pick_bin("DISP"), zone, qty, _s(pe), "Released", "Released")
        mv(b["batch_id"], mid, "DISPATCH", pick_bin("DISP"), None, "DISP", qty, _s(disp))

    # ---------------- production requests ----------------
    preqs = []
    pspan = ((end - D(30)) - start).total_seconds()
    for k in range(d["n_production_requests"]):
        mid = str(rng.choice(purchasable)); rts = (start + pd.Timedelta(seconds=float(rng.random() * pspan))).floor("h")
        q = round(ln(200, .6)); short = rng.random() < .07
        st = rts + H(ln(10 if short else 5, .5))
        preqs.append(dict(request_id=f"PRQ{k + 1:06d}", material_id=mid, requested_qty=float(q), request_ts=_s(rts), required_by_ts=_s(rts + H(12)),
                          staged_ts=_s(st), fulfilled_qty=round(q * rng.uniform(.5, .95), 2) if short else float(q), shortage_flag=int(short),
                          status="Short" if short else "Staged"))

    ev_df = pd.DataFrame(events, columns=["case_id", "case_type", "activity", "event_ts", "resource", "reference_id", "material_id", "supplier_id", "zone", "priority"])
    ev_df["event_ts"] = pd.to_datetime(ev_df["event_ts"])
    ev_df = ev_df.sort_values(["case_id", "event_ts"], kind="mergesort").reset_index(drop=True)
    ev_df["event_ts"] = ev_df["event_ts"].dt.strftime(FMT)
    ev_df.insert(0, "event_id", [f"EVT{i + 1:08d}" for i in range(len(ev_df))])

    mat_df = pd.DataFrame(mats)
    mat_df["shelf_life_days"] = mat_df["shelf_life_days"].astype("Int64")
    kpi = pd.DataFrame([dict(kpi_id=k, target_value=v["target"], direction=v["direction"], unit=v["unit"]) for k, v in cfg["kpi_targets"].items()])
    sc = pd.DataFrame([dict(scenario=s, parameter=p, value=float(v)) for s, ps in cfg["scenarios"].items() for p, v in ps.items() if p != "label"])
    return {
        "suppliers": pd.DataFrame(sups), "materials": mat_df, "warehouse_bins": pd.DataFrame(bins), "purchase_orders": pd.DataFrame(pos),
        "po_lines": pd.DataFrame(lines), "inbound_deliveries": pd.DataFrame(dlv), "inventory_batches": pd.DataFrame(batches),
        "quality_inspections": pd.DataFrame(insp), "warehouse_movements": pd.DataFrame(moves), "production_requests": pd.DataFrame(preqs),
        "customer_orders": pd.DataFrame(orders), "outbound_deliveries": pd.DataFrame(outs), "event_log": ev_df,
        "kpi_targets": kpi, "scenario_assumptions": sc,
    }
