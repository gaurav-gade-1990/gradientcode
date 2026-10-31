def call(name, **args):
    return {"name": name, "arguments": args}


S1 = call("search_tickets", query="refund delayed", status="open")
S1_SWAPPED = {"name": "search_tickets", "arguments": {"status": "open", "query": "refund delayed"}}
S2 = call("search_tickets", query="refund late", status="open")
ORD = call("get_order", order_id="A-1182")
CUS = call("get_customer", customer_id="C-77")
INV = call("get_invoice", invoice_id="INV-9")
NOTE = call("add_note", ticket_id="T-5", body="checked order")


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"calls": [ORD, S1, S1, S1, CUS]},
         "explanation": "Steps 1 to 3 run. At step 4 the last three signatures are identical, so the guard stops the agent before the third search runs."},
        {"name": "Example 2", "hidden": False, "args": {"calls": [S1, ORD, CUS, ORD, CUS, INV]},
         "explanation": "At step 5 the last four calls are [get_order, get_customer] twice: a cycle of length 2."},
        {"name": "Example 3", "hidden": False, "args": {"calls": [S1, S2, S1, S2, ORD], "max_cycle": 2},
         "explanation": "S1 and S2 differ by one word, so they are different signatures. [S1, S2, S1, S2] is a cycle of length 2, found at step 4."},
        {"name": "key order does not matter", "args": {"calls": [S1, S1_SWAPPED, S1, CUS]}},
        {"name": "no loop", "args": {"calls": [S1, S2, ORD, CUS, INV, NOTE, ORD]}},
        {"name": "repeat n=2", "args": {"calls": [ORD, CUS, CUS, INV], "n_repeat": 2}},
        {"name": "repeat beats cycle length check", "args": {"calls": [ORD, ORD, ORD, ORD, ORD], "n_repeat": 5, "max_cycle": 2}},
        {"name": "cycle of 3", "args": {"calls": [S1, ORD, CUS, INV, ORD, CUS, INV, NOTE]}},
        {"name": "cycle of 3 not checked when max_cycle 2", "args": {"calls": [S1, ORD, CUS, INV, ORD, CUS, INV, ORD, CUS], "max_cycle": 2}},
        {"name": "cycle of 4", "args": {"calls": [ORD, CUS, INV, NOTE, ORD, CUS, INV, NOTE, S1], "max_cycle": 4}},
        {"name": "two in a row is fine at n=3", "args": {"calls": [ORD, ORD, CUS, CUS, INV, INV, NOTE]}},
        {"name": "nested args key order", "args": {"calls": [
            call("create_ticket", fields={"priority": "high", "tags": ["billing", "refund"]}, queue="tier2"),
            {"name": "create_ticket", "arguments": {"queue": "tier2", "fields": {"tags": ["billing", "refund"], "priority": "high"}}},
            call("create_ticket", fields={"priority": "high", "tags": ["billing", "refund"]}, queue="tier2"),
            ORD]}},
        {"name": "same args different tool", "args": {"calls": [
            call("get_order", id="A-1"), call("get_invoice", id="A-1"), call("get_shipment", id="A-1"),
            call("get_order", id="A-1"), call("get_invoice", id="A-1"), call("get_shipment", id="A-1")], "max_cycle": 2}},
        {"name": "late cycle after varied prefix", "args": {"calls": [S1, S2, INV, NOTE, S1, ORD, CUS, NOTE, ORD, CUS, NOTE]}},
        {"name": "aabaab cycle of 3", "args": {"calls": [ORD, ORD, CUS, ORD, ORD, CUS, INV]}},
    ]
