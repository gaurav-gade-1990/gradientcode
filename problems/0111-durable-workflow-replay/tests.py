ORDER = {"id": "A-1182", "sku": "LAMP-2", "amount": 84.0, "email": "dana@example.com", "card_limit": 500.0}
POOR = dict(ORDER, card_limit=50.0)


def rec(seq, activity, args, result=None, error=None):
    r = {"seq": seq, "activity": activity, "args": args, "status": "failed" if error else "completed"}
    r.update({"error": error} if error else {"result": result})
    return r


H_RES = rec(0, "reserve_inventory", {"order_id": "A-1182", "sku": "LAMP-2"}, "res_A-1182")
H_CHG = rec(1, "charge_card", {"amount": 84.0, "order_id": "A-1182"}, "ch_A-1182")
H_SHIP = rec(2, "create_shipment", {"order_id": "A-1182", "reservation": "res_A-1182"}, "1ZA-1182")
H_MAIL = rec(3, "send_email", {"to": "dana@example.com", "template": "shipped", "tracking": "1ZA-1182"}, "sent shipped")


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"order": ORDER, "history": [], "runs": [{"workflow": "order_v1"}]},
         "explanation": "Empty history: every activity runs live, and each one is appended to the history as it completes."},
        {"name": "Example 2", "hidden": False, "args": {"order": ORDER, "history": [], "runs": [{"workflow": "order_v1", "crash_at": 3}, {"workflow": "order_v1"}]},
         "explanation": "Run 1 dies before its third activity, with two events recorded. Run 2 replays reserve and charge from the history (no second charge!) and runs only create_shipment and send_email live."},
        {"name": "Example 3", "hidden": False, "args": {"order": ORDER, "history": [H_RES, H_CHG, H_SHIP], "runs": [{"workflow": "order_v2"}]},
         "explanation": "The new code asks for send_email at step 2, but the history recorded create_shipment there. Replay must raise NonDeterminismError before calling anything."},
        {"name": "payment declined live", "args": {"order": POOR, "history": [], "runs": [{"workflow": "order_v1"}]}},
        {"name": "recorded failure is replayed, not retried", "args": {"order": POOR, "history": [], "runs": [{"workflow": "order_v1", "crash_at": 3}, {"workflow": "order_v1"}]}},
        {"name": "finished workflow replays with zero calls", "args": {"order": ORDER, "history": [H_RES, H_CHG, H_SHIP, H_MAIL], "runs": [{"workflow": "order_v1"}]}},
        {"name": "args changed is nondeterminism", "args": {"order": dict(ORDER, amount=99.0), "history": [H_RES, H_CHG], "runs": [{"workflow": "order_v1"}]}},
        {"name": "history longer than workflow", "args": {"order": ORDER, "history": [H_RES, H_CHG, H_SHIP, H_MAIL], "runs": [{"workflow": "order_no_email"}]}},
        {"name": "compatible deploy after early crash", "args": {"order": ORDER, "history": [], "runs": [{"workflow": "order_v1", "crash_at": 3}, {"workflow": "order_v2"}]}},
        {"name": "crash before first activity", "args": {"order": ORDER, "history": [], "runs": [{"workflow": "order_v1", "crash_at": 1}, {"workflow": "order_v1"}]}},
        {"name": "three crashes then finish", "args": {"order": ORDER, "history": [], "runs": [
            {"workflow": "order_v1", "crash_at": 2}, {"workflow": "order_v1", "crash_at": 2}, {"workflow": "order_v1", "crash_at": 1}, {"workflow": "order_v1"}]}},
        {"name": "key order in recorded args", "args": {"order": ORDER, "history": [
            {"seq": 0, "activity": "reserve_inventory", "args": {"sku": "LAMP-2", "order_id": "A-1182"}, "status": "completed", "result": "res_A-1182"}],
            "runs": [{"workflow": "order_v1"}]}},
    ]
