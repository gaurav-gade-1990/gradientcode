## Approach

Two phases. First route everything with a deterministic `min`, then drain the queues round-robin so one busy worker can't starve the others.

```python
def pick(tid):
    options = [n for n in names if needs[tid] <= skills[n] and n not in failed_on[tid]]
    return min(options, key=lambda n: (len(queue[n]), n)) if options else None

for t in subtasks:                      # 1. assign
    w = pick(t["id"])
    (queue[w].append(t["id"]) if w else mark_unroutable(t))

while any(queue.values()):              # 2. rounds
    for n in names:                     # sorted names
        if queue[n]:
            tid = queue[n].pop(0)
            try:
                done(tid, n, execute(n, tid))
            except ToolError:
                failed_on[tid].add(n)
                nxt = pick(tid) if attempts[tid] < 2 else None
                (queue[nxt].append(tid) if nxt else mark_failed(tid, n))

return [results[t["id"]] for t in subtasks]   # 3. original order
```

`needs <= skills` is a subset test: the worker has to cover every requirement. The `failed_on` set is what keeps a retry away from a worker that just crashed.

## Common mistakes

- **Any-skill matching.** A Spanish translation lands on an English-only writer and comes back in English.
- **Ties by config order.** Routing changes whenever someone reorders the worker list, which makes incidents hard to reproduce.
- **Retrying on the same worker.** Its queue just got shorter, so a pure least-loaded pick often chooses it again.
- **No retry cap.** A poison task (bad input, not a bad worker) fails on every worker in turn.
- **Results in completion order.** The supervisor's final answer assembles sections in the wrong order.

## Production notes

- This is the "supervisor" pattern in LangGraph and the manager or orchestrator agent in CrewAI and the OpenAI Agents SDK, with one difference: a production supervisor often lets an LLM choose the worker. Keep a deterministic router like this one as the fallback and for the cases the policy can decide on its own (skills, load, tenant pinning).
- Load is usually measured as in-flight requests or queued tokens, not task count, and it comes from a shared store (Redis) when workers are separate processes.
- Distinguish worker errors (reassign) from task errors (a 400 or a validation failure, so fail fast). That is the same retryable vs non-retryable split as problem 124.
- Pair with problem 105 (agent-handoff-context) for what context each worker receives, and problem 108 (multi-agent-vote) when several workers answer the same subtask.
