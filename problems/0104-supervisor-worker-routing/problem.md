Your supervisor agent breaks a customer escalation into subtasks ("pull the invoice history", "draft an apology in Spanish") and hands them to specialist worker agents. Write the routing and execution loop.

`supervise(subtasks, workers, execute)` gets:

- `subtasks`, a list of `{"id": str, "title": str, "needs": [skill tags]}`.
- `workers`, a list of `{"name": str, "skills": [skill tags]}`. Names are unique, and the list isn't sorted.
- `execute(worker_name, subtask_id)`, which runs the subtask on that worker and returns a string, or raises `gc_runtime.ToolError`.

A worker is **eligible** for a subtask when its skills include **every** tag in `needs`. A worker's **load** is the number of subtasks waiting in its queue right now.

**1. Assign.** Go through `subtasks` in order. Append each one to the queue of the eligible worker with the smallest load, breaking ties by the alphabetically first name. If no worker is eligible, the subtask is `"unroutable"` and is never executed.

**2. Execute in rounds.** In each round, visit the workers in ascending name order. When it's a worker's turn and its queue isn't empty, pop the head and call `execute(name, subtask_id)`. Keep running rounds until every queue is empty.

**3. Reassign once on error.** If `execute` raises `ToolError` and the subtask hasn't been reassigned yet, append it to the queue of the eligible worker with the smallest current load (ties by name), **excluding** the worker that just failed it. If there's no such worker, or this was already the second attempt, the subtask is `"failed"`. A worker that comes later in the current round gets its turn in this round as usual.

Return one dict per subtask, **in the original subtask order**:

| key | value |
|---|---|
| `id` | the subtask id |
| `status` | `"done"`, `"failed"` or `"unroutable"` |
| `worker` | the worker that produced the output (`"done"`), the last worker that tried it (`"failed"`), or `None` |
| `output` | the string `execute` returned, or `None` |
| `attempts` | how many times `execute` was called for this subtask |

The judge records every `execute` call, in order.

**Constraints**

- `1 <= len(subtasks) <= 20`, `1 <= len(workers) <= 6`
- Skill tags and names are lowercase strings
