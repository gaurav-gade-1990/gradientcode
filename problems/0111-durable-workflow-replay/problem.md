Your order agent's fulfillment workflow reserves stock, charges the card, ships and emails, and the worker running it can die at any point. Write the replay engine that makes it durable, the way Temporal does: on restart, replay the recorded results instead of repeating side effects, then continue live.

`run_workflow(workflow, wf_input, history, activities)` gets:

- `workflow(wf_input)`, which returns a **generator**. Each `yield` is a command `(activity_name, args)`. The workflow expects to receive the activity's result back from `yield`, or to have a `gc_runtime.ToolError` raised at that `yield` if the activity failed (it may catch it and compensate).
- `history`, the durable event list, possibly empty. Each event is `{"seq", "activity", "args", "status": "completed", "result"}` or `{"seq", "activity", "args", "status": "failed", "error"}`.
- `activities`, a dict of side-effecting functions: `activities[name](**args)` returns a result or raises `ToolError`.

Number the commands `seq = 0, 1, 2, ...` and handle each one:

| situation | what to do |
|---|---|
| `seq < len(history)` and the event's `activity` and `args` match the command | **replay**: send the recorded `result`, or raise `ToolError(event["error"])` into the workflow. Don't call the activity. |
| `seq < len(history)` and they don't match | raise `NonDeterminismError` |
| `seq >= len(history)` | **live**: call the activity, and **immediately** append its event (with `"error": str(e)` on `ToolError`) to `history` itself, then resume the workflow |
| the workflow returns while `seq < len(history)` | raise `NonDeterminismError` (the history has events the code no longer produces) |
| the workflow returns | return its return value |

Args match when `json.dumps(args, sort_keys=True)` is equal. Define `class NonDeterminismError(Exception)` in your code. Let any other exception, such as the worker crashing inside an activity, propagate.

The judge runs the workflow one or more times against the **same** history list, crashing some runs partway through. It records the live activity calls in each run, each run's outcome, and the final history.

**Constraints**

- Workflows yield at most 10 commands
- Activity args and results are JSON values
