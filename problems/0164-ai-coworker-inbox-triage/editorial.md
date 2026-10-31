## Approach

This is a discrete-event simulation with an earliest-deadline-first dispatcher. Nothing changes between arrivals and completions, so jump from one decision time to the next with a heap of finish times.

At each time `t`:

1. pop every finish at `t` and free its capacity,
2. append the arrivals at `t`,
3. sort pending by `(deadline, arrives, id)` and walk it once.

For each request in the walk there are three outcomes:

```python
best_case = t + min(r["minutes"] / c["speed"] for c in skilled)
if not skilled:            escalate("no_skill")
elif best_case > deadline: escalate("sla")         # nobody can save it
elif free_on_time:         assign(min(free_on_time, key=(finish, active, name)))
else:                      keep waiting            # someone could, once free
```

**Why EDF?** On one machine, earliest deadline first meets every deadline whenever any order can. With several coworkers it is no longer optimal, but it is the standard, explainable greedy, and it never makes a long-deadline request starve an urgent one.

**Why escalate on the best case?** Escalation pages a human. Do it when the SLA is truly lost, not merely when everyone happens to be busy right now. The request waits as long as some skilled coworker, starting now, could still make it, and it is re-checked at every later decision time.

## Common mistakes

- **FIFO instead of EDF.** A 5-minute urgent request queues behind a long, relaxed one and breaches its SLA.
- **Assigning without a feasibility check.** The coworker accepts work it can't finish in time. The breach is discovered at the deadline instead of being escalated while a human could still help.
- **Escalating whenever nobody is free.** Every burst pages the on-call humans, even though a fast coworker frees up a minute later. Alert fatigue follows.
- **Picking the first free coworker by name.** A slow coworker takes the request while a faster one sits idle, which pushes later requests past their deadlines.

## Production notes

- Zendesk, Salesforce Omni-Channel and ServiceNow route on skills, capacity and SLA timers the same way. AI-coworker platforms (Sierra, Decagon, Agentforce) add a confidence check: route to a human when the agent's own confidence is low, not just when time runs out.
- In a real system the durations are estimates. Use a p90 handling time per (skill, coworker), and re-check feasibility when an assignment runs long instead of trusting the estimate made at assignment time.
- Escalation should hand over context (the transcript, what was tried) so the human doesn't start from zero. See `agent-handoff-context`.
- Durable assignment needs leases so a crashed worker's request comes back (`agent-task-queue-leases`), and approvals for risky actions (`human-approval-gates`).
