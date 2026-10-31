TRIAGE_SYS = {"role": "system", "content": "You are the triage agent for Acme Support. Route to billing, shipping or security."}
BILLING = {"name": "billing", "system_prompt": "You are Acme's billing specialist. You can look up invoices and issue refunds up to $200.",
           "tools": ["get_invoice", "issue_refund", "get_order"]}
SHIPPING = {"name": "shipping", "system_prompt": "You are Acme's shipping specialist.", "tools": ["track_package", "get_order"]}


def tc(id, name, **args):
    return {"id": id, "name": name, "arguments": args}


DOUBLE_CHARGE = [
    TRIAGE_SYS,
    {"role": "user", "content": "I was charged twice for order A-1182."},
    {"role": "assistant", "content": "Customer sounds annoyed; check sentiment before routing.", "private": True,
     "tool_calls": [tc("c1", "classify_sentiment", text="I was charged twice for order A-1182.")]},
    {"role": "tool", "tool_call_id": "c1", "content": "negative (0.91)"},
    {"role": "assistant", "content": "Let me pull up that order.", "tool_calls": [tc("c2", "get_order", order_id="A-1182")]},
    {"role": "tool", "tool_call_id": "c2", "content": "A-1182: $84.00, paid 2026-10-20, two captures on card ending 4242"},
    {"role": "assistant", "content": None, "tool_calls": [tc("c3", "transfer_to_agent", agent="billing")]},
    {"role": "tool", "tool_call_id": "c3", "content": "transferring"},
]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"transcript": DOUBLE_CHARGE, "specialist": BILLING,
                                                         "summary": "Customer reports a double charge on order A-1182 ($84.00, card 4242)."},
         "explanation": "The triage system prompt and the private sentiment check (and its result c1) are dropped. get_order is a billing tool, so c2 and its result stay. The transfer call c3 is not a billing tool; that leaves an assistant turn with no content and no calls, so it is dropped along with its result."},
        {"name": "Example 2", "hidden": False, "args": {"transcript": [
            TRIAGE_SYS,
            {"role": "user", "content": "Where is my package? Also, was I charged?"},
            {"role": "assistant", "content": "Checking both.", "tool_calls": [tc("t1", "track_package", tracking="1Z999"), tc("t2", "get_invoice", order_id="A-2001")]},
            {"role": "tool", "tool_call_id": "t1", "content": "1Z999: out for delivery"},
            {"role": "tool", "tool_call_id": "t2", "content": "INV-2001: $129.00 paid"},
            {"role": "user", "content": "Mostly I care about the package."}],
            "specialist": SHIPPING, "summary": "Customer wants delivery status for 1Z999."},
         "explanation": "Shipping has track_package but not get_invoice. The assistant turn keeps its text and only call t1; the t2 result would be orphaned, so it is dropped."},
        {"name": "same transcript to shipping", "args": {"transcript": DOUBLE_CHARGE, "specialist": SHIPPING, "summary": "Double charge; routed by mistake."}},
        {"name": "private turn calling an allowed tool", "args": {"transcript": [
            TRIAGE_SYS,
            {"role": "user", "content": "Refund my order A-77 please."},
            {"role": "assistant", "content": "Peek at the invoice silently first.", "private": True, "tool_calls": [tc("p1", "get_invoice", order_id="A-77")]},
            {"role": "tool", "tool_call_id": "p1", "content": "INV-77: $40.00, internal fraud flag=true"},
            {"role": "assistant", "content": "I'll connect you with billing."}],
            "specialist": BILLING, "summary": "Customer requests a refund on A-77."}},
        {"name": "empty string content dropped", "args": {"transcript": [
            {"role": "user", "content": "My account got locked."},
            {"role": "assistant", "content": "", "tool_calls": [tc("x1", "lookup_user", email="kim@example.com")]},
            {"role": "tool", "tool_call_id": "x1", "content": "user kim@example.com: locked after 5 failed logins"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "Please hurry."}],
            "specialist": {"name": "security", "system_prompt": "You are Acme's security specialist.", "tools": ["unlock_account"]},
            "summary": "Account locked after failed logins."}},
        {"name": "empty string content with a kept tool call survives", "args": {"transcript": [
            {"role": "user", "content": "Someone reset my password, it wasn't me."},
            {"role": "assistant", "content": "", "tool_calls": [tc("u1", "unlock_account", email="lee@example.com"), tc("u2", "lookup_user", email="lee@example.com")]},
            {"role": "tool", "tool_call_id": "u1", "content": "lee@example.com: sessions revoked, account locked"},
            {"role": "tool", "tool_call_id": "u2", "content": "lee@example.com: password reset 2026-10-30 from new device"}],
            "specialist": {"name": "security", "system_prompt": "You are Acme's security specialist.", "tools": ["unlock_account"]},
            "summary": "Unrecognized password reset; sessions revoked."}},
        {"name": "multiple turns, interleaved", "args": {"transcript": [
            TRIAGE_SYS,
            {"role": "user", "content": "Two things: order A-5 never arrived and I want a refund."},
            {"role": "assistant", "content": None, "tool_calls": [tc("a", "get_order", order_id="A-5"), tc("b", "track_package", tracking="1Z5")]},
            {"role": "tool", "tool_call_id": "a", "content": "A-5: $55.00, shipped 2026-10-01"},
            {"role": "tool", "tool_call_id": "b", "content": "1Z5: lost in transit"},
            {"role": "assistant", "content": "Plan: billing handles the refund, mention the loss.", "private": True},
            {"role": "assistant", "content": "Your package was lost. Billing will help with a refund.", "tool_calls": [tc("c", "transfer_to_agent", agent="billing")]},
            {"role": "tool", "tool_call_id": "c", "content": "transferring"},
            {"role": "user", "content": "Thanks."}],
            "specialist": BILLING, "summary": "Order A-5 ($55) was lost in transit; customer wants a refund."}},
        {"name": "nothing but the user", "args": {"transcript": [TRIAGE_SYS, {"role": "user", "content": "Hi"}],
                                                 "specialist": BILLING, "summary": "Customer said hi."}},
        {"name": "extra keys preserved", "args": {"transcript": [
            {"role": "user", "content": "Cancel my subscription", "name": "dana"},
            {"role": "assistant", "content": "Looking it up.", "tool_calls": [tc("s1", "get_invoice", subscription="sub_9")], "model": "triage-small"},
            {"role": "tool", "tool_call_id": "s1", "content": "sub_9: $12/mo, renews 2026-11-01", "name": "get_invoice"}],
            "specialist": BILLING, "summary": "Customer wants to cancel sub_9."}},
    ]
