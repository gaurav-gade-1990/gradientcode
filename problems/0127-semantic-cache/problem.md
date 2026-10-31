Your support assistant answers the same handful of questions thousands of times a day, phrased slightly differently each time. Put a **semantic cache** in front of the model. It must never serve one tenant's answer to another, and it must never serve an answer generated under an old system prompt.

Implement `class SemanticCache`:

- `SemanticCache(clock, log, capacity=100, threshold=0.9, ttl_s=3600.0)`, where `clock` is a `gc_runtime.Clock` and `log` is a `gc_runtime.EventLog`.
- `get(tenant, model, system_prompt, query)` returns a cached answer, or `None`.
- `put(tenant, model, system_prompt, query, answer)` stores an answer.

**Key.** An entry belongs to the partition `(tenant, model, sha256(system_prompt))`, using `hashlib.sha256(system_prompt.encode()).hexdigest()`. Only entries in the same partition are candidates. Each entry stores the vector `embed(query, dim=64)` from `gc_runtime`. The similarity of two queries is the dot product of their vectors, which are unit length, so this is their cosine similarity.

**Every `get` and `put` starts with a purge.** Remove every entry, from any partition, whose `now >= stored_at + ttl_s`, and log `log.append("evict", tenant=..., query=..., reason="ttl")` for each one, in the order the entries were stored (oldest first).

**`get`**: among the entries in the partition, find the one with the highest similarity to `query`. Break ties by the most recently stored. If that similarity is `>= threshold`, it is a **hit**: mark the entry as used, log `("hit", tenant=..., query=query, matched=<the entry's query>, score=<similarity>)` and return its answer. Otherwise log `("miss", tenant=..., query=query)` and return `None`.

**`put`**: if the partition already has an entry with exactly this `query` string, overwrite it in place: a new answer, `stored_at = now`, marked as used, and stored most recently. Otherwise, if the cache already holds `capacity` entries (across **all** tenants), evict the least recently used entry and log `("evict", tenant=..., query=..., reason="lru")`. Then insert. In both cases, log `("store", tenant=..., query=query)`.

**Recency.** Keep one counter that ticks every time an entry is stored or hit. The least recently used entry is the one whose last tick is smallest. A hit refreshes recency but **not** `stored_at`, so a popular answer still expires on schedule.

The judge plays a support queue. For each question it calls `get`, and on a miss it calls the model (which answers `"<tenant>#<n>"`) and then `put`. Some cases also warm the cache by calling `put` directly with a curated answer. It grades the answers users received, the model calls and the event log. Every log entry also carries the time `t`.

**Constraints**

- `1 <= capacity <= 1000`, `0 < threshold <= 1`, `ttl_s > 0`
- At most 300 operations; times never decrease
- Use `embed` and `hashlib` exactly as described so the scores match
