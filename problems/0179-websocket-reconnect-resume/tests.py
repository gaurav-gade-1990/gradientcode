REPLY = ["Your ", "order ", "#1182 ", "shipped ", "on ", "Tuesday ", "and ", "arrives ", "Friday", "."]
J = [0.5, 0.25, 0.9, 0.1, 0.6, 0.3, 0.8, 0.45, 0.7, 0.2, 0.55, 0.35, 0.65, 0.15]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"texts": REPLY[:5], "plans": [{"send": 3}, {"overlap": 2}], "jitter": J},
         "explanation": "The socket drops after events 1-3. The client sleeps 0.5 * min(8, 0.5) = 0.25 s and reconnects "
                        "with connect(3). The server replays from 2, so events 2 and 3 are skipped as duplicates; 4, 5 are "
                        "rendered and event 6 is done."},
        {"name": "Example 2", "hidden": False,
         "args": {"texts": REPLY[:3], "plans": [{"refuse": True}, {"refuse": True}, {}], "jitter": J},
         "explanation": "Two refused connects: sleeps 0.5 * 0.5 = 0.25 and 0.25 * 1.0 = 0.25. Nothing was delivered yet, so "
                        "every attempt is connect(0)."},
        {"name": "Example 3", "hidden": False,
         "args": {"texts": REPLY[:6], "plans": [{"send": 2}, {"skip": 2}], "jitter": J},
         "explanation": "After reconnecting with connect(2), the server's buffer lost events 3 and 4 and sends 5 first. "
                        "The client calls backfill(2, 5), renders 3 and 4, then 5 and 6."},
        {"name": "clean stream", "args": {"texts": REPLY, "plans": [], "jitter": J}},
        {"name": "give up", "args": {"texts": REPLY[:4], "plans": [{"send": 1}] + [{"refuse": True}] * 6, "jitter": J, "max_failures": 4}},
        {"name": "progress resets backoff", "args": {"texts": REPLY, "plans": [{"send": 2}, {"send": 2}, {"send": 2}, {"send": 2}, {}], "jitter": J, "max_failures": 3}},
        {"name": "duplicates are not progress", "args": {"texts": REPLY[:6], "plans": [{"send": 3}, {"overlap": 3, "send": 2}, {"overlap": 1, "send": 1}, {}], "jitter": J, "max_failures": 3}},
        {"name": "gap right before done", "args": {"texts": REPLY[:4], "plans": [{"send": 1}, {"skip": 3}], "jitter": J}},
        {"name": "gap then drop then overlap", "args": {"texts": REPLY, "plans": [{"send": 3}, {"refuse": True}, {"skip": 2, "send": 2}, {"overlap": 4, "send": 6}, {}], "jitter": J}},
        {"name": "drop before first event", "args": {"texts": REPLY[:3], "plans": [{"send": 0}, {"send": 0}, {}], "jitter": J}},
        {"name": "cap reached", "args": {"texts": REPLY[:2], "plans": [{"refuse": True}] * 6 + [{}], "jitter": [0.99] * 8, "max_failures": 8, "base": 1.0, "cap": 4.0}},
        {"name": "max_failures one", "args": {"texts": REPLY[:3], "plans": [{"send": 1}], "jitter": J, "max_failures": 1}},
    ]
