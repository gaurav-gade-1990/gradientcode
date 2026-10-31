SLACK = {"interval": 1.0, "max_attempts": 3, "retry_delay": 2.0}
EMAIL = {"interval": 0.5, "max_attempts": 2, "retry_delay": 1.0}
HOOK = {"interval": 0.25, "max_attempts": 4, "retry_delay": 0.5}
LAT = {"slack": 0.25, "email": 0.5, "webhook": 0.125}


def subs(spec):
    return [{"id": i, "channel": c} for i, c in spec]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"subscribers": subs([("ana@acme", "slack"), ("ben@acme", "slack"), ("ops@acme", "email")]),
                  "channels": {"slack": SLACK, "email": EMAIL}, "latency": LAT, "outcomes": {}},
         "explanation": "Slack allows one send per second, so ben starts at t=1.0 and finishes at 1.25. Email runs in "
                        "parallel on its own worker and delivers ops@acme at 0.5."},
        {"name": "Example 2", "hidden": False,
         "args": {"subscribers": subs([("ana@acme", "slack"), ("ben@acme", "slack"), ("cho@acme", "slack")]),
                  "channels": {"slack": SLACK}, "latency": LAT, "outcomes": {"ana@acme": ["fail"]}},
         "explanation": "ana's first send fails at 0.25, so she is re-queued ready at 0.25 + 2.0 = 2.25. ben and cho go "
                        "at 1.0 and 2.0, then ana's retry starts at max(2.25, 2.0 + 1.0) = 3.0."},
        {"name": "Example 3", "hidden": False,
         "args": {"subscribers": subs([("hook-billing", "webhook"), ("hook-crm", "webhook")]),
                  "channels": {"webhook": HOOK}, "latency": LAT,
                  "outcomes": {"hook-billing": ["reject"], "hook-crm": ["fail", "fail", "fail", "fail"]}},
         "explanation": "A 400 is permanent: hook-billing is rejected after one attempt. hook-crm fails all 4 attempts "
                        "with backoffs 0.5, 1.0 and 2.0, and is exhausted."},
        {"name": "single subscriber", "args": {"subscribers": subs([("ana@acme", "email")]), "channels": {"email": EMAIL}, "latency": LAT, "outcomes": {}}},
        {"name": "retry interleaves with queue", "args": {
            "subscribers": subs([("u%02d" % i, "webhook") for i in range(8)]), "channels": {"webhook": HOOK}, "latency": LAT,
            "outcomes": {"u00": ["fail", "fail"], "u03": ["fail"], "u05": ["reject"]}}},
        {"name": "three channels with failures", "args": {
            "subscribers": subs([("ana", "slack"), ("ops", "email"), ("h1", "webhook"), ("ben", "slack"), ("fin", "email"),
                                 ("h2", "webhook"), ("cho", "slack"), ("h3", "webhook"), ("legal", "email")]),
            "channels": {"slack": SLACK, "email": EMAIL, "webhook": HOOK}, "latency": LAT,
            "outcomes": {"ana": ["fail", "fail", "fail"], "ops": ["fail"], "h2": ["fail", "fail"], "legal": ["reject"], "fin": ["fail", "fail"]}}},
        {"name": "zero interval", "args": {
            "subscribers": subs([("a", "webhook"), ("b", "webhook"), ("c", "webhook")]),
            "channels": {"webhook": {"interval": 0.0, "max_attempts": 2, "retry_delay": 0.0}}, "latency": LAT,
            "outcomes": {"a": ["fail"], "b": ["fail", "fail"]}}},
        {"name": "slow channel, interval shorter than latency", "args": {
            "subscribers": subs([("x1", "email"), ("x2", "email"), ("x3", "email")]),
            "channels": {"email": {"interval": 0.25, "max_attempts": 3, "retry_delay": 0.25}}, "latency": {"email": 1.0},
            "outcomes": {"x1": ["fail"]}}},
        {"name": "two channels, both retrying", "args": {
            "subscribers": subs([("s1", "slack"), ("s2", "slack"), ("w1", "webhook"), ("w2", "webhook")]),
            "channels": {"slack": SLACK, "webhook": HOOK}, "latency": LAT,
            "outcomes": {"s1": ["fail"], "w1": ["fail", "fail", "fail"], "w2": ["fail"]}}},
        {"name": "many subscribers", "args": {
            "subscribers": subs([("user-%02d" % i, ["slack", "email", "webhook"][i % 3]) for i in range(30)]),
            "channels": {"slack": SLACK, "email": EMAIL, "webhook": HOOK}, "latency": LAT,
            "outcomes": {"user-%02d" % i: (["fail"] * (i % 4)) + (["reject"] if i % 7 == 0 else []) for i in range(30)}}},
    ]
