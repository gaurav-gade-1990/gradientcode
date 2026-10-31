ACME = [{"id": "u_10%d" % i, "tenant": "acme", "attrs": {"role": "agent-builder" if i % 3 else "admin", "region": "us"}} for i in range(1, 9)]
GLOBEX = [{"id": "u_10%d" % i, "tenant": "globex", "attrs": {"role": "analyst", "region": "eu"}} for i in range(1, 9)]


def _users(n, tenant, seed):
    out = []
    for i in range(n):
        attrs = {"role": ["admin", "analyst", "agent-builder", "support"][(i * 7 + seed) % 4]}
        if i % 5:
            attrs["region"] = ["us", "eu", "apac"][(i + seed) % 3]
        out.append({"id": "u_%04d" % (i * 37 + seed), "tenant": tenant, "attrs": attrs})
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"flags": [{"key": "agent-autopilot", "killed": False, "rollout_bp": 3000}],
                  "users": [{"id": "u_101", "tenant": "acme", "attrs": {}},
                            {"id": "u_102", "tenant": "acme", "attrs": {}},
                            {"id": "u_101", "tenant": "globex", "attrs": {}}]},
         "explanation": "A 30% rollout. stable_hash('agent-autopilot:acme:u_101') % 10000 = 2090 < 3000, so acme's u_101 is on. "
                        "acme's u_102 lands in bucket 9165 and is off. globex's u_101 is a different person and lands in 6825, so it is off too."},
        {"name": "Example 2", "hidden": False,
         "args": {"flags": [{"key": "ticket-summaries-v2", "killed": False, "tenants": ["acme"], "allow": ["u_102"],
                             "rules": [{"id": "admins", "attr": "role", "op": "eq", "value": "admin", "serve": True},
                                       {"id": "no-eu", "attr": "region", "op": "eq", "value": "eu", "serve": False}],
                             "rollout_bp": 0}],
                  "users": [{"id": "u_102", "tenant": "acme", "attrs": {"role": "analyst"}},
                            {"id": "u_103", "tenant": "acme", "attrs": {"role": "admin", "region": "eu"}},
                            {"id": "u_104", "tenant": "acme", "attrs": {"role": "analyst", "region": "eu"}},
                            {"id": "u_105", "tenant": "globex", "attrs": {"role": "admin"}}]},
         "explanation": "u_102 is allowlisted. u_103 matches the first rule (admins) before 'no-eu'. u_104 matches only 'no-eu' and is served off. "
                        "globex is not in the flag's tenants, so u_105 is off even though it is an admin. Every row still reports its bucket."},
        {"name": "Example 3", "hidden": False,
         "args": {"flags": [{"key": "agent-autopilot", "killed": True, "allow": ["u_101"], "rollout_bp": 10000}],
                  "users": [{"id": "u_101", "tenant": "acme", "attrs": {}}, {"id": "u_105", "tenant": "acme", "attrs": {}}]},
         "explanation": "The kill switch beats everything, including the allowlist and a 100% rollout."},
        {"name": "bucket exactly at threshold", "args": {"flags": [{"key": "agent-autopilot", "rollout_bp": 2090}, {"key": "agent-autopilot", "rollout_bp": 2091}], "users": ACME[:1]}},
        {"name": "bucket 0 at rollout 0", "args": {"flags": [{"key": "agent-autopilot", "rollout_bp": 0}, {"key": "agent-autopilot", "rollout_bp": 1}], "users": [{"id": "u_21036", "tenant": "acme", "attrs": {}}]}},
        {"name": "rollout 0 and 100", "args": {"flags": [{"key": "agent-autopilot", "rollout_bp": 0}, {"key": "agent-autopilot", "rollout_bp": 10000}], "users": ACME + GLOBEX}},
        {"name": "ramp is monotonic", "args": {"flags": [{"key": "ticket-summaries-v2", "rollout_bp": bp} for bp in (500, 1000, 2500, 5000, 9000)], "users": ACME + GLOBEX}},
        {"name": "two flags pick different users", "args": {"flags": [{"key": "agent-autopilot", "rollout_bp": 3000}, {"key": "ticket-summaries-v2", "rollout_bp": 3000}], "users": ACME}},
        {"name": "kill switch over allowlist and rules", "args": {"flags": [{"key": "pii-auto-redact", "killed": True, "allow": ["u_101", "u_102"],
                                                                              "rules": [{"id": "all-admins", "attr": "role", "op": "in", "value": ["admin", "agent-builder"], "serve": True}],
                                                                              "rollout_bp": 10000}], "users": ACME[:4]}},
        {"name": "tenant gate before allowlist", "args": {"flags": [{"key": "voice-coworker", "tenants": ["acme"], "allow": ["u_101", "u_103"], "rollout_bp": 10000}], "users": ACME[:3] + GLOBEX[:3]}},
        {"name": "rule order and missing attrs", "args": {"flags": [{"key": "eu-data-residency", "rules": [
            {"id": "eu-off", "attr": "region", "op": "eq", "value": "eu", "serve": False},
            {"id": "staff", "attr": "role", "op": "in", "value": ["admin", "support"], "serve": True},
            {"id": "apac-on", "attr": "region", "op": "in", "value": ["apac"], "serve": True}], "rollout_bp": 4000}], "users": _users(30, "acme", 3)}},
        {"name": "many users two tenants", "args": {"flags": [{"key": "agent-autopilot", "tenants": ["acme", "globex"], "allow": ["u_0075"], "rollout_bp": 1234},
                                                              {"key": "workflow-builder", "rollout_bp": 7777}], "users": _users(40, "acme", 1) + _users(40, "globex", 1)}},
    ]
