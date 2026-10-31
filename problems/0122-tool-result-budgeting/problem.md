Your agent's tools sometimes return far more than the context window can hold: a 4,000-line log search, a Jira ticket with its whole comment history. Before the results go back to the model, trim them to a token budget without hiding failures from it.

Implement `budget_results(results, budget)`. Each result is `{"id": str, "tool": str, "type": "text" | "list" | "error", "content": ...}`, where `content` is a string for `text` and `error`, and a list of strings or dicts for `list`. Count tokens only with `gc_runtime.count_tokens` (a dict counts as its `json.dumps(..., sort_keys=True)`).

**1. Split the budget.**

- Every `error` result is kept whole, and its tokens are charged first: $E = \sum$ `count_tokens(content)` over errors.
- $R = \max(0,\ \text{budget} - E)$. With $n$ non-error results, each gets $\text{share} = \lfloor R / n \rfloor$. There is no redistribution of unused share.

**2. Fit each non-error result into its share.**

| type | fits (`tokens <= share`) | does not fit |
|---|---|---|
| `text` | keep whole | keep the first $k = \max(0, \text{share} - 5)$ tokens, then the marker |
| `list` | keep every item | keep the longest **prefix** of items whose token sum is `<= share - 3`, then a cursor |

- **Text truncation.** With $T$ = `count_tokens(content)`, the kept text is `content[:end]`, where `end` is the end offset of the $k$-th match of `gc_runtime`'s token regex `\w+|[^\w\s]` (use `re.finditer`; `end = 0` when $k = 0$). Append `" [truncated N tokens]"` with $N = T - k$. When $k = 0$ the content is the marker alone, with no leading space: `"[truncated N tokens]"`. The marker always costs 5 tokens.
- **List pagination.** Items are whole; never split or skip one. Walk from the start and stop at the first item that would push the sum over `share - 3`. The cursor is `base64.b64encode("<id>:<offset>".encode()).decode()`, where `offset` is the number of items kept. A cursor is charged a flat 3 tokens.

**3. Return** `{"results": [...], "total_tokens": int}` with one entry per input result, in input order:

```
{"id": ..., "type": ..., "content": <kept string or list>, "truncated": bool, "next_cursor": str or None, "tokens": int}
```

- `truncated` is True exactly when the text was cut or the list lost items. `next_cursor` is None except for a truncated list.
- `tokens` is `count_tokens(content)` for `text` and `error`, and the sum of the kept items' tokens, plus 3 when there is a cursor, for `list`.
- `total_tokens` is the sum of every entry's `tokens`. It can exceed `budget` only through errors, or when a share is smaller than the marker (5) or the cursor (3).

**Constraints**

- `0 <= budget <= 10^5`, at most 50 results.
- Result ids are unique and contain no `:`.
- Don't estimate tokens from characters. The judge counts with `count_tokens`.
