# Illustrative prices in USD per million tokens. Quality is an offline eval score.
MODELS = [
    {"name": "edge-8b", "quality": 0.62, "p95_ms": 450, "context_window": 8192, "input_per_mtok": 0.10, "output_per_mtok": 0.10},
    {"name": "fast-small", "quality": 0.74, "p95_ms": 900, "context_window": 200000, "input_per_mtok": 0.80, "output_per_mtok": 4.00},
    {"name": "reasoning-mini", "quality": 0.82, "p95_ms": 2900, "context_window": 200000, "input_per_mtok": 0.50, "output_per_mtok": 6.00},
    {"name": "oss-70b", "quality": 0.80, "p95_ms": 2600, "context_window": 128000, "input_per_mtok": 0.90, "output_per_mtok": 0.90},
    {"name": "balanced-mid", "quality": 0.86, "p95_ms": 1800, "context_window": 200000, "input_per_mtok": 3.00, "output_per_mtok": 15.00},
    {"name": "frontier-large", "quality": 0.93, "p95_ms": 4500, "context_window": 200000, "input_per_mtok": 15.00, "output_per_mtok": 75.00},
]
TIERS = {
    "free": {"min_quality": 0.60, "max_p95_ms": 1000, "max_attempts": 2},
    "pro": {"min_quality": 0.75, "max_p95_ms": 3000, "max_attempts": 3},
    "enterprise": {"min_quality": 0.85, "max_p95_ms": 5000, "max_attempts": 3},
}


def req(rid, tier, inp, max_out, actual):
    return {"id": rid, "tier": tier, "input_tokens": inp, "max_output_tokens": max_out, "actual_output_tokens": actual}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"requests": [req("faq-1", "free", 600, 300, 120), req("summ-7", "pro", 2000, 1000, 640), req("legal-3", "enterprise", 12000, 2000, 1500)],
                  "models": MODELS, "tiers": TIERS, "outcomes": {}},
         "explanation": "free can use edge-8b and fast-small, and edge-8b is cheapest. For pro, oss-70b costs (2000*0.9 + 1000*0.9)/1e6 = $0.0027, which beats reasoning-mini's $0.007 even though reasoning-mini has the lower input price. enterprise needs quality >= 0.85, so balanced-mid. Each call is billed on the output tokens it really used."},
        {"name": "Example 2", "hidden": False,
         "args": {"requests": [req("summ-8", "pro", 2000, 1000, 700)], "models": MODELS, "tiers": TIERS,
                  "outcomes": {"summ-8": {"oss-70b": "server", "reasoning-mini": "timeout"}}},
         "explanation": "The ranked pro list is oss-70b, reasoning-mini, balanced-mid. The first two fail with retryable errors, so the router falls back to balanced-mid on the third and last attempt. The failed attempts cost nothing."},
        {"name": "Example 3", "hidden": False,
         "args": {"requests": [req("t-1", "pro", 3000, 500, 400), req("t-2", "pro", 3000, 500, 410), req("t-3", "free", 400, 200, 90)],
                  "models": MODELS, "tiers": TIERS, "outcomes": {"t-1": {"oss-70b": "rate_limit"}, "t-3": {"edge-8b": "bad_request"}}},
         "explanation": "oss-70b returns 429 for t-1, so t-1 falls back to reasoning-mini and oss-70b is skipped for the rest of the batch: t-2 never calls it. t-3 gets a 400, which no other model would fix, so the router stops without a fallback."},
        {"name": "fallback stays inside the tier",
         "args": {"requests": [req("p-1", "pro", 1000, 500, 300), req("e-1", "enterprise", 1000, 500, 300)], "models": MODELS, "tiers": TIERS,
                  "outcomes": {"p-1": {"oss-70b": "server"}, "e-1": {"balanced-mid": "server"}}}},
        {"name": "context window filters",
         "args": {"requests": [req("big-1", "pro", 150000, 4000, 2000), req("big-2", "free", 9000, 500, 200), req("big-3", "pro", 127000, 1000, 800),
                               req("huge", "enterprise", 199000, 2000, 10)],
                  "models": MODELS, "tiers": TIERS, "outcomes": {}}},
        {"name": "exhausted after max_attempts",
         "args": {"requests": [req("x-1", "free", 500, 200, 100), req("x-2", "free", 500, 200, 100)], "models": MODELS, "tiers": TIERS,
                  "outcomes": {"x-1": {"edge-8b": "timeout", "fast-small": "server"}}}},
        {"name": "no eligible model",
         "args": {"requests": [req("n-1", "strict", 100, 100, 10), req("n-2", "free", 100, 100, 50)], "models": MODELS,
                  "tiers": dict(TIERS, strict={"min_quality": 0.99, "max_p95_ms": 10000, "max_attempts": 3}), "outcomes": {}}},
        {"name": "bad request after a fallback",
         "args": {"requests": [req("b-1", "pro", 2000, 1000, 10), req("b-2", "pro", 2000, 1000, 600)], "models": MODELS, "tiers": TIERS,
                  "outcomes": {"b-1": {"oss-70b": "server", "reasoning-mini": "bad_request"}}}},
        {"name": "two rate limits shrink the pool",
         "args": {"requests": [req("r-1", "pro", 2000, 1000, 500), req("r-2", "pro", 2000, 1000, 500), req("r-3", "pro", 2000, 1000, 500),
                               req("r-4", "enterprise", 2000, 1000, 500)],
                  "models": MODELS, "tiers": TIERS,
                  "outcomes": {"r-1": {"oss-70b": "rate_limit", "reasoning-mini": "rate_limit"}, "r-4": {"balanced-mid": "server"}}}},
        {"name": "ties by quality then name",
         "args": {"requests": [req("tie-1", "any", 1000, 1000, 1000), req("tie-2", "any", 1000, 1000, 1000)],
                  "models": [{"name": "zeta", "quality": 0.8, "p95_ms": 100, "context_window": 9000, "input_per_mtok": 1.0, "output_per_mtok": 1.0},
                             {"name": "alpha", "quality": 0.8, "p95_ms": 100, "context_window": 9000, "input_per_mtok": 1.5, "output_per_mtok": 0.5},
                             {"name": "mid", "quality": 0.9, "p95_ms": 100, "context_window": 9000, "input_per_mtok": 0.5, "output_per_mtok": 1.5}],
                  "tiers": {"any": {"min_quality": 0.5, "max_p95_ms": 1000, "max_attempts": 3}},
                  "outcomes": {"tie-2": {"mid": "server", "alpha": "server"}}}},
        {"name": "mixed batch",
         "args": {"requests": [req("m-%d" % i, ["free", "pro", "enterprise"][i % 3], 500 + 700 * i, 256 + 128 * (i % 4), 100 + 37 * i) for i in range(12)],
                  "models": MODELS, "tiers": TIERS,
                  "outcomes": {"m-1": {"oss-70b": "timeout"}, "m-4": {"oss-70b": "server", "reasoning-mini": "server"},
                               "m-5": {"balanced-mid": "rate_limit"}, "m-6": {"edge-8b": "server"}, "m-9": {"fast-small": "bad_request"},
                               "m-10": {"reasoning-mini": "rate_limit"}}}},
    ]
