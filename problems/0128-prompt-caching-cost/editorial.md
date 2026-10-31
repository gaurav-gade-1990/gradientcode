## Approach

Replay the calls with one expiry timestamp per prefix and price each call by its status.

```python
if c["prefix_tokens"] < min_cacheable:
    status, p_prefix = "uncacheable", p_in            # never touches the cache
else:
    hit = pid in expires and c["t"] < expires[pid]
    status, p_prefix = ("read", read_mult * p_in) if hit else ("write", write_mult * p_in)
    expires[pid] = c["t"] + ttl                       # writes AND reads set it
cost = (prefix * p_prefix + inp * p_in + out * p_out) / 1e6
```

The economics in one line: with a 1.25× write and a 0.1× read, caching a prefix pays off as soon as it is read **once** within the TTL ($1.25 + 0.1 = 1.35 < 2$). It loses money only on prompts that are written and never reused, such as one-shot batch jobs or prompts that change on every call.

## Common mistakes

- **Not refreshing the TTL on reads.** Anthropic's cache refreshes on every hit, so an active conversation stays cached indefinitely. Modelling it as "expires five minutes after the write" badly understates the savings.
- **Ignoring the minimum length.** Short prefixes aren't cached at all. Requests go through at full price and no error is raised.
- **Forgetting the write premium.** Caching isn't free. A never-read write costs more than no cache.
- **An off-by-one at the boundary.** Decide whether the expiry instant is a hit, and keep it consistent.

## Production notes

- Anthropic: explicit `cache_control` breakpoints (up to 4), a 5-minute default TTL refreshed on use with a 1-hour option at a higher write price, writes at 1.25× (2× for the 1-hour TTL), reads at 0.1×, and a minimum of 1,024 to 4,096 tokens depending on the model. OpenAI caches automatically for prompts of 1,024+ tokens, charges no write premium, and discounts cached input. Gemini has implicit caching plus explicit cache objects billed per hour of storage. Check current pricing pages, because these numbers change.
- The usage block tells you what really happened: `cache_creation_input_tokens` and `cache_read_input_tokens` (Anthropic) or `prompt_tokens_details.cached_tokens` (OpenAI). Reconcile your forecast against them.
- The cache is a **prefix** match. Put stable content first (tools, system prompt, documents) and volatile content last. A timestamp or a user name in the system prompt silently disables caching.
- Caches are per organization and per model, and they live on the provider side, so traffic spread over many keys or regions may hit far less often than this model predicts.
- This saves on the prefix only. A semantic cache (problem 127) skips the call entirely, and cost attribution (problem 131) has to understand cached-token pricing to bill tenants correctly.
