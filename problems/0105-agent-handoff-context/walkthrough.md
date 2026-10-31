## 1. What the problem is really asking

A triage agent has been talking to the customer. Now a specialist takes over, and you decide what the specialist gets to see. Under the story this is a **filter over a message list** with one pairing rule, followed by one model call:

- drop what the specialist must not see (the triage system prompt, the private scratchpad),
- drop tool calls the specialist can't make, **and the results of those calls**,
- clean up any assistant turn that ends up empty,
- ask the model for a summary of what's left, then wrap it all in the specialist's own system prompt.

The judge records three things: the exact messages you sent to the summarizer, the transcript you return, and whether the input transcript is unchanged afterwards. So a leak can fail you in two places (the returned transcript or the summarizer call), and an in-place edit fails you even when both lists look right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `transcript` | the triage conversation, a list of message dicts | walk it once, in order, building `carried` |
| `m["role"]` | `"system"`, `"user"`, `"assistant"` or `"tool"` | picks the rule from the table |
| `m["private"]` | `True` on the triage agent's internal scratchpad turns | the whole turn and its tool results are dropped |
| `m["tool_calls"]` | optional list of `{"id", "name", "arguments"}` on an assistant turn | filtered to the specialist's tools |
| `m["tool_call_id"]` | on a tool message, the id of the call it answers | kept only if that call was kept |
| `specialist` | `{"name", "system_prompt", "tools"}` | `name` goes in the summary prompt, `tools` is the allow-list |
| `llm` | a `FakeLLM` scripted to answer with the summary | called exactly once |

Three details are easy to miss:

- **"No content" means `None` or `""`.** `not m.get("content")` covers both. Testing `is None` alone keeps an assistant turn whose content is the empty string.
- **The `tool_calls` key goes away when the list ends up empty.** An assistant turn with text and no allowed calls becomes a plain text turn, with no `"tool_calls": []` left behind.
- **Keep every other key.** User messages may carry `"name"`, assistant turns `"model"`. The rule is "keep exactly the keys they had", so copy the message rather than rebuilding it from `role` and `content`.

## 3. Trace Example 1 by hand

The specialist is billing, with tools `get_invoice`, `issue_refund` and `get_order`. Walk the eight messages, tracking the set of kept call ids:

| # | message | rule | result | kept ids |
|---|---|---|---|---|
| 1 | system: triage prompt | system | drop | {} |
| 2 | user: "I was charged twice..." | user | keep | {} |
| 3 | assistant, **private**, calls c1 `classify_sentiment` | private | drop, c1 never enters the set | {} |
| 4 | tool c1: "negative (0.91)" | c1 not kept | drop | {} |
| 5 | assistant "Let me pull up that order.", calls c2 `get_order` | `get_order` is allowed | keep with c2 | {c2} |
| 6 | tool c2: "A-1182: $84.00 ..." | c2 kept | keep | {c2} |
| 7 | assistant, content `None`, calls c3 `transfer_to_agent` | not allowed; no calls left and no content | drop | {c2} |
| 8 | tool c3: "transferring" | c3 not kept | drop | {c2} |

`carried` is messages 2, 5 and 6. The summarizer receives the summary prompt for "billing" followed by those three. The returned transcript is:

```python
[{"role": "system", "content": "You are Acme's billing specialist. You can look up invoices and issue refunds up to $200."},
 {"role": "user", "content": "I was charged twice for order A-1182."},
 {"role": "assistant", "content": "Let me pull up that order.",
  "tool_calls": [{"id": "c2", "name": "get_order", "arguments": {"order_id": "A-1182"}}]},
 {"role": "tool", "tool_call_id": "c2", "content": "A-1182: $84.00, paid 2026-10-20, two captures on card ending 4242"},
 {"role": "system", "content": "Handoff summary from triage: Customer reports a double charge on order A-1182 ($84.00, card 4242)."}]
```

**The subtle hidden case, "private turn calling an allowed tool".** The private turn calls `get_invoice`, which billing *is* allowed to use, and the result says `"INV-77: $40.00, internal fraud flag=true"`. If you filter tool calls by name before checking `private`, that id survives and the fraud flag reaches the specialist. The private check has to come first and short-circuit everything else about that turn. The expected carried list is just the user message and `"I'll connect you with billing."`.

## 4. Key idea: decide which ids survive, then filter tool messages by id

Tool calls and tool results come in pairs. Every provider API checks that a `tool` message answers a call in an earlier assistant turn. Anthropic and OpenAI both return a 400 for an orphaned result. So you can't filter tool messages by their own content. Each one inherits the fate of the call it answers.

Because a result always comes *after* its call, one forward pass is enough. When you keep an assistant turn, add the ids of its surviving calls to `kept_ids`. When you reach a tool message, keep it only if its `tool_call_id` is in that set. A private turn simply never adds its ids, so its results fall out automatically, with no separate rule needed.

In Example 2 this is what drops the invoice result. The assistant turn `"Checking both."` calls `t1 track_package` and `t2 get_invoice`. Shipping has only the first, so the turn keeps its text and `t1`, `kept_ids` is `{t1}`, and the `t2` result `"INV-2001: $129.00 paid"` is dropped. Keeping it would give the shipping agent a result for a call that, as far as its transcript shows, nobody made.

## 5. Key idea: summarize the carried messages, not the raw transcript

The summary is the second way private information can leak. If you send the raw `transcript` to the summarizer, the model sees the triage system prompt, the scratchpad and the hidden lookups, and anything it writes about them lands in the specialist's context as "Handoff summary from triage: ...". The filter would be pointless.

So build `carried` first, then use the **same list** for both the summarizer call and the returned transcript. The judge checks `summarizer_calls`, so this mistake fails even though your returned transcript is perfect.

## 6. Plan before you code

```
allowed = set(specialist tools); kept_ids = {}; carried = []
for m in transcript, in order:
    system    -> skip
    user      -> append a copy
    assistant -> private? skip
                 copy it; if it has tool_calls:
                     keep only allowed calls, add their ids to kept_ids
                     none left -> delete the key
                 no tool_calls and no content -> skip
                 append
    tool      -> append a copy only if tool_call_id in kept_ids
summary = llm.complete([summary prompt] + carried).content
return [specialist system prompt] + carried + [summary message]
```

What happens to an assistant turn after filtering:

| calls left | content | result |
|---|---|---|
| some | anything, even `None` | keep, with the filtered `tool_calls` |
| none | non-empty text | keep, without the `tool_calls` key |
| none | `None` or `""` | drop |

## 7. Build it one piece at a time

**Step 1: the easy roles.** System messages are skipped, users are copied. A deep copy keeps the returned messages independent of the input, so nothing you or the caller does later can change one through the other.

```python
allowed = set(specialist["tools"])
kept_ids = set()
carried = []
for m in transcript:
    role = m["role"]
    if role == "system":
        continue
    if role == "user":
        carried.append(copy.deepcopy(m))
```

**Step 2: the assistant turn.** Check `private` before anything else. Then copy the message *before* you touch `tool_calls`. Assigning `m["tool_calls"] = ...` on the original dict rewrites the caller's transcript, which is the triage record you might be storing for audit. The judge catches this with `input_unchanged: False`.

```python
    elif role == "assistant":
        if m.get("private"):
            continue
        m = copy.deepcopy(m)
        if "tool_calls" in m:
            m["tool_calls"] = [tc for tc in m["tool_calls"] if tc["name"] in allowed]
            kept_ids.update(tc["id"] for tc in m["tool_calls"])
            if not m["tool_calls"]:
                del m["tool_calls"]
        if "tool_calls" not in m and not m.get("content"):
            continue
        carried.append(m)
```

The empty-turn check runs *after* the filter, because a turn only becomes empty once its calls are gone. That's what happens to the `transfer_to_agent` turn in Example 1.

**Step 3: tool messages, by id.**

```python
    elif role == "tool":
        if m["tool_call_id"] in kept_ids:
            carried.append(copy.deepcopy(m))
```

**Step 4: one summary call, then assemble.** The prompt string and the wrapper strings must match the problem exactly, character for character.

```python
prompt = "Summarize this conversation for the " + specialist["name"] + " agent in at most three sentences."
summary = llm.complete([{"role": "system", "content": prompt}] + carried).content
return ([{"role": "system", "content": specialist["system_prompt"]}] + carried
        + [{"role": "system", "content": "Handoff summary from triage: " + summary}])
```

## 8. Full solution

Every line carries a comment saying what it does and why.

```python
# Deep copies keep the caller's triage transcript untouched (it's often the audit record).
import copy


# transcript: the triage conversation; specialist: who takes over; llm: writes the summary.
def handoff(transcript, specialist, llm):
    # The tools the specialist can call; any other call is invisible to it.
    allowed = set(specialist["tools"])
    # Ids of the tool calls we keep; a tool result survives only if its call did.
    kept_ids = set()
    # The filtered messages, used both for the summary and the new transcript.
    carried = []
    # One forward pass: a result always comes after its call, so kept_ids is ready in time.
    for m in transcript:
        role = m["role"]  # the rule depends only on the role
        # The triage instructions would make the specialist route instead of solve.
        if role == "system":
            continue  # the specialist gets its own system prompt at the end
        # What the customer said is always relevant.
        if role == "user":
            carried.append(copy.deepcopy(m))  # copied, every key kept
        # The triage agent's own turns need filtering.
        elif role == "assistant":
            # Internal scratchpad: drop the turn; its call ids never reach kept_ids.
            if m.get("private"):
                continue  # so its tool results are dropped too
            m = copy.deepcopy(m)  # edit a copy, never the caller's message
            # Only turns that asked for tools have calls to filter.
            if "tool_calls" in m:
                # Keep just the calls the specialist could have made itself.
                m["tool_calls"] = [tc for tc in m["tool_calls"] if tc["name"] in allowed]
                kept_ids.update(tc["id"] for tc in m["tool_calls"])  # their results may stay
                # Nothing left: remove the key rather than leave an empty list.
                if not m["tool_calls"]:
                    del m["tool_calls"]  # now it's a plain text turn
            # No calls and no text (None or ""): an empty turn providers reject.
            if "tool_calls" not in m and not m.get("content"):
                continue  # drop it
            carried.append(m)  # the filtered copy
        # A tool result lives or dies with the call it answers.
        elif role == "tool":
            # Its call was kept, so the pairing stays valid.
            if m["tool_call_id"] in kept_ids:
                carried.append(copy.deepcopy(m))  # copied, every key kept
    # The exact summary instruction from the problem, naming the specialist.
    prompt = "Summarize this conversation for the " + specialist["name"] + " agent in at most three sentences."
    # Summarize the CARRIED messages, so private notes can't leak back in through the summary.
    summary = llm.complete([{"role": "system", "content": prompt}] + carried).content
    # The specialist's own prompt, the filtered history, then the summary as a closing note.
    return ([{"role": "system", "content": specialist["system_prompt"]}] + carried
            + [{"role": "system", "content": "Handoff summary from triage: " + summary}])
```

## 9. How the test cases map to the code

| test case | expected carried messages | what it checks |
|---|---|---|
| Example 1 | user, assistant with c2, tool c2 | private turn and its result dropped; the emptied `transfer_to_agent` turn and its result dropped |
| Example 2 | user, assistant "Checking both." with t1 only, tool t1, user | a turn keeps its text and some of its calls; the t2 result is filtered by id |
| same transcript to shipping | user, assistant with c2, tool c2 | the filter depends on `specialist["tools"]`: shipping also has `get_order` |
| private turn calling an allowed tool | user, assistant "I'll connect you with billing." | `private` wins over an allowed tool name; the fraud flag never appears |
| empty string content dropped | the two user messages only | `""` counts as no content, both for the emptied turn and the text-only turn |
| empty string content with a kept tool call survives | the `""` assistant turn stays with only `u1`, and the `u1` result follows it | `""` content alone doesn't drop a turn; it must also have no calls left |
| multiple turns, interleaved | user, assistant `None` with call a, tool a, assistant text, user | a turn with `None` content stays if a call survives; a private turn mid-conversation is dropped |
| nothing but the user | user only | the minimal transcript; the summary is still requested once |
| extra keys preserved | user with `name`, assistant with `model`, tool with `name` | copy the message, don't rebuild it |

Every case also records `input_unchanged`, which is `True` for the reference solution in all eight.

## 10. Complexity

One pass over `M` messages, and each assistant turn filters its `k` calls with a set lookup, so it's O(M + total calls) plus the cost of copying. Memory is one copy of the kept messages. The one model call dominates everything in practice.

At scale, the cost to watch is the specialist's context size. Every message you carry is input tokens on every one of the specialist's future calls (problem 101 explains why the transcript is resent each time). Filtering by tool visibility already trims a lot; long triage conversations also need a token budget (problem 107) before the handoff.

## 11. If you got Wrong Answer

Check `input_unchanged` first, then compare `summarizer_calls`, then `transcript`.

- **`input_unchanged` is `False`.** You assigned `m["tool_calls"]` or deleted the key on the original message. Copy the assistant turn before filtering it.
- **A `tool` message whose call isn't in any assistant turn** (the t2 invoice result in Example 2, "transferring" in Example 1). You're keeping tool messages by role instead of by `tool_call_id`.
- **"Peek at the invoice silently first." or the fraud flag appears.** You're not dropping `private` turns, or you check `private` after deciding which ids to keep.
- **`summarizer_calls` contains the triage system prompt or the scratchpad, but the transcript looks right.** You summarized `transcript` instead of `carried`.
- **An `{"role": "assistant", "content": None}` turn in Example 1.** You're not dropping turns left with no calls and no content.
- **"empty string content dropped" still has an assistant turn.** You tested `content is None`; `""` counts as empty too.
- **"empty string content with a kept tool call survives" loses the assistant turn and the `u1` result.** You dropped the turn for its `""` content before filtering its calls (`wrong_drops_empty_content_with_calls.py`). Drop only when there's no content *and* no kept call.
- **Two system prompts at the start.** You carried the triage system message.

## 12. Follow-ups an interviewer might ask

- *Why not just give the specialist the summary and nothing else?* Summaries lose exact values, like an order id or an amount, that the specialist needs to act on. Carrying the user turns and the relevant tool results keeps the facts; the summary adds intent.
- *Is filtering by tool visibility just a context trick?* It's also a security boundary. A specialist that can't call `get_invoice` usually shouldn't read invoice contents either. Pair it with explicit tool permission scopes (problem 117).
- *The triage transcript is 40,000 tokens long.* Apply a token budget before the handoff: keep the newest turns and summarize or drop old tool results (problem 107).
- *What if the specialist is a third-party model?* Redact PII from the carried messages before sending them (problem 162), and log what was carried so you can audit it.
- *How do you debug a specialist that misbehaves?* Log the handoff as a span: from, to, the carried ids and the summary. The first question is always what context it received.
