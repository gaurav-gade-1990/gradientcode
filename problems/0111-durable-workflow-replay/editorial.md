## Approach

The workflow code is deterministic, so replaying the same inputs reproduces the same sequence of commands. The history then acts as a memo table indexed by sequence number, and the only live work is past its end.

```python
gen, seq, value, error = workflow(wf_input), 0, None, None
while True:
    try:
        name, args = gen.throw(error) if error is not None else gen.send(value)
    except StopIteration as stop:
        if seq < len(history):
            raise NonDeterminismError(...)
        return stop.value
    value, error = None, None
    if seq < len(history):                              # replay
        rec = history[seq]
        if rec["activity"] != name or canon(rec["args"]) != canon(args):
            raise NonDeterminismError(...)
        if rec["status"] == "completed":
            value = rec["result"]
        else:
            error = ToolError(rec["error"])
    else:                                               # live
        try:
            value = activities[name](**args)
            history.append(completed_event)             # durable before resuming
        except ToolError as e:
            history.append(failed_event)
            error = e
    seq += 1
```

The determinism check is what makes replay safe. Feeding recorded results to code that now asks for something else gives each step the wrong result.

## Common mistakes

- **Rerunning from the top.** Without replay, every crash charges the card again.
- **Matching by position only.** After a deploy that inserts a step, the shipment's tracking number is fed into the email step. Nothing crashes; the data is just wrong.
- **Retrying recorded failures.** A failure is part of history too. Re-running a declined charge on every resume both changes the outcome and repeats a side effect.
- **Buffering events.** Writing history only at the end means a crash loses the whole run's progress.
- **Ignoring leftover history.** Code that dropped a step "finishes" early and hides the change.

## Production notes

- This is Temporal's and Cadence's core loop (Azure Durable Functions, Restate and DBOS work the same way). Workflow code may not read the clock, random numbers or the network directly; those go through activities or SDK calls (`workflow.now()`, side effects) so they're recorded too.
- Use versioning to change running workflows safely (Temporal's `patched()` / `GetVersion`). Old histories take the old branch, and new runs take the new one.
- A live activity can run and then crash before its event is recorded, so activities are still **at-least-once**. Give side-effecting ones idempotency keys (problem 119), for example the workflow id plus seq.
- Agent frameworks use the same idea for long-running agents: LangGraph checkpointers, and the OpenAI Agents SDK with Temporal. Pair with problem 106 (plan-and-execute-replan) and problem 173 (saga-compensation).
