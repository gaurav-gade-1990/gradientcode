import numpy as np

TENANTS = ["acme-health", "globex-bank", "initech", "umbrella-retail"]
MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5", "gpt-4o-mini"]

STANDARD = [
    {"column": "request_id", "check": "not_null"},
    {"column": "request_id", "check": "unique"},
    {"column": "request_id", "check": "regex", "pattern": r"req_[0-9a-f]{8}"},
    {"column": "tenant_id", "check": "foreign_key", "ref": "tenants"},
    {"column": "model", "check": "in_set", "values": MODELS},
    {"column": "prompt_tokens", "check": "type", "type": "int"},
    {"column": "prompt_tokens", "check": "range", "min": 1, "max": 200000},
    {"column": "latency_ms", "check": "range", "min": 0},
    {"column": "cost_usd", "check": "type", "type": "float"},
    {"column": "created_at", "check": "regex", "pattern": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"},
    {"column": "cached", "check": "type", "type": "bool"},
    {"column": "status", "check": "in_set", "values": ["ok", "error", "timeout"], "mostly": 0.95},
]


def _batch(rng, n, start):
    rows = []
    for i in range(n):
        cached = bool(rng.random() < 0.3)
        rows.append({
            "request_id": "req_%08x" % (start + 7919 * i),
            "tenant_id": TENANTS[int(rng.integers(len(TENANTS)))],
            "model": MODELS[int(rng.integers(len(MODELS)))],
            "prompt_tokens": int(rng.integers(20, 6000)),
            "latency_ms": round(float(rng.gamma(3.0, 150.0)), 1),
            "cost_usd": None if cached else round(float(rng.random() * 0.02), 6),
            "created_at": "2026-10-30T%02d:%02d:%02dZ" % (int(rng.integers(24)), int(rng.integers(60)), int(rng.integers(60))),
            "cached": cached,
            "status": ["ok", "ok", "ok", "ok", "ok", "ok", "ok", "error", "timeout"][int(rng.integers(9))],
        })
    return rows


def cases():
    rng = np.random.default_rng(137)
    refs = {"tenants": TENANTS}
    clean = _batch(rng, 120, 0x1a2b0000)

    dirty = _batch(rng, 150, 0x3c4d0000)
    dirty[4]["request_id"] = dirty[90]["request_id"]          # a retried request logged twice
    dirty[11]["created_at"] = "2026-10-30T14:02:11Z (retry)"  # trailing junk
    dirty[17]["prompt_tokens"] = True                          # a client SDK bug
    dirty[23]["tenant_id"] = "hooli"                           # unknown tenant
    dirty[31]["latency_ms"] = -12.5                            # clock skew
    dirty[40]["model"] = "gpt-4o-mini-2024"                    # unpinned alias
    dirty[52]["prompt_tokens"] = "512"                         # stringly typed
    del dirty[60]["status"]
    dirty[61]["status"] = "cancelled"
    dirty[77]["request_id"] = None
    dirty[88]["cost_usd"] = "0.004"

    status_drift = _batch(rng, 60, 0x5e6f0000)
    for i in (3, 9):
        status_drift[i]["status"] = "rate_limited"
    status_drift4 = [dict(r) for r in status_drift]
    for i in (15, 21):
        status_drift4[i]["status"] = "rate_limited"

    return [
        {"name": "Example 1", "hidden": False,
         "args": {"records": [
             {"request_id": "req_00a1f3c2", "tenant_id": "acme-health", "prompt_tokens": 812, "status": "ok"},
             {"request_id": "req_00a1f3c3", "tenant_id": "globex-bank", "prompt_tokens": None, "status": "ok"},
             {"request_id": "req_00a1f3c2", "tenant_id": "hooli", "prompt_tokens": 95, "status": "error"},
             {"request_id": "req_00a1f3c5", "tenant_id": "initech", "prompt_tokens": 0, "status": "ok"}],
             "expectations": [
                 {"column": "request_id", "check": "unique"},
                 {"column": "tenant_id", "check": "foreign_key", "ref": "tenants"},
                 {"column": "prompt_tokens", "check": "range", "min": 1}],
             "refs": {"tenants": TENANTS}},
         "explanation": "req_00a1f3c2 appears twice, so both rows 0 and 2 fail unique. hooli is not a known tenant. prompt_tokens is null in row 1, which range skips (3 evaluated), and 0 in row 3 is below min. failed_rows = [0, 2, 3]."},
        {"name": "Example 2", "hidden": False,
         "args": {"records": [
             {"request_id": "req_1b", "created_at": "2026-10-30T09:15:00Z", "cached": True, "cost_usd": None},
             {"request_id": "req_1c", "created_at": "2026-10-30 09:15:04", "cached": "false", "cost_usd": 0.0031},
             {"request_id": "req_1d", "created_at": "2026-10-30T09:15:07Z", "cached": False, "cost_usd": 1}],
             "expectations": [
                 {"column": "created_at", "check": "regex", "pattern": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"},
                 {"column": "cached", "check": "type", "type": "bool"},
                 {"column": "cost_usd", "check": "type", "type": "float"},
                 {"column": "cost_usd", "check": "not_null", "mostly": 0.5}]},
         "explanation": "Row 1 uses a space instead of T, and its cached flag is the string 'false', not a bool. cost_usd is null on the cache hit: the type check skips it, and the int 1 counts as a float. not_null fails 1 of 3 rows, but 2/3 >= mostly = 0.5, so it passes and row 0 is still listed in failed_rows."},
        {"name": "clean hourly batch", "args": {"records": clean, "expectations": STANDARD, "refs": refs}},
        {"name": "dirty batch with incidents", "args": {"records": dirty, "expectations": STANDARD, "refs": refs}},
        {"name": "dirty batch, sample of 5", "args": {"records": dirty, "expectations": STANDARD, "refs": refs, "sample_size": 5}},
        {"name": "mostly holds at 2 of 60", "args": {"records": status_drift, "expectations": STANDARD, "refs": refs}},
        {"name": "mostly breaks at 4 of 60", "args": {"records": status_drift4, "expectations": STANDARD, "refs": refs}},
        {"name": "empty batch", "args": {"records": [], "expectations": STANDARD, "refs": refs}},
        {"name": "column missing everywhere",
         "args": {"records": [{"trace_id": "t-%d" % i} for i in range(4)],
                  "expectations": [{"column": "user_id", "check": "regex", "pattern": "u_.*"},
                                   {"column": "user_id", "check": "not_null"}],
                  "id_column": "trace_id"}},
        {"name": "bools are not ints",
         "args": {"records": [{"request_id": "r%d" % i, "retries": v} for i, v in enumerate([0, 1, True, 2, False, 3.0])],
                  "expectations": [{"column": "retries", "check": "type", "type": "int"},
                                   {"column": "retries", "check": "range", "min": 0, "max": 5},
                                   {"column": "retries", "check": "unique"}]}},
        {"name": "unique by type and value",
         "args": {"records": [{"request_id": "r1", "k": "7"}, {"request_id": "r2", "k": 7}, {"request_id": "r3", "k": "7"},
                              {"request_id": "r4", "k": None}, {"request_id": "r5", "k": None}],
                  "expectations": [{"column": "k", "check": "unique"}]}},
    ]
