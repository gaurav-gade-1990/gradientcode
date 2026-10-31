import numpy as np

QS = [0.0, 0.5, 0.9, 0.95, 0.99, 0.999, 1.0]


def _lat(rng, n, median, sigma, tail=0.0, tail_ms=0.0):
    x = rng.lognormal(np.log(median), sigma, n)
    if tail:
        x = x + rng.choice([0.0, tail_ms], n, p=[1 - tail, tail]) * rng.random(n)
    return [round(float(v), 2) for v in x]


def cases():
    rng = np.random.default_rng(138)
    a, b, c = _lat(rng, 400, 320, 0.35), _lat(rng, 400, 330, 0.35), _lat(rng, 400, 340, 0.4, tail=0.04, tail_ms=8000)
    fleet = {"us-east-1a": {}, "us-east-1b": {}, "us-east-1c": {}, "fleet": {}}
    fleet_ops = [
        {"op": "record", "h": "us-east-1a", "values": a},
        {"op": "record", "h": "us-east-1b", "values": b},
        {"op": "record", "h": "us-east-1c", "values": c},
        {"op": "quantile", "h": "us-east-1c", "qs": QS},
        {"op": "merge", "into": "fleet", "from": "us-east-1a"},
        {"op": "merge", "into": "fleet", "from": "us-east-1b"},
        {"op": "merge", "into": "fleet", "from": "us-east-1c"},
        {"op": "quantile", "h": "fleet", "qs": QS},
        {"op": "snapshot", "h": "fleet"},
    ]
    wide = [round(float(v), 3) for v in np.exp(rng.uniform(np.log(0.5), np.log(120000), 600))]
    cache_mix = [0.0] * 30 + _lat(rng, 70, 45, 0.3) + [-3.2, -0.4, 0.0]
    scrape1, scrape2 = _lat(rng, 150, 250, 0.3), _lat(rng, 150, 900, 0.3)
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"hists": {"api": {"alpha": 0.1}},
                  "ops": [{"op": "record", "h": "api", "values": [100, 120, 250, 900, 1800]},
                          {"op": "snapshot", "h": "api"},
                          {"op": "quantile", "h": "api", "qs": [0.5, 1.0]}]},
         "explanation": "With alpha = 0.1, gamma = 1.1 / 0.9 = 1.2222. 100 ms lands in bucket ceil(ln 100 / ln 1.2222) = ceil(22.95) = 23, and 250 ms in bucket 28. For p50, rank = 0.5 * (5 - 1) = 2, so the answer is the third value's bucket, 28, whose representative 2 * 1.2222^28 / 2.2222 = 248.0 ms is within 10% of 250. p100 is the 1800 ms bucket, reported as 1844.8."},
        {"name": "Example 2", "hidden": False,
         "args": {"hists": {"replica-a": {"alpha": 0.05}, "replica-b": {"alpha": 0.05}, "fleet": {"alpha": 0.05}},
                  "ops": [{"op": "record", "h": "replica-a", "values": [0, 180, 210, 240]},
                          {"op": "record", "h": "replica-b", "values": [190, 2600, -15]},
                          {"op": "merge", "into": "fleet", "from": "replica-a"},
                          {"op": "merge", "into": "fleet", "from": "replica-b"},
                          {"op": "quantile", "h": "fleet", "qs": [0.0, 0.5, 0.99]}]},
         "explanation": "The -15 ms sample from a skewed clock is rejected. The cache hit goes to the zero bucket, so p0 = 0.0. The fleet holds 6 values, so p99 has rank 0.99 * 5 = 4.95. The cumulative count first exceeds it at the fifth value, 240 ms, whose bucket represents 233.5 ms. Neither replica changes when it is merged."},
        {"name": "three replicas, one with a tail", "args": {"hists": fleet, "ops": fleet_ops}},
        {"name": "bucket cap folds the low end",
         "args": {"hists": {"batch-api": {"alpha": 0.02, "max_buckets": 40}},
                  "ops": [{"op": "record", "h": "batch-api", "values": wide[:300]},
                          {"op": "quantile", "h": "batch-api", "qs": [0.01, 0.5, 0.99]},
                          {"op": "record", "h": "batch-api", "values": wide[300:]},
                          {"op": "snapshot", "h": "batch-api"},
                          {"op": "quantile", "h": "batch-api", "qs": QS}]}},
        {"name": "cap applied after merge",
         "args": {"hists": {"r1": {"alpha": 0.02}, "r2": {"alpha": 0.02}, "agg": {"alpha": 0.02, "max_buckets": 25}},
                  "ops": [{"op": "record", "h": "r1", "values": wide[:200]},
                          {"op": "record", "h": "r2", "values": wide[200:400]},
                          {"op": "merge", "into": "agg", "from": "r1"},
                          {"op": "snapshot", "h": "agg"},
                          {"op": "merge", "into": "agg", "from": "r2"},
                          {"op": "snapshot", "h": "agg"},
                          {"op": "quantile", "h": "agg", "qs": [0.5, 0.99]}]}},
        {"name": "cache hits and clock skew",
         "args": {"hists": {"edge-cache": {"alpha": 0.01}},
                  "ops": [{"op": "record", "h": "edge-cache", "values": cache_mix},
                          {"op": "quantile", "h": "edge-cache", "qs": [0.0, 0.25, 0.3, 0.5, 0.99]},
                          {"op": "snapshot", "h": "edge-cache"}]}},
        {"name": "collector merges then replica keeps recording",
         "args": {"hists": {"pod-7f9c": {"alpha": 0.01}, "collector": {"alpha": 0.01}},
                  "ops": [{"op": "record", "h": "pod-7f9c", "values": scrape1},
                          {"op": "merge", "into": "collector", "from": "pod-7f9c"},
                          {"op": "record", "h": "pod-7f9c", "values": scrape2},
                          {"op": "snapshot", "h": "collector"},
                          {"op": "quantile", "h": "collector", "qs": [0.5, 0.99]},
                          {"op": "record", "h": "collector", "value": 15000.0, "count": 3},
                          {"op": "snapshot", "h": "pod-7f9c"}]}},
        {"name": "validation errors",
         "args": {"hists": {"p": {"alpha": 0.01}, "q": {"alpha": 0.02}},
                  "ops": [{"op": "quantile", "h": "p", "qs": [0.5, 1.0]},
                          {"op": "record", "h": "p", "value": 410.0, "count": 0},
                          {"op": "record", "h": "p", "value": 410.0, "count": 2.5},
                          {"op": "record", "h": "p", "value": 410.0, "count": True},
                          {"op": "record", "h": "p", "value": 410.0, "count": 25},
                          {"op": "record", "h": "q", "values": [90.0, 95.0]},
                          {"op": "merge", "into": "p", "from": "q"},
                          {"op": "quantile", "h": "p", "qs": [-0.01, 0.0, 1.0, 1.01]},
                          {"op": "snapshot", "h": "p"}]}},
        {"name": "weighted records",
         "args": {"hists": {"llm-gateway": {"alpha": 0.005}},
                  "ops": [{"op": "record", "h": "llm-gateway", "value": 812.4, "count": 970},
                          {"op": "record", "h": "llm-gateway", "value": 4120.0, "count": 25},
                          {"op": "record", "h": "llm-gateway", "value": 30000.0, "count": 5},
                          {"op": "quantile", "h": "llm-gateway", "qs": [0.5, 0.97, 0.975, 0.99, 0.995, 0.996, 1.0]}]}},
        {"name": "single bucket cap",
         "args": {"hists": {"tiny": {"alpha": 0.01, "max_buckets": 1}},
                  "ops": [{"op": "record", "h": "tiny", "values": [5.0, 50.0, 500.0, 0.0]},
                          {"op": "snapshot", "h": "tiny"},
                          {"op": "quantile", "h": "tiny", "qs": [0.0, 0.3, 1.0]}]}},
    ]
