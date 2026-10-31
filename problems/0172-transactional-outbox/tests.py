def order(oid, tenant, cents, item):
    return {"order_id": oid, "tenant": tenant, "total_cents": cents, "items": [item], "placed_by": "agent:procurement"}


A = order("ord_1001", "acme", 4200, "USB-C dock")
B = order("ord_1002", "acme", 15900, "Standing desk")
C = order("ord_1003", "globex", 899, "Cable kit")
D = order("ord_1004", "globex", 120000, "GPU workstation")
E = order("ord_1005", "initech", 2500, "Ergonomic mouse")


def cases():
    return [
        {"name": "Example 1", "hidden": False, "args": {"orders": [A, C]},
         "explanation": "Each order commits with its outbox row. The relay publishes seq 1 and 2 in order, and the "
                        "consumer applies both. Crashing before every step and recovering always ends in this same state, "
                        "so there are no violations."},
        {"name": "Example 2", "hidden": False, "args": {"orders": [A, B, A]},
         "explanation": "The user double-clicked, so ord_1001 is sent twice. The second call returns \"exists\" and writes "
                        "no second outbox row. acme's revenue is 4200 + 15900."},
        {"name": "Example 3", "hidden": False, "args": {"orders": [A, C], "redeliver": [0]},
         "explanation": "The ack for offset 0 is lost, so the broker delivers evt_ord_1001 again. The consumer finds "
                        "processed/evt_ord_1001 and returns \"duplicate\" without counting it twice."},
        {"name": "single order", "args": {"orders": [E]}},
        {"name": "five orders three tenants", "args": {"orders": [A, B, C, D, E]}},
        {"name": "redeliver everything", "args": {"orders": [A, B, C], "redeliver": [0, 1, 2]}},
        {"name": "duplicates and redelivery", "args": {"orders": [C, D, C, D, E], "redeliver": [1]}},
        {"name": "same tenant many orders", "args": {"orders": [A, B, order("ord_1006", "acme", 1, "Sticker")]}},
    ]
