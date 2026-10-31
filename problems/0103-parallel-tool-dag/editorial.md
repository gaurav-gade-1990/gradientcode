## Approach

This is event-driven list scheduling. Keep a status per node, and every time a slot frees up (plus once at the start) launch the ready nodes in id order until the slots are full.

```python
def fill():
    ready = sorted(nid for nid, st in status.items()
                   if st == "pending" and all(status[d] == "ok" for d in deps[nid]))
    for nid in ready:
        if running[0] >= max_concurrency:
            break
        status[nid] = "running"
        running[0] += 1
        loop.spawn(worker(nid))

def worker(nid):
    try:
        yield loop.spawn(run_tool(nid))
        status[nid] = "ok"
    except ToolError:
        status[nid] = "failed"
        cancel_descendants(nid)   # DFS over children, pending -> cancelled
    running[0] -= 1
    fill()
```

Each wrapper task releases its own slot and refills, so a fast branch never waits on a slow sibling. Sorting the ready set makes the schedule independent of the order the planner listed the nodes in.

## Common mistakes

- **Level-by-level barriers.** `gather` on each topological layer waits for the slowest tool in the layer. In the "level barrier" case the fast branch's summary could start at t=1, but a barrier holds it until t=4.
- **Ignoring the limit.** Starting every ready node at once turns a fan-out of 50 into 50 simultaneous API calls and a burst of 429s.
- **Cancelling everything on failure.** A failed shipping lookup shouldn't stop the loyalty-offer branch.
- **Cancelling only direct children.** Grandchildren then wait forever on a dep that will never be `ok`, and the run never terminates.
- **Iterating in input order.** Two runs of the same plan behave differently when the planner reorders its JSON.

## Production notes

- Anthropic and OpenAI both return parallel tool calls in one assistant turn; the client decides how to run them. LangGraph's `Send` fan-out and Temporal child workflows are the heavier versions of this executor.
- Use a per-provider concurrency limit (an `asyncio.Semaphore`, or a token bucket from problem 123) rather than one global number, since a CRM and an LLM have different rate limits.
- Record start and end per node as tracing spans; problem 112 (trace-critical-path) turns exactly this data into a critical path.
- Real executors also add per-node timeouts and retries (problem 124) before declaring a node failed.
