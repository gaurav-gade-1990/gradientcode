Your company deploys AI coworkers (a billing agent, a refunds agent, a contracts agent) that pick up requests from a shared inbox. Each request has an SLA. When no coworker can meet it, the request must go to a human right away instead of silently breaching. Write the dispatcher and simulate it.

`triage(coworkers, requests)` simulates the inbox in virtual minutes.

- A **coworker** is `{"name", "skills": [str], "capacity": int, "speed": float}`. It works on up to `capacity` requests at once. A request of `minutes` work takes `minutes / speed` on it.
- A **request** is `{"id", "arrives", "skill", "minutes", "deadline"}`. `deadline` is an absolute time; finishing exactly at it meets the SLA.

**Simulation.** The only decision times are request arrivals and assignment finish times. At each decision time `t`, in increasing order:

1. Every coworker assignment finishing at `t` completes and frees one unit of capacity.
2. Requests arriving at `t` join the pending queue.
3. Walk the pending queue **once**, in order of `(deadline, arrives, id)` (earliest deadline first). For each request:

| case | action |
|---|---|
| no coworker has the skill | escalate, reason `"no_skill"` |
| `t + minutes / speed > deadline` even for the **fastest** skilled coworker | escalate, reason `"sla"` |
| some skilled coworker has free capacity and would finish by the deadline | assign it (see below) |
| otherwise | leave it pending for a later decision time |

Choose among the free, on-time skilled coworkers by earliest finish time, then fewest active assignments (before this one), then name. Assignments made earlier in the same walk count toward capacity and active counts.

Return

```
{"events": [...], "assigned": int, "escalated": int, "busy_minutes": {name: float}}
```

`events` lists, in the order they happen, `{"t", "request", "action": "assign", "coworker", "finish"}` and `{"t", "request", "action": "escalate", "reason"}`. `busy_minutes` maps every coworker name (sorted) to the total duration of the work assigned to it.

**Constraints**

- `1 <= len(coworkers) <= 10`, `0 <= len(requests) <= 300`, `1 <= capacity <= 5`
- Speeds are powers of two (`0.25` to `4`), and times and minutes are integers, so all times are exact floats.
- `requests` may be in any order. Ids are unique.
