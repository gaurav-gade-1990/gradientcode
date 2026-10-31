GOAL = "Refund the duplicate charge on order A-1182 and tell the customer."
TOOLS = {
    "get_order": [{"args": {"order_id": "A-1182"}, "result": "A-1182: $84.00, charges ch_1 and ch_2"}],
    "find_duplicate": [{"args": {"order": "A-1182: $84.00, charges ch_1 and ch_2"}, "result": "ch_2"}],
    "refund_charge": [{"args": {"charge_id": "ch_2"}, "error": "stripe: card network timeout"},
                      {"args": {"charge_id": "ch_1"}, "result": "re_901"}],
    "ledger_refund": [{"args": {"charge_id": "ch_2", "reason": "duplicate"}, "result": "re_ledger_55"}],
    "email_customer": [{"args": {"order_id": "A-1182", "refund": "re_ledger_55"}, "result": "sent"},
                       {"args": {"order_id": "A-1182", "refund": "re_901"}, "result": "sent"}],
    "open_ticket": [{"args": {"summary": "manual refund needed for A-1182"}, "result": "TKT-311"}],
}
S1 = {"id": "s1", "tool": "get_order", "args": {"order_id": "A-1182"}}
S2 = {"id": "s2", "tool": "find_duplicate", "args": {"order": {"$ref": "s1"}}}
S3 = {"id": "s3", "tool": "refund_charge", "args": {"charge_id": {"$ref": "s2"}}}
S4 = {"id": "s4", "tool": "email_customer", "args": {"order_id": "A-1182", "refund": {"$ref": "s3"}}}
S3B = {"id": "s3b", "tool": "ledger_refund", "args": {"charge_id": {"$ref": "s2"}, "reason": "duplicate"}}
S4B = {"id": "s4b", "tool": "email_customer", "args": {"order_id": "A-1182", "refund": {"$ref": "s3b"}}}
TICKET = {"id": "t1", "tool": "open_ticket", "args": {"summary": "manual refund needed for A-1182"}}


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"goal": GOAL, "plans": [[S1, S2, S3, S4], [S3B, S4B]], "tool_table": TOOLS, "max_replans": 2},
         "explanation": "s1 and s2 run, and s2's $ref resolves to s1's result. s3 fails on Stripe, so the planner is called again with completed [s1, s2] and the failure. The new plan [s3b, s4b] replaces s3 and s4."},
        {"name": "Example 2", "hidden": False, "args": {"goal": GOAL, "plans": [[S1, S2, S3, S4], [S1, S2, S3B, S4B]], "tool_table": TOOLS, "max_replans": 1},
         "explanation": "The replanned list repeats s1 and s2. They already completed, so they are skipped, not re-run. Only s3b and s4b call tools."},
        {"name": "Example 3", "hidden": False, "args": {"goal": GOAL, "plans": [[S1, S2, S3, S4]], "tool_table": TOOLS, "max_replans": 0},
         "explanation": "No replans allowed: the run stops as failed right after s3 fails, and s4 never runs."},
        {"name": "no failures", "args": {"goal": "Refund charge ch_1.", "plans": [[{"id": "r", "tool": "refund_charge", "args": {"charge_id": "ch_1"}},
                                                                                    {"id": "e", "tool": "email_customer", "args": {"order_id": "A-1182", "refund": {"$ref": "r"}}}]],
                                         "tool_table": TOOLS, "max_replans": 2}},
        {"name": "replan budget exhausted", "args": {"goal": GOAL, "plans": [[S1, S2, S3, S4], [S3, S4], [S3, S4], [TICKET]], "tool_table": TOOLS, "max_replans": 2}},
        {"name": "budget exactly enough", "args": {"goal": GOAL, "plans": [[S1, S2, S3, S4], [S3, S4], [TICKET]], "tool_table": TOOLS, "max_replans": 2}},
        {"name": "unresolved reference never calls tool", "args": {"goal": GOAL, "plans": [
            [S1, {"id": "s3", "tool": "refund_charge", "args": {"charge_id": {"$ref": "s2"}}}], [S2, S3B, S4B]], "tool_table": TOOLS, "max_replans": 1}},
        {"name": "unknown tool then empty plan", "args": {"goal": GOAL, "plans": [
            [S1, {"id": "x", "tool": "wire_transfer", "args": {"amount": "84.00"}}, S2], []], "tool_table": TOOLS, "max_replans": 3}},
        {"name": "replan replaces the tail", "args": {"goal": GOAL, "plans": [
            [S1, S2, S3, S4, {"id": "s5", "tool": "open_ticket", "args": {"summary": "manual refund needed for A-1182"}}], [S3B]],
            "tool_table": TOOLS, "max_replans": 1}},
        {"name": "failed id reused with new args", "args": {"goal": GOAL, "plans": [
            [S1, S2, S3, S4], [{"id": "s3", "tool": "refund_charge", "args": {"charge_id": "ch_1"}}, S4]], "tool_table": TOOLS, "max_replans": 1}},
        {"name": "two failures, history grows", "args": {"goal": GOAL, "plans": [
            [S1, S3], [S2, S3], [S3B, S4B]], "tool_table": TOOLS, "max_replans": 3}},
    ]
