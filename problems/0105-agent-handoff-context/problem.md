Your support stack has a triage agent that talks to the customer first and then hands off to a specialist (billing, shipping, security). Write the function that builds the specialist's starting transcript.

`handoff(transcript, specialist, llm)` gets:

- `transcript`, the triage conversation, a list of messages shaped like this:
  - `{"role": "system", "content": str}`
  - `{"role": "user", "content": str}`
  - `{"role": "assistant", "content": str or None, "tool_calls": [{"id", "name", "arguments"}]}`. `tool_calls` is optional, and `"private": True` marks the triage agent's internal scratchpad.
  - `{"role": "tool", "tool_call_id": str, "content": str}`
- `specialist`, `{"name": str, "system_prompt": str, "tools": [tool names]}`.
- `llm`, a `gc_runtime.FakeLLM` that writes the handoff summary.

Build the **carried** messages by walking the transcript in order:

| message | rule |
|---|---|
| `system` | drop (the specialist has its own prompt) |
| `user` | keep unchanged |
| `assistant` with `"private": True` | drop it, and the results of every tool call it made |
| other `assistant` | keep only the tool calls whose `name` is in `specialist["tools"]`, and if none are left, remove the `tool_calls` key; if it ends up with no tool calls and no content (`None` or `""`), drop the message |
| `tool` | keep only if its `tool_call_id` belongs to a tool call you kept |

Kept messages keep exactly the keys they had, except for the filtered `tool_calls`. Don't mutate the input.

Then call the model **once** for the summary:

```python
llm.complete([{"role": "system", "content": "Summarize this conversation for the " + specialist["name"] + " agent in at most three sentences."}] + carried)
```

and return:

```python
[{"role": "system", "content": specialist["system_prompt"]}] + carried + [{"role": "system", "content": "Handoff summary from triage: " + summary}]
```

where `summary` is the response's `.content`.

The judge records the exact messages sent to the summarizer and the transcript you return.

**Constraints**

- At most 30 messages
- Tool call ids are unique within a transcript
