## 1. What the problem is really asking

Twenty browser tabs ask the same question at the same moment. Without help you send twenty identical completions to the provider and pay for all of them. You're putting a **single-flight** layer in front of the provider: while one call for a question is in progress, everyone else asking that exact question waits for it instead of making their own.

Under the story this is a **dictionary from a key to an in-progress task**:

- no entry for the key: start a task, store it, wait on it;
- an entry exists: wait on the same task;
- the task settles: remove the entry, so the next request starts fresh.

Everything hard about the problem is in two places. What goes **into the key** (the full identity of the answer), and **when the entry leaves** the dictionary (exactly when the upstream call settles, success or failure). It is not a cache. Nothing outlives the flight.

The judge records every upstream call (its time, the `request_id` that was sent, the tenant) and, for every request, the response id or error class it got plus its `start` and `end` time. So if you make one extra upstream call, reuse a finished answer, or hand one tenant another tenant's response, the output differs.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `loop` | the deterministic `EventLoop` from `gc_runtime` | `loop.spawn(gen)` starts a task and returns a `Task` |
| `upstream(request)` | returns a **generator** that makes one provider call | run it inside a task: `yield from self.upstream(request)` |
| `call(request)` | your generator; clients do `resp = yield from coalescer.call(req)` | return the response, or let the error propagate |
| `request["tenant"]`, `["model"]`, `["messages"]` | the parts that decide what the answer is | go into the key |
| `request["temperature"]` | `0.0` or something like `0.9` | `> 0` means bypass the coalescer entirely |
| `request["request_id"]` | a per-request label | **not** in the key |

The `EventLoop` rules you need, from `gc_runtime.py`:

- Inside a task, `yield 1.5` sleeps 1.5 virtual seconds. The fake upstream does exactly this for its latency.
- `r = yield task` parks you until `task` finishes. You resume with its return value, or its exception is thrown into you at the `yield`. If the task is already done, you resume immediately with its stored result.
- When a task finishes, the loop schedules every waiter at the current time, in the order they started waiting.

Three details are easy to miss:

- `messages` is a list of dicts. Two clients can send `{"role": "user", "content": ...}` and `{"content": ..., "role": "user"}`. The statement says these are the same request, so a plain `json.dumps` won't do. You need `sort_keys=True`.
- A sampled request (`temperature > 0`) neither **joins** an open flight nor **opens** one. It is not enough to give it its own key; it must not touch the dictionary at all.
- The constraint "no request arrives at exactly the instant an upstream call settles" removes the one ambiguous ordering, so you never have to decide whether a request at t=2.0 joins a flight that ends at t=2.0.

## 3. Trace the examples by hand

**Example 1.** Three acme requests for the same prompt at t=0, 0.5 and 1.0. The provider takes 2 s.

| t | event | `inflight` after |
|---|---|---|
| 0 | r1 arrives, no entry: spawn flight task F0 running `upstream(r1)`, then `yield F0` | `{K: F0}` |
| 0 | F0 starts: the upstream records call `{t: 0, request_id: "r1"}` and sleeps 2 s | `{K: F0}` |
| 0.5 | r2 arrives, entry found: `yield F0` | `{K: F0}` |
| 1.0 | r3 arrives, entry found: `yield F0` | `{K: F0}` |
| 2.0 | upstream returns `resp_0`; F0's `finally` deletes `K`; the loop wakes r1, r2, r3 | `{}` |

Output: one upstream call, and all three responses are `resp_0` with `end: 2`. The `start` values stay 0, 0.5 and 1. A coalesced request still waits for the remainder of the shared call, not for a whole call of its own.

**Example 3: the failure path.** The script is `[server error after 1.5 s, ok after 1 s]`. r1 opens the flight at t=0, r2 joins at 0.5. At t=1.5 the upstream raises `ServerError`. The flight's `finally` deletes the key, the exception becomes the task's error, and both waiters have `ServerError` raised to them at `end: 1.5`. At t=3 r3 arrives, finds no entry, and opens a new flight, which is upstream call 2 at `t: 3`, returning `resp_1` at t=4.

**The trickiest hidden case, "timeout shared then retry window".** Five initech requests, script `[timeout after 5 s, rate_limit after 1 s, ok after 1 s]`:

| request | arrives | joins | result | end |
|---|---|---|---|---|
| r1 | 0 | opens flight 1 | `TimeoutError_` | 5 |
| r2 | 4 | flight 1 | `TimeoutError_` | 5 |
| r3 | 5.5 | opens flight 2 | `RateLimitError` | 6.5 |
| r4 | 6 | flight 2 | `RateLimitError` | 6.5 |
| r5 | 7.5 | opens flight 3 | `resp_2` | 8.5 |

The upstream calls are at t=0 (r1), 5.5 (r3) and 7.5 (r5). Each failure is shared only by the requests that overlapped it, and the next arrival after a failure always makes a fresh attempt.

## 4. Key idea: the key is the full identity of the answer

Ask "what could make two responses differ?" and put all of it in the key:

```python
json.dumps([request["tenant"], request["model"], request["messages"]],
           sort_keys=True, separators=(",", ":"))
```

- **tenant.** Acme and globex pasting the same prompt must get separate calls. Sharing would hand one customer another customer's completion, a data leak rather than a cache miss. Example 2 tests it: two calls, `response_tenant` matches each request.
- **model.** A Haiku answer is not a Sonnet answer. "model is part of the key" fails if you drop it.
- **messages, canonicalised.** `sort_keys=True` sorts keys at every depth, so the flipped user message produces the same string.
- **not `request_id`.** It is different on every request, so including it would disable coalescing completely.

Temperature is handled before the key is even computed, which is why it doesn't need to be in it.

## 5. Key idea: the flight evicts itself, in a `finally`

The entry must disappear the moment the upstream call settles. The cleanest owner of that moment is the flight task itself:

```python
def _flight(self, k, request):
    try:
        return (yield from self.upstream(request))
    finally:
        del self.inflight[k]
```

The `finally` runs inside the generator as it returns or raises, which is *before* the loop's `_finish` schedules any waiter. So by the time anyone wakes, the dictionary is already clean.

Getting this wrong has two shapes:

- **Never evicting.** The dictionary becomes a cache with no expiry. In "no stale reuse after success", r3 at t=2.5 and r4 at t=2.6 find the finished task, `yield` it, resume instantly with the old `resp_0` and `end: 2.5`, and the second upstream call never happens.
- **Evicting only on success** (putting `del` after the `yield from` without `finally`). The failed task stays in the map, so every later identical request gets the cached exception immediately. In Example 3, r3 gets `ServerError` at `end: 3` with no upstream call.

## 6. Plan before you code

```
__init__: store loop and upstream; inflight = {}
call(request):
    if temperature > 0: return (yield from upstream(request))      # bypass
    k = canonical key of (tenant, model, messages)
    task = inflight.get(k)
    if no task: task = loop.spawn(_flight(k, request)); inflight[k] = task
    return (yield task)                                             # everyone waits, the first caller too
_flight(k, request):
    try: return (yield from upstream(request))
    finally: delete inflight[k]
```

| request | key in `inflight`? | action |
|---|---|---|
| `temperature > 0` | not looked at | call upstream inline |
| `temperature == 0` | no | spawn a flight, store it, wait on it |
| `temperature == 0` | yes | wait on the stored task |

## 7. Build it one piece at a time

**Step 1: the state.** One dictionary from key to `Task`.

```python
import json


class Coalescer:
    def __init__(self, loop, upstream):
        self.loop = loop
        self.upstream = upstream
        self.inflight = {}
```

**Step 2: the bypass.** Put it first, so a sampled request never reads or writes `inflight`.

```python
    def call(self, request):
        if request["temperature"] > 0:
            return (yield from self.upstream(request))
```

`return (yield from gen)` runs the upstream generator inline and hands its return value back to the client. An exception raised inside it propagates to the client unchanged, which is what the judge expects.

**Step 3: join or open a flight.**

```python
        k = self.key(request)
        task = self.inflight.get(k)
        if task is None:
            task = self.loop.spawn(self._flight(k, request), name="flight")
            self.inflight[k] = task
        return (yield task)
```

Store the task **before** yielding. A request arriving while you're parked must find it. The first caller also waits with `yield task` rather than running the upstream call inline. That way there is exactly one place where the call runs and one place where it cleans up, and every caller, first or not, receives the result the same way.

**Step 4: the flight and its eviction**, as in section 5.

## 8. Full solution

```python
import json  # canonical JSON turns the request's identity into a hashable string


class Coalescer:  # single flight: one upstream call per key while it is in progress
    def __init__(self, loop, upstream):  # the judge hands us the event loop and the provider call
        self.loop = loop  # the only scheduler we may spawn tasks on
        self.upstream = upstream  # upstream(request) is a generator making one provider call
        self.inflight = {}  # key -> Task of the one upstream call for that key

    def key(self, request):  # everything that can change the answer, and nothing else
        # tenant stops cross-customer leaks; model and messages define the answer; sort_keys ignores key order
        return json.dumps([request["tenant"], request["model"], request["messages"]],
                          sort_keys=True, separators=(",", ":"))

    def call(self, request):  # clients run this with `yield from`, so it must be a generator
        if request["temperature"] > 0:  # sampled outputs are meant to differ, so never share them
            return (yield from self.upstream(request))  # its own call, without touching the map
        k = self.key(request)  # identical deterministic requests produce the same string
        task = self.inflight.get(k)  # is a call for this exact request already running?
        if task is None:  # no: this caller opens the flight
            task = self.loop.spawn(self._flight(k, request), name="flight")  # one upstream call, in its own task
            self.inflight[k] = task  # store it before yielding, so overlapping requests find it
        return (yield task)  # everyone, first caller included, waits for the shared result or error

    def _flight(self, k, request):  # the task body that owns the upstream call and its cleanup
        try:  # the finally below must run whether the call succeeds or fails
            return (yield from self.upstream(request))  # this result goes to every waiter
        finally:  # runs before any waiter resumes
            del self.inflight[k]  # close the flight: no stale reuse, no cached errors
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | 1 upstream call; all three get `resp_0` at t=2 | the basic join path |
| Example 2 | 2 calls; acme gets `resp_0`, globex gets `resp_1` | tenant is in the key |
| Example 3 | r1, r2 get `ServerError` at 1.5; r3 makes call 2 and gets `resp_1` at 4 | errors are shared, then evicted |
| no stale reuse after success | calls at t=0 and t=2.5; r3 and r4 share `resp_1`, ending at 4.5 | eviction after success |
| sampled requests bypass | 3 calls; r2, r3 get their own `resp_1`, `resp_2`; r4 joins r1's `resp_0` | `temperature > 0` skips the map |
| sampled request does not join an open flight | r2 makes its own call at 0.5 and ends at 1, before r1's 3 s flight | bypass happens before the lookup |
| model is part of the key | haiku r1 and r3 share `resp_0`; sonnet r2 gets `resp_1` | model in the key |
| dict key order does not matter | 1 call; both get `resp_0` | `sort_keys=True` |
| timeout shared then retry window | calls at 0, 5.5, 7.5; two timeouts, two rate limits, then `resp_2` | each failure closes its flight |
| interleaved keys and tenants | 6 calls; a1/a3 share, g1/g2 share, a4 opens a new deploys flight at 1.1 | several open keys at once |
| failure on one key leaves others alone | incidents fail at t=1; deploys still succeed at 1.6; r5 retries incidents at 2 | flights are independent |
| thundering herd | 40 requests, 6 calls at 0, 0.07, 1.12, 1.19, 2.24, 2.31 | two tenants, three waves each |

In "thundering herd" the requests alternate acme and globex every 0.07 s. Each wave's flight lasts 1 s, so the first request after a flight settles opens the next one: r16 (acme) at 1.12, r17 (globex) at 1.19. The first four flights each serve 8 requests and the last two serve 4.

## 10. Complexity

Each `call` costs one `json.dumps` of the messages, O(m) in their total size, plus O(1) dictionary work. The dictionary holds at most one entry per distinct key currently in flight, so memory is bounded by concurrent distinct requests, not by traffic. Each waiter is one entry in the task's waiter list.

The win at scale is the ratio of requests to upstream calls. In the herd case 40 requests make 6 calls. At provider prices that is the difference between paying for 40 completions and paying for 6, and the same goes for rate-limit headroom. The cost is that a coalesced error hits every waiter at once, so the retry policy above the coalescer has to expect correlated failures.

## 11. If you got Wrong Answer

- **Example 2 shows globex getting `resp_0` with `response_tenant: "acme"`.** The tenant is missing from your key. "interleaved keys and tenants" and "thundering herd" fail the same way.
- **"dict key order does not matter" shows two upstream calls.** You serialise messages without `sort_keys=True`.
- **"model is part of the key" shows sonnet r2 getting the haiku answer.** The model is missing from the key (`wrong_key_without_model.py`).
- **In Example 3, r3 gets `ServerError` at `end: 3` with only one upstream call.** You evict only on success. Move the `del` into a `finally`.
- **In "no stale reuse after success", r3 and r4 get `resp_0` instantly at 2.5 and 2.6.** You never evict.
- **In "sampled requests bypass", r2 and r3 get `resp_0`.** You coalesce sampled requests. Return early when `temperature > 0`.
- **Runtime Error "some requests never completed".** A client task crashed before recording its result. The starter does this: `call` returns `None`, so the client's `resp["id"]` fails. Returning the `Task` itself instead of `yield task` fails the same way.

## 12. Follow-ups an interviewer might ask

- *How is this different from a cache?* Coalescing only shares a call while it is in flight. A request one millisecond after settlement goes upstream again. Put an exact or semantic cache behind it (problem 127, semantic-cache) to cover that gap.
- *What if the first caller disconnects?* Keep the flight running for the other waiters. Count waiters and cancel the upstream call only when the count reaches zero. Problem 120 (oauth-single-flight-refresh) uses the same single-flight shape for token refreshes.
- *How do you coalesce across replicas?* An in-process map only collapses requests on one box. Route by key with consistent hashing (problem 175, consistent-hashing-sessions) so identical requests land on the same replica, or hold a short Redis lock per key.
- *What about streaming responses?* A late joiner has missed the tokens already sent. You either buffer the stream and replay it to new waiters, or don't coalesce streams at all.
- *What does Go do?* `golang.org/x/sync/singleflight` is the reference design: `Do` runs or joins, and `Forget` evicts a key early. Envoy and Nginx (`proxy_cache_lock`) call the same thing request collapsing.
