## 1. What the problem is really asking

Producers make work faster than consumers can finish it. Something has to give. If nothing gives, the buffer between them grows until the process runs out of memory, which is the outage in the story. A **bounded queue** forces you to choose what gives when it is full:

- **block:** the producer waits. Nothing is lost, and the slowness travels upstream (that is *backpressure*).
- **drop_oldest:** the oldest queued item is thrown away. The producer never waits, and the consumer always sees the freshest data.
- **reject:** the new item is refused and `put` returns `False`, so the caller can answer 429.

Under the story this is a classic **producer/consumer queue built from three FIFOs**: the items, the consumers waiting for an item, and the producers waiting for a slot. Each operation does the cheap thing first and parks its caller on a future only when it has no other choice.

The judge doesn't just count deliveries. It records an **event trail** of `[t, event, who, item]` rows, with `put`, `reject`, `drop`, `get` and `done` events, plus `max_depth`, time spent blocked per producer, and `stuck_producers`. So *who* gets an item, *when*, and *in what order at the same virtual time* are all graded. That makes the "don't yield unless you wait" rule and the FIFO wakeup order matter as much as the policies.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `loop` | the judge's `EventLoop` with two extra helpers | `loop.future()` and `loop.resolve(fut, value)` |
| `fut = loop.future()` | a pending future | a task parks on it with `value = yield fut` |
| `loop.resolve(fut, value)` | completes a future | the parked task resumes at the current time, receiving `value` |
| `capacity` | the most items the queue may hold | the "full" test is `len(self.items) < self.capacity` |
| `policy` | `"block"`, `"drop_oldest"` or `"reject"` | picks the full-queue branch of `put` |
| `self.dropped`, `self.rejected` | lists the judge reads | append the dropped (old) item, or the rejected (new) item |
| `self.max_depth`, `len(q)` | high-water mark and current size | update the mark every time you append to the queue |

Three details are easy to miss:

- **Both methods are generators, but must not yield on the fast path.** The driver calls `ok = yield from q.put(item)`. If `put` yields even once (say `yield None`), the producer goes to the back of the run queue and other tasks at the same time run first. The event order changes and tests fail. A `yield fut` that is only reached when you truly wait is enough to make the function a generator.
- **The driver spawns producers before consumers.** At `t=0` the first producer runs before any consumer has called `get`, so its first item goes *into* the queue. The consumer then pops it straight away. That's why every trail starts `put`, then `get`.
- **`loop.resolve` doesn't run the waiter immediately.** It schedules the waiter at the current time. The task that called `resolve` keeps running until it next yields. So in a trail you see the consumer's `get` event *before* the woken producer's `put` event at the same timestamp.

## 3. Trace Example 1 by hand

`capacity=2`, `policy="block"`. The crawler puts `page-1` to `page-5`, sleeping 0.5 s after each. The single consumer `llm-1` takes 2 s per page.

| t | who runs | what happens | queue after | blocked producers |
|---|---|---|---|---|
| 0 | crawler | `put(page-1)`: no consumer waiting yet, room, so append | `[page-1]` | none |
| 0 | llm-1 | `get()` pops `page-1`, starts a 2 s job | `[]` | none |
| 0.5 | crawler | `put(page-2)` appends | `[page-2]` | none |
| 1.0 | crawler | `put(page-3)` appends | `[page-2, page-3]` | none |
| 1.5 | crawler | `put(page-4)`: full, so park on a future | `[page-2, page-3]` | crawler(page-4) |
| 2.0 | llm-1 | done `page-1`; `get()` pops `page-2`, **moves page-4 in**, resolves crawler | `[page-3, page-4]` | none |
| 2.0 | crawler | resumes; logs `put page-4` (blocked 0.5 s) | same | none |
| 2.5 | crawler | `put(page-5)`: full again, park | `[page-3, page-4]` | crawler(page-5) |
| 4.0 | llm-1 | pops `page-3`, moves `page-5` in, resolves crawler (blocked 1.5 s) | `[page-4, page-5]` | none |
| 6.0, 8.0 | llm-1 | pops `page-4`, then `page-5` | `[]` | none |

The judge's output matches: `blocked_s = {"crawler": 2}` (0.5 + 1.5), `max_depth = 2`, `delivered = 5`, `makespan = 10`, `throughput = 0.5`. The rows at t=2 come out as `[2, 'done', 'llm-1', 'page-1']`, `[2, 'get', 'llm-1', 'page-2']`, `[2, 'put', 'crawler', 'page-4']`, in that order, because `resolve` only schedules the crawler.

**Example 2 is the same timeline under `drop_oldest`.** At t=1.5 the queue holds `[tick-2, tick-3]`. Instead of blocking, `put(tick-4)` drops `tick-2` and appends, so the trail shows `[1.5, 'drop', 'price-feed', 'tick-2']`. At t=2.0 both the agent and the producer wake. The agent went to sleep first (at t=0), so it runs first and pops `tick-3`, and `tick-5` then fits without a drop. Final `dropped = ['tick-2']`, `delivered = 4`.

**The tricky hidden case, "consumers wait first".** The producer `late` only starts at t=2. Consumers `a`, `b`, `c` all call `get()` at t=0 on an empty queue, so all three park: `getters = [a, b, c]`. At t=2, `put(job-1)` sees a waiting consumer and hands `job-1` straight to `a`. The queue never holds anything, so `max_depth = 0`. When `a` finishes at 2.5 it parks again, behind `b` and `c`. So `job-2` goes to `b`, `job-3` to `c`, and `job-4` back to `a`: strict round-robin, because the getters deque is FIFO.

## 4. Key idea: the invariant that keeps both methods short

At any moment, **consumers wait only when the queue is empty, and producers wait only when it is full.** Both can't happen at once, because capacity is at least 1.

That has two consequences:

- `put` checks for a waiting consumer first. If one is waiting, the queue must be empty, so you hand the item over directly. You never need to look at blocked producers inside `put`.
- `get` only needs to wake a blocked producer when it has just popped from a full queue. You never need to look at waiting consumers inside `get`.

The order of checks in `put` matters. If you test capacity before checking for waiting consumers, the item goes into the (empty) queue and the sleeping consumer is never woken. In "consumers wait first", `job-1` would sit in the queue at t=2 with three idle consumers.

## 5. Key idea: move the blocked producer's item inside `get`

When `get` frees a slot and a producer is blocked, the reference solution does the producer's work for it: it pushes the waiting item into the queue, then resolves the future with `True`. The woken producer just returns.

The alternative, waking the producer and letting it re-check capacity itself, looks equivalent but isn't. Between the resolve and the producer actually resuming, another task at the same time can run `put` and take the freed slot, and the original producer has to wait again. Moving the item inside `get` guarantees blocked producers are served strictly in arrival order. That is the FIFO rule the problem states, and it is what "block two producers fifo" and "three blocked producers" check.

## 6. Plan before you code

```
state: items (deque), getters (deque of futures), putters (deque of (future, item))

put(item):
    a consumer is waiting      -> resolve the oldest getter with item; return True
    room in the queue          -> append; update max_depth; return True
    full and drop_oldest       -> move the oldest item to dropped; append; return True
    full and reject            -> add item to rejected; return False
    full and block             -> park (future, item) at the back of putters; yield it; return True

get():
    queue has items -> pop the oldest
                       if a producer is blocked: move its item in, resolve its future
                       return the popped item
    queue empty     -> park a future at the back of getters; yield it; return what it brings
```

| queue state | `put` does | `get` does |
|---|---|---|
| empty, consumers waiting | hand off, no queue change | (can't happen: getters only exist when empty) |
| partly full | append | pop |
| full, producers blocked | policy branch | pop, then move the oldest blocked item in |
| empty, nobody waiting | append | park |

## 7. Build it one piece at a time

**Step 1: the three FIFOs and the depth tracker.** Funnel every append through one helper so `max_depth` can't be forgotten on one of the three paths that add an item.

```python
def __init__(self, loop, capacity, policy):
    self.loop, self.capacity, self.policy = loop, capacity, policy
    self.items = deque()
    self.getters = deque()   # futures of waiting consumers
    self.putters = deque()   # (future, item) of blocked producers
    self.dropped, self.rejected, self.max_depth = [], [], 0

def _push(self, item):
    self.items.append(item)
    self.max_depth = max(self.max_depth, len(self.items))
```

Use `deque`, not `list`. `popleft()` is O(1) on a deque and O(n) on a list.

**Step 2: the fast paths of `put`.** Hand off first, then check capacity. Each branch returns without yielding.

```python
def put(self, item):
    if self.getters:
        self.loop.resolve(self.getters.popleft(), item)
        return True
    if len(self.items) < self.capacity:
        self._push(item)
        return True
```

`popleft()` gives the item to the *oldest* waiting consumer. `pop()` would give it to the newest, and in "consumers wait first" `job-1` would go to `c` instead of `a`.

**Step 3: the full-queue policies.** `drop_oldest` removes from the front, the same end `get` reads from, so the consumer keeps seeing the freshest data.

```python
    if self.policy == "drop_oldest":
        self.dropped.append(self.items.popleft())
        self._push(item)
        return True
    if self.policy == "reject":
        self.rejected.append(item)
        return False
    fut = self.loop.future()
    self.putters.append((fut, item))
    yield fut
    return True
```

The single `yield fut` at the bottom is what makes `put` a generator. It runs only on the block path.

**Step 4: `get`, with the wakeup.** Pop first, then refill the freed slot from the oldest blocked producer.

```python
def get(self):
    if self.items:
        item = self.items.popleft()
        if self.putters:
            fut, waiting = self.putters.popleft()
            self._push(waiting)
            self.loop.resolve(fut, True)
        return item
    fut = self.loop.future()
    self.getters.append(fut)
    item = yield fut
    return item
```

Forget the `if self.putters:` block and nothing errors. The producers just never wake, and the run ends with them listed in `stuck_producers`.

## 8. Full solution

```python
# deque gives O(1) pops from the front, which every FIFO here needs
from collections import deque


# a bounded FIFO between producers and consumers, with a policy for when it is full
class BoundedQueue:
    # set up the queue, its two wait lists and the counters the judge reads
    def __init__(self, loop, capacity, policy):
        self.loop = loop  # the event loop that makes and resolves futures
        self.capacity = capacity  # the most items the queue may ever hold
        self.policy = policy  # what to do when full: block, drop_oldest or reject
        self.items = deque()  # the queued items, oldest on the left
        self.getters = deque()   # futures of waiting consumers
        self.putters = deque()   # (future, item) of blocked producers
        self.dropped = []  # items thrown away by drop_oldest, for the judge
        self.rejected = []  # items refused by reject, for the judge
        self.max_depth = 0  # the high-water mark of len(items)

    # the judge reads the current depth with len(q)
    def __len__(self):
        return len(self.items)  # only queued items count, not ones handed straight over

    # every append goes through here so max_depth is never missed
    def _push(self, item):
        self.items.append(item)  # newest item joins the back
        self.max_depth = max(self.max_depth, len(self.items))  # record a new high-water mark

    # producer side: add an item, waiting only if the policy is block and the queue is full
    def put(self, item):
        if self.getters:  # a consumer is parked, so the queue is empty: skip it entirely
            self.loop.resolve(self.getters.popleft(), item)  # hand the item to the oldest waiter
            return True  # delivered without waiting
        if len(self.items) < self.capacity:  # there is still room
            self._push(item)  # queue it
            return True  # accepted without waiting
        if self.policy == "drop_oldest":  # full, and fresh data matters more than old
            self.dropped.append(self.items.popleft())  # evict the stalest item
            self._push(item)  # the new item takes the freed slot
            return True  # the producer never waits under this policy
        if self.policy == "reject":  # full, and the caller should hear about it
            self.rejected.append(item)  # record the refused item
            return False  # tells the caller to answer 429 or retry later
        fut = self.loop.future()  # full under block: make something to wait on
        self.putters.append((fut, item))  # join the back of the blocked-producer line
        yield fut  # sleep until get() moves our item into the queue
        return True  # our item is queued now

    # consumer side: take the oldest item, waiting if the queue is empty
    def get(self):
        if self.items:  # something is queued, so no need to wait
            item = self.items.popleft()  # take the oldest item
            if self.putters:  # we just freed a slot in a full queue
                fut, waiting = self.putters.popleft()  # the producer that has waited longest
                self._push(waiting)  # move its item in now, so no newcomer can take the slot
                self.loop.resolve(fut, True)  # wake that producer; its put has succeeded
            return item  # hand the popped item to the consumer
        fut = self.loop.future()  # empty: make something to wait on
        self.getters.append(fut)  # join the back of the waiting-consumer line
        item = yield fut  # sleep until put() hands us an item
        return item  # the item that put() resolved our future with
```

## 9. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | crawler blocked 2 s, `max_depth` 2, 5 delivered | block policy, and `get` waking the blocked producer |
| Example 2 | `dropped = ['tick-2']`, 4 delivered | drop_oldest evicts the front, not the incoming item |
| Example 3 | `rejected = ['evt-3']`, 3 delivered | reject returns `False` and leaves the queue unchanged |
| block two producers fifo | items alternate `s-1, f-1, s-2, f-2, ...`; blocked 4.7 s and 5.7 s | blocked producers wake oldest first |
| block two consumers | 12 delivered, `makespan` 6, ingest blocked 2.2 s | hand-off to whichever consumer is idle, plus blocking |
| consumers wait first | `max_depth` 0; jobs go to a, b, c, a | `put` checks waiting consumers before capacity; getters are FIFO |
| drop oldest burst | `dropped` starts `['q-1', 'm-2', 'm-3', 'q-2', ...]` | eviction order across two interleaved producers |
| reject burst | `rejected = ['req-7', 'req-8', 'req-11', 'req-12']` | reject under load with two consumers |
| fast consumer never fills | `max_depth` 1, nobody blocked | the fast path never yields, and depth is counted even when the item is popped at once |
| three blocked producers | blocked 4.6, 5.0 and 5.4 s; 15 delivered | FIFO wakeup with three producers in line |

## 10. Complexity

Every `put` and `get` is O(1): a few deque operations and at most one `resolve`. Memory is O(capacity) for items plus O(P + C) for parked producers and consumers. That bound is the whole point. With `wrong_unbounded_buffer.py`, Example 1 reaches depth 3 on a capacity-2 queue, and in production that depth keeps growing until the pod is OOM-killed.

At scale, the two numbers to watch are queue depth and producer blocked time. Size capacity with Little's law: depth ≈ arrival rate × the wait you are willing to tolerate. A deeper queue doesn't add throughput. Rerunning Example 1 with capacity 1, 2, 5 and 10 gives the same `throughput` of 0.5 and `makespan` of 10 every time. Only the crawler's blocked time changes (4.0, 2.0, 0 and 0 s). The consumer sets the pace, and extra depth only moves the waiting from the producer into the queue.

## 11. If you got Wrong Answer

- **`stuck_producers` is non-empty and `delivered` is short** (Example 1 delivers 3 instead of 5). `get` pops but never wakes a blocked producer: the lost wakeup in `wrong_lost_wakeup.py`.
- **Extra `overflow` events and `blocked_s` of 0 under block.** You append instead of parking: `wrong_unbounded_buffer.py`, which reaches depth 3 in Example 1.
- **`dropped` holds the newest item** (`tick-4` instead of `tick-2` in Example 2). You discarded the incoming item: `wrong_drops_newest.py`.
- **"block two producers fifo" shows `p-files` where `p-search` was expected.** You wake producers with `putters.pop()` (newest first): `wrong_lifo_wakeup.py`.
- **"consumers wait first" gives `job-1` to `c`, not `a`.** You hand off with `getters.pop()`.
- **Event times are late, such as `w2`'s first `get` at 0.6 instead of 0.2 in "block two consumers".** `put` checks capacity before waiting consumers, so the item sits in the queue while a consumer sleeps.
- **A `put` appears before the matching `get`, or `max_depth` is 0 in "fast consumer never fills".** Your method yields on the fast path (for example a `yield None` at the top), which reorders tasks at the same virtual time.

## 12. Follow-ups an interviewer might ask

- *How does `asyncio.Queue` do this?* Exactly this way. `asyncio.Queue(maxsize)` keeps `_getters` and `_putters` deques of futures, and Go's buffered channels keep the same two wait queues. The block policy is the default in both.
- *How would you add a timeout to a blocked `put`?* Race the future against a timer. If the timer wins, remove `(fut, item)` from `putters` (or mark it cancelled so `get` skips it) and return `False`. The tricky part is cancelling after `get` has already moved the item in.
- *Which policy for which stream?* Block for work that must all be processed (ingestion, tool results). Drop-oldest for state where only the latest matters (prices, presence, progress). Reject for public APIs, answering 429 with `Retry-After`, which the caller handles as in problem 123 (token-bucket-rate-limiter).
- *How does backpressure cross the network?* Credit-based flow control: HTTP/2 and gRPC windows, Reactive Streams' `request(n)`, Kafka consumers pausing partitions. The consumer advertises how much it can take, and the producer never sends more.
- *What sits on the delivery side?* Fan-out to rate-limited channels with per-channel retries is problem 177 (rate-limited-fanout), and leased task queues with redelivery are problem 163 (agent-task-queue-leases).
