When a popular dashboard loads, dozens of browser tabs ask your gateway the same question at once ("summarize today's incidents") and you pay for every identical completion. Put a single-flight coalescer in front of the provider: identical requests that overlap in time share **one** upstream call.

Implement `class Coalescer` on the deterministic `EventLoop` from `gc_runtime`.

- `Coalescer(loop, upstream)`: `loop` is the `EventLoop`. `upstream(request)` returns a **generator** (an EventLoop task body) that makes one provider call and returns the response dict or raises a `gc_runtime` error.
- `call(request)` is a generator. The judge's client tasks use it as `response = yield from coalescer.call(request)`. It must return the response or raise the error.

A request is a dict `{"request_id": str, "tenant": str, "model": str, "messages": [...], "temperature": float}`.

| rule | |
|---|---|
| same flight | Two requests share a flight when `temperature == 0` for both and they have equal `tenant`, `model` and `messages`. `messages` are compared as JSON values, so dict key order does not matter. `request_id` is ignored. |
| first caller | If no flight is open for the key, spawn one task with `loop.spawn(...)` that runs `upstream(request)` with **this** request. |
| later callers | If a flight is open, wait for it. Do not call `upstream`. |
| success | Every waiter receives the flight's response. |
| failure | Every waiter has the flight's exception raised to it. |
| settle | The flight closes the moment its upstream call returns or raises. A request that arrives after that starts a new flight, even with the same key, so there is no stale reuse and no cached errors. |
| sampled | A request with `temperature > 0` never joins or opens a flight. It calls `upstream` itself with `yield from upstream(request)`. |

To wait for a task inside a generator, use `result = yield task`. The loop resumes you with the task's result or raises its exception. `yield from gen` runs another generator inline.

The judge grades every upstream call (time, which `request_id` was sent, tenant), and for every request the response it got (or the error), when it started and when it finished.

**Constraints**

- `1 <= len(requests) <= 60`, arrival times in `[0, 100]` seconds
- No request arrives at exactly the instant an upstream call settles
- Use only the `loop` you're given for spawning; no threads, `asyncio` or `time`
