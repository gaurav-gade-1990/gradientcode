CFG = {"window_s": 10.0, "failure_rate": 0.5, "min_calls": 4, "open_timeout_s": 5.0, "half_open_probes": 2}


def call(cid, t, ok, latency=0.5):
    return {"id": cid, "t": t, "latency": latency, "ok": ok}


def trace(n, seed):
    # A deterministic flaky provider: an outage between t=20 and t=45.
    out, x = [], seed
    for i in range(n):
        x = (x * 1103515245 + 12345) % (2 ** 31)
        t = i * 0.75
        bad = 20 <= t < 45
        ok = (x % 10) >= (8 if bad else 1)
        out.append(call("req-%03d" % i, t, ok, 0.25 + (x % 7) * 0.25))
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"calls": [call("c1", 0, True), call("c2", 1, False), call("c3", 2, False), call("c4", 3, False),
                            call("c5", 4, True), call("c6", 8, True)], "config": CFG},
         "explanation": "At t=2.5 the window has 2 failures out of 3, but min_calls is 4, so the breaker stays closed. At t=3.5 it holds 3 of 4 and trips. c5 and c6 are rejected without touching the provider because the open timeout runs until 3.5 + 5 = 8.5."},
        {"name": "Example 2", "hidden": False,
         "args": {"calls": [call("c1", 0, False), call("c2", 0, False), call("c3", 0, False), call("c4", 0, False),
                            call("p1", 6, True, 1.0), call("p2", 6.25, True, 1.0), call("p3", 6.5, True), call("c8", 8, True)], "config": CFG},
         "explanation": "Four failures trip the breaker at t=0.5. At t=6 the timeout has passed, so the first allow() moves to half_open and issues probe 1. p2 gets the second probe, and p3 is rejected because both probes are out. When both probes succeed (t=7, t=7.25) the breaker closes and c8 goes through normally."},
        {"name": "Example 3", "hidden": False,
         "args": {"calls": [call("slow", 0, True, 9.0), call("c2", 0, False), call("c3", 0, False), call("c4", 0, False), call("c5", 0, False),
                            call("p1", 7, False), call("c7", 8, True)], "config": CFG},
         "explanation": "slow is admitted while closed but finishes at t=9, after the breaker has tripped (t=0.5), gone half_open (t=7) and reopened when probe p1 failed (t=7.5). Its success belongs to an old generation and is ignored, so the breaker stays open and c7 is rejected."},
        {"name": "stale success must not close a half-open breaker",
         "args": {"calls": [call("slow", 0, True, 6.5), call("c2", 0, False), call("c3", 0, False), call("c4", 0, False), call("c5", 0, False),
                            call("p1", 6, True, 3.0), call("p2", 6, True, 3.0), call("c8", 7, True), call("c9", 9.5, True)], "config": CFG}},
        {"name": "stale failure must not reopen",
         "args": {"calls": [call("c1", 0, False), call("c2", 0, False), call("c3", 0, False), call("slowfail", 0, False, 6.0), call("c5", 0, False),
                            call("p1", 5.5, True, 2.0), call("p2", 5.75, True, 2.0), call("c8", 8, True)], "config": CFG}},
        {"name": "probe limit under concurrency",
         "args": {"calls": [call("c%d" % i, 0, False) for i in range(4)] +
                  [call("h%d" % i, 6 + 0.1 * i, True, 2.0) for i in range(5)] + [call("after", 9, True)],
                  "config": dict(CFG, half_open_probes=3)}},
        {"name": "rolling window forgets old failures",
         "args": {"calls": [call("a", 0, False), call("b", 4, False), call("c", 8, True), call("d", 12, False), call("e", 16, True),
                            call("f", 20, False), call("g", 24, True), call("h", 28, False), call("i", 29, True)], "config": CFG}},
        {"name": "window boundary is exclusive",
         "args": {"calls": [call("a", 0, False, 0), call("b", 1, False, 0), call("c", 2, True, 0), call("d", 10, False, 0), call("e", 11, False, 0)],
                  "config": CFG}},
        {"name": "below min_calls never trips",
         "args": {"calls": [call("a", 0, False), call("b", 0.25, False), call("c", 0.5, False), call("d", 30, True)], "config": CFG}},
        {"name": "open timeout boundary is inclusive",
         "args": {"calls": [call("a", 0, False, 1.0), call("b", 0, False, 1.0), call("c", 0, False, 1.0), call("d", 0, False, 1.0),
                            call("e", 5.75, True, 0.25), call("f", 6, True, 0.25), call("g", 6.25, True, 0.25)], "config": CFG}},
        {"name": "min_calls 1 and failure_rate 1",
         "args": {"calls": [call("a", 0, True), call("b", 1, False), call("c", 2, True), call("d", 3, True), call("e", 3.5, True)],
                  "config": {"window_s": 2.0, "failure_rate": 1.0, "min_calls": 1, "open_timeout_s": 1.0, "half_open_probes": 1}}},
        {"name": "reopen then recover twice",
         "args": {"calls": [call("x%d" % i, 0, False) for i in range(4)] + [call("p1", 5.5, False), call("p2", 6.5, True),
                            call("p3", 11, True), call("p4", 11.25, True), call("ok1", 12, True)] +
                           [call("y%d" % i, 13, False) for i in range(4)] + [call("p5", 18.5, True), call("p6", 18.5, True)],
                  "config": CFG}},
        {"name": "outage trace", "args": {"calls": trace(90, 125), "config": CFG}},
    ]
