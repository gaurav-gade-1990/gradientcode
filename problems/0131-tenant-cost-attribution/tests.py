# Illustrative prices per million tokens. mid-model gets a price cut on 2026-10-15.
PRICES = {
    "mid-model": [{"effective": "2026-10-15", "input": 2.5, "cached_input": 0.25, "output": 12.5},
                  {"effective": "2026-09-01", "input": 3.0, "cached_input": 0.30, "output": 15.0}],
    "small-model": [{"effective": "2026-09-01", "input": 0.8, "cached_input": 0.08, "output": 4.0}],
}
SHARED = [{"name": "vector-db", "amount": 120.0}, {"name": "eval-cluster", "amount": 80.0}]


def ev(eid, date, tenant, feature, model, inp, cached, out):
    return {"id": eid, "date": date, "tenant": tenant, "feature": feature, "model": model,
            "input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out}


def month(n):
    tenants = ["acme", "globex", "initech"]
    feats = ["support-bot", "doc-search", "agent"]
    out = []
    for i in range(n):
        day = 1 + i * 30 // n
        out.append(ev("u-%04d" % i, "2026-10-%02d" % day, tenants[i % 3], feats[(i // 3) % 3], "mid-model" if i % 4 else "small-model",
                      20000 + 1500 * (i % 7), 12000 if i % 2 else 0, 800 + 90 * (i % 5)))
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"events": [ev("u-1", "2026-10-03", "acme", "support-bot", "mid-model", 1_000_000, 800_000, 100_000),
                             ev("u-2", "2026-10-03", "globex", "doc-search", "small-model", 2_000_000, 0, 50_000)],
                  "prices": PRICES, "shared_costs": SHARED, "budgets": {}},
         "explanation": "acme: 200k uncached at $3 + 800k cached at $0.30 + 100k output at $15 = 0.6 + 0.24 + 1.5 = $2.34. globex: 2M x $0.80 + 50k x $4 = $1.80. The $200 of shared cost splits 2.34 : 1.80, so acme gets $113.04 and globex $86.96."},
        {"name": "Example 2", "hidden": False,
         "args": {"events": [ev("u-1", "2026-10-14", "acme", "agent", "mid-model", 1_000_000, 0, 0),
                             ev("u-2", "2026-10-15", "acme", "agent", "mid-model", 1_000_000, 0, 0),
                             ev("u-3", "2026-08-30", "acme", "agent", "mid-model", 1_000_000, 0, 0),
                             ev("u-4", "2026-10-15", "acme", "agent", "big-model", 1_000_000, 0, 0)],
                  "prices": PRICES, "shared_costs": [], "budgets": {}},
         "explanation": "The price cut takes effect on 2026-10-15, so u-1 pays $3.00 and u-2 pays $2.50. u-3 predates the first price entry, and big-model has no prices at all, so both go to unpriced."},
        {"name": "Example 3", "hidden": False,
         "args": {"events": [ev("u-%d" % i, "2026-10-%02d" % (i + 1), "acme", "support-bot", "small-model", 1_000_000, 0, 0) for i in range(6)],
                  "prices": PRICES, "shared_costs": [], "budgets": {"acme": 3.9}},
         "explanation": "Each event costs $0.80 against a $3.90 budget. 50% ($1.95) is crossed by u-2 ($2.40), 80% ($3.12) by u-3 ($3.20) and 100% by u-4 ($4.00). Each threshold fires once, so u-5 adds no alert even though acme is over budget."},
        {"name": "one event crosses several thresholds",
         "args": {"events": [ev("big", "2026-10-02", "acme", "agent", "mid-model", 5_000_000, 0, 1_000_000), ev("next", "2026-10-03", "acme", "agent", "mid-model", 10, 0, 10)],
                  "prices": PRICES, "shared_costs": SHARED, "budgets": {"acme": 20.0, "globex": 1.0}}},
        {"name": "cached tokens are billed once",
         "args": {"events": [ev("c1", "2026-10-20", "acme", "support-bot", "mid-model", 6_000_000, 6_000_000, 0), ev("c2", "2026-10-20", "acme", "support-bot", "mid-model", 6_000_000, 2_000_000, 200_000)],
                  "prices": PRICES, "shared_costs": [], "budgets": {"acme": 30.0}}},
        {"name": "no priced events leaves shared unallocated",
         "args": {"events": [ev("x", "2026-10-01", "acme", "agent", "unknown-model", 100, 0, 100)], "prices": PRICES, "shared_costs": SHARED, "budgets": {"acme": 1.0}}},
        {"name": "price entries out of order",
         "args": {"events": [ev("a", "2026-09-30", "globex", "agent", "mid-model", 0, 0, 1_000_000), ev("b", "2026-11-02", "globex", "agent", "mid-model", 0, 0, 1_000_000)],
                  "prices": {"mid-model": [{"effective": "2026-11-01", "input": 2.0, "cached_input": 0.2, "output": 10.0}] + PRICES["mid-model"]},
                  "shared_costs": [{"name": "gpu-reservation", "amount": 500.0}], "budgets": {"globex": 29.0}}},
        {"name": "price entries oldest first",
         "args": {"events": [ev("o1", "2026-10-20", "acme", "agent", "mid-model", 1_000_000, 0, 0)],
                  "prices": {"mid-model": PRICES["mid-model"][::-1]}, "shared_costs": [], "budgets": {}}},
        {"name": "month of traffic",
         "args": {"events": month(240), "prices": PRICES, "shared_costs": SHARED, "budgets": {"acme": 15.0, "globex": 4.0}}},
    ]
