import numpy as np

POLICY = {"min_requests": 200, "abort_error_bp": 2000, "max_error_delta_bp": 100, "max_p99_pct": 120, "pass_windows": 3, "fail_windows": 2}


def arm(rng, requests, err_rate, lat_mu, slow_frac=0.0, n_lat=60):
    errors = int(round(requests * err_rate))
    lat = [int(x) for x in rng.lognormal(np.log(lat_mu), 0.12, n_lat)]
    for i in range(int(round(slow_frac * n_lat))):
        lat[i * 7 % n_lat] = int(lat_mu * 6)
    return {"requests": requests, "errors": errors, "latencies_ms": lat}


def W(label, b, c):
    return {"window": label, "baseline": b, "canary": c}


def _pol(**kw):
    p = dict(POLICY)
    p.update(kw)
    return p


def _label(i):
    return "14:%02d" % (5 * i) if i < 12 else "15:%02d" % (5 * (i - 12))


def _series(rng, specs):
    return [W(_label(i), arm(rng, *bs), arm(rng, *cs)) for i, (bs, cs) in enumerate(specs)]


def cases():
    rng = np.random.default_rng(147)
    lat_b = [410, 380, 450, 520, 390, 610, 430, 470, 400, 980]
    lat_c = [400, 395, 430, 500, 405, 600, 445, 460, 420, 1010]
    ex1 = [
        W("14:00", {"requests": 950, "errors": 9, "latencies_ms": lat_b}, {"requests": 50, "errors": 1, "latencies_ms": lat_c[:5]}),
        W("14:05", {"requests": 900, "errors": 9, "latencies_ms": lat_b}, {"requests": 300, "errors": 4, "latencies_ms": lat_c}),
        W("14:10", {"requests": 880, "errors": 8, "latencies_ms": lat_b}, {"requests": 310, "errors": 3, "latencies_ms": lat_c}),
        W("14:15", {"requests": 905, "errors": 10, "latencies_ms": lat_b}, {"requests": 295, "errors": 5, "latencies_ms": lat_c}),
        W("14:20", {"requests": 900, "errors": 9, "latencies_ms": lat_b}, {"requests": 300, "errors": 90, "latencies_ms": lat_c}),
    ]
    slow = [x * 2 for x in lat_c]
    ex2 = [
        W("09:00", {"requests": 1000, "errors": 10, "latencies_ms": lat_b}, {"requests": 400, "errors": 5, "latencies_ms": slow}),
        W("09:05", {"requests": 1000, "errors": 10, "latencies_ms": lat_b}, {"requests": 400, "errors": 18, "latencies_ms": slow}),
    ]
    ex3 = [W("02:00", {"requests": 600, "errors": 2, "latencies_ms": lat_b}, {"requests": 30, "errors": 9, "latencies_ms": lat_c[:3]})]

    late = _series(rng, [((1200, 0.01, 400), (400, 0.01, 400))] * 2 + [((1200, 0.01, 400), (400, 0.045, 400))] * 4)
    blips = _series(rng, [((1200, 0.01, 400), (400, 0.01, 400)), ((1200, 0.01, 400), (400, 0.03, 400)), ((1200, 0.01, 400), (400, 0.01, 400)),
                          ((1200, 0.01, 400), (400, 0.03, 400)), ((1200, 0.01, 400), (400, 0.01, 400)), ((1200, 0.01, 400), (400, 0.01, 400)),
                          ((1200, 0.01, 400), (400, 0.01, 400))])
    tail = _series(rng, [((1500, 0.005, 300), (500, 0.005, 300, 0.05))] * 4)
    night = _series(rng, [((150, 0.0, 300), (40, 0.0, 300))] * 3 + [((800, 0.01, 300), (250, 0.01, 300))] * 3)
    tiny_err = [W("03:00", {"requests": 1000, "errors": 5, "latencies_ms": lat_b}, {"requests": 4, "errors": 1, "latencies_ms": lat_c[:4]})] + \
        _series(rng, [((1000, 0.005, 400), (300, 0.005, 400))] * 3)
    recover = _series(rng, [((1000, 0.01, 400), (300, 0.05, 400))] * 2 + [((1000, 0.01, 400), (300, 0.01, 400))] * 4)
    exact_bp = [W("10:%02d" % i, {"requests": 1000, "errors": 10, "latencies_ms": [100] * 10}, {"requests": 500, "errors": 10, "latencies_ms": [120] * 10}) for i in range(3)]
    empty_lat = [W("11:%02d" % i, {"requests": 500, "errors": 5, "latencies_ms": []}, {"requests": 500, "errors": 5, "latencies_ms": [900] if i else []}) for i in range(3)]
    gap = [W("16:00", {"requests": 900, "errors": 9, "latencies_ms": lat_b}, {"requests": 300, "errors": 3, "latencies_ms": lat_c}),
           W("16:05", {"requests": 880, "errors": 9, "latencies_ms": lat_b}, {"requests": 290, "errors": 3, "latencies_ms": lat_c}),
           W("16:10", {"requests": 150, "errors": 2, "latencies_ms": lat_b}, {"requests": 40, "errors": 0, "latencies_ms": lat_c[:4]}),
           W("16:15", {"requests": 910, "errors": 9, "latencies_ms": lat_b}, {"requests": 305, "errors": 3, "latencies_ms": lat_c}),
           W("16:20", {"requests": 900, "errors": 9, "latencies_ms": lat_b}, {"requests": 300, "errors": 3, "latencies_ms": lat_c})]
    return [
        {"name": "Example 1", "hidden": False, "args": {"windows": ex1, "policy": POLICY},
         "explanation": "14:00 has only 50 canary requests, so it extends without touching the streaks. 14:05 to 14:15 are healthy, but the third healthy window is the promote. 14:20 is never analyzed."},
        {"name": "Example 2", "hidden": False, "args": {"windows": ex2, "policy": POLICY},
         "explanation": "The canary p99 is 2020 ms against a baseline of 980 ms (100 * 2020 > 120 * 980), so 09:00 fails on latency. In 09:05 the error rate is also 4.5% vs 1% (> 100 bp), so the fail streak reaches 2 and the canary rolls back."},
        {"name": "Example 3", "hidden": False, "args": {"windows": ex3, "policy": POLICY},
         "explanation": "9 errors in 30 requests is 30% > 20%, the abort threshold. It rolls back at once, even though 30 requests is below min_requests."},
        {"name": "regression starts late", "args": {"windows": late, "policy": _pol(pass_windows=5)}},
        {"name": "isolated blips", "args": {"windows": blips, "policy": _pol(pass_windows=3, fail_windows=2)}},
        {"name": "tail latency only", "args": {"windows": tail, "policy": _pol(pass_windows=4, fail_windows=3)}},
        {"name": "overnight low traffic", "args": {"windows": night, "policy": _pol(pass_windows=2)}},
        {"name": "tiny first window", "args": {"windows": tiny_err, "policy": _pol(abort_error_bp=3000, pass_windows=3)}},
        {"name": "recovers then promotes", "args": {"windows": recover, "policy": _pol(fail_windows=3, pass_windows=3)}},
        {"name": "exactly at thresholds", "args": {"windows": exact_bp, "policy": _pol(min_requests=100, pass_windows=3)}},
        {"name": "missing latency samples", "args": {"windows": empty_lat, "policy": _pol(min_requests=100, pass_windows=3)}},
        {"name": "low-traffic gap keeps the pass streak", "args": {"windows": gap, "policy": POLICY}},
        {"name": "runs out of windows", "args": {"windows": late[:2], "policy": _pol(pass_windows=5)}},
    ]
