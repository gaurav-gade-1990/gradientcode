CHARGE = {"customer_id": "cus_4821", "amount_cents": 12900, "currency": "usd"}
CHARGE_REORDERED = {"currency": "usd", "amount_cents": 12900, "customer_id": "cus_4821"}


def op(at, key, tool, args, **extra):
    d = {"at": at, "key": key, "tool": tool, "args": args}
    d.update(extra)
    return d


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"ttl": 3600, "ops": [
            op(0, "run_77:step_3", "charge_card", CHARGE),
            op(2.5, "run_77:step_3", "charge_card", CHARGE),
            op(4, "run_77:step_4", "send_email", {"to": "dana@northwind.io", "template": "receipt"})]},
         "explanation": "The retry at t=2.5 has the same key and the same arguments, so it replays the stored charge and the card is charged "
                        "once. tool_runs shows exactly two real side effects."},
        {"name": "Example 2", "hidden": False, "args": {"ttl": 3600, "ops": [
            op(0, "run_77:step_3", "charge_card", CHARGE),
            op(1, "run_77:step_3", "charge_card", dict(CHARGE, amount_cents=1290)),
            op(2, "run_77:step_3", "refund_charge", {"charge_id": "ch_001"})]},
         "explanation": "The same key with a different amount, or a different tool, is a conflict. Neither runs, so the agent has a bug to "
                        "surface instead of a silent double charge."},
        {"name": "Example 3", "hidden": False, "args": {"ttl": 60, "ops": [
            op(0, "k1", "charge_card", CHARGE, fail="card_declined: insufficient_funds"),
            op(5, "k1", "charge_card", CHARGE),
            op(70, "k1", "charge_card", CHARGE)]},
         "explanation": "A failure isn't stored, so the retry at t=5 really runs. At t=70 the entry is 65 s old, which is at least the "
                        "60 s TTL, so it has expired and the charge runs again."},
        {"name": "key order does not matter", "args": {"ttl": 600, "ops": [
            op(0, "idem-9", "charge_card", CHARGE), op(1, "idem-9", "charge_card", CHARGE_REORDERED),
            op(2, "idem-9", "charge_card", {"customer_id": "cus_4821", "amount_cents": 12900, "currency": "usd", "meta": {"b": 1, "a": 2}}),
            op(3, "idem-10", "create_ticket", {"meta": {"b": 1, "a": 2}, "title": "Broken mug"}),
            op(4, "idem-10", "create_ticket", {"title": "Broken mug", "meta": {"a": 2, "b": 1}})]}},
        {"name": "exact ttl boundary", "args": {"ttl": 30, "ops": [
            op(0, "k", "send_sms", {"to": "+15125550101", "body": "Your order shipped"}),
            op(29.999, "k", "send_sms", {"to": "+15125550101", "body": "Your order shipped"}),
            op(30, "k", "send_sms", {"to": "+15125550101", "body": "Your order shipped"}),
            op(45, "k", "send_sms", {"to": "+15125550101", "body": "Your order shipped"})]}},
        {"name": "replay does not extend ttl", "args": {"ttl": 10, "ops": [
            op(0, "k", "charge_card", CHARGE), op(6, "k", "charge_card", CHARGE),
            op(12, "k", "charge_card", CHARGE), op(15, "k", "charge_card", CHARGE)]}},
        {"name": "never expires catches", "args": {"ttl": 5, "ops": [
            op(0, "nightly", "export_report", {"day": "2026-10-30"}),
            op(100, "nightly", "export_report", {"day": "2026-10-31"})]}},
        {"name": "no key always runs", "args": {"ttl": 100, "ops": [
            op(0, None, "post_slack", {"channel": "#support", "text": "Escalated T-88"}),
            op(1, None, "post_slack", {"channel": "#support", "text": "Escalated T-88"}),
            op(2, "slack-1", "post_slack", {"channel": "#support", "text": "Escalated T-88"}),
            op(3, "slack-1", "post_slack", {"channel": "#support", "text": "Escalated T-88"})]}},
        {"name": "repeated failures then success then conflict", "args": {"ttl": 300, "ops": [
            op(0, "pay-1", "charge_card", CHARGE, fail="gateway_timeout"),
            op(1, "pay-1", "charge_card", CHARGE, fail="gateway_timeout"),
            op(3, "pay-1", "charge_card", CHARGE),
            op(4, "pay-1", "charge_card", CHARGE, fail="should not run"),
            op(5, "pay-1", "charge_card", dict(CHARGE, currency="eur"))]}},
        {"name": "conflict after expiry becomes fresh", "args": {"ttl": 60, "ops": [
            op(0, "k", "charge_card", CHARGE), op(30, "k", "charge_card", dict(CHARGE, amount_cents=500)),
            op(61, "k", "charge_card", dict(CHARGE, amount_cents=500)), op(62, "k", "charge_card", dict(CHARGE, amount_cents=500))]}},
        {"name": "many keys interleaved", "args": {"ttl": 20, "ops": [
            op(i, "k%d" % (i % 3), "charge_card", {"customer_id": "cus_%d" % (i % 3), "amount_cents": 100 * (i % 3 + 1)}) for i in range(0, 50, 2)]}},
    ]
