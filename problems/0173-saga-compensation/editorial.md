## Approach

A saga replaces one distributed transaction with a chain of local ones, each paired with a compensation. Crash safety comes from one idea: **the journal is the state**. Write the intent before every side effect and the outcome after it, and rebuild everything from the journal on start-up. Then `run_saga` is just `resume_saga` on an empty journal.

```python
for r in journal.records():          # rebuild: done results, started, failed, comps closed
    ...
if not failed:
    for s in steps:
        if s in done: continue
        if s not in started: journal.append({"type": "step_started", "step": s})
        try:
            result = services.do(s, "%s:%s" % (saga_id, s))   # same key on every run
        except ToolError as e:
            journal.append({"type": "step_failed", "step": s, "error": str(e)}); failed = True; break
        journal.append({"type": "step_done", "step": s, "result": result}); done[s] = result
for s in reversed([s for s in steps if s in done]):            # newest first, only what happened
    ...retry undo with sleeps 1, 2, 4, ...; comp_done or comp_failed
journal.append({"type": "saga_finished", "status": status})
```

Each crash point has a different recovery:

| crash | journal shows | resume does |
|---|---|---|
| before `do` | `step_started` only | `do` once, as if new |
| after `do` (the effect happened) | `step_started` only | `do` with the same key; the provider returns the stored result |
| before or after `undo` | `comp_started` only | `undo` again; cancel is idempotent |

The idempotency key is what makes "after `do`" safe. The journal cannot tell whether the call landed, so the call has to be safe to repeat.

## Common mistakes

- **A key that changes between runs** (attempt number, a fresh UUID, the journal length). Every crash after a charge becomes a second charge.
- **Compensating in forward order.** You cancel the hotel while the payment is still captured, and downstream systems that assume LIFO (release the hold, then the reservation) break.
- **Undoing the step that failed.** A declined charge has nothing to refund; calling refund on it errors or, worse, refunds a different charge.
- **Treating `comp_started` as done.** A crash mid-undo leaves a live reservation that nobody will ever cancel.
- **Restarting from scratch on resume.** Even with idempotent providers it repeats work, re-sends emails that have no idempotency, and duplicates journal entries.

## Production notes

- Temporal, AWS Step Functions and LangGraph checkpoints all persist an event history like this journal and replay it on a new worker. Temporal's saga pattern is a list of compensations pushed as each activity completes and run in reverse.
- Stripe, Adyen and most booking APIs accept an `Idempotency-Key`. Derive it from the workflow id and step name, never from attempt counters.
- A `stuck` saga needs a human: page on-call or open a ticket with the journal attached, and keep retrying the compensation on a slow schedule in the background.
- Put irreversible steps (sending email, shipping) last, as the "pivot". Everything before it must be compensable; everything after it must be retryable until it succeeds.
- Pair with `transactional-outbox` (172) for getting the journal write and the event publish into one atomic step, and `durable-workflow-replay` (111) for replaying non-side-effecting steps.
