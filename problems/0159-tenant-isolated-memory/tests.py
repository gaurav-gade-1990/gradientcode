def C(tenant, user, agent, team=None):
    return {"tenant": tenant, "user": user, "agent": agent, "team": team}


DANA = C("acme", "u_1", "assistant", "support")
DANA_HR = C("acme", "u_1", "hr-agent", "support")
LEE = C("acme", "u_2", "assistant", "support")
SAM = C("acme", "u_3", "assistant", "finance")
G_U1 = C("globex", "u_1", "assistant", "support")
G_U9 = C("globex", "u_9", "assistant", None)


def W(ctx, key, value, scope="private", sources=()):
    return {"op": "write", "ctx": ctx, "key": key, "value": value, "scope": scope, "sources": list(sources)}


def RD(ctx, key):
    return {"op": "read", "ctx": ctx, "key": key}


def V(ctx):
    return {"op": "visible", "ctx": ctx}


def D(tenant, user):
    return {"op": "delete_user", "tenant": tenant, "user": user}


def _bulk():
    ctxs = [DANA, DANA_HR, LEE, SAM, G_U1, G_U9, C("globex", "u_2", "assistant", "support")]
    ops = []
    scopes = ["private", "team", "org"]
    for i in range(90):
        ctx = ctxs[(i * 5) % len(ctxs)]
        scope = scopes[(i * 7) % 3]
        if scope == "team" and ctx["team"] is None:
            scope = "org"
        src = ["mem_%d" % (i // 2)] if i % 4 == 3 and i > 2 else []
        ops.append(W(ctx, "fact_%d" % (i % 13), {"n": i, "by": ctx["user"]}, scope, src))
        if i % 9 == 0:
            ops.append(RD(ctxs[i % len(ctxs)], "fact_%d" % (i % 13)))
    ops += [V(c) for c in ctxs]
    ops += [D("acme", "u_2"), D("globex", "u_1")]
    ops += [V(c) for c in ctxs]
    ops += [RD(c, "fact_%d" % k) for c in ctxs for k in (0, 4, 7)]
    return ops


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"ops": [
            W(DANA, "summary_cadence", "weekly"),
            W(LEE, "refund_policy", "30 days, receipts required", "team"),
            W(G_U1, "refund_policy", "globex: no refunds after 14 days", "team"),
            RD(LEE, "summary_cadence"), RD(DANA, "refund_policy"), RD(G_U1, "refund_policy"), V(DANA)]},
         "explanation": "Lee can't read Dana's private memory. Dana and Lee share acme's support team. globex also has a support team and its own u_1, "
                        "but tenants never mix, so each side sees only its own refund policy."},
        {"name": "Example 2", "hidden": False, "args": {"ops": [
            W(DANA, "tone", "concise"), W(LEE, "tone", "friendly", "team"), W(SAM, "tone", "formal", "org"),
            RD(DANA, "tone"), RD(LEE, "tone"), RD(SAM, "tone"), W(DANA, "tone", "bullet points"), RD(DANA, "tone"), V(LEE)]},
         "explanation": "Dana's own private memory beats the team and org ones. Lee's team memory beats the org one. "
                        "Sam isn't on the support team and gets the org value. Rewriting Dana's 'tone' keeps the id mem_1."},
        {"name": "Example 3", "hidden": False, "args": {"ops": [
            W(DANA, "allergy", "peanuts"),
            W(DANA, "lunch_order_notes", "no peanuts for the offsite", "org", ["mem_1"]),
            W(SAM, "offsite_menu", "nut-free menu booked", "org", ["mem_2"]),
            W(SAM, "budget", "$40 per head", "org"),
            D("acme", "u_1"), V(SAM)]},
         "explanation": "Erasing u_1 removes mem_1 and mem_2 (Dana's own), then mem_3 because it was derived from mem_2. Sam's unrelated budget memory stays."},
        {"name": "same user, different agent", "args": {"ops": [
            W(DANA_HR, "salary_band", "L5"), RD(DANA, "salary_band"), RD(DANA_HR, "salary_band"), V(DANA), V(DANA_HR)]}},
        {"name": "team and user ids collide across tenants", "args": {"ops": [
            W(DANA, "escalation", "page #acme-oncall", "team"), W(G_U1, "escalation", "email globex-ops", "team"),
            W(DANA, "vip_list", ["cust_77"]), RD(G_U1, "vip_list"), RD(G_U1, "escalation"), RD(LEE, "escalation"),
            V(G_U1), V(LEE), V(G_U9)]}},
        {"name": "erasure is scoped to the tenant", "args": {"ops": [
            W(DANA, "a", 1, "org"), W(G_U1, "a", 2, "org"), W(G_U1, "b", 3), D("acme", "u_1"), V(G_U1), RD(G_U1, "a"), RD(LEE, "a")]}},
        {"name": "multi-level cascade", "args": {"ops": [
            W(LEE, "note", "customer churned", "team"), W(DANA, "digest", "1 churn this week", "org", ["mem_1"]),
            W(SAM, "forecast", "churn up 2%", "org", ["mem_2"]), W(SAM, "board_deck", "see forecast", "org", ["mem_3"]),
            W(SAM, "unrelated", "q3 hiring", "org"), D("acme", "u_2"), V(SAM), RD(SAM, "board_deck"), D("acme", "u_2")]}},
        {"name": "sources must be visible", "args": {"ops": [
            W(G_U1, "secret", "globex merger"), W(DANA, "leak", "derived", "org", ["mem_1"]), W(DANA, "bad", "x", "org", ["mem_99"]),
            W(LEE, "lee_private", "x"), W(DANA, "also_bad", "y", "org", ["mem_2"]), W(DANA, "ok", "z", "org"), V(DANA)]}},
        {"name": "invalid scopes", "args": {"ops": [
            W(G_U9, "x", 1, "team"), W(DANA, "x", 1, "public"), W(G_U9, "x", 1, "org"), V(G_U9), RD(G_U9, "x")]}},
        {"name": "overwrite changes scope and sources", "args": {"ops": [
            W(DANA, "plan", "draft", "org"), W(LEE, "input", "data", "team"), W(DANA, "plan", "final", "private", ["mem_2"]),
            RD(SAM, "plan"), RD(DANA, "plan"), D("acme", "u_2"), V(DANA), W(DANA, "plan", "again", "org"), V(SAM)]}},
        {"name": "most recent write wins a scope tie", "args": {"ops": [
            W(LEE, "policy", "v1", "org"), W(SAM, "policy", "v2", "org"), RD(DANA, "policy"), W(LEE, "policy", "v3", "org"), RD(DANA, "policy"),
            W(DANA, "policy", "team-v", "team"), RD(SAM, "policy"), RD(LEE, "policy")]}},
        {"name": "busy store", "args": {"ops": _bulk()}},
    ]
