DEFAULT_RULES = [
    {"severity": "page", "long": 60, "short": 5, "factor": 14.4},
    {"severity": "ticket", "long": 360, "short": 30, "factor": 6.0},
]
KEYS = ("minute", "severity", "event", "long_burn", "short_burn")


def run(ns, slo, segments, rules=None):
    """Expand the traffic trace, feed it minute by minute, and grade every event plus the final state.

    segments: [[minutes, requests_per_minute, errors_per_minute], ...] played back in order.
    """
    rules = rules or DEFAULT_RULES
    alerter = ns["BurnRateAlerter"](slo, [dict(r) for r in rules])
    events, minute = [], 0
    for count, req, err in segments:
        for _ in range(count):
            got = alerter.observe(minute, req, err)
            for e in got or []:
                events.append({k: e[k] for k in KEYS})
            minute += 1
    intervals, opened = [], {}
    for e in events:
        if e["event"] == "open":
            opened[e["severity"]] = len(intervals)
            intervals.append({"severity": e["severity"], "opened": e["minute"], "closed": None})
        elif e["severity"] in opened:
            intervals[opened.pop(e["severity"])]["closed"] = e["minute"]
    return {"events": events, "intervals": intervals, "active": list(alerter.active() or []), "minutes": minute}
