## 1. What the problem is really asking

A planner model has already decided *what* to call. It handed you a dependency graph: fetch the customer and the order, then payments once the order is in, then a fraud score, then a reply. Your job is the executor that decides *when* each call runs, and it has to finish as early as the concurrency limit allows.

Under the story this is **event-driven list scheduling on a DAG**:

> keep a status per node → whenever a slot frees up (and once at the start), start the ready nodes in id order until the slots are full → when a node fails, cancel everything downstream of it.

There's no clever algorithm. The difficulty is in the bookkeeping: who is ready, who is running, how many slots are taken, and what happens to the descendants of a failure. The judge doesn't only look at your returned statuses. It records **every start, finish and fail event with its virtual time**, the peak number of tools running at once, the makespan, and how many times you called `run_tool` for each node. So the exact schedule is what's graded, not just the outcome.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `loop` | a `gc_runtime.EventLoop` with virtual time | `loop.spawn(gen)` to start a task, `loop.run()` once at the end |
| `nodes` | `[{"id", "tool", "deps"}]`, acyclic | build `deps[id]` and `children[id]` from it |
| `run_tool(node_id)` | returns a **generator** that runs the tool | `yield loop.spawn(run_tool(nid))` inside your own task |
| `max_concurrency` | the most tools running at once | a counter you check before every start |
| return value | `{id: "ok" or "failed" or "cancelled"}` | one entry for every node |

The `EventLoop` is the piece most people haven't seen before. A task is a plain generator, and what it yields tells the loop what to do:

```python
yield 1.5                # sleep 1.5 virtual seconds
r = yield other_task     # wait for another Task; get its return value, or its exception re-raised here
```

`loop.spawn(gen)` only *schedules* the task; nothing runs until you call `loop.run()`. When `run()` returns, every task has finished.

Three details are easy to miss:

- `run_tool` returns a generator, not a result. Calling `run_tool("order")` on its own does nothing. You have to spawn it (or `yield from` it) inside a task.
- When the tool raises `ToolError`, the exception comes out of **your** `yield`, so the `try/except` goes around the yield. An uncaught exception doesn't crash the judge; it silently ends your task, and the node is stuck as `"running"` forever.
- "Ready" means every dep finished **`"ok"`**. A dep that failed or was cancelled never makes its children ready, which is why the children have to be marked `"cancelled"` explicitly.

## 3. Trace Example 2 by hand

Four nodes, two slots. `reply` depends on the other three.

| node | duration | deps |
|---|---|---|
| `crm` | 2.0 | |
| `kb` | 1.0 | |
| `orders` | 1.5 | |
| `reply` | 1.0 | crm, kb, orders |

| t | event | ready set (sorted) | running after | what happens |
|---|---|---|---|---|
| 0 | start | crm, kb, orders | crm, kb | two slots, so the two lowest ids start |
| 1.0 | kb finishes | orders | crm, orders | the freed slot goes to `orders` immediately |
| 2.0 | crm finishes | (none) | orders | `reply` still waits on `orders`; a slot sits idle |
| 2.5 | orders finishes | reply | reply | all three deps are `ok` |
| 3.5 | reply finishes | | | makespan 3.5 |

The judge's event list for this case, from `trace.py`:

```python
[[0, 'start', 'crm'], [0, 'start', 'kb'], [1, 'finish', 'kb'], [1, 'start', 'orders'],
 [2, 'finish', 'crm'], [2.5, 'finish', 'orders'], [2.5, 'start', 'reply'], [3.5, 'finish', 'reply']]
```

Notice that at t=0 the ready set has three nodes but only two start. The order they start in is **string order of `id`**: `"crm" < "kb" < "orders"`. The planner's list order doesn't matter.

**Example 1 adds one twist.** With two slots, `customer` and `order` start at 0. `customer` finishes at 1.0, and a slot frees up, but nothing is ready: `payments` needs `order` and `fraud` needs `payments`. The slot stays empty until `order` finishes at 1.5. This is why the "unbounded slots" case, the same graph with `max_concurrency = 6`, gives the identical schedule and makespan 5.4: the graph is never more than 2 wide, so extra slots buy nothing.

**The hidden case worth tracing is "fail in the middle with siblings"** (two slots):

| t | event | effect |
|---|---|---|
| 0 | `root` starts | |
| 1.0 | `root` finishes | `geo` and `hist` both ready; both start (`"geo" < "hist"`) |
| 1.5 | `geo` **fails** | `geo` → failed. Its child `risk` → cancelled, even though `risk`'s other dep `hist` is still running |
| 3.0 | `hist` finishes | `sum` is ready (`risk` is cancelled, not pending, so it isn't a candidate) |
| 4.0 | `sum` finishes | `route` starts |
| 4.25 | `route` finishes | makespan 4.25 |

Final statuses: `geo` failed, `risk` cancelled, and `root`, `hist`, `sum`, `route` all `ok`. The failure took out exactly one node downstream of it, and the `hist → sum → route` branch carried on.

## 4. Key idea: each finished tool refills its own slot

The tempting design is level by level: run every node with no deps, wait for all of them, then run the next layer. That's what `asyncio.gather` per layer gives you, and it's wrong here. The rule says to start ready nodes *right after each tool finishes*, and a layer barrier makes fast branches wait for slow ones.

The "level barrier is slower" case shows it. `a` (4.0s) and `b` (1.0s) start at 0. `c` (3.5s) depends only on `b`.

| | `c` starts | `d` starts | makespan |
|---|---|---|---|
| correct (refill on each finish) | 1 | 4 | 5.5 |
| level barrier (`wrong_level_barrier.py`) | 4 | 4 | 8 |

`c` sat idle for three seconds it didn't need to wait. Because `b → c` is 4.5s of work, that idle time lands on the critical path: `c` finishes at 7.5 instead of 4.5, so `e` can't start until 7.5 and the makespan grows from 5.5 to 8.

The fix is to make every node's own wrapper task responsible for what happens after it finishes: record the status, free the slot, call `fill()`. No central coordinator, no layers.

## 5. Key idea: mark a node "running" before you spawn it

`fill()` picks nodes whose status is `"pending"`. If you spawn a node's task but leave its status as `"pending"`, the next `fill()` call (after any other tool finishes) sees it as ready again and starts it a second time. With `"running"` set only after the tool finishes, Example 2 becomes:

```python
'run_tool_calls': {'crm': 2, 'kb': 1, 'orders': 2, 'reply': 2}    # makespan 5.5, expected 3.5
```

So the status moves `pending → running → ok/failed` in `fill()` and `worker()`, and `cancelled` is only ever written over `pending`. The slot counter `running[0]` is incremented in the same place, at the moment you commit to starting a node, not inside the task when it first runs.

## 6. Key idea: cancel the whole subtree, and nothing else

When a node fails, its children can never become ready. If you mark only the direct children `"cancelled"`, the grandchildren stay `"pending"` forever: their dep is `"cancelled"`, not `"ok"`, so nothing ever starts them, and nothing ever marks them either. In "failure cancels transitive descendants only", `wrong_cancels_direct_children_only.py` returns:

```python
{'a_fetch': 'failed', 'b_parse': 'cancelled', 'c_embed': 'pending', 'd_index': 'pending', ...}
```

In production that's a run that never terminates. A short DFS over `children` fixes it, and checking `status[c] == "pending"` before recursing means a node reachable two ways is only visited once.

The opposite mistake is cancelling every pending node on any failure. In the same case `e_meta → f_notify` has nothing to do with `a_fetch` and must still complete. Notice too that `d_index` depends on both `c_embed` (doomed) and `e_meta` (fine). One failed dep is enough to cancel it.

## 7. Plan before you code

```
deps[id]     = set of its deps
children[id] = nodes that list id as a dep
status       = every id "pending"
running      = 0

fill():
    ready = sorted ids that are pending with every dep "ok"
    for each id in ready, while running < max_concurrency:
        status[id] = "running"; running += 1; spawn worker(id)

worker(id):                       # a generator task
    try:   yield spawn(run_tool(id)); status[id] = "ok"
    except ToolError: status[id] = "failed"; cancel every pending descendant
    running -= 1
    fill()

fill(); loop.run(); return status
```

| what happened to a dep | effect on the child |
|---|---|
| all deps `ok` | ready; starts on the next `fill()` with a free slot |
| some dep still pending or running | not ready yet |
| any dep failed or cancelled | the child is `cancelled` (set by the DFS when the failure happens) |

## 8. Build it one piece at a time

**Step 1: the graph and the state.** `children` is the reverse of `deps`, and it's what the cancellation walk needs.

```python
from collections import defaultdict
from gc_runtime import ToolError

def run_dag(loop, nodes, run_tool, max_concurrency):
    deps = {n["id"]: set(n["deps"]) for n in nodes}
    children = defaultdict(list)
    for n in nodes:
        for d in n["deps"]:
            children[d].append(n["id"])
    status = {nid: "pending" for nid in deps}
    running = [0]
```

`running` is a one-element list so the nested functions can change it without `nonlocal`. Either works.

**Step 2: `fill()`.** Sort the ready set every time. This is what makes the "input order is not id order" case start `audit` and `hubspot` first, even though the planner listed `zendesk` first.

```python
    def fill():
        ready = sorted(nid for nid, st in status.items()
                       if st == "pending" and all(status[d] == "ok" for d in deps[nid]))
        for nid in ready:
            if running[0] >= max_concurrency:
                break
            status[nid] = "running"
            running[0] += 1
            loop.spawn(worker(nid), nid)
```

**Step 3: the worker.** It waits on the tool, records the outcome, then frees its slot and refills. The order of the last two lines matters: if you call `fill()` before `running[0] -= 1`, `fill()` still sees every slot taken and starts nothing. In Example 2 `orders` then waits until `crm` finishes at 2.0 instead of starting at 1.0, and the makespan becomes 4.5 instead of 3.5.

```python
    def worker(nid):
        try:
            yield loop.spawn(run_tool(nid))
            status[nid] = "ok"
        except ToolError:
            status[nid] = "failed"
            cancel_descendants(nid)
        running[0] -= 1
        fill()
```

**Step 4: cancellation, and starting the loop.** Without the final `loop.run()` nothing executes: Example 1 returns no events and `customer` and `order` stuck at `"running"`.

```python
    def cancel_descendants(nid):
        for c in children[nid]:
            if status[c] == "pending":
                status[c] = "cancelled"
                cancel_descendants(c)

    fill()
    loop.run()
    return status
```

## 9. Full solution

```python
from collections import defaultdict  # children[] starts as an empty list for every id

from gc_runtime import ToolError  # the one exception a tool raises when it fails


def run_dag(loop, nodes, run_tool, max_concurrency):  # the executor the judge calls once per case
    deps = {n["id"]: set(n["deps"]) for n in nodes}  # what each node waits on, to test readiness
    children = defaultdict(list)  # the reverse edges, so a failure can walk downstream
    for n in nodes:  # fill children[] from every node's dep list
        for d in n["deps"]:  # each dep d gains n as a child
            children[d].append(n["id"])  # record the edge d -> n
    status = {nid: "pending" for nid in deps}  # every node starts not yet run
    running = [0]  # tools in flight now; a list so the nested functions can change it

    def cancel_descendants(nid):  # mark everything downstream of a failure, at any depth
        for c in children[nid]:  # look at each direct child
            if status[c] == "pending":  # skip nodes already cancelled (reachable twice) or finished
                status[c] = "cancelled"  # it can never become ready, so it must never start
                cancel_descendants(c)  # recurse so grandchildren don't stay pending forever

    def fill():  # start ready nodes until the slots are full; runs at t=0 and after every finish
        # ready = not started and every dep finished ok; sorted so ids decide, not input order
        ready = sorted(nid for nid, st in status.items()
                       if st == "pending" and all(status[d] == "ok" for d in deps[nid]))
        for nid in ready:  # lowest id first
            if running[0] >= max_concurrency:  # every slot is taken
                break  # the rest wait for the next finish
            status[nid] = "running"  # mark it now so a later fill() can't start it twice
            running[0] += 1  # claim the slot at the moment we commit to the node
            loop.spawn(worker(nid), nid)  # its wrapper task runs the tool on the loop

    def worker(nid):  # one wrapper task per started node
        try:  # a ToolError comes out of the yield below
            yield loop.spawn(run_tool(nid))  # run the tool and wait for it in virtual time
            status[nid] = "ok"  # it returned, so its children may now be ready
        except ToolError:  # the tool failed
            status[nid] = "failed"  # record the failure itself
            cancel_descendants(nid)  # and doom everything that depends on it, nothing else
        running[0] -= 1  # free the slot first, or fill() would still see it taken
        fill()  # refill right away: no waiting for the rest of a layer

    fill()  # start the first batch at t=0
    loop.run()  # nothing executes until the loop runs; it returns when every task is done
    return status  # one final status for every node
```

## 10. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | makespan 5.4, peak 2 | refill on each finish; a free slot can stay idle when nothing is ready |
| Example 2 | `orders` starts at 1.0, makespan 3.5 | the limit caps the start at t=0; a freed slot is reused at once |
| Example 3 | `shipping` failed, `eta_note` cancelled, `offer` ok | a failure cancels its child; the independent branch finishes |
| unbounded slots | same schedule as Example 1, peak 2 | more slots than the graph is wide changes nothing |
| serial | one tool at a time, makespan 6.4 | `max_concurrency = 1` |
| input order is not id order | `audit` and `hubspot` start first | the ready set is sorted by id |
| failure cancels transitive descendants only | `b_parse`, `c_embed`, `d_index` cancelled; `e_meta`, `f_notify` ok | the DFS goes all the way down, and stops there |
| level barrier is slower | `c` starts at 1, not 4; makespan 5.5, not 8 | no layer barriers |
| freed slot goes to lowest ready id | `q1` starts at 3, `q9` at 3.5 | sort by id, not by deps order or input order |
| fail in the middle with siblings | `geo` failed, `risk` cancelled, `route` ok | a node with one failed dep is cancelled while its other dep is still running |
| wide fan-out | peak 3, makespan 6 | a long queue of ready nodes drained 3 at a time |
| single node failing | `{'only': 'failed'}` | the smallest failure; nothing to cancel |

"freed slot goes to lowest ready id" is the subtle one. `p2` finishes at 1.0 and makes both `q9` and `q1` ready, but `p3` (`"p3" < "q1"`) takes the slot. At 3.0 `p1` finishes and the lowest ready id is `q1`, even though the planner listed `q9` first. Starting in input order gives `q9` at 3 and a makespan of 5 instead of 4.75.

## 11. Complexity

With `V` nodes and `E` dependency edges, each `fill()` scans every node and its deps and sorts the ready set: O(V log V + E). `fill()` runs once at the start and once per finished tool, so the total is O(V · (V log V + E)). The cancellation DFS touches each node at most once overall, because only `pending` nodes are visited. At `V ≤ 15` none of this matters.

At scale, the scan is the part you'd replace. Keep an in-degree counter per node, decrement it when a dep finishes `ok`, and push a node onto a min-heap of ready ids when its counter hits zero. Each start is then O(log V) and the whole run is O((V + E) log V). The real cost in production is never the scheduler. It's the tools, and the makespan you save by not putting barriers between layers.

## 12. If you got Wrong Answer

Compare the `events` list first. The first event at the wrong time usually points straight at the bug:

- **`peak_concurrency` is higher than `max_concurrency`, and more nodes start at t=0 than there are slots.** You never check the slot count (`wrong_ignores_max_concurrency.py`). It fails Example 2, serial and wide fan-out.
- **A child starts only when its whole layer finishes** (`c` at 4 in "level barrier is slower"). You're running level by level (`wrong_level_barrier.py`).
- **The right nodes run, but in a different order** (`zendesk` before `audit`, `q9` before `q1`). You start in input order, not `sorted` id order (`wrong_starts_in_input_order.py`).
- **Some statuses come back `"pending"`.** You cancel only direct children (`wrong_cancels_direct_children_only.py`).
- **An independent branch is `"cancelled"`.** You cancel every pending node on any failure (`wrong_failure_aborts_whole_dag.py`). In "fail in the middle with siblings" `sum` and `route` come back cancelled.
- **A failed node's status is `"running"`.** The `ToolError` escaped your task. Put the `try/except` around the `yield`.
- **`run_tool_calls` shows a node called twice.** You didn't mark it `"running"` before spawning.
- **A freed slot isn't reused until a later finish.** You call `fill()` before releasing the slot.
- **No events at all.** You never called `loop.run()`.

## 13. Follow-ups an interviewer might ask

- *Where do these graphs come from?* A planner model emits them, either as several tool calls in one assistant turn (Anthropic and OpenAI both support parallel tool calls) or as an explicit plan. Problem 106 (plan-and-execute-replan) covers planning and replanning; problem 101 (react-tool-loop) is the one-call-at-a-time version.
- *What if a tool hangs?* Give every node a timeout and treat a timeout as a failure, possibly after a retry with backoff (problem 124). Without it, one stuck CRM call holds a slot forever.
- *Should one number cap every tool?* Usually not. A CRM and an LLM provider have different rate limits, so keep a semaphore or a token bucket per provider (problem 123) and check the right one before starting a node.
- *How would you find what made the run slow?* Record each node's start and end as a trace span. The longest dependency chain through those spans is the critical path, which is exactly problem 112 (trace-critical-path).
- *What if the whole run crashes halfway?* Persist each node's status and result as it finishes, and on restart skip the nodes already `ok`. That's durable execution, as in problem 111 (durable-workflow-replay) and Temporal.
