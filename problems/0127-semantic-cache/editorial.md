## Approach

A semantic cache is an **exact** partition key with a **fuzzy** lookup inside it.

```python
key = (tenant, model, sha256(system_prompt))      # exact: never fuzzy across these
best = max((e for e in entries if e.key == key),
           key=lambda e: (q_vec @ e.vec, e.store_order))
if best and score >= threshold: hit
```

Everything that changes the answer has to be part of the exact key: the tenant (whose data the answer may contain), the model, and the system prompt (whose rules the answer follows). Only the user's wording is allowed to be fuzzy.

The bookkeeping:

- **Purge first.** Every `get`/`put` starts by dropping entries with `now >= stored_at + ttl`, oldest first, which keeps the log deterministic.
- **One use counter.** Store and hit both tick it. The LRU victim is `min(entries, key=used)`, taken over the whole cache, because memory is shared even though lookups are not.
- **TTL is not recency.** A hit refreshes `used`, never `stored_at`.

## Common mistakes

- **No tenant in the key.** This is the classic cross-tenant leak. It passes every single-tenant test and fails the first time two customers ask the same question.
- **No system prompt in the key.** After a prompt change (a new disclaimer, a new policy) the cache keeps serving answers that violate it.
- **A hit refreshes the TTL.** Popular stale answers then live forever, and those are exactly the ones you most need to expire.
- **FIFO instead of LRU.** The hottest entries are the oldest, so FIFO evicts them first.

## Production notes

- GPTCache, Redis (RedisVL `SemanticCache`), and the semantic caching in API gateways (Portkey, Kong AI Gateway, Cloudflare AI Gateway) all follow this shape: filter metadata exactly, then do a vector search with a distance threshold. In Redis the partition becomes tag filters on the vector index.
- The threshold is a product decision. Tune it on labelled paraphrase pairs from your own logs, per use case. False hits (a confident wrong answer) cost far more than misses, so FAQ bots run around 0.9 to 0.95 cosine on a real embedding model.
- Don't cache responses that depend on tool calls, the user's account state, or the time ("where is my order?"). Most teams cache only after a classifier or a route tag says the question is generic.
- Invalidate on content changes, not just on TTL. When the help-center article behind an answer changes, delete its entries by tag.
- This cache saves the whole call. Provider prompt caching (problem 128) saves only the prefix, and the two stack. Track the hit rate and the cost saved per tenant together with cost attribution (problem 131).
