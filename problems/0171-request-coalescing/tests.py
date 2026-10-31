SYS = {"role": "system", "content": "You are the ops assistant for the incident dashboard."}
Q_INCIDENTS = "Summarize today's incidents."
Q_DEPLOYS = "List deploys since 09:00."


def req(rid, at, tenant, prompt, model="claude-sonnet", temperature=0.0, flip=False):
    user = {"content": prompt, "role": "user"} if flip else {"role": "user", "content": prompt}
    return {"request_id": rid, "at": at, "tenant": tenant, "model": model,
            "messages": [SYS, user], "temperature": temperature}


def ok(latency, content):
    return {"latency": latency, "content": content}


def err(latency, kind):
    return {"latency": latency, "error": kind}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"requests": [req("r1", 0.0, "acme", Q_INCIDENTS), req("r2", 0.5, "acme", Q_INCIDENTS),
                               req("r3", 1.0, "acme", Q_INCIDENTS)],
                  "upstream_script": [ok(2.0, "2 incidents: checkout latency, SSO outage.")]},
         "explanation": "r1 opens a flight at t=0 and the provider takes 2 s. r2 and r3 arrive while it is in flight and "
                        "wait for it. One upstream call is made, and all three finish at t=2 with resp_0."},
        {"name": "Example 2", "hidden": False,
         "args": {"requests": [req("r1", 0.0, "acme", Q_INCIDENTS), req("r2", 0.2, "globex", Q_INCIDENTS)],
                  "upstream_script": [ok(1.0, "acme: 2 incidents."), ok(1.0, "globex: none today.")]},
         "explanation": "Same prompt, different tenants. They must not share a response, so there are two upstream "
                        "calls, and each tenant gets its own."},
        {"name": "Example 3", "hidden": False,
         "args": {"requests": [req("r1", 0.0, "acme", Q_INCIDENTS), req("r2", 0.5, "acme", Q_INCIDENTS),
                               req("r3", 3.0, "acme", Q_INCIDENTS)],
                  "upstream_script": [err(1.5, "server"), ok(1.0, "2 incidents.")]},
         "explanation": "The shared call fails at t=1.5, so r1 and r2 both get ServerError. The flight is closed, so r3 at "
                        "t=3 makes a fresh call and succeeds at t=4. The error is not cached."},
        {"name": "no stale reuse after success",
         "args": {"requests": [req("r1", 0.0, "acme", Q_INCIDENTS), req("r2", 1.0, "acme", Q_INCIDENTS),
                               req("r3", 2.5, "acme", Q_INCIDENTS), req("r4", 2.6, "acme", Q_INCIDENTS)],
                  "upstream_script": [ok(2.0, "v1: 2 incidents."), ok(2.0, "v2: 3 incidents.")]}},
        {"name": "sampled requests bypass",
         "args": {"requests": [req("r1", 0.0, "acme", "Write a tagline.", temperature=0.0),
                               req("r2", 0.1, "acme", "Write a tagline.", temperature=0.9),
                               req("r3", 0.2, "acme", "Write a tagline.", temperature=0.9),
                               req("r4", 0.3, "acme", "Write a tagline.", temperature=0.0)],
                  "upstream_script": [ok(1.0, "Ship faster."), ok(0.5, "Build boldly."), ok(0.5, "Code calmly.")]}},
        {"name": "model is part of the key",
         "args": {"requests": [req("r1", 0.0, "acme", Q_DEPLOYS, model="claude-haiku"),
                               req("r2", 0.1, "acme", Q_DEPLOYS, model="claude-sonnet"),
                               req("r3", 0.2, "acme", Q_DEPLOYS, model="claude-haiku")],
                  "upstream_script": [ok(1.0, "haiku: 4 deploys"), ok(1.2, "sonnet: 4 deploys")]}},
        {"name": "dict key order does not matter",
         "args": {"requests": [req("r1", 0.0, "acme", Q_DEPLOYS), req("r2", 0.3, "acme", Q_DEPLOYS, flip=True)],
                  "upstream_script": [ok(1.0, "4 deploys.")]}},
        {"name": "timeout shared then retry window",
         "args": {"requests": [req("r1", 0.0, "initech", Q_DEPLOYS), req("r2", 4.0, "initech", Q_DEPLOYS),
                               req("r3", 5.5, "initech", Q_DEPLOYS), req("r4", 6.0, "initech", Q_DEPLOYS),
                               req("r5", 7.5, "initech", Q_DEPLOYS)],
                  "upstream_script": [err(5.0, "timeout"), err(1.0, "rate_limit"), ok(1.0, "4 deploys.")]}},
        {"name": "interleaved keys and tenants",
         "args": {"requests": [req("a1", 0.0, "acme", Q_INCIDENTS), req("g1", 0.0, "globex", Q_INCIDENTS),
                               req("a2", 0.0, "acme", Q_DEPLOYS), req("a3", 0.4, "acme", Q_INCIDENTS),
                               req("g2", 0.7, "globex", Q_INCIDENTS), req("a4", 1.1, "acme", Q_DEPLOYS),
                               req("g3", 2.2, "globex", Q_INCIDENTS), req("a5", 2.9, "acme", Q_INCIDENTS)],
                  "upstream_script": [ok(1.5, "acme incidents"), ok(2.0, "globex incidents"), ok(1.0, "acme deploys"),
                                      ok(1.0, "acme deploys v2"), ok(1.0, "globex incidents v2"),
                                      ok(1.0, "acme incidents v2")]}},
        {"name": "thundering herd",
         "args": {"requests": [req("r%02d" % i, round(0.07 * i, 2), ["acme", "globex"][i % 2], Q_INCIDENTS) for i in range(40)],
                  "upstream_script": [ok(1.0, "acme wave 1"), ok(1.0, "globex wave 1"), ok(1.0, "acme wave 2"),
                                      ok(1.0, "globex wave 2"), ok(1.0, "acme wave 3"), ok(1.0, "globex wave 3")]}},
        {"name": "sampled request does not join an open flight",
         "args": {"requests": [req("r1", 0.0, "acme", Q_INCIDENTS), req("r2", 0.5, "acme", Q_INCIDENTS, temperature=0.7)],
                  "upstream_script": [ok(3.0, "deterministic"), ok(0.5, "sampled")]}},
        {"name": "failure on one key leaves others alone",
         "args": {"requests": [req("r1", 0.0, "acme", Q_INCIDENTS), req("r2", 0.1, "acme", Q_DEPLOYS),
                               req("r3", 0.2, "acme", Q_INCIDENTS), req("r4", 0.3, "acme", Q_DEPLOYS),
                               req("r5", 2.0, "acme", Q_INCIDENTS)],
                  "upstream_script": [err(1.0, "server"), ok(1.5, "4 deploys."), ok(1.0, "2 incidents.")]}},
    ]
