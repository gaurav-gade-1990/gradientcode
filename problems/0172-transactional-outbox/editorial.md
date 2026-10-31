## Approach

The bug is a **dual write**: the database and the broker are two systems, and no single commit covers both. The outbox moves the event into the database, so one local transaction makes "the order exists" and "the event will be sent" true together. A relay then copies the outbox to the broker.

```python
txn = db.begin()
if txn.get("orders", oid) is not None:          # client retry after a lost response
    txn.rollback(); return "exists"
txn.put("orders", oid, order)
txn.put("outbox", len(txn.scan("outbox")) + 1, {..., "published": False})
txn.commit()
```

The relay can only be **at-least-once**. It publishes, then marks the row. A crash between the two republishes on restart, which is fine. The opposite order (mark, then publish) is at-most-once, and a crash there loses the event. Duplicates are inevitable, so the consumer makes its effect idempotent. It writes the dedupe marker and the revenue update in **one** transaction in its own store:

```python
if txn.get("processed", eid): return "duplicate"
txn.put("revenue", tenant, (txn.get("revenue", tenant) or 0) + cents)
txn.put("processed", eid, True)
txn.commit()
```

At-least-once delivery plus an idempotent consumer is how you get effectively-once processing. Enumerating every crash point is the honest test for it, and the judge does exactly that.

## Common mistakes

- **Outbox in a second transaction.** `save(order)` then `save(event)` looks atomic in a code review. A crash between them leaves an order with no event, and the client's retry sees the order and stops, so the event is lost for good.
- **Mark before publish.** This is the dual write again, inside the relay. One crash, one lost event.
- **Dedupe in memory.** A `set()` on the consumer works until the pod restarts, and then every redelivered message counts twice.
- **Dedupe marker and effect in separate commits.** Marker first loses the effect on a crash. Effect first double-counts on redelivery.
- **Non-idempotent create.** A double-click or a client retry writes a second outbox row, and downstream sees the order twice.

## Production notes

- Debezium reads the outbox from the WAL or binlog (change data capture) instead of polling it, which gives you ordering and low latency. Its Outbox Event Router turns rows into Kafka messages keyed by aggregate id.
- A polling relay should claim rows with `SELECT ... FOR UPDATE SKIP LOCKED`, and it can delete or archive rows instead of flagging them. Key messages by `order_id` so per-entity order holds across Kafka partitions.
- Kafka's idempotent producer and transactions give exactly-once delivery inside Kafka only. The consumer's side effects in another database still need the processed-ids table (the inbox pattern), committed with the effect.
- Temporal, Restate and AWS Step Functions sidestep the problem by making the workflow itself durable. **saga-compensation** (173) adds rollback across services, and **durable-workflow-replay** (111) is the replay side.
- Expire the processed-ids table on a horizon longer than the broker's retention. Otherwise it grows forever.
