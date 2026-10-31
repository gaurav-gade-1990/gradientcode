## Approach

Three steps: reserve, split, fit.

1. **Reserve the errors.** An error is the one result the model must see verbatim, so it is charged first and never cut. $R = \max(0, \text{budget} - E)$.
2. **Split evenly.** $\text{share} = \lfloor R / n \rfloor$ per non-error result. Even splitting is predictable and keeps one huge result from starving the rest.
3. **Fit each result.** Text is cut at a token boundary and gets a marker that tells the model how much is missing. Lists keep whole items and get a cursor the model can pass back to fetch the next page.

```python
def _truncate_text(text, share):
    total = count_tokens(text)
    if total <= share:
        return text, False
    k = max(0, share - 5)                       # the marker costs 5 tokens
    end = 0
    for i, m in enumerate(TOKEN_RE.finditer(text)):
        if i == k:
            break
        end = m.end()
    marker = "[truncated %d tokens]" % (total - k)
    return (text[:end] + " " + marker if k else marker), True
```

Cutting at `m.end()` of the k-th token means the prefix tokenizes to exactly k tokens, so the result costs exactly `share` whenever `share >= 5`. For lists, walk the items, stop at the first one that would push the sum over `share - 3`, and encode `id:offset` as the cursor.

## Common mistakes

- **Truncating errors.** `ERROR: relation "orders_v2" does not exist (SQLSTA... [truncated]` loses the SQLSTATE the model needed to fix the query, so it retries the same broken call. Errors are small and high-signal; keep them whole.
- **Silent truncation.** If you cut with no marker, the model treats half a ticket as the whole ticket and confidently answers from it. The marker turns "missing" into something the model can reason about ("ask for the rest").
- **Not reserving the marker.** Keeping `share` tokens and then appending the marker overshoots every truncated result by 5. Across 20 tool results that is 100 tokens past a budget that was supposed to be hard.
- **Estimating with `len(text) // 4`.** The 4-characters-per-token rule is a rough average for English prose. JSON, code, IDs and log lines tokenize very differently, so the estimate both overshoots and undershoots. Count with the same tokenizer that enforces the budget.
- **Skipping items to pack the page.** Leaving out a big item and taking smaller ones after it makes the cursor offset wrong: the next page starts after an item the model never saw, so it is lost for good.

## Production notes

- MCP tool results come back as `content` blocks with no size limit, and Claude Code, for example, caps and warns on very large MCP outputs. Do the budgeting in your client or gateway, where you know the model's context window and what else is in the prompt.
- Real systems count with the provider's tokenizer (Anthropic's `count_tokens` endpoint, `tiktoken`) or a calibrated estimator with a safety margin. Never trust a character ratio for hard limits.
- Prefer giving tools their own pagination (`limit`, `cursor` arguments) so the model can ask for page 2 itself. Make cursors opaque and signed, so the model cannot forge offsets into another tenant's results (see cursor pagination, problem 170).
- Smarter splits weight the share by relevance or redistribute unused share. Head-and-tail truncation keeps the end of a stack trace. Large results can also be summarized by a cheap model or stored behind a handle the agent can read with a follow-up tool call.
- This pairs with building the context under a token budget (problem 107) and choosing retrieved chunks under a budget (problem 157).
