## 1. What the problem is really asking

A shared inbox feeds requests to a team of AI coworkers. Each request has a skill, an amount of work and a deadline. Your dispatcher decides, moment by moment, who takes what, and when a request can no longer make its SLA, it hands it to a human straight away instead of letting it breach quietly.

Under the story this is a **discrete-event simulation with an earliest-deadline-first (EDF) dispatcher**:

- Time doesn't tick minute by minute. Nothing can change except when a request **arrives** or an assignment **finishes**, so you jump from one of those moments to the next, using a heap of finish times.
- At each moment you walk the waiting requests in deadline order and give each one of three outcomes: escalate it, assign it, or leave it waiting.

The judge compares the full `events` list (every assign and escalate, with its time, coworker and finish), the two counts, and `busy_minutes` per coworker. So the order of events matters, not just who ends up doing what.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| coworker `name` | e.g. `"billing-bot"` | the tie-breaker of last resort, and the `busy_minutes` key |
| `skills` | list of skills | who is *skilled* for a request |
| `capacity` | requests it can work on at once | compare with its active count |
| `speed` | work rate | a request takes `minutes / speed` on it |
| request `arrives` | when it enters the queue | an event time |
| `minutes` | work needed at speed 1 | duration depends on who takes it |
| `deadline` | absolute time | finishing exactly at it is on time |

Three details are easy to miss:

- **Escalating for `"sla"` uses the fastest skilled coworker, busy or not.** The question is "could anyone, starting right now, still make it?" If yes, the request waits, even if every skilled coworker is busy at this moment. Only when even the best case misses does a human get paged.
- **The choice among free coworkers is by earliest finish, then fewest active assignments, then name.** Not by name alone, and not by speed alone (speed and finish time are the same thing here, but the load tie-break is extra).
- **Assignments made earlier in the same walk count.** If `billing-bot` has capacity 2 and takes one request, the next request in the same walk sees it with 1 active.

## 3. Trace Example 2 by hand

The team is `billing-bot` (billing, refunds; capacity 2; speed 1), `refunds-pro` (refunds; capacity 1; speed 2) and `contracts-ai` (contracts, billing; capacity 1; speed 0.5). Only `contracts-ai` does contracts, and at speed 0.5 every 20-minute request takes it **40 minutes**.

| t | what happens first | pending, in `(deadline, arrives, id)` order | outcome |
|---|---|---|---|
| 0 | T-10 arrives | T-10 (dl 40) | 0 + 40 = 40 ≤ 40: assign to contracts-ai, finish 40 |
| 5 | T-11 and T-12 arrive | T-12 (dl 50), T-11 (dl 90) | T-12: best case 5 + 40 = 45 ≤ 50, but contracts-ai is busy, so **wait**. T-11: also wait |
| 40 | contracts-ai finishes T-10 | T-12 (dl 50), T-11 (dl 90) | T-12: best case 40 + 40 = 80 > 50, **escalate `sla`**. T-11: 80 ≤ 90, assign, finish 80 |

The events are:

```python
{"t": 0,  "request": "T-10", "action": "assign",   "coworker": "contracts-ai", "finish": 40}
{"t": 40, "request": "T-12", "action": "escalate", "reason": "sla"}
{"t": 40, "request": "T-11", "action": "assign",   "coworker": "contracts-ai", "finish": 80}
```

Two things to notice. At `t = 5`, T-12 is *not* escalated, because it could still make it if someone were free. And at `t = 40` the escalation of T-12 and the assignment of T-11 happen in the same walk, in deadline order. `busy_minutes` for contracts-ai is 40 + 40 = 80.

**Example 1** shows the coworker choice. At `t = 0`, T-2 (refunds, 30 minutes, deadline 40) goes to `refunds-pro` (finish 15) rather than `billing-bot` (finish 30), because earlier finish wins. Then T-1 (deadline 60) finds `refunds-pro` full at capacity 1 and goes to `billing-bot`, finishing at 30. T-3 needs `legal`, which nobody has, so it's escalated with `no_skill`.

**The trickiest hidden case, "wait for the fast one".** Two refunds coworkers: `slow` (capacity 3, speed 0.25) and `fast` (capacity 1, speed 4).

| t | event | decision |
|---|---|---|
| 0 | R1 arrives (40 min, dl 20) | fast finishes at 10, slow at 160: assign fast, finish 10 |
| 1 | R2 arrives (20 min, dl 20) | best case is fast: 1 + 5 = 6 ≤ 20, so no escalation. slow would finish at 81 > 20, so it isn't an on-time choice. fast is busy: **wait** |
| 2 | R3 arrives (4 min, dl 200) | walk: R2 still waits; R3 goes to slow, finish 2 + 16 = 18 |
| 10 | fast finishes R1 | R2: 10 + 5 = 15 ≤ 20, assign fast, finish 15 |

R2 waits nine minutes for the fast coworker and still makes its deadline. A dispatcher that escalates whenever no on-time coworker is free right now would have paged a human at `t = 1` for nothing.

## 4. Key idea: earliest deadline first, walked once

Why sort the queue by deadline? Look at "edf beats fifo", with one coworker `solo` (capacity 1, speed 1) and four 10-minute requests: A (arrives 0, deadline 100), B (0, 30), C (1, 21), D (2, 45).

| order | schedule | result |
|---|---|---|
| EDF | B 0–10, C 10–20, D 20–30, A 30–40 | all four on time |
| FIFO (`arrives`, `id`) | A 0–10, B 10–20, then C at 20 needs to finish by 21 | C escalated `sla` |

On a single machine, EDF meets every deadline whenever any order can. With several coworkers it's no longer guaranteed to be optimal, but it's the standard, explainable greedy, and it never lets a relaxed request starve an urgent one.

"Walk the queue once" means you don't loop until nothing changes. Each request is considered exactly once per decision time. A request left waiting is looked at again at the next arrival or finish, which is the only moment its situation can change.

## 5. Key idea: three outcomes, checked in this order

| check | outcome | why it comes here |
|---|---|---|
| no coworker has the skill | escalate `no_skill` | nothing will ever change that |
| `t + min(minutes / speed over skilled) > deadline` | escalate `sla` | even the best case misses, so waiting can only make it worse |
| some skilled coworker is free **and** would finish by the deadline | assign | pick by `(finish, active, name)` |
| otherwise | wait | someone could make it, once free |

The "and would finish by the deadline" part is what separates this from a simple router. Example 3 shows it at the boundary: T-21 needs 10 minutes and has 9, so it's escalated at `t = 0`. T-20 needs 10 minutes and has 10: finishing exactly at the deadline is on time, so it's assigned with `finish: 10`. That's `<=`, not `<`.

Can a waiting request get stuck forever? No. It only waits when some skilled coworker could finish it in time, and that coworker is busy, so there's a pending finish on the heap. That finish is a future decision time, and at it the request is either assigned or escalated. So the simulation loop can run "while there are arrivals left or finishes on the heap".

## 6. Plan before you code

```
arrivals = requests sorted by (arrives, id); i = 0
finishing = heap of (finish, seq, name); active[name] = 0; busy[name] = 0
while arrivals remain or finishing is non-empty:
    t = the earlier of the next arrival and the next finish
    pop every finish at t: active[name] -= 1
    move every arrival at t into pending
    sort pending by (deadline, arrives, id)
    for r in pending:
        skilled = coworkers with r.skill
        none              -> escalate no_skill
        best case late    -> escalate sla
        free and on time  -> assign min by (finish, active, name); push finish
        else              -> keep r for next time
    pending = the kept ones
return events, counts, busy_minutes sorted by name
```

## 7. Build it one piece at a time

**Step 1: state and the next decision time.** Sort arrivals once and move an index through them. The heap's `seq` counter breaks ties between equal finish times, so Python never tries to compare names, and pops are deterministic:

```python
    finishing = []                       # heap of (finish time, seq, coworker)
    arrivals = sorted(requests, key=lambda r: (r["arrives"], r["id"]))
    ...
    while i < len(arrivals) or finishing:
        t = float(min(arrivals[i]["arrives"] if i < len(arrivals) else float("inf"),
                      finishing[0][0] if finishing else float("inf")))
```

**Step 2: free, then admit.** Finishes at `t` come before arrivals at `t`, and both come before the walk, so a coworker that finishes at `t` can take work arriving at `t`. "same time completion and arrival" depends on the walk seeing the freed capacity: X finishes at 10 just as Y arrives, and Z (waiting since 3) wins the slot because of its earlier arrival with the same deadline 15.

```python
        while finishing and finishing[0][0] == t:
            _, _, name = heapq.heappop(finishing)
            active[name] -= 1
        while i < len(arrivals) and arrivals[i]["arrives"] == t:
            pending.append(arrivals[i])
            i += 1
```

**Step 3: the walk.** The escalation test uses every skilled coworker; the assignment test uses only the free, on-time ones:

```python
        for r in pending:
            skilled = [c for c in coworkers if r["skill"] in c["skills"]]
            if not skilled:
                ...  # escalate no_skill
            if t + min(duration(c, r) for c in skilled) > r["deadline"]:
                ...  # escalate sla
            free = [c for c in skilled
                    if active[c["name"]] < c["capacity"] and t + duration(c, r) <= r["deadline"]]
```

**Step 4: choose and record.** `active` is read before you increment it, which is the "fewest active assignments before this one" rule. In "choose earliest finish then load then name", `alpha` and `zeta` both finish at 4: B0 goes to `alpha` by name, B1 to `zeta` because `alpha` now has one active, and they alternate until both are full, so B6 goes to the slower `beta`.

```python
            c = min(free, key=lambda c: (t + duration(c, r), active[c["name"]], c["name"]))
```

## 8. Full solution

```python
import heapq  # a min-heap of finish times gives the next completion in O(log n)


def triage(coworkers, requests):  # simulate the inbox and return every dispatch decision
    by_name = {c["name"]: c for c in coworkers}  # every coworker, keyed by name, for the final report
    active = {c["name"]: 0 for c in coworkers}  # requests each coworker is working on right now
    busy = {c["name"]: 0.0 for c in coworkers}  # total minutes of work assigned to each
    finishing = []  # heap of (finish time, seq, coworker): the future completion events
    arrivals = sorted(requests, key=lambda r: (r["arrives"], r["id"]))  # input may be in any order
    pending, events, seq, i = [], [], 0, 0  # waiting requests, the log, a heap tie-breaker, next arrival

    def duration(c, r):  # how long request r takes on coworker c
        return r["minutes"] / c["speed"]  # faster coworkers finish sooner

    while i < len(arrivals) or finishing:  # stop once nothing can arrive or finish any more
        # the next decision time is the earlier of the next arrival and the next completion
        t = float(min(arrivals[i]["arrives"] if i < len(arrivals) else float("inf"),
                      finishing[0][0] if finishing else float("inf")))
        while finishing and finishing[0][0] == t:  # step 1: every assignment ending now completes
            _, _, name = heapq.heappop(finishing)  # take one finished assignment off the heap
            active[name] -= 1  # its coworker gets one unit of capacity back
        while i < len(arrivals) and arrivals[i]["arrives"] == t:  # step 2: arrivals at t join the queue
            pending.append(arrivals[i])  # it waits with the others
            i += 1  # move to the next arrival
        pending.sort(key=lambda r: (r["deadline"], r["arrives"], r["id"]))  # step 3: earliest deadline first
        still = []  # requests that keep waiting after this walk
        for r in pending:  # walk the queue exactly once
            skilled = [c for c in coworkers if r["skill"] in c["skills"]]  # who could ever do it
            if not skilled:  # nobody has the skill, so waiting can't help
                events.append({"t": t, "request": r["id"], "action": "escalate", "reason": "no_skill"})  # send it to a human
                continue  # it's handled; look at the next request
            if t + min(duration(c, r) for c in skilled) > r["deadline"]:  # even the fastest, starting now, is late
                events.append({"t": t, "request": r["id"], "action": "escalate", "reason": "sla"})  # SLA is lost: escalate now
                continue  # it's handled; look at the next request
            # free skilled coworkers that would still finish by the deadline
            free = [c for c in skilled if active[c["name"]] < c["capacity"] and t + duration(c, r) <= r["deadline"]]
            if not free:  # someone could make it, but nobody suitable is free right now
                still.append(r)  # keep waiting until the next arrival or completion
                continue  # look at the next request
            c = min(free, key=lambda c: (t + duration(c, r), active[c["name"]], c["name"]))  # earliest finish, then least loaded, then name
            finish = t + duration(c, r)  # when this assignment will complete
            active[c["name"]] += 1  # later requests in this walk see the reduced capacity
            busy[c["name"]] += duration(c, r)  # add the work to its total
            seq += 1  # a fresh tie-breaker so equal finish times pop in assignment order
            heapq.heappush(finishing, (finish, seq, c["name"]))  # schedule the completion as a future decision time
            events.append({"t": t, "request": r["id"], "action": "assign", "coworker": c["name"], "finish": finish})  # log the assignment
        pending = still  # only the waiting ones carry over
    assigned = sum(1 for e in events if e["action"] == "assign")  # count assignments from the log
    # every other event is an escalation; busy_minutes lists every coworker by sorted name
    return {"events": events, "assigned": assigned, "escalated": len(events) - assigned,
            "busy_minutes": {name: busy[name] for name in sorted(by_name)}}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | T-2 to refunds-pro (finish 15), T-1 to billing-bot (30), T-3 `no_skill` | earliest-finish choice, capacity 1, the no-skill branch |
| Example 2 | T-12 waits at 5, escalated `sla` at 40; T-11 assigned at 40 | wait while the best case is feasible, escalate when it isn't |
| Example 3 | T-21 `sla` at 0; T-20 assigned with finish 10 | finishing exactly at the deadline is on time |
| empty inbox | no events, every `busy_minutes` 0 | the loop never runs; every coworker still reported |
| edf beats fifo | B, C, D, A all on time; 40 busy minutes | the `(deadline, arrives, id)` sort |
| wait for the fast one | R2 waits from 1 to 10 for `fast`, finishes 15 | escalation uses the fastest skilled coworker, busy or not |
| choose earliest finish then load then name | alpha and zeta alternate, B6 to beta | the full `(finish, active, name)` key |
| same time completion and arrival | Z assigned at 10, Y escalated `sla` at 15 | free before the walk; `arrives` breaks the deadline tie |
| unsorted input | T-3, T-1 at 0; T-5 at 20; T-9 at 50, billing-bot 90 busy minutes | sort arrivals yourself |
| busy afternoon | 59 assigned, 61 escalated (55 `sla`, 6 `no_skill`) | 120 random requests through every branch |
| bigger team | 113 assigned, 137 escalated | 250 requests, five coworkers |

## 10. Complexity

There are at most `R` arrival times and `R` finish times, so at most `2R` decision times. At each one the pending queue (up to `R`) is sorted and walked, and each request scans the `C` coworkers. That's O(R · (R log R + R · C)) in the worst case, about 300 · 300 · 10 operations here: instant.

In production the queue stays short because requests are resolved quickly, so the real costs are elsewhere. Durations are estimates, not facts: use a p90 handling time per skill and coworker, and re-check feasibility when an assignment runs long, rather than trusting the estimate made at assignment time. Escalation should also carry context (the transcript and what was tried) so the human doesn't start from zero.

## 11. If you got Wrong Answer

Compare the first event that differs.

- **Example 1 sends T-2 to `billing-bot` with finish 30.** You picked the first free coworker by name. Use `(finish, active, name)`.
- **"choose earliest finish then load then name" gives `alpha` B0, B1 and B2 in a row.** You left out the active-count tie-break.
- **"edf beats fifo" escalates C at `t = 20`.** You sorted pending by arrival. Sort by `(deadline, arrives, id)`.
- **Example 2 escalates T-12 and T-11 at `t = 5`.** You escalate whenever no free coworker can take a request now. A request whose best case is feasible should wait.
- **"wait for the fast one" escalates R2 at `t = 1`.** You computed the best case from free coworkers only. Use every skilled coworker, busy or not.
- **Example 3 assigns T-21, or Example 2 assigns T-12 with finish 80.** You skipped the deadline checks and assign work nobody can finish in time.
- **Example 3 escalates T-20.** You used `<` against the deadline. Finishing exactly at it meets the SLA.

## 12. Follow-ups an interviewer might ask

- *Is EDF optimal with several coworkers?* No. On one machine it meets every deadline whenever any schedule can. With parallel workers of different speeds, the general problem is NP-hard, and EDF is a good, explainable heuristic. If you need better, look at the requests that were escalated and ask whether a different assignment would have saved them.
- *What if an AI coworker isn't confident it can handle a request?* Add a confidence check before assigning. Platforms such as Sierra, Decagon and Agentforce route to a human on low confidence, not only on time.
- *What if a coworker crashes mid-request?* The assignment needs a lease so the request comes back to the queue after a timeout. Problem 163 (agent-task-queue-leases) builds exactly that.
- *How do you keep humans from drowning in escalations?* Escalate only when the SLA is truly lost (as here), batch low-priority escalations, and track the escalation rate per skill. A skill that escalates often needs more capacity or a faster coworker, not more pages.
- *Which actions need a human even when the SLA is fine?* Risky ones, such as large refunds or contract changes. Gate them with approvals (problem 110, human-approval-gates).
