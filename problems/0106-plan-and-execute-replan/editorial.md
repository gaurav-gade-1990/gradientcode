## Approach

Separate the two jobs. The planner owns *what* to do, and the executor owns *exactly once* and *in order*. The executor keeps two pieces of state that outlive any single plan: `results` (id to result) and the ordered `completed` list it reports back.

```python
steps, i, replans = plan(None), 0, 0
while i < len(steps):
    step = steps[i]
    if step["id"] in results:          # never redo a completed step
        i += 1
        continue
    result, error = run_step(step)     # resolves {"$ref": id}, unknown tool, ToolError
    if error is None:
        results[step["id"]] = result
        completed.append({"id": step["id"], "tool": step["tool"], "result": result})
        i += 1
        continue
    if replans >= max_replans:
        return failed_result()
    replans += 1
    steps, i = plan({"id": step["id"], "tool": step["tool"], "error": error}), 0
return completed_result()
```

Replacing `steps` wholesale is the splice: the completed prefix lives in `results`, and the new plan becomes the whole future. Because completed ids are skipped, a planner that restates the full plan (which models often do) is harmless.

## Common mistakes

- **Re-running completed steps.** The planner echoes `s1, s2` in its new plan and the executor runs them again. With side-effecting tools that's a second refund.
- **Replanning without history.** If the planner only sees the error, it starts over and asks for steps that already ran.
- **Inserting instead of replacing.** The old tail still runs after the new plan, and the customer gets two emails.
- **Off-by-one on the budget.** Checking after the call gives the planner one more turn than you're paying for.
- **Calling tools with unresolved placeholders.** `refund_charge(charge_id={"$ref": "s2"})` reaches the payment API. Fail before the call.

## Production notes

- This is LangGraph's plan-and-execute template and the "planner and executor" split in most agent frameworks. Production versions persist `completed` (problem 111, durable-workflow-replay) so a crash mid-plan doesn't redo side effects either.
- Skipping by step id is only as safe as the ids are stable. Real systems also put idempotency keys on side-effecting tools (problem 119), because a planner can rename a step.
- Validate the plan before running it: the JSON shape, that tools exist, and that refs point backwards. Problem 113 (tool-args-schema-validation) covers the argument checks, and problem 116 covers repairing malformed planner JSON.
- Cap total tool calls as well as replans, and send the final `failed` state to a human queue (problem 110) rather than returning silently.
