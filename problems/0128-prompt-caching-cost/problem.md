Your agent sends the same 6,000-token system prompt and tool catalog on every turn. Finance wants to know what provider **prompt caching** would really save on last week's traffic. Write the cost model.

`prompt_cache_cost(calls, pricing)` replays the calls in order (their times never decrease).

Each call is `{"id", "t", "prefix_id", "prefix_tokens", "input_tokens", "output_tokens"}`. The prompt is a cacheable prefix (system prompt, tools and documents up to the cache breakpoint) of `prefix_tokens` tokens, identified by `prefix_id`, plus `input_tokens` of uncached suffix (the new user turn). `t` is in seconds.

`pricing` is `{"input_per_mtok", "output_per_mtok", "cache_write_mult", "cache_read_mult", "ttl_s", "min_cacheable_tokens"}`. Prices are US dollars per million tokens (illustrative). Writing the prefix into the cache costs `cache_write_mult` × the input price, and reading it back costs `cache_read_mult` × the input price.

The cache holds one expiry time per `prefix_id`, and it starts empty. For each call:

| condition | status | prefix billed at | cache effect |
|---|---|---|---|
| `prefix_tokens < min_cacheable_tokens` | `"uncacheable"` | `input_per_mtok` | none: no write and no refresh |
| `prefix_id` cached and `t < expires_at` | `"read"` | `cache_read_mult * input_per_mtok` | `expires_at = t + ttl_s` |
| otherwise | `"write"` | `cache_write_mult * input_per_mtok` | `expires_at = t + ttl_s` |

A call at exactly `expires_at` is a miss. The suffix is always billed at `input_per_mtok` and the output at `output_per_mtok`. A call's cost is

$$
\frac{\text{prefix\_tokens} \cdot p_{\text{prefix}} + \text{input\_tokens} \cdot p_{\text{in}} + \text{output\_tokens} \cdot p_{\text{out}}}{10^6}
$$

Without caching, every call would cost $\big((\text{prefix\_tokens} + \text{input\_tokens}) \cdot p_{\text{in}} + \text{output\_tokens} \cdot p_{\text{out}}\big) / 10^6$.

Return

```
{"calls": [{"id", "status", "cost"}, ...],     # in input order
 "total_with_cache": float,
 "total_without_cache": float,
 "savings": total_without_cache - total_with_cache}
```

`savings` can be negative: cache writes that are never read cost more than not caching.

**Constraints**

- `0 <= len(calls) <= 10_000`
- Token counts are non-negative integers; `ttl_s > 0`
