def N(id, tool, deps, duration, fail=None):
    n = {"id": id, "tool": tool, "deps": deps, "duration": duration}
    if fail:
        n["fail"] = fail
    return n


# An account review for a refund request.
REVIEW = [
    N("customer", "crm.get_customer", [], 1.0),
    N("order", "orders.get", [], 1.5),
    N("payments", "billing.list_payments", ["order"], 2.0),
    N("fraud", "risk.score", ["customer", "payments"], 0.7),
    N("reply", "llm.draft_reply", ["fraud", "order"], 1.2),
]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"nodes": REVIEW, "max_concurrency": 2},
         "explanation": "customer and order start at t=0. payments starts when order finishes (1.5), fraud when payments finishes (3.5), reply at 4.2. Makespan 5.4."},
        {"name": "Example 2", "hidden": False, "args": {"nodes": [
            N("crm", "crm.get_customer", [], 2.0), N("kb", "kb.search", [], 1.0), N("orders", "orders.list", [], 1.5),
            N("reply", "llm.draft_reply", ["crm", "kb", "orders"], 1.0)], "max_concurrency": 2},
         "explanation": "Only two slots. crm and kb start at t=0 (id order). kb finishes at 1.0 and orders takes its slot, finishing at 2.5. reply waits for all three."},
        {"name": "Example 3", "hidden": False, "args": {"nodes": [
            N("order", "orders.get", [], 1.0), N("shipping", "shipping.track", ["order"], 2.0, fail="carrier API 503"),
            N("eta_note", "llm.write_eta", ["shipping"], 1.0), N("loyalty", "crm.loyalty_tier", [], 1.5),
            N("offer", "promo.pick_offer", ["loyalty"], 0.5)], "max_concurrency": 3},
         "explanation": "shipping fails at 3.0, so eta_note is cancelled and never starts. The loyalty and offer branch is independent and completes."},
        {"name": "unbounded slots", "args": {"nodes": REVIEW, "max_concurrency": 6}},
        {"name": "serial", "args": {"nodes": REVIEW, "max_concurrency": 1}},
        {"name": "input order is not id order", "args": {"nodes": [
            N("zendesk", "zendesk.get_ticket", [], 1.0), N("stripe", "stripe.get_charge", [], 2.0),
            N("hubspot", "hubspot.get_contact", [], 3.0), N("audit", "audit.write", [], 0.5)], "max_concurrency": 2}},
        {"name": "failure cancels transitive descendants only", "args": {"nodes": [
            N("a_fetch", "docs.fetch", [], 1.0, fail="403 from SharePoint"),
            N("b_parse", "docs.parse", ["a_fetch"], 1.0), N("c_embed", "embed.batch", ["b_parse"], 1.0),
            N("d_index", "index.upsert", ["c_embed", "e_meta"], 1.0), N("e_meta", "meta.fetch", [], 2.5),
            N("f_notify", "slack.post", ["e_meta"], 0.5)], "max_concurrency": 2}},
        {"name": "level barrier is slower", "args": {"nodes": [
            N("a", "search.web", [], 4.0), N("b", "search.kb", [], 1.0), N("c", "llm.summarize_kb", ["b"], 3.5),
            N("d", "llm.summarize_web", ["a"], 1.0), N("e", "llm.merge", ["c", "d"], 0.5)], "max_concurrency": 3}},
        {"name": "freed slot goes to lowest ready id", "args": {"nodes": [
            N("p1", "orders.get", [], 3.0), N("p2", "orders.get", [], 1.0), N("p3", "orders.get", [], 2.5),
            N("q9", "llm.classify", ["p2"], 0.25), N("q1", "llm.classify", ["p2"], 1.75)], "max_concurrency": 2}},
        {"name": "fail in the middle with siblings", "args": {"nodes": [
            N("root", "tickets.get", [], 1.0), N("geo", "ip.lookup", ["root"], 0.5, fail="timeout"),
            N("hist", "tickets.history", ["root"], 2.0), N("sum", "llm.summarize", ["hist"], 1.0),
            N("risk", "risk.score", ["geo", "hist"], 1.0), N("route", "router.pick_queue", ["sum"], 0.25)], "max_concurrency": 2}},
        {"name": "wide fan-out", "args": {"nodes": [N("src", "s3.list", [], 0.5)] + [
            N("doc%02d" % i, "llm.extract", ["src"], 1.0 + 0.1 * i) for i in range(1, 9)] + [
            N("merge", "llm.merge", ["doc%02d" % i for i in range(1, 9)], 1.0)], "max_concurrency": 3}},
        {"name": "single node failing", "args": {"nodes": [N("only", "github.create_issue", [], 1.0, fail="422")], "max_concurrency": 1}},
    ]
