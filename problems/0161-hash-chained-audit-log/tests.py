REFUND = {"actor": "agent:billing-bot", "action": "refund.issue", "tenant": "acme", "target": "order_1182", "amount": 42.5}
READ = {"actor": "agent:support-coworker", "action": "customer.read", "tenant": "acme", "target": "cust_77", "fields": ["email", "plan"]}
ROLE = {"actor": "user:dana@acme.com", "action": "role.grant", "tenant": "acme", "target": "agent:billing-bot", "role": "refunds:write"}


def _events(n):
    actions = ["ticket.update", "customer.read", "refund.issue", "role.grant", "export.run"]
    out = []
    for i in range(n):
        e = {"tenant": ["acme", "globex", "initech"][i % 3], "actor": "agent:coworker-%d" % (i % 7), "action": actions[i % 5],
             "target": "obj_%04d" % (i * 13 % 1000), "ok": i % 11 != 0}
        if i % 4 == 0:
            e["amount"] = round(i * 1.25, 2)
        if i % 6 == 0:
            e["meta"] = {"ip": "10.0.%d.%d" % (i % 255, i * 7 % 255), "reason": None}
        out.append(e)
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"events": [REFUND, READ, ROLE]},
         "explanation": "Each entry hashes the previous hash plus the canonical JSON of its event, so the chain is intact and both verifications return -1."},
        {"name": "Example 2", "hidden": False, "args": {"events": [REFUND, READ, ROLE], "tamper": [{"op": "edit", "index": 0, "field": "amount", "value": 4250.0}]},
         "explanation": "Someone changes the refund amount in row 0. Its stored hash no longer matches the recomputed one, so check 3 fails at index 0."},
        {"name": "Example 3", "hidden": False, "args": {"events": [REFUND, READ, ROLE],
                                                        "tamper": [{"op": "edit", "index": 0, "field": "amount", "value": 4250.0}, {"op": "rehash", "index": 0}]},
         "explanation": "The attacker also recomputes row 0's hash. Row 0 now passes, but row 1's prev_hash still points at the old hash, so check 2 fails at index 1."},
        {"name": "empty log", "args": {"events": []}},
        {"name": "empty log truncation of nothing", "args": {"events": [], "tamper": [{"op": "truncate", "keep": 0}]}},
        {"name": "key order does not matter",
         "args": {"events": [{"tenant": "acme", "action": "export.run", "actor": "agent:etl", "target": "warehouse"},
                             {"target": "warehouse", "actor": "agent:etl", "action": "export.run", "tenant": "acme"},
                             {"z": 1, "a": {"y": 2, "b": [3, {"d": 4, "c": 5}]}}]}},
        {"name": "non-ascii names", "args": {"events": [{"actor": "user:zoë@acme.com", "action": "customer.read", "target": "cust_Ã©", "note": "Müller GmbH 東京"}, READ]}},
        {"name": "delete and renumber", "args": {"events": _events(8), "tamper": [{"op": "delete", "index": 3}, {"op": "renumber"}]}},
        {"name": "delete without renumber", "args": {"events": _events(8), "tamper": [{"op": "delete", "index": 5}]}},
        {"name": "rewrite whole tail, anchored", "args": {"events": _events(10), "tamper": [{"op": "edit", "index": 6, "field": "action", "value": "export.cancel"}, {"op": "rewrite_from", "index": 6}]}},
        {"name": "rewrite whole tail, no anchor", "args": {"events": _events(10), "anchor": False,
                                                           "tamper": [{"op": "edit", "index": 6, "field": "action", "value": "export.cancel"}, {"op": "rewrite_from", "index": 6}]}},
        {"name": "truncate tail", "args": {"events": _events(12), "tamper": [{"op": "truncate", "keep": 9}]}},
        {"name": "swap two rows", "args": {"events": _events(6), "tamper": [{"op": "swap", "i": 2, "j": 4}]}},
        {"name": "forged seq", "args": {"events": _events(6), "tamper": [{"op": "set", "index": 4, "field": "seq", "value": 7}]}},
        {"name": "caller reuses its dict", "args": {"events": [dict(REFUND), dict(READ), dict(ROLE)],
                                                    "mutate_input": [{"index": 1, "field": "fields", "value": ["ssn"]}]}},
        {"name": "long log, edit late", "args": {"events": _events(150), "tamper": [{"op": "edit", "index": 141, "field": "action", "value": "customer.delete"}]}},
    ]
