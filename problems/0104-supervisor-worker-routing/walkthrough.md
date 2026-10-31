## 1. What the problem is really asking

A supervisor agent has split an escalation into subtasks and now has to hand them to specialists. Under the story there's no LLM at all. This is a small **job scheduler** with three parts:

- a **filter** (which workers can do this subtask?),
- a **least-loaded pick** with a deterministic tie-break (which of them gets it?),
- a **round-robin drain** of per-worker queues, with **one retry** on a different worker when a call fails.

The judge records every `execute(worker, subtask_id)` call in the order you make it, and it compares your returned list of result dicts. So both *who* runs each subtask and *in what order* the calls happen are graded. A solution that gets every status right but calls the workers in a different order still fails.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `subtasks` | list of `{"id", "title", "needs"}` | assigned in this order; the result list is in this order too |
| `needs` | list of skill tags the subtask requires | `set(needs) <= set(skills)` decides eligibility |
| `workers` | list of `{"name", "skills"}`, **not sorted** | build `skills[name]`, and sort the names yourself |
| `execute(name, tid)` | runs the subtask on that worker | returns the output string or raises `ToolError` |
| return value | one dict per subtask: `id`, `status`, `worker`, `output`, `attempts` | built up as you go, returned in subtask order |

Three details are easy to miss:

- **Eligible means every tag, not any tag.** A worker with `["writing"]` can't take a subtask that needs `["writing", "spanish"]`. A subtask with `needs: []` is a subset of every skill set, so anyone is eligible, including a worker with no skills at all.
- **Load is the queue length right now.** It isn't the number of subtasks a worker has ever been given. During execution, popping a subtask makes the queue shorter, and that changes who looks "least loaded" for a retry.
- **The worker list order means nothing.** Ties go to the alphabetically first name, and rounds visit workers in ascending name order. If you iterate `workers` as given, the call order follows whoever edited the config last.

## 3. Trace Example 1 by hand

Workers sorted by name are `analyst (sql, charts)`, `billing (billing, sql)`, `polyglot (writing, english, spanish)` and `writer (writing, english)`.

**Phase 1: assign**, going through the subtasks in order. The eligible list shows each candidate with its load at that moment:

| subtask | needs | eligible (load) | goes to |
|---|---|---|---|
| t1 | sql | analyst (0), billing (0) | analyst, tie broken by name |
| t2 | billing, sql | billing (0) | billing |
| t3 | writing, english | polyglot (0), writer (0) | polyglot, tie broken by name |
| t4 | writing, spanish | polyglot (1) | polyglot |
| t5 | sql, charts | analyst (1) | analyst |
| t6 | writing | polyglot (2), writer (0) | writer, lower load wins |

The queues are now `analyst: [t1, t5]`, `billing: [t2]`, `polyglot: [t3, t4]`, `writer: [t6]`.

**Phase 2: rounds.** Each round visits analyst, billing, polyglot, writer and pops one subtask from each non-empty queue:

| round | calls |
|---|---|
| 1 | analyst t1, billing t2, polyglot t3, writer t6 |
| 2 | analyst t5, polyglot t4 |

So `execute_calls` is `[analyst t1], [billing t2], [polyglot t3], [writer t6], [analyst t5], [polyglot t4]`. Notice that t6 runs before t4 even though t4 comes first in the input. That's the point of rounds: polyglot's two-deep queue doesn't make writer wait.

**The failure path, "second attempt also fails".** Three identical sql workers `bq`, `duck`, `pg`. `bq` fails t1, `pg` fails t1, `duck` fails t2.

- Assign: t1 goes to `bq` (all at 0, name wins). t2 sees `bq (1), duck (0), pg (0)` and goes to `duck`.
- Round 1, `bq` runs t1: fails. Excluding `bq`, the candidates are `duck (1)` and `pg (0)`, so t1 goes to the back of `pg`'s queue.
- Round 1, `duck` runs t2: fails. Excluding `duck`, the candidates are `bq (0)` and `pg (1)`, so t2 goes to `bq`.
- Round 1 continues to `pg`, which now holds t1. A worker later in the round gets its turn as usual, so `pg` runs t1 **in round 1**. It fails again. That's the second attempt, so t1 is `"failed"` with `worker: "pg"` and `attempts: 2`.
- Round 2: `bq` runs t2 and succeeds.

The calls are `[bq t1], [duck t2], [pg t1], [bq t2]`. If you kept retrying, t1 would go on to `duck` for a third attempt.

## 4. Key idea: remember who already failed each subtask

Look at "reassign never returns to failing worker": `amy` and `zed`, both writers, and `amy` crashes on t1. At assignment, t1 goes to `amy` (tie at 0, name wins) and t2 goes to `zed`. In round 1 `amy` pops t1, so her queue is now **empty**, while `zed` still holds t2. A plain least-loaded pick would choose `amy` again, the worker that just crashed on it.

The fix is a per-subtask set `failed_on[tid]`. Add the worker on every failure and filter it out of the candidates. Then t1 goes to `zed`, behind t2, and runs in round 2. Without the set, the calls are `[amy t1], [zed t2], [amy t1]` and t1 ends `"failed"` instead of `"done"`.

The same `pick` function serves both phases. During assignment `failed_on` is empty, so the filter does nothing.

## 5. Plan before you code

```
skills = {name: set(skills)}; names = sorted(skills)
queue = {name: []}; results = {tid: blank result}; failed_on = {tid: set()}

pick(tid): among names whose skills cover needs[tid] and not in failed_on[tid],
           return the min by (len(queue[name]), name), or None

for each subtask in order:
    w = pick(tid); if None: status = "unroutable" else queue[w].append(tid)

while any queue is non-empty:
    for name in names:
        if queue[name] is empty: skip
        tid = pop the head; attempts += 1; worker = name
        try execute -> output, status "done"
        on ToolError: failed_on[tid].add(name)
                      nxt = pick(tid) if attempts < 2 else None
                      nxt is None -> status "failed", else queue[nxt].append(tid)

return [results[tid] for tid in original order]
```

The outcome table for one `execute` call:

| what happens | status | next step |
|---|---|---|
| returns a string | `"done"` | store `output`, `worker = name` |
| raises, first attempt, another eligible worker exists | unchanged | append to that worker's queue |
| raises, first attempt, no other eligible worker | `"failed"` | `worker` stays the one that just failed |
| raises, second attempt | `"failed"` | same |

## 6. Build it one piece at a time

**Step 1: the lookups.** Sort the names once and use that list everywhere. Results live in a dict keyed by id so you can update them from any round.

```python
skills = {w["name"]: set(w["skills"]) for w in workers}
names = sorted(skills)
queue = {n: [] for n in names}
results = {t["id"]: {"id": t["id"], "status": None, "worker": None, "output": None, "attempts": 0}
           for t in subtasks}
needs = {t["id"]: set(t["needs"]) for t in subtasks}
failed_on = {t["id"]: set() for t in subtasks}
```

**Step 2: the pick.** `<=` on sets is "is a subset of". The tuple key `(load, name)` gives both rules in one `min`: the lowest load first, then the alphabetically first name.

```python
def pick(tid):
    options = [n for n in names if needs[tid] <= skills[n] and n not in failed_on[tid]]
    return min(options, key=lambda n: (len(queue[n]), n)) if options else None
```

Using `needs & skills` (any overlap) instead of `<=` is the classic mistake. In "needs all tags, not any" it sends the Spanish apology to `aaron`, who only has `writing`.

**Step 3: assign.** An unroutable subtask never enters a queue, so it keeps `worker: None`, `output: None` and `attempts: 0`.

```python
for t in subtasks:
    w = pick(t["id"])
    if w is None:
        results[t["id"]]["status"] = "unroutable"
    else:
        queue[w].append(t["id"])
```

**Step 4: the rounds.** `pop(0)` takes the head, because the queue is first in, first out. Set `attempts` and `worker` *before* calling `execute`, so a failure still records who tried it.

```python
while any(queue.values()):
    for n in names:
        if not queue[n]:
            continue
        tid = queue[n].pop(0)
        r = results[tid]
        r["attempts"] += 1
        r["worker"] = n
        try:
            r["output"] = execute(n, tid)
            r["status"] = "done"
        except ToolError:
            failed_on[tid].add(n)
            nxt = pick(tid) if r["attempts"] < 2 else None
            if nxt is None:
                r["status"] = "failed"
            else:
                queue[nxt].append(tid)
```

Iterating `for n in names` while a retry appends to a later worker's queue is safe. You aren't changing the list you loop over, only the queues, so a later worker sees the new item when its turn comes, which is what the rules ask for.

**Step 5: return in subtask order,** not in the order things finished.

```python
return [results[t["id"]] for t in subtasks]
```

## 7. Full solution

Every line carries a comment saying what it does and why.

```python
# The one failure execute() raises on purpose; it triggers a reassignment, anything else is a real bug.
from gc_runtime import ToolError


# subtasks: what to do, workers: who can do it, execute: runs one subtask on one worker.
def supervise(subtasks, workers, execute):
    # Skill sets per worker, so eligibility is one subset test.
    skills = {w["name"]: set(w["skills"]) for w in workers}
    # Sorted once: this order drives both the tie-break and the round order, whatever the config order.
    names = sorted(skills)
    # One FIFO queue per worker; its length is that worker's load.
    queue = {n: [] for n in names}
    # A result per subtask, keyed by id so any round can update it; defaults match "never executed".
    results = {t["id"]: {"id": t["id"], "status": None, "worker": None, "output": None, "attempts": 0} for t in subtasks}
    # Required tags as sets, for the same subset test.
    needs = {t["id"]: set(t["needs"]) for t in subtasks}
    # Workers that already failed each subtask; a retry must never go back to one of them.
    failed_on = {t["id"]: set() for t in subtasks}

    # Choose the worker for a subtask, or None when nobody can take it.
    def pick(tid):
        # Eligible = covers EVERY needed tag, and hasn't already failed this subtask.
        options = [n for n in names if needs[tid] <= skills[n] and n not in failed_on[tid]]
        # Least loaded first, alphabetical name on a tie; None when the list is empty.
        return min(options, key=lambda n: (len(queue[n]), n)) if options else None

    # Phase 1: assign every subtask, in input order.
    for t in subtasks:
        w = pick(t["id"])  # loads change as we go, so each pick sees the queues so far
        # Nobody has all the skills: the subtask is never executed.
        if w is None:
            results[t["id"]]["status"] = "unroutable"  # worker, output and attempts keep their defaults
        # Somebody can do it.
        else:
            queue[w].append(t["id"])  # join the back of that worker's queue

    # Phase 2: keep running rounds until every queue is drained (retries refill queues).
    while any(queue.values()):
        # One round: each worker, in name order, gets at most one turn.
        for n in names:
            # Nothing waiting for this worker this round.
            if not queue[n]:
                continue  # move on to the next worker
            tid = queue[n].pop(0)  # FIFO: the head of the queue
            r = results[tid]  # the record we're about to update
            r["attempts"] += 1  # count the call before making it
            r["worker"] = n  # record who tried, so a failure still names the last worker
            # Run it; ToolError means this worker couldn't do it.
            try:
                r["output"] = execute(n, tid)  # the worker's output string
                r["status"] = "done"  # success ends this subtask
            # The worker failed this subtask.
            except ToolError:
                failed_on[tid].add(n)  # never hand it back to this worker
                # One reassignment only: a second failure is final.
                nxt = pick(tid) if r["attempts"] < 2 else None
                # No retry allowed, or no other eligible worker.
                if nxt is None:
                    r["status"] = "failed"  # worker already holds the last one that tried
                # Another worker can try.
                else:
                    queue[nxt].append(tid)  # back of its queue; it runs this round if that worker is still to come
    # The caller assembles its answer from these, so keep the original subtask order.
    return [results[t["id"]] for t in subtasks]
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | all done; t6 runs before t4 | least-loaded pick, name tie-break, sorted rounds |
| Example 2 | t1 done on billing with 2 attempts; t7 unroutable | a retry joins the back of the new queue; no eligible worker means unroutable |
| Example 3 | t2 failed on billing after 1 attempt | no other eligible worker, so it fails without a second try |
| everyone eligible, balance by load | ada, milo, wren, ada, milo, wren, ada | ties at equal load cycle by name, whatever the input order (`wren, ada, milo`) |
| needs all tags, not any | both on cruz | the subset test `<=` |
| second attempt also fails | t1 failed on pg, 2 attempts; t2 done on bq | the retry cap, and a retry runs later in the same round |
| reassign never returns to failing worker | t1 done on zed, 2 attempts | `failed_on` excludes the crashed worker even when its queue is empty |
| reassigned to worker earlier in the round | a2 done on plot in round 3 | a retry to a worker already visited this round waits for the next round |
| results in subtask order despite rounds | z9, a1, m5, b2 | return in input order, not completion order |
| all down | every subtask failed; 9 calls | cap and exclusion together, across many subtasks |
| no needs means anyone | bravo, echo, bravo | the empty set is a subset of every skill set, even an empty one |

## 9. Complexity

With `S` subtasks and `W` workers, each `pick` scans `W` workers and does a subset test of size at most the number of tags, so assignment is O(S·W·k). Each subtask is executed at most twice, and each round does O(W) work, so execution is O(S·W) plus the `execute` calls. `pop(0)` on a list is O(queue length); use `collections.deque` if queues get long.

At scale the cost that matters is the worker calls, not the bookkeeping. The retry cap bounds that: at most `2·S` calls, however many workers there are. Without the cap a poison subtask walks through every eligible worker.

## 10. If you got Wrong Answer

Compare `execute_calls` first. It shows the first decision you made differently.

- **A tie goes to whoever is listed first in `workers`** (t1 lands on `billing` and t3 on `writer` in Example 1, instead of `analyst` and `polyglot`). Your tie-break follows the input list instead of the name (`wrong_ties_by_list_order.py`). If the *round* order follows the input list too, you're iterating `workers` as given instead of sorted names.
- **A Spanish subtask runs on an English-only worker** ("needs all tags, not any" calls `aaron`). You used any-overlap (`&`) instead of the subset test (`<=`).
- **The same worker appears twice for one subtask** (`[amy t1], ..., [amy t1]`). You're not excluding workers that already failed it.
- **A subtask has `attempts: 3`** ("second attempt also fails" ends with `[duck t1]`). There's no retry cap.
- **The results are in the right state but the wrong order** (`a1, z9, b2, m5`). You built the list as subtasks finished.
- **An unroutable subtask shows `attempts: 1` or a worker.** You're executing it anyway, or recording it before checking `pick` returned `None`.

## 11. Follow-ups an interviewer might ask

- *What if the supervisor is an LLM choosing the worker?* Keep this router as the guard rail: the model may choose only among eligible workers, and the deterministic pick is the fallback when its choice is invalid or the call fails.
- *How would you tell a bad worker from a bad task?* Classify the error. A 5xx or timeout from the worker is worth reassigning; a 400 or a validation error means the input is bad and every worker will fail it, so fail fast (problem 124's retryable vs non-retryable split).
- *Is queue length a good measure of load?* Only when subtasks are similar. In production you'd weight by expected tokens or in-flight requests, and keep the counts in a shared store when workers run in separate processes.
- *What context should each worker receive?* Only what its subtask needs, passed explicitly at the handoff (problem 105, agent-handoff-context).
- *What if two workers should both answer and you pick the best?* That's a vote or a judge over their outputs, not routing (problem 108, multi-agent-vote).
