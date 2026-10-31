import numpy as np

FEATS = ["account_age_days", "avg_order_value_30d", "country", "is_premium", "txn_count_7d"]
POLICY = {"abs_tol": 0.01, "max_mismatch_rate": 0.05, "max_distance": 0.25, "max_missing_delta": 0.05, "top_k": 3}


def _pol(**kw):
    p = dict(POLICY)
    p.update(kw)
    return p


def _user(rng, i):
    return {
        "account_age_days": int(rng.integers(1, 2000)),
        "avg_order_value_30d": round(float(rng.lognormal(3.5, 0.6)), 2),
        "country": ["US", "US", "US", "CA", "GB", "DE", "IN"][int(rng.integers(7))],
        "is_premium": bool(rng.random() < 0.3),
        "txn_count_7d": int(rng.poisson(4)),
    }


def _world(rng, n, bugs, dup_frac=0.2, extra_serve=10, drop_train=10):
    train, serve = [], []
    for i in range(n):
        eid = "user_%05d" % (1000 + i)
        f = _user(rng, i)
        train.append({"entity_id": eid, "features": dict(f)})
        s = dict(f)
        if "cents" in bugs and rng.random() < 0.4:
            s["avg_order_value_30d"] = round(s["avg_order_value_30d"] * 100, 2)
        if "tz" in bugs and rng.random() < 0.3:
            s["account_age_days"] += 1
        if "country_null" in bugs and rng.random() < 0.15:
            s["country"] = None
        if "float_noise" in bugs:
            s["avg_order_value_30d"] = round(s["avg_order_value_30d"] + float(rng.normal(0, 0.002)), 4)
        if "premium_str" in bugs:
            s["is_premium"] = "true" if s["is_premium"] else "false"
        ts = 1700000000 + i
        if rng.random() < dup_frac:
            stale = dict(s)
            stale["txn_count_7d"] = max(0, s["txn_count_7d"] - 2)
            serve.append({"entity_id": eid, "ts": ts - 3600, "features": stale})
        serve.append({"entity_id": eid, "ts": ts, "features": s})
    for j in range(extra_serve):
        serve.append({"entity_id": "user_9%04d" % j, "ts": 1700005000 + j, "features": _user(rng, j)})
    order = rng.permutation(len(serve))
    serve = [serve[int(k)] for k in order]
    return train[drop_train:], serve


def cases():
    rng = np.random.default_rng(150)
    ex1_train = [
        {"entity_id": "u1", "features": {"aov": 52.10, "country": "US"}},
        {"entity_id": "u2", "features": {"aov": 18.00, "country": "CA"}},
        {"entity_id": "u3", "features": {"aov": 75.50, "country": "US"}},
        {"entity_id": "u4", "features": {"aov": 30.00, "country": "GB"}},
    ]
    ex1_serve = [
        {"entity_id": "u3", "ts": 100, "features": {"aov": 75.50, "country": "US"}},
        {"entity_id": "u1", "ts": 100, "features": {"aov": 5210.0, "country": "US"}},
        {"entity_id": "u2", "ts": 100, "features": {"aov": 18.004, "country": None}},
        {"entity_id": "u4", "ts": 100, "features": {"aov": 30.00, "country": "GB"}},
    ]
    ex2_train = [{"entity_id": "u1", "features": {"txn_7d": 3}}, {"entity_id": "u2", "features": {"txn_7d": 5}}, {"entity_id": "u3", "features": {"txn_7d": 4}}]
    ex2_serve = [
        {"entity_id": "u1", "ts": 50, "features": {"txn_7d": 1}},
        {"entity_id": "u1", "ts": 90, "features": {"txn_7d": 3}},
        {"entity_id": "u2", "ts": 90, "features": {"txn_7d": 2}},
        {"entity_id": "u2", "ts": 90, "features": {"txn_7d": 5}},
        {"entity_id": "u9", "ts": 90, "features": {"txn_7d": 4}},
    ]
    clean = _world(rng, 120, set())
    cents = _world(rng, 120, {"cents", "tz"})
    nulls = _world(rng, 120, {"country_null", "float_noise"})
    prem = _world(rng, 80, {"premium_str"})
    const_train = [{"entity_id": "c%d" % i, "features": {"api_version": 2, "flag": True}} for i in range(5)]
    const_serve = [{"entity_id": "c%d" % i, "ts": 1, "features": {"api_version": 2 if i < 4 else 3, "flag": i != 0}} for i in range(5)]
    disjoint = ([{"entity_id": "a", "features": {"x": 1.0}}], [{"entity_id": "b", "ts": 0, "features": {"x": None}}])
    return [
        {"name": "Example 1", "hidden": False, "args": {"train_rows": ex1_train, "serve_rows": ex1_serve, "features": ["aov", "country"], "policy": POLICY},
         "explanation": "Joined on entity_id (serving is in a different order). u1's AOV is logged in cents: a mismatch. u2's 18.004 is within abs_tol. u2's country is missing in serving: a mismatch for country, and the serving missing rate is 0.25. Both features are skewed."},
        {"name": "Example 2", "hidden": False, "args": {"train_rows": ex2_train, "serve_rows": ex2_serve, "features": ["txn_7d"], "policy": _pol(max_distance=1.0)},
         "explanation": "u1's latest serving row (ts 90) matches. u2 has two rows at ts 90, so the later one (5) wins and matches. u9 is serve_only and u3 is train_only. The mismatch rate is 0, the training std of [3, 5, 4] is 0.8165, and the serving mean (3 + 5 + 4) / 3 equals the training mean, so the distance is 0."},
        {"name": "clean pipeline", "args": {"train_rows": clean[0], "serve_rows": clean[1], "features": FEATS, "policy": POLICY}},
        {"name": "cents and timezone bugs", "args": {"train_rows": cents[0], "serve_rows": cents[1], "features": FEATS, "policy": POLICY}},
        {"name": "dropped country, float noise", "args": {"train_rows": nulls[0], "serve_rows": nulls[1], "features": FEATS, "policy": _pol(top_k=5)}},
        {"name": "bool flag logged as string", "args": {"train_rows": prem[0], "serve_rows": prem[1], "features": FEATS, "policy": POLICY}},
        {"name": "constant training feature", "args": {"train_rows": const_train, "serve_rows": const_serve, "features": ["api_version", "flag"], "policy": _pol(max_mismatch_rate=0.5)}},
        {"name": "no overlap", "args": {"train_rows": disjoint[0], "serve_rows": disjoint[1], "features": ["x", "absent_feature"], "policy": POLICY}},
    ]
