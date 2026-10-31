## 1. What the problem is really asking

The incident in the story is the classic **dual write**. The code committed the order to the database and then sent an event to Kafka. Those are two systems, and no single commit covers both. A crash between them leaves an order that exists with an event that never will.

The fix has three parts, and you write all three:

1. **`place_order`** puts the order *and* a row describing its event (the outbox row) in **one** local transaction. Now "the order exists" and "the event will be sent" become true together or not at all.
2. **`relay`** copies unpublished outbox rows to the broker, **publishing first and marking second**. A crash in between means the event is sent again on restart. That is a duplicate, never a loss.
3. **`RevenueConsumer.handle`** accepts that duplicates will arrive. It writes the revenue change and a "processed" marker in **one** transaction in its own store, so a redelivered event is recognised and skipped.

This combination is called at-least-once delivery with an idempotent consumer, and together it gives you effectively-once processing.

The judge is unusually thorough. It runs the scenario once cleanly and grades the visible results. Then it reruns it once **per step boundary**, crashing just before that step, restarts from durable state, and checks seven invariants. For Example 1 there are 30 step boundaries, so there are 30 crash reruns. A design that is correct "most of the time" is caught at the one boundary where it isn't.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `db` | the orders database | `txn = db.begin()`, then `get`, `scan`, `put`, `commit` or `rollback` |
| `txn.get(table, key)` | the value or `None`; sees your own uncommitted puts | the existence check, the counter read |
| `txn.scan(table)` | `[(key, value), ...]` sorted by key | count outbox rows, find unpublished ones |
| `txn.commit()` | applies every put atomically | the only moment anything becomes durable |
| `broker.publish(topic, msg)` | appends to a durable log | `broker.publish("orders", message)` |
| `store` | the consumer's own database, same API as `db` | revenue and processed markers |
| `order` | `{"order_id", "tenant", "total_cents", ...}` | the order row is the whole dict |

What happens on a crash, from `driver.py`:

- The crash is a `Crash(BaseException)`. `except Exception` won't catch it, and you must not catch it with a bare `except:` either.
- Uncommitted puts vanish. Committed rows and published messages stay.
- After a restart, the client resends the order it was in the middle of sending, `relay` runs again **from the start**, and a **brand-new** `RevenueConsumer` resumes at the first un-acked offset.

Three details are easy to miss:

- **Every `begin`, `put`, `commit` and `publish` is a crash point**, and so are "response to client" and each ack. `get`, `scan` and `rollback` are not. A design is only safe if every gap between two of those steps is safe.
- **The client's retry is your idempotency problem.** If the crash lands after the commit but before the response, the order is durable but the client never heard. It sends the same order again, and `place_order` must answer `"exists"` without writing a second outbox row.
- **The consumer object doesn't survive a restart.** Anything you keep on `self` other than `store` is gone. The statement says it directly: keep no dedupe state in memory.

## 3. Trace Example 1 by hand

Orders `A` (`ord_1001`, acme, 4200) and `C` (`ord_1003`, globex, 899). These are the 30 step boundaries of the clean run:

| steps | context | what happens |
|---|---|---|
| 0–4 | place_order ord_1001 | `begin`, `put orders/ord_1001`, `put outbox/1`, `commit`, response |
| 5–9 | place_order ord_1003 | the same with `outbox/2` |
| 10 | relay | `begin` to scan the outbox: two unpublished rows |
| 11–14 | relay | `publish evt_ord_1001`, then `begin`, `put outbox/1`, `commit` (marks seq 1 published) |
| 15–18 | relay | the same for seq 2 |
| 19 | relay | relay returns 2 |
| 20–24 | consumer offset 0 | `begin`, `put revenue/acme`, `put processed/evt_ord_1001`, `commit`, ack |
| 25–29 | consumer offset 1 | the same for globex |

Clean result: responses `["created", "created"]`, `published: 2`, consumer `["applied", "applied"]`, broker log seq 1 then 2, revenue `{"acme": 4200, "globex": 899}`.

Now pick crash points and recover from each:

| crash before | durable at that moment | what recovery does | end state |
|---|---|---|---|
| step 4, response to client | order 1001 and outbox/1 committed | client resends 1001 → `"exists"`, then 1003 proceeds | correct |
| step 11, publish evt_ord_1001 | both rows unpublished | relay starts over and publishes both | correct |
| step 12, the `begin` that marks seq 1 | evt_ord_1001 already on the broker, row 1 still `published: False` | relay republishes 1001, then 1003 | broker log is `1001, 1001, 1003`; consumer sees the second 1001 as a duplicate; revenue still 4200 and 899 |
| step 24, ack offset 0 | revenue and marker committed, offset not acked | new consumer gets offset 0 again, finds `processed/evt_ord_1001` | `"duplicate"`, no double count |

Step 12 is the whole design in one row. The relay's crash window produces a **duplicate on the broker**, and the consumer's marker turns that duplicate into a no-op. Every one of the 30 reruns ends with no violations.

**Example 3** shows the same consumer logic without a crash. The ack for offset 0 is "lost", so the broker delivers `evt_ord_1001` twice and the consumer results are `["applied", "duplicate", "applied"]`.

## 4. Key idea: one transaction per fact that must be true together

Look for every pair of writes where "first happened, second didn't" would be a bug. Each such pair must share one commit.

| pair | if split, a crash between them gives | so |
|---|---|---|
| order row + outbox row | an order with no event; the client's retry sees `"exists"` and stops, so the event is lost forever | one transaction in `place_order` |
| revenue update + processed marker | marker first: the revenue is never added. Revenue first: a redelivery adds it twice | one transaction in `handle` |

The relay is different, because the broker and the database **can't** share a transaction. There you choose which failure you prefer, and you put the step whose loss would hurt (the publish) first:

| relay order | crash between the two | delivery guarantee |
|---|---|---|
| publish, then mark | event sent twice | at-least-once (safe with an idempotent consumer) |
| mark, then publish | event never sent | at-most-once (loses revenue) |

## 5. Key idea: count the outbox inside the same transaction

The sequence number is `1 + len(txn.scan("outbox"))`, computed in the same transaction that writes the row. Because the orders are placed one after another and a crashed transaction leaves no rows behind, the count is always the number of committed orders, and the next `seq` is never reused. Sorted integer keys also give the relay its order for free: `scan` returns rows by key, so publishing in scan order publishes in `seq` order, which is what `published_out_of_order` checks.

## 6. Plan before you code

```
place_order(db, order):
    txn = begin
    if orders/<id> exists: rollback, return "exists"
    seq = 1 + rows in outbox
    put orders/<id> = order; put outbox/<seq> = event row with published False
    commit; return "created"

relay(db, broker):
    read all unpublished rows in seq order (read-only transaction)
    for each: publish message (row minus published, plus seq); then commit published True
    return how many

handle(message):
    txn = begin on store
    if processed/<event_id>: rollback, return "duplicate"
    put revenue/<tenant> += total_cents; put processed/<event_id> = True
    commit; return "applied"
```

## 7. Build it one piece at a time

**Step 1: `place_order`, idempotent and atomic.**

```python
def place_order(db, order):
    txn = db.begin()
    if txn.get("orders", order["order_id"]) is not None:
        txn.rollback()
        return "exists"
    seq = len(txn.scan("outbox")) + 1
    txn.put("orders", order["order_id"], order)
    txn.put("outbox", seq, {"event_id": "evt_" + order["order_id"], "type": "order.placed",
                            "order_id": order["order_id"], "tenant": order["tenant"],
                            "total_cents": order["total_cents"], "published": False})
    txn.commit()
    return "created"
```

The existence check runs inside the same transaction as the writes, so it reads the same state that the writes build on. The `event_id` is derived from the `order_id`, not random, so a retry could never produce a second, different event id for the same order.

**Step 2: the relay reads the pending rows once.**

```python
def relay(db, broker):
    txn = db.begin()
    pending = [(seq, row) for seq, row in txn.scan("outbox") if not row["published"]]
    txn.rollback()
```

This transaction only reads, so `rollback` closes it without adding a commit step. Each mark then gets its own short transaction, so each mark is durable on its own the moment it commits.

**Step 3: publish, then mark, row by row.**

```python
    for seq, row in pending:
        message = {k: v for k, v in row.items() if k != "published"}
        message["seq"] = seq
        broker.publish("orders", message)
        mark = db.begin()
        mark.put("outbox", seq, dict(row, published=True))
        mark.commit()
    return len(pending)
```

Committing each mark right after its publish keeps the duplicate window to one message. If you published everything and marked all rows in one transaction at the end, a crash before that commit would republish the whole batch.

**Step 4: the idempotent consumer.**

```python
class RevenueConsumer:
    def __init__(self, store):
        self.store = store

    def handle(self, message):
        txn = self.store.begin()
        if txn.get("processed", message["event_id"]):
            txn.rollback()
            return "duplicate"
        total = txn.get("revenue", message["tenant"]) or 0
        txn.put("revenue", message["tenant"], total + message["total_cents"])
        txn.put("processed", message["event_id"], True)
        txn.commit()
        return "applied"
```

The `or 0` covers a tenant's first order. The marker lives in `store`, the same database as the revenue, so the two commit together and both survive a restart.

## 8. Full solution

```python
def place_order(db, order):  # write the order and its event in one atomic step
    txn = db.begin()  # one transaction covers the existence check and both writes
    if txn.get("orders", order["order_id"]) is not None:  # a client retry or a double click
        txn.rollback()  # nothing to write, so close the transaction
        return "exists"  # no second order row and no second outbox row
    seq = len(txn.scan("outbox")) + 1  # next event number, counted inside this transaction
    txn.put("orders", order["order_id"], order)  # the order itself
    txn.put("outbox", seq, {  # the event, stored in the same database as the order
        "event_id": "evt_" + order["order_id"],  # derived from the order, so it is stable across retries
        "type": "order.placed",  # what kind of event the relay will publish
        "order_id": order["order_id"],  # lets downstream join back to the order
        "tenant": order["tenant"],  # the consumer adds revenue per tenant
        "total_cents": order["total_cents"],  # the amount the consumer adds
        "published": False,  # the relay has not sent it yet
    })
    txn.commit()  # the order and its event become durable together, or not at all
    return "created"  # tell the client the order is new


def relay(db, broker):  # copy every unpublished event to the broker, in seq order
    txn = db.begin()  # a read-only transaction to find the pending rows
    pending = [(seq, row) for seq, row in txn.scan("outbox") if not row["published"]]  # scan is sorted by seq
    txn.rollback()  # nothing was written, so just close it
    for seq, row in pending:  # oldest first, so the broker sees events in seq order
        message = {k: v for k, v in row.items() if k != "published"}  # the event without the relay's flag
        message["seq"] = seq  # downstream can order and audit events
        broker.publish("orders", message)  # send first: a crash after this only causes a duplicate
        mark = db.begin()  # only after the broker accepted it: at-least-once
        row = dict(row, published=True)  # same row, now marked as sent
        mark.put("outbox", seq, row)  # record that this event is out
        mark.commit()  # one mark per message keeps the duplicate window to one event
    return len(pending)  # how many events this call published


class RevenueConsumer:  # applies each order.placed event exactly once to revenue
    def __init__(self, store):  # a fresh consumer is built after every restart
        self.store = store  # all dedupe state lives here, never in memory

    def handle(self, message):  # called once per delivery, including redeliveries
        txn = self.store.begin()  # the check, the effect and the marker share one transaction
        if txn.get("processed", message["event_id"]):  # this event was already applied
            txn.rollback()  # nothing to write
            return "duplicate"  # skip it so revenue isn't counted twice
        tenant = message["tenant"]  # revenue is tracked per tenant
        total = txn.get("revenue", tenant) or 0  # a tenant's first order starts from 0
        txn.put("revenue", tenant, total + message["total_cents"])  # the effect
        txn.put("processed", message["event_id"], True)  # the dedupe marker
        txn.commit()  # effect and dedupe marker in the same transaction
        return "applied"  # the event changed revenue
```

## 9. How the test cases map to the code

Every case also runs the full crash sweep. For the reference solution, `crash_recovery.violations` is `[]` and `first_violation` is `None` in all of them.

| test case | expected (clean run) | what it checks |
|---|---|---|
| Example 1 | `created, created`; published 2; acme 4200, globex 899 | the basic path, plus a crash at each of the 30 boundaries |
| Example 2 | `created, created, exists`; 2 outbox rows; acme 20100 | the existence check in `place_order` |
| Example 3 | consumer `applied, duplicate, applied` | the processed marker on a lost ack |
| single order | published 1; initech 2500 | the smallest scenario still survives every crash |
| five orders three tenants | published 5 in seq 1–5; globex 120899 | ordering across many rows, revenue per tenant |
| redeliver everything | consumer `applied, duplicate` three times | every offset redelivered |
| duplicates and redelivery | `created, created, exists, exists, created`; 3 rows | retries and redelivery together |
| same tenant many orders | acme 20101 | the read-add-write on one tenant's revenue |

## 10. Complexity

`place_order` scans the outbox to count it, O(n) in outbox rows. `relay` is O(n) to scan plus one publish and one small transaction per pending row. `handle` is O(1): two gets and two puts. Memory is the pending list in the relay.

In production the counting scan would be replaced by a database sequence or auto-increment key, and the polling relay by change data capture (Debezium reading the write-ahead log). The `processed` table grows with every event, so you expire it on a horizon longer than the broker's retention. The crash sweep the judge runs is a small version of what Jepsen-style fault injection does to real systems.

## 11. If you got Wrong Answer

The clean run usually passes. Look at `crash_recovery.first_violation`, which names the step the crash came before.

- **`event_missing_from_outbox` and `revenue_missing`, first crash `place_order ord_1001: before orders_db.begin`.** You commit the order and then open a second transaction for the outbox row. That `begin` is the crash point: the order is saved, and the retry sees `"exists"`.
- **`event_never_published` and `revenue_missing`, first crash `relay: before broker.publish evt_ord_1001`.** You mark the row published before you publish it.
- **`revenue_double_counted`, first crash `consumer offset 0 (evt_ord_1001): before ack offset 0`.** Your dedupe is a `set` on the consumer. The rebuilt consumer has an empty set when offset 0 is redelivered.
- **`revenue_double_counted`, first crash `consumer offset 0 (evt_ord_1001): before consumer_db.begin`.** You commit the revenue, then write the marker in a second transaction. The crash lands at that second `begin`.
- **`duplicate_outbox_row` and `published_out_of_order`, even in the clean run of Example 2.** `place_order` doesn't check for an existing order. The double click writes `outbox/3` for `evt_ord_1001`.
- **Runtime Error `your code caught the simulated crash`.** A bare `except:` or `except BaseException` swallowed `Crash`. Let it propagate.

## 12. Follow-ups an interviewer might ask

- *Why not use Kafka transactions instead?* They make writes atomic *within* Kafka. They can't include your Postgres commit, so the dual write remains. The consumer's side effects in another database still need the processed table, which is the inbox pattern.
- *How do you run several relay workers?* Claim rows with `SELECT ... FOR UPDATE SKIP LOCKED` so two workers never publish the same row at the same time, and key messages by `order_id` so per-order ordering survives Kafka partitioning.
- *How do you avoid polling?* Use change data capture. Debezium tails the write-ahead log and its Outbox Event Router turns outbox inserts into Kafka messages, with lower latency and no polling load.
- *What if the workflow spans several services that each need to undo work?* That is a saga with compensations (problem 173, saga-compensation). For replaying a long-running workflow from a durable log, see problem 111 (durable-workflow-replay).
- *How would you make a tool call idempotent in an agent?* The same way: derive a key from the request and store the result next to the effect in one transaction (problem 180, api-idempotent-create).
