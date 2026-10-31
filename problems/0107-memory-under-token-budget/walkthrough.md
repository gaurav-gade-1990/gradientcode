## 1. What the problem is really asking

Every model call resends the whole conversation (problem 101). Long support chats eventually stop fitting in the context window, and even before that they get expensive. This function decides what the model sees on the next call.

The policy is the one most production agents use, often called a **summary buffer**:

> keep the system prompt, keep the most recent turns verbatim, and replace everything older with one summary.

Under the story it's a **greedy walk backwards over a list of groups**, with a running total and a hard stop. The only twists are that some messages must travel together (a tool call and its results), and that the walk stops at the first thing that doesn't fit instead of hunting for smaller things further back.

The judge's driver records three things: the context list you return, its token count via `message_tokens`, and **every call to `summarize`**, including the exact messages you passed. So the grade covers both what you keep and what you hand to the summarizer, and whether you called it at all.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `messages` | the full conversation; `messages[0]` is the system prompt | split off `messages[0]`, group the rest into units |
| `budget` | the token limit | the walk's ceiling is `budget - reserve` |
| `keep_last` | how many of the newest **units** are pinned | `units[-keep_last:]`, always kept |
| `reserve` | tokens set aside for the summary message you might add | subtracted from the ceiling |
| `summarize` | `summarize(list_of_messages) -> str`, a (fake) LLM call | called once, only when something was dropped |
| `message_tokens` | `gc_runtime.message_tokens(list)` | 3 tokens per message for role framing, plus content tokens, plus tool-call name and argument tokens |

Three details are easy to miss:

- **`keep_last` counts units, not messages.** The tool call `c1` and its result form one unit of 37 tokens. With `keep_last=4` the pinned tail is the tool unit plus the three short turns after it, which is five messages.
- **The pinned part is kept even when it alone is over the budget.** In "pinned tail exceeds budget" the system prompt plus four pinned units cost 81 tokens against a ceiling of `20 - 5 = 15`. You still return them. The walk just adds nothing.
- **The reserve is an estimate, not a guarantee.** In Example 3 the summary message ends up larger than the 10 reserved tokens and the context is 52 tokens against a budget of 40. The judge expects exactly that. Don't try to "fix" it by trimming more.

## 3. Trace Example 2 by hand

`CHAT` has a system prompt and seven units after it. Their costs from `message_tokens`:

| unit | messages | tokens |
|---|---|---|
| system | "You are Acme's support agent. Be concise." | 14 |
| 0 | user: "Hi, my desk lamp from order A-1182 flickers." | 15 |
| 1 | assistant: "Sorry to hear that. Is it the bulb or the switch?" | 16 |
| 2 | user: "The switch, I think." | 9 |
| 3 | assistant `get_order` call `c1` + its tool result | 37 |
| 4 | assistant: "Your order is eligible for a replacement." | 11 |
| 5 | user: "Great, please send one." | 9 |
| 6 | assistant: "Done. A replacement ships tomorrow." | 10 |

Example 2 has `budget=120`, `keep_last=2`, `reserve=30`, so the ceiling is 90.

**Pin.** Units 5 and 6 plus the system prompt: `14 + 9 + 10 = 33`. `used = 33`.

**Walk back from unit 4:**

| unit | cost | used if included | ≤ 90? | action |
|---|---|---|---|---|
| 4 | 11 | 44 | yes | include |
| 3 | 37 | 81 | yes | include (both messages) |
| 2 | 9 | 90 | yes, exactly | include |
| 1 | 16 | 106 | no | **stop** |

**Drop and summarize.** Units 0 and 1 are left, so `summarize` is called once with those two messages in order. The fake returns `"2 earlier messages; customer first said: Hi, my desk lamp from order A-1182 flickers."` and the context becomes:

```python
[system,
 {"role": "system", "content": "Summary of earlier conversation: 2 earlier messages; customer first said: ..."},
 user "The switch, I think.", assistant tool_call c1, tool c1, assistant "...eligible...", user "Great...", assistant "Done..."]
```

That's 118 tokens. Note the `<=`: unit 2 lands exactly on 90 and still fits.

**The tricky one, "tool pair too big stops the walk".** Same chat, `budget=75`, `keep_last=2`, `reserve=0`. Pinned is 33. Unit 4 brings it to 44. Unit 3, the tool pair, would make 81 > 75, so the walk stops there. Units 2, 1 and 0 are small (9, 16, 15) and some of them would still fit, but they're older than the unit that failed, so they're dropped too. `summarize` receives five messages: units 0, 1, 2 and both messages of the tool unit. The context is 72 tokens.

## 4. Key idea: group before you count

A `tool` message is only valid if the assistant message that made the call is also in the prompt, and an assistant message with `tool_calls` is only valid if every call has its result. Providers reject either half on its own with a 400. So the unit of keeping and dropping isn't a message, it's:

- an assistant message with non-empty `tool_calls`, plus every `tool` message right after it, or
- any other single message.

The parallel-calls chat shows why "every `tool` message right after it" matters. The assistant turn "Checking both." makes two calls, `p1` and `p2`, and both results follow. That's one 68-token unit holding three messages. If you grouped only one result with the call, you could keep `p2`'s result and drop `p1`'s.

## 5. Key idea: stop at the first miss

Why not skip a unit that doesn't fit and keep looking for smaller, older ones? Because the result would have a hole in it. The model would see the summary, then a customer turn from early on, then a gap, then recent turns, and the summary would describe messages that appear *after* things it skipped. Stopping at the first miss guarantees the dropped messages are always a **contiguous prefix** of the history. The context then reads as "summary of everything up to here, then everything since, word for word."

It also makes the code simpler. The dropped part is `older[:j + 1]`, where `j` is where the walk stopped.

## 6. Plan before you code

```
system, rest = messages[0], messages[1:]
units = group rest (assistant-with-tool_calls swallows the tool messages after it)
tail  = last keep_last units; older = everything before
used  = message_tokens([system] + tail messages)
j = last index of older
while j >= 0 and used + tokens(older[j]) <= budget - reserve:
    used += tokens(older[j]); keep older[j]; j -= 1
dropped = messages of older[0 .. j]
head = [system] + ([summary message] if dropped else [])
return head + kept messages + tail messages, in original order
```

| situation | `summarize` called? | summary message in context? |
|---|---|---|
| everything fits | no | no |
| `keep_last` covers all units | no | no |
| at least one older unit dropped | once, with all dropped messages in order | yes, right after the system prompt |

## 7. Build it one piece at a time

**Step 1: group into units.** A manual index loop is easier than a `for` here, because one unit can consume several messages.

```python
system, rest = messages[0], messages[1:]
units, i = [], 0
while i < len(rest):
    unit = [rest[i]]
    i += 1
    if unit[0]["role"] == "assistant" and unit[0].get("tool_calls"):
        while i < len(rest) and rest[i]["role"] == "tool":
            unit.append(rest[i])
            i += 1
    units.append(unit)
```

Use `.get("tool_calls")`, not `["tool_calls"]`. Plain assistant messages don't have the key, and an empty list must count as "no tool calls".

**Step 2: split off the pinned tail.**

```python
cut = max(0, len(units) - keep_last)
older, tail = units[:cut], units[cut:]
used = message_tokens([system] + [m for u in tail for m in u])
```

The `max(0, ...)` handles `keep_last` larger than the number of units ("keep_last covers everything", `keep_last=20`). Don't write `units[-keep_last:]`: with `keep_last=0` that's `units[-0:]`, which is the *whole* list, not an empty one.

**Step 3: walk back with a hard stop.**

```python
kept = []
j = len(older) - 1
while j >= 0 and used + message_tokens(older[j]) <= budget - reserve:
    used += message_tokens(older[j])
    kept.insert(0, older[j])
    j -= 1
```

The condition is in the `while`, so the first unit that fails ends the loop. `insert(0, ...)` keeps `kept` in original order as you walk backwards.

**Step 4: summarize the prefix, once, and assemble.**

```python
dropped = [m for u in older[:j + 1] for m in u]
head = [system]
if dropped:
    head.append({"role": "system", "content": "Summary of earlier conversation: " + summarize(dropped)})
return head + [m for u in kept + tail for m in u]
```

The `if dropped` guard is what keeps Example 1 at zero summarize calls.

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# The judge's token counter: 3 per message plus content and tool-call tokens.
from gc_runtime import message_tokens


# summarize is an LLM call, so it must run at most once and only when something was dropped.
def build_context(messages, budget, keep_last, reserve, summarize):
    system, rest = messages[0], messages[1:]  # the system prompt is always pinned, apart from the units
    units, i = [], 0  # units we build, and our position in rest
    # A while loop, because one unit can consume several messages.
    while i < len(rest):
        unit = [rest[i]]  # every unit starts with one message
        i += 1  # that message is now consumed
        # An assistant turn that called tools owns the tool results that follow it.
        if unit[0]["role"] == "assistant" and unit[0].get("tool_calls"):
            # Swallow every consecutive tool message (parallel calls give more than one).
            while i < len(rest) and rest[i]["role"] == "tool":
                unit.append(rest[i])  # the result travels with its call
                i += 1  # consumed
        units.append(unit)  # a finished unit, never split later
    cut = max(0, len(units) - keep_last)  # max(0, ...) copes with keep_last > number of units
    older, tail = units[:cut], units[cut:]  # tail is pinned; older is what the walk may keep
    # The pinned part is paid for first, even if it alone is over the budget.
    used = message_tokens([system] + [m for u in tail for m in u])
    kept = []  # older units that fit, in original order
    j = len(older) - 1  # start with the newest older unit, right before the tail
    # Keep walking back only while the next unit fits; the first miss ends the walk.
    while j >= 0 and used + message_tokens(older[j]) <= budget - reserve:
        used += message_tokens(older[j])  # pay for this unit
        kept.insert(0, older[j])  # prepend, so kept stays oldest-first
        j -= 1  # move one unit further back
    dropped = [m for u in older[:j + 1] for m in u]  # always a contiguous prefix, in order
    head = [system]  # the context always opens with the system prompt
    # Only summarize when something was actually dropped: no wasted LLM call.
    if dropped:
        # One summarize call with every dropped message; its output goes right after the system prompt.
        head.append({"role": "system", "content": "Summary of earlier conversation: " + summarize(dropped)})
    # Kept units come before the pinned tail, so the result is in original order.
    return head + [m for u in kept + tail for m in u]
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | all 9 messages, 121 tokens, no summarize call | nothing dropped means no summary |
| Example 2 | summarize gets 2 messages; 118 tokens | the walk, the `<=` at exactly 90, the tool unit kept whole |
| Example 3 | summarize gets 7 messages; context is system, summary, last turn | a tight budget; the reserve is only an estimate (52 tokens > 40) |
| pinned tail exceeds budget | the 4 pinned units (5 messages) kept, 3 messages summarized | pinned units are kept no matter what, and they're counted in units |
| keep_last covers everything | everything kept, no summarize call, 121 tokens against a budget of 10 | `max(0, len(units) - keep_last)` |
| tool pair kept whole | the `c1` call and its result both kept; 3 messages summarized | a unit is included as a whole |
| tool pair too big stops the walk | `c1` pair plus units 0–2 summarized (5 messages); 72 tokens | stop at the first miss, even though older units would fit |
| parallel calls one unit | the 68-token unit with two results dropped whole; 4 messages summarized | one assistant turn with two `tool` results is one unit |
| keep_last zero | nothing pinned; the walk keeps 3 units and stops at the tool pair | `keep_last=0` doesn't mean "keep everything" |
| only system | just the system prompt, 14 tokens, no summarize call | the empty-history edge case |

## 10. Complexity

Grouping is O(n) in the number of messages. The walk calls `message_tokens` on each older unit once (twice in this code, which is fine), so the total work is O(total tokens). `kept.insert(0, ...)` is O(n) per insert, O(n²) worst case, which is irrelevant at 40 messages. With thousands of messages, append and reverse once at the end.

In production the real cost is the **summarize call**, a full LLM request. This function calls it at most once per turn, but a naive deployment still re-summarizes the whole dropped prefix on every turn. Cache the summary and summarize incrementally: the previous summary plus the units dropped since. The pinned system prompt plus a stable summary is also a stable prefix, which is what prompt caching rewards (problem 128).

## 11. If you got Wrong Answer

Compare `summarize_calls` first. It shows exactly which messages you dropped.

- **Example 1 or "only system" shows a summarize call with an empty list, or a summary message.** You call `summarize` unconditionally. Guard it with `if dropped`.
- **Example 2 keeps the greeting and drops the tool unit instead.** You filled oldest-first. The walk goes from newest to oldest, starting just before the pinned tail.
- **Example 2 keeps one more turn than expected (unit 1), and Example 3 keeps "Great, please send one."** You compared against `budget` and forgot to subtract `reserve`.
- **"tool pair too big stops the walk" or "parallel calls one unit" keeps an old turn after a gap.** You skipped the unit that didn't fit and kept walking. Put the fit test in the `while` condition so the first miss ends the loop.
- **"pinned tail exceeds budget" starts with a `tool` message whose call was summarized away.** You treated every message as its own unit, so `keep_last=4` pinned four messages instead of four units.
- **"keep_last zero" keeps everything.** You used `units[-keep_last:]`, and `units[-0:]` is the whole list.

## 12. Follow-ups an interviewer might ask

- *How would you avoid re-summarizing the whole history every turn?* Store the last summary with the index it covers. Next turn, call `summarize(previous_summary + newly_dropped)` only when the cut moves. One small call instead of a growing one.
- *What if the pinned tail alone is over the budget?* This problem keeps it and lets the request fail upstream. In production you'd truncate the largest tool result inside the tail (keep its head and tail, mark the cut) before sending, since tool outputs are usually the bulk.
- *Is greedy newest-first the best selection?* It maximizes recency, not relevance. If an old turn holds the order number the user keeps referring to, retrieve it by relevance instead, packing chunks under a budget (problem 157, context-packing).
- *How do you count tokens for real?* Use the provider's tokenizer or count-tokens endpoint, and include the tool definitions in the pinned cost: they're sent on every call.
- *How does this change when one agent hands off to another?* The receiving agent needs a curated slice, not a trimmed transcript. Problem 105 (agent-handoff-context) covers what to pass across.
