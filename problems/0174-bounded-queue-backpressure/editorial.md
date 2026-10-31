## Approach

A bounded queue is three FIFOs: the items, the consumers waiting for an item, and the producers waiting for a slot. Every operation does the cheap thing first and only parks the caller when it has no choice.

```python
def put(self, item):
    if self.getters:                                   # someone is already waiting: hand off
        self.loop.resolve(self.getters.popleft(), item)
        return True
    if len(self.items) < self.capacity:
        self._push(item)
        return True
    if self.policy == "drop_oldest":
        self.dropped.append(self.items.popleft())
        self._push(item)
        return True
    if self.policy == "reject":
        self.rejected.append(item)
        return False
    fut = self.loop.future()                           # block: park until get() makes room
    self.putters.append((fut, item))
    yield fut
    return True

def get(self):
    if self.items:
        item = self.items.popleft()
        if self.putters:                               # the slot we freed goes to the oldest blocked producer
            fut, waiting = self.putters.popleft()
            self._push(waiting)
            self.loop.resolve(fut, True)
        return item
    fut = self.loop.future()
    self.getters.append(fut)
    return (yield fut)
```

The key invariant is that a consumer waits only when the queue is empty and a producer waits only when it is full, so `put` never needs to check for blocked producers and `get` never needs to check for waiting consumers. Moving the blocked producer's item into the slot inside `get` (rather than letting the producer retry when it wakes) keeps FIFO order and prevents a newcomer from stealing the slot.

The three policies are three answers to "the consumer is slower than the producer":

| policy | producer sees | data | use it for |
|---|---|---|---|
| block | latency (backpressure propagates upstream) | nothing lost | ingestion, tool results that must all be processed |
| drop_oldest | nothing | oldest lost | prices, presence, progress updates where only the latest matters |
| reject | an error it must handle | newest lost, caller knows | public APIs: answer 429 with `Retry-After` |

## Common mistakes

- **Unbounded buffering.** "It'll drain" works until a burst outlasts memory. The queue depth, not the error rate, is the first sign of overload.
- **Dropping the newest under drop-oldest.** The agent keeps acting on stale state, which is the opposite of why you picked the policy.
- **Lost wakeups.** Freeing a slot without waking a blocked producer deadlocks the pipeline. Nothing errors; throughput just goes to zero.
- **LIFO wakeups.** Waking the most recent waiter starves the oldest producer and reorders events from different sources.

## Production notes

- `asyncio.Queue(maxsize)` and Go's buffered channels implement the block policy with exactly these waiter deques. Reactive Streams (and gRPC/HTTP2 flow control) push the same idea across the network with credit-based demand.
- Kafka consumers apply backpressure by pausing partitions; SQS and Pub/Sub rely on visibility timeouts and a DLQ instead (see `agent-task-queue-leases`, 163).
- In LLM serving the bounded queue sits in front of the GPU: vLLM and TGI cap waiting requests and reject with 429/503 rather than letting time-to-first-token grow without limit.
- Alert on queue depth and producer blocked time, and size capacity with Little's law: depth ≈ arrival rate × wait time you are willing to tolerate.
- Pair with `rate-limited-fanout` (177) for the delivery side and `token-bucket-rate-limiter` (123) for admission control at the edge.
