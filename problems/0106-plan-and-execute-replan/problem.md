Your billing agent fixes duplicate charges with a plan-and-execute loop: a planner model writes a list of tool steps, and an executor runs them. When a step fails, the planner gets one more look and rewrites the rest of the plan. Write the executor.

`execute_plan(llm, tools, goal, max_replans)` gets a `gc_runtime.FakeLLM` (the planner), a dict of tool functions (`tools[name](**args)` returns a string or raises `gc_runtime.ToolError`), the goal string, and the replan budget.

**Calling the planner.** Every planner call, the first one included, is exactly:

```python
llm.complete([
    {"role": "system", "content": "You are the planner. Reply with only a JSON list of steps, each {\"id\", \"tool\", \"args\"}."},
    {"role": "user", "content": json.dumps({"goal": goal, "completed": completed, "failed": failed}, sort_keys=True)},
])
```

- `completed` lists every step that has succeeded so far, in the order it finished, as `{"id", "tool", "result"}`.
- `failed` is `None` on the first call, and `{"id", "tool", "error"}` for the step that just failed on a replan.

The response's `.content` is a JSON list of steps `{"id": str, "tool": str, "args": dict}`.

**Running a step.** Take the steps of the current plan in order:

| situation | what happens |
|---|---|
| the step's `id` already completed | skip it; never run a completed step twice |
| an arg value is `{"$ref": "s2"}` and `s2` has completed | replace it with `s2`'s result string (top-level args only) |
| an arg value is `{"$ref": x}` and `x` hasn't completed | the step fails with error `"unresolved reference " + x` without calling the tool |
| `tool` isn't in `tools` | the step fails with error `"unknown tool " + tool` |
| the tool returns `r` | the step completes with result `r` |
| the tool raises `ToolError` `e` | the step fails with error `str(e)` |

**On failure.** If you've already made `max_replans` replan calls, stop with status `"failed"`. Otherwise call the planner again with the failure. Its new plan **replaces** the failed step and everything after it, and execution continues from the start of the new plan. If you run out of steps, the status is `"completed"`.

Return `{"status": ..., "completed": [ids in completion order], "replans": number of replan calls, "results": {id: result}}`.

The judge records every planner call's messages and every tool call with its resolved arguments.

**Constraints**

- `0 <= max_replans <= 3`, and plans have at most 8 steps
- Step ids are unique within a single plan
