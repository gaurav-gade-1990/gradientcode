import numpy as np

SAME_TENANT = {"attr": "resource.tenant", "op": "eq", "value": {"attr": "principal.tenant"}}

RULES = [
    {"id": "tenant-guard", "effect": "deny", "principals": ["*"], "actions": ["*"], "resources": ["*"],
     "conditions": [{"attr": "resource.tenant", "op": "neq", "value": {"attr": "principal.tenant"}}]},
    {"id": "platform-admin", "effect": "allow", "principals": ["role:platform-admin"], "actions": ["*"], "resources": ["*"]},
    {"id": "support-read", "effect": "allow", "principals": ["role:support-agent"],
     "actions": ["tickets:read", "tickets:update", "customers:read"], "resources": ["*/tickets/*", "*/customers/*"], "conditions": [SAME_TENANT]},
    {"id": "refund-small", "effect": "allow", "principals": ["role:refund-agent"], "actions": ["refunds:create"], "resources": ["*/orders/*"],
     "conditions": [{"attr": "resource.amount", "op": "lte", "value": 500}, SAME_TENANT]},
    {"id": "refund-large-approved", "effect": "allow", "principals": ["role:refund-agent"], "actions": ["refunds:create"], "resources": ["*/orders/*"],
     "conditions": [{"attr": "resource.amount", "op": "gt", "value": 500}, {"attr": "context.approved_by", "op": "in", "value": ["dana@acme.com", "lee@acme.com"]}, SAME_TENANT]},
    {"id": "no-pii-export", "effect": "deny", "principals": ["agent:*"], "actions": ["customers:export"], "resources": ["*"],
     "conditions": [{"attr": "resource.contains_pii", "op": "eq", "value": True}]},
    {"id": "acme-analytics-export", "effect": "allow", "principals": ["agent:acme-analytics"], "actions": ["customers:export"], "resources": ["acme/reports/*"]},
    {"id": "billing-freeze", "effect": "deny", "principals": ["*"], "actions": ["refunds:*", "billing:*"], "resources": ["acme/*"],
     "conditions": [{"attr": "context.change_freeze", "op": "eq", "value": True}]},
    {"id": "ticket-writer", "effect": "allow", "principals": ["agent:triage-*"], "actions": ["tickets:*"], "resources": ["acme/tickets/*"],
     "conditions": [SAME_TENANT, {"attr": "context.channel", "op": "not_in", "value": ["sms"]}]},
]


def P(id, roles=None, tenant="acme", **kw):
    p = {"id": id, "tenant": tenant}
    if roles is not None:
        p["roles"] = roles
    if tenant is None:
        del p["tenant"]
    p.update(kw)
    return p


def R(principal, action, rid, context=None, **attrs):
    res = {"id": rid}
    if "tenant" not in attrs:
        res["tenant"] = rid.split("/")[0]
    elif attrs["tenant"] is None:
        attrs.pop("tenant")
    res.update(attrs)
    return {"principal": principal, "action": action, "resource": res, "context": context or {}}


SUPPORT = P("agent:support-coworker", ["support-agent"])
REFUNDER = P("agent:billing-bot", ["refund-agent"])
ANALYTICS = P("agent:acme-analytics", ["analyst"])
ADMIN = P("user:root@acme.com", ["platform-admin", "support-agent"])


def _random_requests(n, seed):
    rng = np.random.default_rng(seed)
    principals = [SUPPORT, REFUNDER, ANALYTICS, ADMIN, P("agent:triage-7", []), P("agent:support-coworker", ["support-agent"], "globex"),
                  P("agent:billing-bot", ["refund-agent"], "globex")]
    actions = ["tickets:read", "tickets:update", "tickets:delete", "customers:read", "customers:read_pii", "customers:export", "refunds:create", "billing:adjust"]
    resources = ["acme/tickets/T-%d", "globex/tickets/T-%d", "acme/customers/C-%d", "acme/orders/O-%d", "globex/orders/O-%d", "acme/reports/R-%d"]
    out = []
    for i in range(n):
        p = principals[int(rng.integers(len(principals)))]
        rid = resources[int(rng.integers(len(resources)))] % int(rng.integers(1000, 9999))
        attrs = {}
        if "orders" in rid:
            attrs["amount"] = [120, 500, 501, 2500][int(rng.integers(4))]
        if rng.random() < 0.3:
            attrs["contains_pii"] = bool(rng.random() < 0.5)
        ctx = {}
        if rng.random() < 0.3:
            ctx["approved_by"] = ["dana@acme.com", "mallory@evil.io"][int(rng.integers(2))]
        if rng.random() < 0.2:
            ctx["change_freeze"] = True
        if rng.random() < 0.3:
            ctx["channel"] = ["sms", "email", "chat"][int(rng.integers(3))]
        out.append(R(p, actions[int(rng.integers(len(actions)))], rid, ctx, **attrs))
    return out


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"rules": RULES, "requests": [R(SUPPORT, "tickets:read", "acme/tickets/T-1182")]},
         "explanation": "The support coworker reads a ticket in its own tenant. Only support-read matches (tenant-guard's neq condition is false), so it is allowed."},
        {"name": "Example 2", "hidden": False,
         "args": {"rules": RULES, "requests": [R(SUPPORT, "tickets:read", "globex/tickets/T-77"), R(REFUNDER, "refunds:create", "acme/orders/O-1182", amount=900)]},
         "explanation": "The first request crosses tenants: tenant-guard matches and its explicit deny wins. "
                        "The second is a 900 refund with no approver, so neither refund rule's conditions hold and the default is deny with no rule."},
        {"name": "Example 3", "hidden": False,
         "args": {"rules": RULES, "requests": [R(ANALYTICS, "customers:export", "acme/reports/q3-churn", contains_pii=True)]},
         "explanation": "acme-analytics-export is the more specific match (13 literal resource characters against 0), but no-pii-export also matches and an explicit deny always wins."},
        {"name": "suffix must match too", "args": {"rules": RULES, "requests": [R(SUPPORT, "customers:read_pii", "acme/customers/C-9"), R(SUPPORT, "customers:read", "acme/customers/C-9")]}},
        {"name": "missing tenants are not equal", "args": {"rules": RULES, "requests": [
            R(P("svc:nightly-sync", ["support-agent"], None), "tickets:read", "shared/tickets/T-1", tenant=None),
            R(P("svc:nightly-sync", ["support-agent"], None), "tickets:read", "acme/tickets/T-1")]}},
        {"name": "admin during a change freeze", "args": {"rules": RULES, "requests": [
            R(ADMIN, "refunds:create", "acme/orders/O-5", {"change_freeze": True}, amount=50),
            R(ADMIN, "refunds:create", "acme/orders/O-5", {}, amount=50),
            R(ADMIN, "tickets:update", "acme/tickets/T-5")]}},
        {"name": "refund boundaries and types", "args": {"rules": RULES, "requests": [
            R(REFUNDER, "refunds:create", "acme/orders/O-1", amount=500),
            R(REFUNDER, "refunds:create", "acme/orders/O-2", amount=500.5),
            R(REFUNDER, "refunds:create", "acme/orders/O-3", {"approved_by": "dana@acme.com"}, amount=501),
            R(REFUNDER, "refunds:create", "acme/orders/O-4", {"approved_by": "mallory@evil.io"}, amount=501),
            R(REFUNDER, "refunds:create", "acme/orders/O-5", amount="120"),
            R(REFUNDER, "refunds:create", "acme/orders/O-6", amount=True),
            R(REFUNDER, "refunds:create", "acme/orders/O-7")]}},
        {"name": "glob principals and not_in", "args": {"rules": RULES, "requests": [
            R(P("agent:triage-7"), "tickets:delete", "acme/tickets/T-3", {"channel": "email"}),
            R(P("agent:triage-7"), "tickets:delete", "acme/tickets/T-3", {"channel": "sms"}),
            R(P("agent:triage-7"), "tickets:delete", "acme/tickets/T-3"),
            R(P("agent:triage"), "tickets:delete", "acme/tickets/T-3", {"channel": "email"})]}},
        {"name": "specificity tie-breaks", "args": {"rules": [
            {"id": "broad", "effect": "allow", "principals": ["*"], "actions": ["kb:*"], "resources": ["acme/*"]},
            {"id": "two-patterns", "effect": "allow", "principals": ["*"], "actions": ["kb:*", "kb:search"], "resources": ["acme/*", "acme/kb/*"]},
            {"id": "same-as-broad", "effect": "allow", "principals": ["*"], "actions": ["kb:*"], "resources": ["acme/*"]},
            {"id": "conditional", "effect": "allow", "principals": ["*"], "actions": ["kb:*"], "resources": ["acme/*"], "conditions": [{"attr": "context.mfa", "op": "eq", "value": True}]},
            {"id": "deny-a", "effect": "deny", "principals": ["*"], "actions": ["kb:delete"], "resources": ["*"]},
            {"id": "deny-b", "effect": "deny", "principals": ["*"], "actions": ["kb:*"], "resources": ["acme/kb/*"]}],
            "requests": [R(P("agent:x"), "kb:search", "acme/kb/doc-1"), R(P("agent:x"), "kb:read", "acme/wiki/doc-1"),
                         R(P("agent:x"), "kb:read", "acme/wiki/doc-1", {"mfa": True}), R(P("agent:x"), "kb:delete", "acme/kb/doc-1"),
                         R(P("agent:x"), "kb:delete", "acme/wiki/doc-1")]}},
        {"name": "best pattern inside a rule", "args": {"rules": [
            {"id": "broad", "effect": "allow", "principals": ["*"], "actions": ["kb:*"], "resources": ["acme/*"]},
            {"id": "two-patterns", "effect": "allow", "principals": ["*"], "actions": ["kb:*", "kb:search"], "resources": ["acme/*", "acme/kb/*"]},
            {"id": "conditional", "effect": "allow", "principals": ["*"], "actions": ["kb:*"], "resources": ["acme/kb/*"], "conditions": [{"attr": "context.mfa", "op": "eq", "value": True}]}],
            "requests": [R(P("agent:x"), "kb:search", "acme/kb/doc-1", {"mfa": True}), R(P("agent:x"), "kb:read", "acme/kb/doc-1", {"mfa": True}),
                         R(P("agent:x"), "kb:read", "acme/kb/doc-1")]}},
        {"name": "no rules", "args": {"rules": [], "requests": [R(ADMIN, "tickets:read", "acme/tickets/T-1")]}},
        {"name": "mixed traffic", "args": {"rules": RULES, "requests": _random_requests(120, 160)}},
    ]
