SHORT_RULES = [{"severity": "page", "long": 6, "short": 2, "factor": 10.0}]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"slo": 0.999, "segments": [[90, 2000, 1], [12, 2000, 400], [30, 2000, 1]]},
         "explanation": "Checkout serves 2,000 requests a minute at a 0.05% error rate (burn 0.5). A bad deploy fails 20% of requests in minutes 90-101 (burn 200). "
                        "The ticket opens first, at minute 92: only 93 minutes have been observed, so its 360-minute window is partial and already burns 6.94. "
                        "The page needs its 60-minute window above 14.4, which takes until minute 94 (17.125). After the rollback the 5-minute window is clean "
                        "at minute 106 and the page closes, though the 60-minute window still burns 40.4. The 30-minute window keeps the ticket open until minute 131."},
        {"name": "Example 2", "hidden": False,
         "args": {"slo": 0.999, "segments": [[100, 1500, 1], [300, 1500, 15]]},
         "explanation": "A slow leak: 1% errors is burn 10. That never reaches the page factor of 14.4, but the ticket opens at minute 233, once the "
                        "360-minute window (still partial, 234 minutes) burns 6.01. The ticket is open when the trace ends, so its interval has closed = None."},
        {"name": "Example 3", "hidden": False,
         "args": {"slo": 0.99, "rules": SHORT_RULES, "segments": [[4, 100, 0], [3, 100, 28], [3, 100, 0]]},
         "explanation": "One rule with 6- and 2-minute windows and a 1% budget; minutes 4-6 fail 28 of 100 requests. Minute 4: the 2-minute window burns "
                        "28/200/0.01 = 14 but the 6-minute window only 28/500/0.01 = 5.6. Minute 5: 9.33 and 28, still no page. Minute 6: 84/600 = 14 and 28, so the "
                        "page opens. Minute 7 the 2-minute window (minutes 6-7) is still 14. Minute 8 it is 0, so the page closes while the long window still says 14."},
        {"name": "night traffic is not averaged per minute",
         "args": {"slo": 0.999, "segments": [[60, 3000, 2], [30, 20, 10], [60, 3000, 2]]}},
        {"name": "two incidents reopen the page",
         "args": {"slo": 0.999, "segments": [[70, 2000, 1], [10, 2000, 600], [40, 2000, 1], [10, 2000, 600], [20, 2000, 1]]}},
        {"name": "zero-traffic minutes at start",
         "args": {"slo": 0.999, "segments": [[20, 0, 0], [8, 400, 120], [20, 400, 0], [40, 0, 0]]}},
        {"name": "flapping short window",
         "args": {"slo": 0.99, "rules": SHORT_RULES,
                  "segments": [[3, 200, 1], [2, 200, 80], [1, 200, 0], [2, 200, 80], [2, 200, 0], [1, 200, 90], [4, 200, 0]]}},
        {"name": "custom rules and slo 99.5%",
         "args": {"slo": 0.995, "rules": [{"severity": "fast", "long": 30, "short": 3, "factor": 10.0},
                                          {"severity": "slow", "long": 120, "short": 15, "factor": 3.0}],
                  "segments": [[40, 800, 2], [25, 800, 50], [10, 800, 300], [60, 800, 2]]}},
        {"name": "sustained outage ends open",
         "args": {"slo": 0.999, "segments": [[30, 5000, 2], [80, 5000, 2500]]}},
        {"name": "healthy day no events",
         "args": {"slo": 0.999, "segments": [[300, 2500, 1], [100, 2500, 2]]}},
        {"name": "ticket from a long moderate burn",
         "args": {"slo": 0.999, "segments": [[60, 1000, 0], [400, 1000, 7], [100, 1000, 0]]}},
    ]
