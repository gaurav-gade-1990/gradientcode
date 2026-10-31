import numpy as np

PLANS = {
    "starter": {"base_fee": 30000, "meters": {
        "agent_tasks": {"included": 300, "tiers": [{"up_to": 1000, "unit_price": 10}, {"up_to": None, "unit_price": 6}]},
        "tool_calls": {"included": 3000, "tiers": [{"up_to": None, "unit_price": 1}]}}},
    "growth": {"base_fee": 90000, "meters": {
        "agent_tasks": {"included": 1500, "tiers": [{"up_to": 2000, "unit_price": 8}, {"up_to": 10000, "unit_price": 5}, {"up_to": None, "unit_price": 3}]},
        "tool_calls": {"included": 20000, "tiers": [{"up_to": 50000, "unit_price": 1}, {"up_to": None, "unit_price": 0}]}}},
    "enterprise": {"base_fee": 250000, "meters": {
        "agent_tasks": {"included": 10000, "tiers": [{"up_to": None, "unit_price": 2}]},
        "tool_calls": {"included": 100000, "tiers": [{"up_to": None, "unit_price": 0}]}}},
}
SMALL = {"starter": PLANS["starter"]}


def _ev(i, day, meter, qty):
    return {"id": "evt_%05d" % i, "day": day, "meter": meter, "qty": qty}


def _stream(n, days, seed, dup_rate=0.1):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append(_ev(i, int(rng.integers(-1, days + 1)), ["agent_tasks", "tool_calls"][int(rng.integers(0, 2))], int(rng.integers(0, 400))))
        if rng.random() < dup_rate:
            j = int(rng.integers(0, len(out)))
            out.append(dict(out[j]))
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"plans": SMALL, "plan_changes": [{"day": 0, "plan": "starter"}], "period_days": 30,
                  "events": [_ev(1, 2, "agent_tasks", 900), _ev(2, 9, "agent_tasks", 650), _ev(3, 9, "tool_calls", 2000), _ev(2, 9, "agent_tasks", 650)]},
         "explanation": "evt_00002 is redelivered and counted once. agent_tasks: used 1550, included 300, billable 1250 = 1000 x 10 + 250 x 6 = 11500 cents. "
                        "tool_calls stay under the 3000 included. Total 30000 + 11500 + 0 = 41500."},
        {"name": "Example 2", "hidden": False,
         "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "starter"}, {"day": 10, "plan": "growth"}], "period_days": 30,
                  "events": [_ev(1, 4, "agent_tasks", 400), _ev(2, 10, "agent_tasks", 1200), _ev(3, 29, "tool_calls", 25000), _ev(4, 30, "agent_tasks", 99)]},
         "explanation": "Upgrade on day 10. Starter covers days 0-9 (10 days): base 30000*10//30 = 10000, included tasks 300*10//30 = 100, so 300 billable tasks = 3000. "
                        "Growth covers days 10-29 (20 days): base 60000, included tasks 1000 so 200 billable = 1600, included tool calls 13333 so 11667 billable = 11667. "
                        "The day-10 event belongs to growth. The day-30 event is outside the period."},
        {"name": "no usage", "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "growth"}], "period_days": 31, "events": []}},
        {"name": "exactly at quota and tier edge",
         "args": {"plans": SMALL, "plan_changes": [{"day": 0, "plan": "starter"}], "period_days": 30,
                  "events": [_ev(1, 0, "agent_tasks", 1300), _ev(2, 29, "tool_calls", 3000)]}},
        {"name": "three tiers", "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "growth"}], "period_days": 30,
                                         "events": [_ev(i, i % 30, "agent_tasks", 1000) for i in range(16)] + [_ev(100, 3, "tool_calls", 90000)]}},
        {"name": "downgrade mid month", "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "enterprise"}, {"day": 21, "plan": "starter"}], "period_days": 28,
                                                 "events": [_ev(1, 20, "agent_tasks", 9000), _ev(2, 21, "agent_tasks", 500), _ev(3, 27, "tool_calls", 4000)]}},
        {"name": "three segments, 31 days", "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "starter"}, {"day": 7, "plan": "growth"}, {"day": 19, "plan": "enterprise"}],
                                                     "period_days": 31, "events": [_ev(1, 6, "agent_tasks", 700), _ev(2, 7, "agent_tasks", 700), _ev(3, 18, "tool_calls", 30000),
                                                                                    _ev(4, 19, "agent_tasks", 12000), _ev(5, -1, "agent_tasks", 5000)]}},
        {"name": "duplicate of an out-of-period event", "args": {"plans": SMALL, "plan_changes": [{"day": 0, "plan": "starter"}], "period_days": 30,
                                                                  "events": [_ev(1, 31, "agent_tasks", 50), _ev(1, 31, "agent_tasks", 50), _ev(2, 5, "agent_tasks", 500), _ev(2, 5, "agent_tasks", 500)]}},
        {"name": "redelivery storm", "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "starter"}, {"day": 15, "plan": "growth"}], "period_days": 30,
                                              "events": _stream(400, 30, 166, 0.3)}},
        {"name": "long stream", "args": {"plans": PLANS, "plan_changes": [{"day": 0, "plan": "growth"}, {"day": 3, "plan": "enterprise"}], "period_days": 31,
                                         "events": _stream(500, 31, 1660)}},
    ]
