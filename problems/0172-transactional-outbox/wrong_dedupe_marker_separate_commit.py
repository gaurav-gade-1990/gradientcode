def place_order(db, order):
    txn = db.begin()
    if txn.get("orders", order["order_id"]) is not None:
        txn.rollback()
        return "exists"
    seq = len(txn.scan("outbox")) + 1
    txn.put("orders", order["order_id"], order)
    txn.put("outbox", seq, {
        "event_id": "evt_" + order["order_id"],
        "type": "order.placed",
        "order_id": order["order_id"],
        "tenant": order["tenant"],
        "total_cents": order["total_cents"],
        "published": False,
    })
    txn.commit()                       # the order and its event become durable together, or not at all
    return "created"


def relay(db, broker):
    txn = db.begin()
    pending = [(seq, row) for seq, row in txn.scan("outbox") if not row["published"]]
    txn.rollback()
    for seq, row in pending:          # seq order
        message = {k: v for k, v in row.items() if k != "published"}
        message["seq"] = seq
        broker.publish("orders", message)
        mark = db.begin()               # only after the broker accepted it: at-least-once
        row = dict(row, published=True)
        mark.put("outbox", seq, row)
        mark.commit()
    return len(pending)


class RevenueConsumer:
    def __init__(self, store):
        self.store = store              # all dedupe state lives here, never in memory

    def handle(self, message):
        txn = self.store.begin()
        if txn.get("processed", message["event_id"]):
            txn.rollback()
            return "duplicate"
        tenant = message["tenant"]
        total = txn.get("revenue", tenant) or 0
        txn.put("revenue", tenant, total + message["total_cents"])
        txn.commit()
        mark = self.store.begin()
        mark.put("processed", message["event_id"], True)
        mark.commit()
        return "applied"
