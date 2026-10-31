## 1. What the problem is really asking

Strip away the wording and this is the loop at the heart of every tool-using agent:

> ask the model → if it wants tools, run them and show it the results → ask again → stop when it answers or you run out of steps.

The model can't run code. It can only *ask* for a tool by emitting a structured tool call. Your code is the hands: it runs the tool and writes the result back into the conversation. The judge doesn't just check the final answer. It records **every transcript you sent**, so the shape of the conversation is what's being graded.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `llm` | a fake model that replays a script | `resp = llm.complete(messages, tools=list(tools))` |
| `resp.stop_reason` | `"end_turn"` or `"tool_use"` | decides whether you're done |
| `resp.content` | the model's text (may be `None` alongside tool calls) | returned as the answer, or stored in the assistant turn |
| `resp.tool_calls` | list of `ToolCall(id, name, arguments)` | each one must be run and answered |
| `tools` | `{"get_order": fn, ...}` | `tools[name](**arguments)` |
| `max_steps` | max number of **model calls** | your loop bound |

Two details are easy to miss:

- `list(tools)` on a dict gives you the tool **names**. That's what the fake expects for `tools=`.
- `tc.arguments` is a dict like `{"order_id": "A-1182"}`. The `**` spreads it into keyword arguments: `get_order(order_id="A-1182")`.

## 3. Trace Example 2 by hand

Script: the model first asks for two tools at once, then answers.

**Model call 1.** You send:

```python
[{"role": "user", "content": "Can I still return the lamps from order A-1182?"}]
```

It returns `stop_reason="tool_use"`, `content="Let me check both."`, and two calls, `call_1` (get_order) and `call_2` (get_refund_policy).

**Your work between calls.** Append, in this exact order:

```python
{"role": "assistant", "content": "Let me check both.",
 "tool_calls": [{"id": "call_1", "name": "get_order", "arguments": {"order_id": "A-1182"}},
                {"id": "call_2", "name": "get_refund_policy", "arguments": {"category": "lighting"}}]}
{"role": "tool", "tool_call_id": "call_1", "content": "order A-1182: 2x desk lamp, delivered ..."}
{"role": "tool", "tool_call_id": "call_2", "content": "lighting: refundable within 30 days ..."}
```

**Model call 2.** You send all four messages. The model returns `end_turn` with the final text, and you return it.

The thing to notice is that the transcript **only grows**. Every call resends everything, because the model has no memory between calls. The transcript *is* its memory.

## 4. Plan before you code

Write the plan as comments first. It's the fastest way to avoid the ordering bugs:

```
messages = [user turn]
repeat up to max_steps times:
    call the model with the full transcript
    if it answered: return the answer
    if this was the last allowed call: stop (don't run its tools)
    append the assistant turn (with its tool_calls)
    for each tool call, in order:
        work out the result string (success / ToolError / unknown tool)
        append a tool message carrying that call's id
return the sentinel
```

Then decide the three branches for a single tool call:

| situation | result string |
|---|---|
| `tc.name not in tools` | `"error: unknown tool " + tc.name` |
| the tool raises `ToolError e` | `"error: " + str(e)` |
| it returns `s` | `s` |

## 5. Build it one piece at a time

**Step 1: the skeleton that handles a direct answer.** This alone passes the "answers immediately" case.

```python
def run_agent(llm, tools, user_msg, max_steps):
    messages = [{"role": "user", "content": user_msg}]
    for step in range(max_steps):
        resp = llm.complete(messages, tools=list(tools))
        if resp.stop_reason == "end_turn":
            return resp.content
    return "STOPPED: max_steps reached"
```

**Step 2: record the assistant turn.** It has to come *before* any tool results. A tool result that points to a call the model never made is invalid, and real providers reject it with a 400.

```python
        messages.append({"role": "assistant", "content": resp.content,
                         "tool_calls": [tc.to_dict() for tc in resp.tool_calls]})
```

**Step 3: run every tool call and answer each one with its own id.**

```python
        for tc in resp.tool_calls:
            if tc.name not in tools:
                result = "error: unknown tool " + tc.name
            else:
                try:
                    result = tools[tc.name](**tc.arguments)
                except ToolError as e:
                    result = "error: " + str(e)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
```

Check the unknown-tool case *before* the `try`, rather than catching `KeyError`. A `KeyError` raised *inside* a real tool would otherwise be misreported as "unknown tool".

**Step 4: don't run tools on the last step.** If this was call number `max_steps`, you'll never call the model again, so nobody would read those results. Worse, a real tool may have side effects (sending an email, issuing a refund). Put the check after the `end_turn` test and before the append:

```python
        if step == max_steps - 1:
            break
```

## 6. Full solution

Every line carries a comment saying what it does and why.

```python
# The one exception type tools raise on purpose; anything else is a real bug and should surface.
from gc_runtime import ToolError

# The exact string the problem asks for when the step budget runs out.
SENTINEL = "STOPPED: max_steps reached"


# llm: scripted fake model; tools: name -> function; max_steps: max number of model calls.
def run_agent(llm, tools, user_msg, max_steps):
    # The transcript starts with just the customer's message. It only ever grows.
    messages = [{"role": "user", "content": user_msg}]
    # One iteration per model call, so the loop bound is exactly max_steps calls.
    for step in range(max_steps):
        # Send the WHOLE transcript every time: the model has no memory between calls.
        resp = llm.complete(messages, tools=list(tools))  # list(dict) = the tool names
        # The model answered instead of asking for tools.
        if resp.stop_reason == "end_turn":
            return resp.content  # that answer is the result of the run
        # This was the last allowed call: no one would read these tool results, so don't run them.
        if step == max_steps - 1:
            break  # fall through to the sentinel
        # Record the model's request first; a tool result must follow the call that asked for it.
        messages.append({"role": "assistant", "content": resp.content,
                         "tool_calls": [tc.to_dict() for tc in resp.tool_calls]})
        # Answer every tool call in the response, in the order the model made them.
        for tc in resp.tool_calls:
            # The model asked for a tool we don't have; check before calling so we never KeyError.
            if tc.name not in tools:
                result = "error: unknown tool " + tc.name  # tell the model, don't crash
            # The tool exists, so try to run it.
            else:
                # Guard the call: a failing backend must not end the conversation.
                try:
                    result = tools[tc.name](**tc.arguments)  # spread the dict as keyword arguments
                # The tool reported a failure (e.g. "order not found").
                except ToolError as e:
                    result = "error: " + str(e)  # errors become data the model can react to
            # Reply to this specific call, echoing its id so the model matches result to request.
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    # Only reached via the break: the budget ran out while the model still wanted tools.
    return SENTINEL
```

## 7. How the test cases map to the code

| test case | what it checks | line that handles it |
|---|---|---|
| Example 1 | the basic round trip: user, assistant turn with tool_calls, tool result | steps 2 and 3 |
| answers immediately | one call, no tools | `if resp.stop_reason == "end_turn"` |
| Example 2, three parallel calls then chained call | every call runs, in order, with its own id, and the loop keeps going across rounds | the `for tc in resp.tool_calls` loop with `tc.id` |
| Example 3 | `ToolError` becomes data and the loop continues | `except ToolError` |
| unknown tool | nothing is called, and the error string is exact | the `tc.name not in tools` branch |
| mixed error and success in one turn | an unknown tool in the same response doesn't stop the next call from running | each call gets its own branch inside the loop |
| max steps hit, last tools not run | the response to the final call is not acted on | `if step == max_steps - 1: break` |
| max_steps 1 with tool use | the same rule at its smallest | the same `break` |
| exactly max_steps calls ending in answer | an answer on the last call still wins | `end_turn` is checked *before* the step check |
| explicit ids from model | you echo the model's ids, not your own counter | `tc.id` |

## 8. Complexity

Each model call resends the whole transcript, so with `S` steps and `k` tool calls per step, the work is O(S²·k) in messages copied. That's fine at `S ≤ 10`. In production the same quadratic growth shows up as **token cost**: step 10 pays for the inputs of steps 1–9 again. That's why prompt caching and transcript trimming (problem 107) matter.

## 9. If you got Wrong Answer

Compare `model_calls` in the expected and actual output. The first transcript that differs tells you which bug you have:

- **The assistant turn is missing before the tool messages.** You forgot step 2.
- **Only one tool message for a multi-call response.** You're using `resp.tool_calls[0]`.
- **`tool_call_id` is `"call_1"` everywhere, or `0, 1, 2`.** Use `tc.id`.
- **`tool_runs` has an extra entry at the end.** You ran tools after the last step.
- **Runtime Error mentioning `ToolError`.** The exception escaped your loop.
- **Your answer is `"STOPPED: ..."` when the last call answered.** Your step check runs before the `end_turn` check.

## 10. Follow-ups an interviewer might ask

- *How would you run the tool calls in parallel?* Use a thread pool or `asyncio.gather`, but **append the results in call order**, not completion order (problem 103).
- *How do you stop an agent stuck repeating itself?* Add a loop guard before each tool call (problem 102).
- *The transcript is too long for the context window.* Summarize or drop old tool results under a token budget (problem 107).
- *How do you report tool errors more precisely?* Anthropic's `tool_result` has `is_error: true`, and MCP has `isError`. The model treats a flagged error differently from a normal string.
