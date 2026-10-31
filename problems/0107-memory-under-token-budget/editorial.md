## Approach

Group, pin, walk back, summarize the rest.

```python
units = group(messages[1:])            # assistant+tool_calls with its tool results = one unit
cut = max(0, len(units) - keep_last)
older, tail = units[:cut], units[cut:]
used = message_tokens([system] + flatten(tail))

kept, j = [], len(older) - 1
while j >= 0 and used + message_tokens(older[j]) <= budget - reserve:
    used += message_tokens(older[j])
    kept.insert(0, older[j])
    j -= 1
dropped = flatten(older[:j + 1])       # always a contiguous prefix
head = [system] + ([summary_msg(summarize(dropped))] if dropped else [])
return head + flatten(kept + tail)
```

Stopping at the first unit that doesn't fit keeps the verbatim history contiguous. The model sees "summary, then everything since". That reads coherently, whereas a history with a hole in the middle doesn't.

## Common mistakes

- **Splitting a tool call from its result.** The provider rejects a `tool` message whose call isn't in the prompt, and an orphaned call without a result is just as invalid.
- **Skipping and continuing.** Squeezing a small old turn in after a big one doesn't fit produces a non-contiguous history, and the summary then contradicts what follows it.
- **Forgetting the reserve.** The selection fits, then the summary is added and the request is over the limit.
- **Filling oldest-first.** The greeting survives while the turns the user is talking about get summarized.
- **Summarizing every turn.** An extra LLM call per request, for nothing.

## Production notes

- Real systems count tokens with the provider's tokenizer (Anthropic's `count_tokens` endpoint, `tiktoken` for OpenAI) and add tool-definition tokens to the pinned set.
- Cache the summary and summarize incrementally ("previous summary plus newly dropped turns"), so each turn costs one small call instead of re-summarizing the whole history.
- The pinned system prompt plus a stable summary is a stable prefix, which is exactly what prompt caching rewards (problem 128).
- LangGraph's `trim_messages` and LangChain's `ConversationSummaryBufferMemory` implement this policy. Check how they group tool calls before relying on them. Pair with problem 105 (agent-handoff-context) and, for retrieval-backed memory, problem 157 (context-packing).
