Your support agent's conversations get long, and every turn resends the whole history. Write the function that builds the prompt for the next model call so that it stays under the context budget.

`build_context(messages, budget, keep_last, reserve, summarize)` gets:

- `messages`, the full conversation. `messages[0]` is the system prompt. After it come `user`, `assistant` and `tool` messages. An assistant message may carry `tool_calls`, and the `tool` messages that answer it come right after it.
- `budget`, the token limit, measured with `gc_runtime.message_tokens(list_of_messages)`.
- `keep_last`, the number of most recent **units** that are always kept.
- `reserve`, tokens set aside for the summary message.
- `summarize(list_of_messages)`, which returns a summary string. It's an LLM call, so call it only when you have to.

**Units.** An assistant message with a non-empty `tool_calls`, together with every `tool` message that immediately follows it, is one unit. Every other message after the system prompt is a unit by itself. Units are never split.

**Selection.**

1. Pin the system prompt and the last `keep_last` units (all of them if there are fewer). They're always included, even if they alone exceed the budget. Let `used = message_tokens(pinned messages)`.
2. Walk the older units from **newest to oldest**. Include a unit if `used + message_tokens(unit) <= budget - reserve`, and add its tokens to `used`. **Stop at the first unit that doesn't fit**, even if an older, smaller one would.
3. The units you didn't include are the **dropped** messages. If there are any, call `summarize(dropped)` exactly once, with the messages in their original order.

**Output.** Return a new list: the system prompt, then `{"role": "system", "content": "Summary of earlier conversation: " + summary}` if you summarized, then the included and pinned messages in their original order.

The judge records your context, its token count, and every `summarize` call.

**Constraints**

- `1 <= len(messages) <= 40`
- `0 <= keep_last`, `0 <= reserve < budget`
