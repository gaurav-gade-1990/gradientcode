ROLES = ["privacy-officer", "fraud-investigator"]


def red(tenant, text):
    return {"op": "redact", "tenant": tenant, "text": text}


def rei(tenant, role, src):
    op = {"op": "reidentify", "tenant": tenant, "role": role}
    if isinstance(src, int):
        op["text_from"] = src
    else:
        op["text"] = src
    return op


TICKETS = [
    "Customer Dana.Reyes@Acme.com says card 4111 1111 1111 1111 was charged twice; call (512) 555-0100.",
    "Follow-up from dana.reyes@acme.com: refund to card 4111-1111-1111-1111 please. SSN on file 123-45-6789.",
    "Order 1234 5678 9012 3456 shipped. Tracking 9400 1000 0000 0000 0000 00.",
    "Escalate: +1 512-555-0100 and 512.555.0199, amex 378282246310005, mc 5500 0000 0000 0004.",
    "Two SSNs 078-05-1120 and 219-09-9999, invoice INV-2024-000123, ext 555-0100.",
]


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"reidentify_roles": ROLES, "ops": [
            red("acme", "Refund dana@acme.com, card 4111 1111 1111 1111, phone 512-555-0100."),
            rei("acme", "privacy-officer", 0)]},
         "explanation": "Emails are replaced first, then Luhn-valid cards, then SSNs, then phones. The privacy officer can map the tokens back, and the call is audited."},
        {"name": "Example 2", "hidden": False, "args": {"reidentify_roles": ROLES, "ops": [
            red("acme", "From Dana@Acme.com: order 1234 5678 9012 3456 is late."),
            red("acme", "Second note from dana@acme.com about the same order."),
            rei("acme", "support-agent", 1)]},
         "explanation": "The order number has 16 digits but fails the Luhn check, so it stays. The two spellings of Dana's email are one person and share [EMAIL_1]. "
                        "A support agent may not re-identify: the call raises PermissionError and the denied attempt is still audited."},
        {"name": "Example 3", "hidden": False, "args": {"reidentify_roles": ROLES, "ops": [
            red("acme", "Contact ops@acme.com"), red("globex", "Call legal on 415-555-0142"),
            rei("globex", "privacy-officer", 0), rei("globex", "privacy-officer", 1)]},
         "explanation": "Each tenant has its own vault and numbering. globex's officer can re-identify globex's [PHONE_1], "
                        "but globex's vault has no [EMAIL_1], so acme's token stays a token and is not listed in the audit entry."},
        {"name": "ticket thread", "args": {"reidentify_roles": ROLES, "ops": [red("acme", t) for t in TICKETS] + [rei("acme", "fraud-investigator", i) for i in range(5)]}},
        {"name": "two tenants, same values", "args": {"reidentify_roles": ROLES, "ops": [
            red("globex", TICKETS[3]), red("acme", TICKETS[0]), red("acme", TICKETS[3]),
            rei("acme", "privacy-officer", 0), rei("globex", "privacy-officer", 0), rei("globex", "privacy-officer", 1)]}},
        {"name": "phone formats normalize", "args": {"reidentify_roles": ROLES, "ops": [
            red("initech", "Call 512-555-0100, (512) 555-0100, +1 512 555 0100, 5125550100 or 512.555.0100."),
            rei("initech", "privacy-officer", 0)]}},
        {"name": "card formats and lengths", "args": {"reidentify_roles": ROLES, "ops": [
            red("acme", "Cards: 4111111111111111, 4111 1111 1111 1112, 4222222222222, 6011-1111-1111-1117, 378282246310005, 30569309025904."),
            rei("acme", "fraud-investigator", 0)]}},
        {"name": "no pii", "args": {"reidentify_roles": ROLES, "ops": [red("acme", "The agent closed ticket T-1182 at 14:05 on 2024-06-01."),
                                                                     rei("acme", "privacy-officer", "No tokens here, and [EMAIL_9] is unknown.")]}},
        {"name": "denied then allowed", "args": {"reidentify_roles": ["privacy-officer"], "ops": [
            red("acme", "SSN 123-45-6789, email a.b+tag@sub.acme.co.uk"),
            rei("acme", "fraud-investigator", 0), rei("acme", "admin", 0), rei("acme", "privacy-officer", 0)]}},
        {"name": "repeated token reported once", "args": {"reidentify_roles": ROLES, "ops": [
            red("acme", "dana@acme.com cc DANA@ACME.COM cc ops@acme.com cc dana@acme.com"), rei("acme", "privacy-officer", 0)]}},
        {"name": "many messages", "args": {"reidentify_roles": ROLES, "ops": [
            red(["acme", "globex"][i % 2], "Ticket %d from user%d@corp%d.com, phone 512-555-%04d, card %s." %
                (i, i % 7, i % 3, 100 + i % 9, ["4111 1111 1111 1111", "5500 0000 0000 0004", "1234 5678 9012 3456"][i % 3]))
            for i in range(40)] + [rei("globex", "privacy-officer", i) for i in (1, 3, 38)] + [rei("acme", "privacy-officer", i) for i in (0, 39)]}},
    ]
