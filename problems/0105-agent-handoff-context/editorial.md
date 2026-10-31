## Approach

A handoff is a filter plus a summary. The filter has one non-obvious invariant: **tool calls and tool results must stay paired**. Decide which call ids survive while walking assistant turns, then keep a tool message only if its id survived.

```python
for m in transcript:
    if m["role"] == "system":
        continue
    if m["role"] == "assistant":
        if m.get("private"):
            continue                              # its call ids never enter kept_ids
        m = copy.deepcopy(m)
        if "tool_calls" in m:
            m["tool_calls"] = [tc for tc in m["tool_calls"] if tc["name"] in allowed]
            kept_ids.update(tc["id"] for tc in m["tool_calls"])
            if not m["tool_calls"]:
                del m["tool_calls"]
        if "tool_calls" not in m and not m.get("content"):
            continue
    elif m["role"] == "tool" and m["tool_call_id"] not in kept_ids:
        continue
    carried.append(copy.deepcopy(m))
```

The summarizer gets the **carried** messages, not the raw transcript. Otherwise the private notes come back in through the summary.

## Common mistakes

- **Orphaned tool results.** Filtering the calls but not their results. Both Anthropic and OpenAI reject a tool result whose call isn't in the previous assistant turn.
- **Leaking the scratchpad.** Private reasoning ("fraud flag = true, don't tell them") ends up in front of a specialist that may quote it to the customer.
- **Summarizing the raw transcript.** The same leak, one step removed.
- **Empty assistant turns.** A turn left with no text and no calls is rejected by some providers and confuses others.
- **Mutating the input.** The triage transcript is usually persisted for audit; rewriting it in place corrupts the record.
- **Two system prompts.** Carrying triage's instructions makes the specialist route instead of solving.

## Production notes

- The OpenAI Agents SDK exposes this as `handoff(..., input_filter=...)` with helpers like `remove_all_tools`; LangGraph does it with a `Command(goto=..., update=...)` that rewrites the state. Both leave the filtering policy to you.
- Filtering by **tool visibility** is also a security boundary. A specialist that can't call `get_invoice` usually shouldn't see invoice contents either; pair this with problem 117 (tool-permission-scopes).
- Long transcripts need the token-budget treatment from problem 107 before handoff, and PII redaction (problem 162) if the specialist is a third-party model.
- Log the handoff (from, to, carried ids, summary) as a span; when a specialist misbehaves, the first question is always what context it received.
