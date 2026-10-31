Your agent platform lets an agent place orders through a tool. Finance's revenue dashboard is fed by an `order.placed` event. Last month a pod was OOM-killed between `db.commit()` and `kafka.send()`, and $41k of orders never reached the dashboard. Rebuild the flow with a transactional outbox that survives a crash at **any** point.

Write three pieces against the fakes the judge passes in.

**Fakes**

| object | API |
|---|---|
| `db`, `store` | `txn = db.begin()`; `txn.get(table, key)` returns the value or `None` (your own uncommitted writes are visible); `txn.scan(table)` returns `[(key, value), ...]` sorted by key; `txn.put(table, key, value)`; `txn.commit()` applies every write atomically; `txn.rollback()` |
| `broker` | `broker.publish(topic, message)` appends to a durable log |

A crash kills the process. Uncommitted writes are lost, and committed writes and published messages survive. After a restart the judge builds everything from durable state only: the client resends the order it was sending, `relay` runs again from the start, and a **new** `RevenueConsumer` resumes at the first message that was not acked. A message is acked only after `handle` returns, so a crash before the ack redelivers it. The crash is a `BaseException`, so don't catch it.

**1. `place_order(db, order) -> str`.** `order` is `{"order_id", "tenant", "total_cents", ...}`.

- If `orders/<order_id>` already exists, write nothing and return `"exists"`.
- Otherwise, in **one** transaction, put `orders/<order_id> = order` and `outbox/<seq>`, where `seq = 1 + (number of rows in outbox)`. The outbox row is `{"event_id": "evt_" + order_id, "type": "order.placed", "order_id", "tenant", "total_cents", "published": False}`. Commit, then return `"created"`.

**2. `relay(db, broker) -> int`.** Take every outbox row with `published == False`, in increasing `seq`. For each one, `broker.publish("orders", message)`, where `message` is the row without `published` plus `"seq": seq`. **Then** commit the row with `published = True`. Return how many rows this call published.

**3. `RevenueConsumer(store).handle(message) -> str`.** If `processed/<event_id>` is set in `store`, return `"duplicate"`. Otherwise, in **one** transaction, add `total_cents` to `revenue/<tenant>` (missing means 0) and set `processed/<event_id> = True`. Commit, then return `"applied"`. Keep no dedupe state in memory.

The judge first runs the scenario with no crash and grades the responses, the relay count, the consumer results, the broker log, the outbox and the revenue. It may also make the broker redeliver some offsets (a lost ack). Then, for **every** step boundary of that run (each `begin`, `put`, `commit`, `publish`, response and ack), it reruns the scenario with a crash just before that step, recovers, and checks these invariants:

| invariant | name when violated |
|---|---|
| every order is stored | `order_lost` |
| one outbox row per order, no repeats | `event_missing_from_outbox`, `duplicate_outbox_row` |
| every row ends up published | `outbox_not_drained` |
| every event reaches the broker, and nothing else does | `event_never_published`, `phantom_event` |
| events first reach the broker in seq order | `published_out_of_order` |
| revenue per tenant equals the sum of its unique orders | `revenue_missing`, `revenue_double_counted` |

It returns the union of the violation names and the first crash that caused one. Both must be empty or `None`.

**Constraints**

- `1 <= len(orders) <= 6`; an `order_id` may repeat (a double-clicked submit)
- `total_cents` is a positive int
- Don't import `time`, threads or anything that touches a real database
