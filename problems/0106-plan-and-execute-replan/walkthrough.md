## 1. What the problem is really asking

Plan-and-execute splits an agent into two jobs. The **planner** (a model) decides *what* to do and writes it down as a list of tool steps. The **executor** (your code) runs those steps exactly once each, in order, wiring one step's output into the next. When a step fails, the planner gets one more look and rewrites the rest.

Under the story this is a **loop over a list that can be swapped out mid-iteration**, with two pieces of state that outlive any one plan:

- `results`, a dict from step id to result string, which answers "has this already run?" and resolves `{"$ref": id}` arguments;
- `completed`, the ordered list of finished steps you report back to the planner.

The judge records every planner call's messages, every tool call with its *resolved* arguments, and your return value. So it sees whether you re-ran a step, called a tool with a placeholder, gave the planner the wrong history, or replanned once too often.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `llm` | a `FakeLLM` that replays the planner's replies in order | `llm.complete([system, user]).content` is a JSON list of steps |
| `tools` | `{name: fn}` | `tools[name](**args)` returns a string or raises `ToolError` |
| `goal` | the task string | goes into every planner payload |
| `max_replans` | how many *replan* calls you may make (0 to 3) | the first planner call doesn't count |
| a step | `{"id", "tool", "args"}` | `args` values are plain values or `{"$ref": step_id}` |
| return value | `{"status", "completed", "replans", "results"}` | `completed` is ids only; the planner payload uses full dicts |

Three details are easy to miss:

- **The payload is `json.dumps(..., sort_keys=True)`.** The judge compares the exact string, so key order matters: `completed`, `failed`, `goal` alphabetically, and inside each completed step `id`, `result`, `tool`. `failed` is `None` on the first call, which serializes as `null`.
- **`completed` means two different shapes.** The planner sees `{"id", "tool", "result"}` dicts. The return value lists just the ids. Keep the dicts and derive the ids at the end.
- **A failure doesn't always involve the tool.** An unresolved `$ref` and an unknown tool are failed steps too, with their own error strings, and they never call anything.

## 3. Trace Example 1 by hand

The first plan is `[s1 get_order, s2 find_duplicate(order=$ref s1), s3 refund_charge(charge_id=$ref s2), s4 email_customer(refund=$ref s3)]`, with `max_replans = 2`.

**Planner call 1.** The user message is:

```
{"completed": [], "failed": null, "goal": "Refund the duplicate charge on order A-1182 and tell the customer."}
```

**Running the steps:**

| step | resolved args | outcome | `completed` after |
|---|---|---|---|
| s1 `get_order` | `{"order_id": "A-1182"}` | `"A-1182: $84.00, charges ch_1 and ch_2"` | s1 |
| s2 `find_duplicate` | `{"order": "A-1182: $84.00, charges ch_1 and ch_2"}` | `"ch_2"` | s1, s2 |
| s3 `refund_charge` | `{"charge_id": "ch_2"}` | `ToolError("stripe: card network timeout")` | s1, s2 |

**Replan.** `replans` is 0 and the budget is 2, so you may replan. The second user message is:

```
{"completed": [{"id": "s1", "result": "A-1182: $84.00, charges ch_1 and ch_2", "tool": "get_order"},
               {"id": "s2", "result": "ch_2", "tool": "find_duplicate"}],
 "failed": {"error": "stripe: card network timeout", "id": "s3", "tool": "refund_charge"},
 "goal": "Refund the duplicate charge on order A-1182 and tell the customer."}
```

(The real string is on one line; it's wrapped here to read.) The planner answers `[s3b ledger_refund(charge_id=$ref s2, reason="duplicate"), s4b email_customer(refund=$ref s3b)]`. That list **replaces** s3 and s4. s4 never runs.

| step | resolved args | outcome |
|---|---|---|
| s3b `ledger_refund` | `{"charge_id": "ch_2", "reason": "duplicate"}` | `"re_ledger_55"` |
| s4b `email_customer` | `{"order_id": "A-1182", "refund": "re_ledger_55"}` | `"sent"` |

The return value is `{"status": "completed", "completed": ["s1", "s2", "s3b", "s4b"], "replans": 1, "results": {...}}`. Note that s3b's `$ref` points at s2, a step from the *old* plan. That works because `results` lives outside any single plan.

**The tricky hidden case, "two failures, history grows".** The first plan is `[s1, s3]`, and s3 refers to s2, which this plan never defines. s3 fails with `"unresolved reference s2"` without calling `refund_charge`. Replan 1 sees `completed: [s1]`. The new plan `[s2, s3]` runs s2 (`"ch_2"`), then s3 fails on Stripe. Replan 2 sees `completed: [s1, s2]` and the Stripe error. The plan `[s3b, s4b]` finishes the job: status `"completed"`, `replans: 2`. The planner's view of history grows with each call, and only 5 tools are called in total.

## 4. Key idea: skip completed ids, and let the new plan replace the tail

Planners often restate the whole plan when they replan. In Example 2 the second plan is `[s1, s2, s3b, s4b]`, even though s1 and s2 already ran. If you execute it as written, you fetch the order twice and, with a real side-effecting tool, could refund twice.

The fix is one check at the top of the loop: **if `step["id"]` is in `results`, skip it.** With that rule, "replace everything from the failed step onward" becomes trivial: set `steps` to the new plan and `i` to 0. The completed prefix is safe in `results`, so restated steps are skipped and new steps run.

The alternative, splicing the new plan in front of the old tail (`new_plan + steps[i+1:]`), is wrong. In "replan replaces the tail", the old tail is `[s4, s5]`. After s3b succeeds, the leftover s4 runs and fails with `"unresolved reference s3"` (s3 never succeeded), and the run ends as `"failed"` instead of `"completed"`.

Note what the skip rule does *not* cover: a step that **failed** isn't in `results`, so a new plan can reuse its id. In "failed id reused with new args" the second plan has `s3 refund_charge(charge_id="ch_1")`, which runs and returns `"re_901"`.

## 5. Key idea: check the budget before you call the planner

`max_replans` counts replan calls. The question to ask on each failure is "have I already used them all?", which is `replans >= max_replans`, checked *before* calling the planner. With `max_replans = 0` (Example 3) the first failure ends the run immediately: status `"failed"`, `completed: ["s1", "s2"]`, `replans: 0`, and the planner is called only once.

If you increment first and check afterwards, or test `replans > max_replans`, you make one extra planner call. In Example 3 the scripted planner has only one reply, so the extra call crashes with `GCError: FakeLLM script exhausted after 1 calls`, which the judge reports as a Runtime Error.

## 6. Plan before you code

```
completed = [], results = {}
plan(failed): build the payload from goal, completed, failed; call the planner; json.loads the reply
run_step(step) -> (result, error):
    resolve each top-level {"$ref": x}: missing -> (None, "unresolved reference x")
    tool not in tools -> (None, "unknown tool T")
    call it: success -> (r, None); ToolError e -> (None, str(e))

steps, i, replans = plan(None), 0, 0
while i < len(steps):
    step = steps[i]
    already in results -> i += 1, continue
    result, error = run_step(step)
    success -> record in results and completed, i += 1
    failure -> replans >= max_replans ? return "failed"
               replans += 1; steps, i = plan(failure), 0
return "completed"
```

The step outcomes in one place:

| situation | tool called? | error string |
|---|---|---|
| id already in `results` | no | none, skipped |
| `$ref` to a step not in `results` | no | `"unresolved reference " + x` |
| tool not in `tools` | no | `"unknown tool " + tool` |
| tool raises `ToolError e` | yes | `str(e)` |
| tool returns `r` | yes | none, completes with `r` |

## 7. Build it one piece at a time

**Step 1: one planner helper.** The first call and every replan share it, so the payload format can't drift between them. `sort_keys=True` sorts the keys of the nested dicts too.

```python
def plan(failed):
    payload = json.dumps({"goal": goal, "completed": completed, "failed": failed}, sort_keys=True)
    resp = llm.complete([{"role": "system", "content": PLANNER}, {"role": "user", "content": payload}])
    return json.loads(resp.content)
```

The helper reads `completed` at call time, so every replan automatically includes everything finished so far. Sending only the failure (no history) is a common mistake: the planner can't see that s1 and s2 already ran, and the payload no longer matches.

**Step 2: resolve references before touching the tool.** A reference is a dict whose only key is `"$ref"`. Only top-level arg values are resolved.

```python
def run_step(step):
    args = {}
    for k, v in step["args"].items():
        if isinstance(v, dict) and set(v) == {"$ref"}:
            if v["$ref"] not in results:
                return None, "unresolved reference " + v["$ref"]
            v = results[v["$ref"]]
        args[k] = v
```

Return early on a missing reference. If you pass the placeholder through, `refund_charge` is called with `{"charge_id": {"$ref": "s2"}}`. A real payment API might reject it, or do something worse, and the error the planner sees becomes `refund_charge: bad arguments ...` instead of the real cause.

**Step 3: the tool call, with errors as values.** Returning `(result, error)` keeps the main loop flat: one `if error is None` branch for success, one path for every kind of failure.

```python
    if step["tool"] not in tools:
        return None, "unknown tool " + step["tool"]
    try:
        return tools[step["tool"]](**args), None
    except ToolError as e:
        return None, str(e)
```

**Step 4: the main loop.** Use an index and a `while`, not `for step in steps`, because `steps` is replaced in the middle of the loop.

```python
steps, i, replans = plan(None), 0, 0
while i < len(steps):
    step = steps[i]
    if step["id"] in results:
        i += 1
        continue
    result, error = run_step(step)
    if error is None:
        results[step["id"]] = result
        completed.append({"id": step["id"], "tool": step["tool"], "result": result})
        i += 1
        continue
    if replans >= max_replans:
        return {"status": "failed", "completed": [c["id"] for c in completed], "replans": replans, "results": results}
    replans += 1
    steps, i = plan({"id": step["id"], "tool": step["tool"], "error": error}), 0
```

An empty new plan (`[]`) is valid. The `while` condition is false straight away, and the run ends as `"completed"` with whatever finished before. That's what "unknown tool then empty plan" checks.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# The planner payload and its reply are both JSON.
import json

# The one failure a tool raises on purpose; it becomes an error string the planner can react to.
from gc_runtime import ToolError

# The exact system prompt every planner call uses.
PLANNER = "You are the planner. Reply with only a JSON list of steps, each {\"id\", \"tool\", \"args\"}."


# llm: the planner; tools: name -> function; max_replans: how many replan calls we may make.
def execute_plan(llm, tools, goal, max_replans):
    # State that outlives any one plan: finished steps in order, and id -> result.
    completed, results = [], {}

    # One helper for the first call and every replan, so the payload never drifts.
    def plan(failed):
        # sort_keys makes the string exact; completed is read now, so history is always current.
        payload = json.dumps({"goal": goal, "completed": completed, "failed": failed}, sort_keys=True)
        # Exactly two messages: the planner instructions and the JSON state.
        resp = llm.complete([{"role": "system", "content": PLANNER}, {"role": "user", "content": payload}])
        return json.loads(resp.content)  # the new list of steps

    # Run one step; returns (result, None) on success or (None, error string) on any failure.
    def run_step(step):
        args = {}  # the resolved arguments the tool will actually receive
        # Resolve top-level arguments only, as the problem says.
        for k, v in step["args"].items():
            # A reference is a dict whose only key is "$ref".
            if isinstance(v, dict) and set(v) == {"$ref"}:
                # The step it points to hasn't succeeded: fail before touching the tool.
                if v["$ref"] not in results:
                    return None, "unresolved reference " + v["$ref"]  # never call with a placeholder
                v = results[v["$ref"]]  # substitute that step's result string
            args[k] = v  # plain values pass through unchanged
        # The planner named a tool we don't have.
        if step["tool"] not in tools:
            return None, "unknown tool " + step["tool"]  # a failed step, not a crash
        # Run the tool; its own failures become data.
        try:
            return tools[step["tool"]](**args), None  # success
        # The tool reported a failure (e.g. a payment timeout).
        except ToolError as e:
            return None, str(e)  # the error the planner will see

    # First plan (failed is None); start at its first step; no replans used yet.
    steps, i, replans = plan(None), 0, 0
    # A while over an index, because a replan swaps `steps` mid-loop.
    while i < len(steps):
        step = steps[i]  # the next step of the current plan
        # Already succeeded (the planner restated it): never run a step twice.
        if step["id"] in results:
            i += 1  # move past it
            continue  # skip without calling anything
        result, error = run_step(step)  # attempt it
        # It worked.
        if error is None:
            results[step["id"]] = result  # later $refs and the skip check use this
            completed.append({"id": step["id"], "tool": step["tool"], "result": result})  # history for the planner
            i += 1  # on to the next step
            continue  # back to the top of the loop
        # Budget check BEFORE calling the planner: max_replans calls, never one more.
        if replans >= max_replans:
            # Out of replans: stop here and report what did finish.
            return {"status": "failed", "completed": [c["id"] for c in completed], "replans": replans, "results": results}
        replans += 1  # this replan is now spent
        # The new plan replaces the failed step and everything after it; restart at its first step.
        steps, i = plan({"id": step["id"], "tool": step["tool"], "error": error}), 0
    # Ran out of steps without an unrecoverable failure.
    return {"status": "completed", "completed": [c["id"] for c in completed], "replans": replans, "results": results}
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | completed s1, s2, s3b, s4b; 1 replan | `$ref` resolution, history in the replan payload, the new plan replaces s3 and s4 |
| Example 2 | same result; `get_order` called once | the skip rule for restated steps |
| Example 3 | failed after s1, s2; 0 replans; 1 planner call | `max_replans = 0` means no replan at all |
| no failures | completed r, e; 0 replans | the happy path, with a `$ref` |
| replan budget exhausted | failed; 2 replans; 3 `refund_charge` calls | the budget stops the third replan; the fourth scripted plan is never requested |
| budget exactly enough | completed s1, s2, t1; 2 replans | using the last replan is allowed |
| unresolved reference never calls tool | completed s1, s2, s3b, s4b; `refund_charge` never called | a missing `$ref` fails before the tool |
| unknown tool then empty plan | completed s1; 1 replan | the `"unknown tool wire_transfer"` error, and an empty plan ends the run |
| replan replaces the tail | completed s1, s2, s3b | the old s4 and s5 never run |
| failed id reused with new args | completed s1, s2, s3, s4; s3 = `"re_901"` | a failed id isn't in `results`, so it can run again |
| two failures, history grows | completed s1, s2, s3b, s4b; 2 replans | each replan sees the history so far |

## 10. Complexity

Each plan has at most 8 steps, and each replan restarts at index 0, so the loop visits at most `8 × (max_replans + 1)` steps. Each visit resolves a few arguments with dict lookups. Building the payload is O(size of `completed`) per planner call. All of it is negligible next to the planner and tool calls themselves.

In production the cost to bound is the number of model and tool calls. The replan budget caps planner calls at `max_replans + 1`, and the skip rule means each step id runs successfully at most once, however often the planner restates it. Real systems also cap the total number of tool calls, since a planner can keep inventing new step ids.

## 11. If you got Wrong Answer

Compare `tool_calls` first, then the planner payloads in `planner_calls`.

- **`get_order` and `find_duplicate` appear twice in Example 2, and `completed` lists s1 and s2 twice.** You're not skipping ids already in `results`.
- **The second planner payload has `"completed": []`.** Your replan sends only the failure. Build every payload from the shared `completed` list.
- **`refund_charge` is called with `{"charge_id": {"$ref": "s2"}}`.** You pass unresolved references through. Fail the step before calling the tool.
- **"replan replaces the tail" ends `"failed"` after s3b succeeds.** You prepended the new plan to the old tail, so the old s4 ran with an unresolved reference.
- **Runtime Error "FakeLLM script exhausted" in Example 3.** Off by one on the budget: you replan once more than `max_replans` allows.
- **The payload strings differ only in key order.** You forgot `sort_keys=True`.

## 12. Follow-ups an interviewer might ask

- *The process crashes after s2. How do you avoid re-running s1 and s2 on restart?* Persist `completed` and `results` after every step and replay from the log (problem 111, durable-workflow-replay).
- *Skipping by id assumes ids are stable. What if the planner renames a step?* Then the skip rule misses it, so side-effecting tools also need idempotency keys derived from their arguments (problem 119).
- *How would you validate a plan before running any of it?* Check the JSON shape, that every tool exists, that refs only point to earlier steps or completed ones, and that arguments match each tool's schema (problem 113, tool-args-schema-validation). Malformed planner JSON can be repaired or re-requested (problem 116).
- *The run ends `"failed"`. Then what?* Don't fail silently. Send the state (goal, completed, last error) to a human review queue (problem 110, human-approval-gates).
- *When is plan-and-execute better than a ReAct loop?* When the steps are predictable and you want fewer model calls: one planner call can schedule several tool calls, while ReAct (problem 101) pays one model call per round.
