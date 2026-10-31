Your agent platform streams tool events (search results, file chunks, webhook payloads) from producers to a pool of LLM workers. Workers are slower than producers during bursts, and an unbounded buffer has already taken a node down once. Build the bounded queue between them, with a configurable overload policy.

Implement `class BoundedQueue(loop, capacity, policy)` on the judge's `EventLoop`. Tasks are generators; your methods are generators used with `yield from`:

```python
ok = yield from q.put(item)     # in a producer
item = yield from q.get()       # in a consumer
```

To wait, use the two helpers the judge's loop adds to `gc_runtime.EventLoop`:

- `fut = loop.future()` creates a pending future. A task waits on it with `value = yield fut`.
- `loop.resolve(fut, value)` completes it. The waiting task resumes at the current virtual time with `value`.

**Rules**

| situation | `put(item)` |
|---|---|
| a consumer is waiting | hand `item` to the **oldest** waiting consumer (resolve its future with `item`); the queue stays empty; return `True` |
| queue has fewer than `capacity` items | append; return `True` |
| full, `policy == "block"` | wait (FIFO behind other blocked producers) until a `get` moves your item into the queue; then return `True` |
| full, `policy == "drop_oldest"` | remove the oldest queued item, append it to `self.dropped`, append `item`; return `True` |
| full, `policy == "reject"` | append `item` to `self.rejected`; return `False` |

`get()`: if the queue has items, pop the oldest. Then, if a producer is blocked, append the **oldest** blocked producer's item to the queue and resolve that producer's future. Return the popped item. If the queue is empty, wait (FIFO behind other waiting consumers) for an item handed over by `put`.

Neither method may yield unless it actually waits. Tasks that wake at the same virtual time run in the order they were scheduled (the `EventLoop` rule), so a consumer that went to sleep before a producer also wakes before it. Also keep `self.max_depth`, the largest number of items ever in the queue, and `len(q)`, the current count.

The judge spawns the producers (in order), then the consumers. A producer calls `put` for each of its items and sleeps `interval` seconds after each one. A consumer loops forever: `get`, then sleep `service` seconds. The judge reports the event trail `[t, event, who, item]`, the dropped and rejected items, `max_depth`, total time producers spent blocked, delivered count, makespan and throughput.

**Constraints**

- `1 <= capacity <= 10`; `policy` is one of `"block"`, `"drop_oldest"`, `"reject"`.
- At most 4 producers, 4 consumers and 40 items.
- Don't import `time`, `threading` or `asyncio`. All waiting goes through `loop.future()`.
