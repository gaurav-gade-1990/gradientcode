import numpy as np

H = 3600
D = 86400
SPAN = 6 * D


def S(sid, ent, feat, val, ts, ver=1, created=None):
    return {"snapshot_id": sid, "entity_id": ent, "feature": feat, "value": val, "ts": ts, "version": ver, "created_at": ts if created is None else created}


def L(lid, ent, ts, y):
    return {"label_id": lid, "entity_id": ent, "event_ts": ts, "label": y}


def _bulk(rng, n_users, n_labels):
    specs = {
        "txn_count_24h": {"lag": 5 * 60, "ttl": 2 * H, "default": 0},
        "avg_amount_30d": {"lag": H, "ttl": 2 * D, "default": 0.0},
        "account_tier": {"lag": 0, "ttl": 30 * D, "default": "unknown"},
        "device_risk": {"lag": 10 * 60, "ttl": 6 * H, "default": -1.0},
    }
    t0 = 1_700_000_000
    snaps, k = [], 0
    for u in range(n_users):
        ent = "acct_%04d" % u
        for f in specs:
            step = {"txn_count_24h": 3 * H, "avg_amount_30d": D // 2, "account_tier": 3 * D, "device_risk": 4 * H}[f]
            t = t0 - int(rng.integers(0, step))
            while t < t0 + SPAN:
                if rng.random() < 0.85:
                    k += 1
                    if f == "txn_count_24h":
                        v = int(rng.poisson(3))
                    elif f == "avg_amount_30d":
                        v = round(float(rng.lognormal(4, 0.5)), 2)
                    elif f == "account_tier":
                        v = ["free", "pro", "business"][int(rng.integers(3))]
                    else:
                        v = round(float(rng.random()), 3)
                    delay = int(rng.integers(0, 20 * 60))
                    if rng.random() < 0.05:
                        delay += int(rng.integers(1, 10)) * D
                    snaps.append(S("s%05d" % k, ent, f, v, t, 1, t + delay))
                    if rng.random() < 0.1:
                        k += 1
                        snaps.append(S("s%05d" % k, ent, f, v if f == "account_tier" else (v * 2 if f != "txn_count_24h" else v + 1), t, 2, t + delay + int(rng.integers(0, 2 * D))))
                t += step
    labels = []
    for i in range(n_labels):
        u = int(rng.integers(0, n_users + 2))
        labels.append(L("cb_%04d" % i, "acct_%04d" % u, t0 + int(rng.integers(0, SPAN)), int(rng.random() < 0.1)))
    order = rng.permutation(len(snaps))
    return labels, [snaps[int(j)] for j in order], specs


def cases():
    rng = np.random.default_rng(143)
    T = 1_000_000
    ex1_snaps = [
        S("s1", "acct_7", "txn_count_24h", 2, T - 2 * H),
        S("s2", "acct_7", "txn_count_24h", 9, T - 10 * 60),
        S("s3", "acct_7", "txn_count_24h", 14, T + 5 * 60),
    ]
    ex1_specs = {"txn_count_24h": {"lag": 15 * 60, "ttl": 6 * H, "default": 0}}
    ex2_snaps = [
        S("t1", "acct_3", "credit_limit", 5000, T - D, 1, T - D + 60),
        S("t2", "acct_3", "credit_limit", 7500, T - D, 2, T - D + 600),
        S("t3", "acct_3", "credit_limit", 2500, T - D, 3, T + 7 * D),
        S("t4", "acct_3", "zip_risk", 0.8, T - 3 * D),
    ]
    ex2_specs = {"credit_limit": {"lag": 0, "ttl": 2 * D, "default": None}, "zip_risk": {"lag": 0, "ttl": 2 * D, "default": 0.5}}
    big = _bulk(rng, 7, 120)
    edge_snaps = [
        S("e1", "a", "f", 1, 100), S("e2", "a", "f", 2, 200, 1, 260), S("e3", "a", "f", 3, 300),
        S("e4", "b", "f", 10, 500, 1, 500), S("e5", "b", "f", 11, 500, 2, 900), S("e6", "a", "g", "x", 0),
        S("e7", "a", "unused", 99, 0),
    ]
    edge_specs = {"f": {"lag": 50, "ttl": 100, "default": -1}, "g": {"lag": 0, "ttl": 0, "default": "none"}}
    edge_labels = [L("l1", "a", 350, 1), L("l2", "a", 310, 0), L("l3", "a", 250, 0), L("l4", "b", 600, 1), L("l5", "b", 950, 1),
                   L("l6", "a", 0, 0), L("l7", "c", 400, 0), L("l8", "a", 149, 1), L("l9", "a", 251, 0)]
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"labels": [L("cb_101", "acct_7", T, 1)], "snapshots": ex1_snaps, "feature_specs": ex1_specs},
         "explanation": "as_of = T - 15 min. s3 is in the future and s2 (T - 10 min) is after the cutoff, so neither is visible. s1 is 1h45m old at the cutoff, within the 6h TTL, so the value is 2 from s1."},
        {"name": "Example 2", "hidden": False,
         "args": {"labels": [L("cb_102", "acct_3", T, 0)], "snapshots": ex2_snaps, "feature_specs": ex2_specs},
         "explanation": "t1 to t3 share ts = T - 1 day. t3 is the newest version, but it was written a week after the event (a backfill), so it isn't visible. t2 beats t1 on version, giving 7500. zip_risk's only row is 3 days old against a 2-day TTL: expired, so it takes the default 0.5 and no source."},
        {"name": "Example 3", "hidden": False,
         "args": {"labels": [L("cb_103", "acct_new", T, 0)], "snapshots": ex1_snaps, "feature_specs": ex1_specs},
         "explanation": "No snapshots exist for acct_new. The feature is missing and takes the default 0."},
        {"name": "boundaries and ties", "args": {"labels": edge_labels, "snapshots": edge_snaps, "feature_specs": edge_specs}},
        {"name": "chargeback training set", "args": {"labels": big[0], "snapshots": big[1], "feature_specs": big[2]}},
        {"name": "no snapshots at all", "args": {"labels": edge_labels[:3], "snapshots": [], "feature_specs": edge_specs}},
        {"name": "lag pushes cutoff before every row", "args": {"labels": [L("x", "a", 300, 1)], "snapshots": edge_snaps, "feature_specs": {"f": {"lag": 250, "ttl": 1000, "default": 0}}}},
    ]
