# Illustrative pricing for a mid-size model: $3 / $15 per million tokens, a 1.25x write premium,
# reads at 0.1x, a 5-minute TTL refreshed on every read, and a 1,024-token minimum prefix.
P = {"input_per_mtok": 3.0, "output_per_mtok": 15.0, "cache_write_mult": 1.25, "cache_read_mult": 0.1, "ttl_s": 300, "min_cacheable_tokens": 1024}


def call(cid, t, prefix_id, prefix, inp, out):
    return {"id": cid, "t": t, "prefix_id": prefix_id, "prefix_tokens": prefix, "input_tokens": inp, "output_tokens": out}


def session(n, gap, start=0, pid="agent-v12"):
    return [call("turn-%d" % i, start + i * gap, pid, 6000, 120 + 15 * i, 250) for i in range(n)]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"calls": [call("t1", 0, "support-v7", 6000, 200, 300), call("t2", 40, "support-v7", 6000, 180, 250), call("t3", 90, "support-v7", 6000, 220, 400)], "pricing": P},
         "explanation": "The first call writes the 6,000-token prefix at 1.25 x $3 = $3.75 per million. The next two calls fall inside the 5-minute TTL and read it at $0.30 per million. One write plus two reads already beat paying full price three times."},
        {"name": "Example 2", "hidden": False,
         "args": {"calls": [call("a", 0, "support-v7", 6000, 200, 300), call("b", 280, "support-v7", 6000, 200, 300), call("c", 560, "support-v7", 6000, 200, 300),
                            call("d", 900, "support-v7", 6000, 200, 300)], "pricing": P},
         "explanation": "Reads refresh the TTL. b at 280 s hits and moves the expiry to 580, so c at 560 s also hits. d comes 340 s after c, the cache has expired, and it pays the write premium again."},
        {"name": "Example 3", "hidden": False,
         "args": {"calls": [call("short", 0, "classifier", 800, 50, 5), call("short2", 10, "classifier", 800, 50, 5), call("once", 20, "batch-job-17", 4000, 100, 200)], "pricing": P},
         "explanation": "An 800-token prefix is under the 1,024-token minimum, so it is billed as plain input every time. The batch prompt is written once and never read, so caching costs 25% more on that prefix: savings is negative."},
        {"name": "expiry boundary is a miss", "args": {"calls": [call("a", 0, "p", 2048, 10, 10), call("b", 300, "p", 2048, 10, 10), call("c", 599.5, "p", 2048, 10, 10)], "pricing": P}},
        {"name": "uncacheable does not refresh",
         "args": {"calls": [call("a", 0, "p", 2000, 0, 0), call("b", 200, "p", 1000, 0, 0), call("c", 350, "p", 2000, 0, 0)], "pricing": P}},
        {"name": "interleaved prefixes", "args": {"calls": [call("a1", 0, "tenant-a", 3000, 100, 100), call("b1", 10, "tenant-b", 5000, 100, 100),
                                                             call("a2", 200, "tenant-a", 3000, 100, 100), call("b2", 320, "tenant-b", 5000, 100, 100),
                                                             call("b3", 330, "tenant-b", 5000, 100, 100), call("a3", 499, "tenant-a", 3000, 100, 100)], "pricing": P}},
        {"name": "exactly at the minimum is cacheable", "args": {"calls": [call("a", 0, "p", 1024, 0, 0), call("b", 1, "p", 1024, 0, 0), call("c", 2, "p", 1023, 0, 0)], "pricing": P}},
        {"name": "empty", "args": {"calls": [], "pricing": P}},
        {"name": "long agent session", "args": {"calls": session(40, 45) + session(5, 400, start=2000, pid="agent-v13"), "pricing": P}},
        {"name": "1-hour ttl, 2x write",
         "args": {"calls": session(6, 1000), "pricing": dict(P, cache_write_mult=2.0, ttl_s=3600)}},
    ]
