## 1. What the problem is really asking

Tools don't know how big the model's context window is. A log search returns 4,000 lines, a ticket comes back with its whole comment history, and if you paste all of it into the next model call you either blow the context window or crowd out everything else. Before results go back to the model, you trim them to a token budget, with two promises to the model:

- **Errors are never cut.** An error message is small and is exactly what the model needs to fix its next call.
- **Nothing is cut silently.** Trimmed text ends with a marker that says how much is missing, and a trimmed list comes with a cursor for the next page.

Under the story, this is **budget arithmetic plus two prefix cuts**: reserve the errors, split the rest evenly with integer division, then cut each text at a token boundary or each list at an item boundary. The function is pure. The judge compares the full output dict: every entry's `content`, `truncated`, `next_cursor` and `tokens`, plus `total_tokens`, so the counts have to be exact.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `results` | list of `{"id", "tool", "type", "content"}` | one output entry each, in input order |
| `type` | `"text"`, `"list"` or `"error"` | picks the fitting rule |
| `content` | a string, or a list of strings or dicts | counted with `count_tokens` |
| `budget` | total tokens for all results | split after errors are charged |
| `count_tokens` | `gc_runtime`'s counter | words and single punctuation marks; a dict counts as sorted JSON |

Three details are easy to miss:

- **The tokenizer is a regex,** `\w+|[^\w\s]`. `PAY-4821` is three tokens (`PAY`, `-`, `4821`), and the marker `[truncated 19 tokens]` is five (`[`, `truncated`, `19`, `tokens`, `]`).
- **Fixed overheads are reserved before you cut.** A truncated text keeps `share - 5` tokens so that, with the marker, it costs exactly `share`. A truncated list keeps items summing to at most `share - 3`, because the cursor costs 3.
- **The share can be smaller than the overhead.** When `share < 5`, a truncated text is the marker alone, and it costs 5 anyway. That's one of the documented ways `total_tokens` can exceed `budget`.

## 3. Trace Example 1 by hand

Budget 40. Two results: a 41-token Jira ticket (`t1`, text) and a 13-token SQL error (`t2`).

| step | value |
|---|---|
| E (error tokens) | 13 |
| R = max(0, 40 − 13) | 27 |
| n (non-error results) | 1 |
| share = 27 // 1 | 27 |
| ticket fits? | 41 > 27, no |
| k = max(0, 27 − 5) | 22 |
| N = 41 − 22 | 19 |

The 22nd token of the ticket is the second `ledger`, so the kept text is

```
PAY-4821 Refund webhook drops events. Steps: create refund, wait 30s, check ledger. Expected: ledger [truncated 19 tokens]
```

That's 22 + 5 = 27 tokens. The error is kept whole at 13. `total_tokens` is exactly 40.

**Example 2** is a list. Budget 60, one result with four log dicts. Each dict is counted as `json.dumps(..., sort_keys=True)`: 31, 30, 30 and 29 tokens, 120 in all. That's over the share of 60, so walk items while the sum stays `<= 60 - 3 = 57`:

| item | size | running sum | ≤ 57? |
|---|---|---|---|
| 1 | 31 | 31 | yes, keep |
| 2 | 30 | 61 | no, stop |

One item is kept. The cursor is `base64("logs:1")`, which is `bG9nczox`. `tokens` is 31 + 3 = 34.

**The trickiest hidden case, "big item first blocks smaller later items".** Budget 20, one list. The first hit is 31 tokens, the next two are 5 and 4. The limit is `20 - 3 = 17`. The first item doesn't fit, so you stop **immediately**: zero items, cursor `base64("hits:0")` = `aGl0czow`, `tokens` 3. It's tempting to skip the big item and pack the two small ones (9 tokens fit), but then the cursor's offset would be wrong. The next page would start after an item the model never saw.

## 4. Key idea: cut at a token boundary, not a character count

The budget is enforced in tokens, so the cut must be in tokens. The rule: find the `k`-th match of the tokenizer regex and cut at its `end()`. The prefix `content[:end]` then tokenizes to exactly `k` tokens, because it ends at the end of a token and no later token has started.

"punctuation heavy cut" shows why a character estimate fails. The content is a config line, `retry.max=5; retry.base_ms=250; ...`, where almost every character is its own token. With budget 15, `k = 10`, and the cut lands after `retry.base_ms=`:

| tokens 1–10 |
|---|
| `retry` `.` `max` `=` `5` `;` `retry` `.` `base_ms` `=` |

`len(text) // 4` assumes four characters per token. That's a rough average for English prose, and it's wrong for JSON, code, IDs and log lines. The wrong solution that uses it fails 11 of the 15 cases.

## 5. Plan before you code

```
E = sum of error tokens; n = number of non-error results
share = max(0, budget - E) // n   (0 if n == 0)
for each result, in order:
    error: keep whole
    text:  fits -> whole; else keep k = max(0, share - 5) tokens + marker
    list:  fits -> whole; else keep the longest prefix with sum <= share - 3, add a cursor
    record tokens
total_tokens = sum of tokens
```

| type | fits | `truncated` | `next_cursor` | `tokens` |
|---|---|---|---|---|
| `error` | always kept | `False` | `None` | its count |
| `text` | `T <= share` | `False` | `None` | `T` |
| `text` | `T > share` | `True` | `None` | count of the cut text with marker |
| `list` | sum `<= share` | `False` | `None` | the sum |
| `list` | sum `> share` | `True` | base64 `id:offset` | kept sum + 3 |

## 6. Build it one piece at a time

**Step 1: the split.** Guard `n == 0`: in "no non-error results" both results are errors, and dividing by zero would crash.

```python
    errors = sum(count_tokens(r["content"]) for r in results if r["type"] == "error")
    n = sum(1 for r in results if r["type"] != "error")
    share = max(0, budget - errors) // n if n else 0
```

**Step 2: text.** The loop leaves `end` at the end of token `k`, then breaks when it reaches the token after it. With `k = 0` it breaks on the first iteration and `end` stays 0.

```python
def _truncate_text(text, share):
    total = count_tokens(text)
    if total <= share:
        return text, False
    k = max(0, share - MARKER_TOKENS)
    end = 0
    for i, m in enumerate(TOKEN_RE.finditer(text)):
        if i == k:
            break
        end = m.end()
    marker = "[truncated %d tokens]" % (total - k)
    return (text[:end] + " " + marker if k else marker), True
```

The fit test is `<=`. In "text one over", the budget is 41 and the ticket is exactly 41 tokens, so it's kept whole; a `<` test would truncate it.

**Step 3: lists.** First test the whole list against the full `share`; only a list that doesn't fit pays for a cursor. Then walk and `break` at the first item that doesn't fit.

```python
def _page_list(rid, items, share):
    sizes = [count_tokens(x) for x in items]
    if sum(sizes) <= share:
        return list(items), False, None, sum(sizes)
    kept, used = 0, 0
    for s in sizes:
        if used + s > share - CURSOR_TOKENS:
            break
        kept += 1
        used += s
    cursor = base64.b64encode(("%s:%d" % (rid, kept)).encode()).decode()
    return list(items[:kept]), True, cursor, used + CURSOR_TOKENS
```

`b64encode` takes and returns bytes, so encode the string first and decode the result.

**Step 4: assemble.** For text and errors, `tokens` is a fresh `count_tokens` of what you're returning. For lists it's the kept sum plus the cursor's flat 3, which isn't the same as counting the cursor string.

## 7. Full solution

```python
import base64  # cursors are base64("<id>:<offset>")
import re  # the judge's tokenizer regex, to find token boundaries

from gc_runtime import count_tokens  # the one counter the judge uses for every budget

TOKEN_RE = re.compile(r"\w+|[^\w\s]")  # same pattern as gc_runtime.tokenize: words and single punctuation
MARKER_TOKENS = 5  # "[truncated N tokens]" always tokenizes to 5
CURSOR_TOKENS = 3  # a cursor is charged a flat 3


def _truncate_text(text, share):  # fit one text into share tokens -> (content, truncated)
    total = count_tokens(text)  # T, the full size
    if total <= share:  # it fits, inclusive
        return text, False  # keep it whole, no marker
    k = max(0, share - MARKER_TOKENS)  # reserve room for the marker so the result costs share
    end = 0  # character offset where the kept prefix ends; 0 keeps nothing
    for i, m in enumerate(TOKEN_RE.finditer(text)):  # walk the tokens in order
        if i == k:  # we've passed k tokens
            break  # stop; end is the end of token k
        end = m.end()  # extend the prefix to the end of this token
    marker = "[truncated %d tokens]" % (total - k)  # tell the model how much is missing
    return (text[:end] + " " + marker if k else marker), True  # no leading space when nothing is kept


def _page_list(rid, items, share):  # fit one list -> (items, truncated, cursor, tokens)
    sizes = [count_tokens(x) for x in items]  # dicts count as sorted JSON inside count_tokens
    if sum(sizes) <= share:  # the whole list fits
        return list(items), False, None, sum(sizes)  # no cursor needed
    kept, used = 0, 0  # items kept so far and their tokens
    for s in sizes:  # walk from the start
        if used + s > share - CURSOR_TOKENS:  # this item would leave no room for the cursor
            break  # stop here; never skip ahead, or the offset would lose an item
        kept += 1  # keep it whole
        used += s  # and pay for it
    cursor = base64.b64encode(("%s:%d" % (rid, kept)).encode()).decode()  # where the next page starts
    return list(items[:kept]), True, cursor, used + CURSOR_TOKENS  # the prefix plus the cursor's cost


def budget_results(results, budget):  # trim every tool result to fit one shared budget
    errors = sum(count_tokens(r["content"]) for r in results if r["type"] == "error")  # E: charged first, never cut
    n = sum(1 for r in results if r["type"] != "error")  # results that share what's left
    share = max(0, budget - errors) // n if n else 0  # even split; no division when everything is an error
    out = []  # one entry per input result, in order
    for r in results:  # fit each result on its own
        entry = {"id": r["id"], "type": r["type"], "next_cursor": None}  # fields common to every type
        if r["type"] == "error":  # the model needs errors verbatim
            entry.update(content=r["content"], truncated=False, tokens=count_tokens(r["content"]))  # whole
        elif r["type"] == "text":  # cut at a token boundary with a marker
            content, cut = _truncate_text(r["content"], share)  # the kept text and whether it was cut
            entry.update(content=content, truncated=cut, tokens=count_tokens(content))  # count what we return
        else:  # a list: a prefix of whole items plus a cursor
            items, cut, cursor, used = _page_list(r["id"], r["content"], share)  # the kept page
            entry.update(content=items, truncated=cut, next_cursor=cursor, tokens=used)  # cursor charged at 3
        out.append(entry)  # keep input order
    return {"results": out, "total_tokens": sum(e["tokens"] for e in out)}  # what all of it costs
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | ticket cut to 27 tokens with `[truncated 19 tokens]`; total 40 | errors charged first; the marker is reserved |
| Example 2 | 1 item, cursor `bG9nczox`, 34 tokens | dicts counted as sorted JSON; the `share - 3` limit |
| Example 3 | everything whole; total 26 | `share = 25 // 2 = 12`; fits are inclusive |
| no non-error results | both errors whole; total 26 with budget 5 | `n == 0` guard; errors can exceed the budget |
| errors exceed budget | text is `[truncated 41 tokens]`, list has 0 items and cursor `bDow`; total 21 | `R = max(0, ...)` and share 0 |
| share below marker | marker alone (5 tokens) next to a 3-token text that fits; total 8 | `k = 0` gives the marker with no leading space |
| share exactly marker plus one | `PAY [truncated 40 tokens]`, 6 tokens | `k = 1` |
| text exactly fits | kept whole at 41 with budget 42 | the whole-text path |
| text one over | kept whole at 41 with budget 41 | `<=`, not `<` |
| punctuation heavy cut | `retry.max=5; retry.base_ms= [truncated 19 tokens]` | cutting by regex token, not characters |
| big item first blocks smaller later items | 0 items, cursor `aGl0czow`, 3 tokens | `break`, never skip ahead |
| list cursor with zero items | 0 items, cursor `bG9nczow` | an empty page still gets a cursor |
| empty list and empty text | both whole, 0 tokens | empty content with share 0 still fits |
| many results mixed | 15 results; total 801 with budget 900 | everything together; unused share isn't redistributed |
| large log search | 22 of 120 logs, cursor `cS03NzoyMg==`; ticket whole | a large real page |

## 9. Complexity

One pass to charge errors, then one pass over each result's tokens or items: O(total tokens) overall, plus O(items) `count_tokens` calls for lists. It runs once per model turn, next to a model call that costs far more.

The production concern is what the trimming throws away. Even splitting is predictable and stops one huge result from starving the others, but it wastes share: in "many results mixed" the total is 801 of 900, because the texts that fit don't hand their unused tokens to the lists that didn't. Smarter schemes redistribute leftover share, weight it by relevance, keep the head and tail of a stack trace, or store a large result behind a handle the agent can read with a follow-up tool call.

## 10. If you got Wrong Answer

- **Nearly every case is off, by small amounts.** You estimated tokens with `len(text) // 4`. Use `count_tokens` and cut at regex token boundaries.
- **Example 1's ticket is 32 tokens instead of 27.** You kept `share` tokens and then added the marker. Keep `share - 5`.
- **Example 1's ticket has no marker.** Silent truncation. The model will treat half a ticket as the whole ticket.
- **Example 1's SQL error is cut, or Example 3's share is 10 instead of 12.** You treated errors like other results. Charge them first and keep them whole.
- **"big item first blocks smaller later items" returns two items with cursor offset 2.** You skipped the big item and kept packing. Stop at the first item that doesn't fit.
- **"text one over" is truncated.** Your fit test is `<`. Use `<=`.
- **"share below marker" content starts with a space.** When `k == 0`, return the marker alone.

## 11. Follow-ups an interviewer might ask

- *How would the model fetch the next page?* Give the tool `cursor` and `limit` arguments, and have the client decode `id:offset` and call it again. Make cursors opaque and signed so the model can't forge an offset into another tenant's results (problem 170, cursor-pagination).
- *Why not just summarize big results with a cheap model?* You can, and it's often better for prose. But summaries can drop the one line that mattered, and they cost a model call. Truncation with a marker is free and honest about what's missing.
- *What if the budget should depend on the rest of the prompt?* Compute it from the context window minus the system prompt, history and expected output. That's packing the whole context under a budget (problem 107, memory-under-token-budget, and problem 157, context-packing).
- *Which tokenizer should a real system use?* The provider's: Anthropic's token counting endpoint, or `tiktoken` for OpenAI models, or a calibrated estimator with a safety margin. Never a character ratio for a hard limit.
- *Should errors ever be trimmed?* Only if one is huge, such as a full stack trace. Then keep the head and the tail, because the exception type and the innermost frame carry the signal.
