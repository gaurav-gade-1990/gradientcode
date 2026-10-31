# Illustrative prices per million tokens.
PROVIDERS = [
    {"name": "primary", "input_per_mtok": 3.0, "output_per_mtok": 15.0},
    {"name": "secondary", "input_per_mtok": 2.5, "output_per_mtok": 10.0},
    {"name": "selfhosted", "input_per_mtok": 0.9, "output_per_mtok": 0.9},
]
REQ = {"input_tokens": 2000}


def s(latency, outcome="ok", out=400):
    return {"latency": latency, "outcome": outcome, "output_tokens": out}


def prov(**open_until):
    return [dict(p, open_until=open_until.get(p["name"], 0)) for p in PROVIDERS]


def case(script, providers=None, hedge=1.0, deadline=8.0):
    return {"providers": providers or prov(), "script": script, "request": REQ, "hedge_delay": hedge, "deadline": deadline}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": case({"primary": s(0.75), "secondary": s(0.5), "selfhosted": s(0.5)}),
         "explanation": "The primary answers at 0.75 s, before the 1 s hedge delay, so nothing else is sent. Cost: (2000 x $3 + 400 x $15) / 1e6 = $0.012."},
        {"name": "Example 2", "hidden": False,
         "args": case({"primary": s(3.0), "secondary": s(1.0, out=380), "selfhosted": s(0.5)}),
         "explanation": "The primary is slow. At t=1 it has been in flight for the hedge delay, so the gateway hedges to secondary, which answers at t=2. The primary is cancelled at t=2 and bills only its 2,000 input tokens ($0.006). The secondary bills $0.0088. The user waited 2 s instead of 3 s."},
        {"name": "Example 3", "hidden": False,
         "args": case({"primary": s(0.5), "secondary": s(0.25, "rate_limit"), "selfhosted": s(1.25, out=420)}, providers=prov(primary=60)),
         "explanation": "The primary's circuit is open, so it is skipped without a request. secondary returns a 429 at t=0.25, and with nothing else in flight the gateway fails over at once to selfhosted, which answers at t=1.5."},
        {"name": "hedge timer runs from the attempt in flight",
         "args": case({"primary": s(0.5, "server"), "secondary": s(3.0), "selfhosted": s(0.5)})},
        {"name": "fail over immediately on error",
         "args": case({"primary": s(0.25, "server"), "secondary": s(0.5), "selfhosted": s(0.5)})},
        {"name": "deadline cancels everything",
         "args": case({"primary": s(10.0), "secondary": s(10.0), "selfhosted": s(10.0)}, deadline=4.0)},
        {"name": "response exactly at the deadline counts",
         "args": case({"primary": s(10.0), "secondary": s(3.0), "selfhosted": s(1.0)}, deadline=4.0)},
        {"name": "primary fails after the hedge went out",
         "args": case({"primary": s(1.5, "timeout"), "secondary": s(4.0), "selfhosted": s(1.0)})},
        {"name": "everything fails",
         "args": case({"primary": s(0.5, "server"), "secondary": s(0.25, "timeout"), "selfhosted": s(0.5, "server")})},
        {"name": "every circuit open",
         "args": case({"primary": s(1.0), "secondary": s(1.0), "selfhosted": s(1.0)}, providers=prov(primary=30, secondary=30, selfhosted=30))},
        {"name": "circuit closes before the hedge",
         "args": case({"primary": s(2.5), "secondary": s(0.5), "selfhosted": s(0.5)}, providers=prov(secondary=0.5))},
        {"name": "circuit still open at hedge time",
         "args": case({"primary": s(2.5), "secondary": s(0.5), "selfhosted": s(0.75)}, providers=prov(secondary=2.0))},
        {"name": "simultaneous finish, error first",
         "args": case({"primary": s(2.0, "server"), "secondary": s(1.0), "selfhosted": s(0.5)})},
        {"name": "simultaneous finish, both ok",
         "args": case({"primary": s(2.0, out=100), "secondary": s(1.0, out=900), "selfhosted": s(0.5)})},
        {"name": "single provider times out",
         "args": {"providers": PROVIDERS[:1], "script": {"primary": s(5.0)}, "request": REQ, "hedge_delay": 1.0, "deadline": 2.5}},
        {"name": "short hedge delay chains three providers",
         "args": case({"primary": s(4.0), "secondary": s(0.25, "server"), "selfhosted": s(2.0)}, hedge=0.5)},
    ]
