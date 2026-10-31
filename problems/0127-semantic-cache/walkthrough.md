## 1. What the problem is really asking

A support assistant gets the same few questions thousands of times a day, worded a little differently. A **semantic cache** answers a new question from a stored answer when the two questions are similar enough, which saves a whole model call. The danger is serving an answer to someone it wasn't written for: another tenant (a data leak), or the same tenant under an old system prompt (a policy violation).

Under the story, this is **an exact partition key with a fuzzy lookup inside it**, plus the usual cache bookkeeping:

- The **exact** part is `(tenant, model, sha256(system_prompt))`. Nothing outside the partition is ever a candidate.
- The **fuzzy** part is the dot product of two unit embedding vectors, compared against a threshold.
- **TTL** expires entries a fixed time after they were stored, and **LRU** decides what to evict when the cache is full.

The judge plays a support queue: `get`, and on a miss, call the model and `put`. It grades the answers users received, the model calls, and the full event log (`hit`, `miss`, `store`, `evict`), including each hit's similarity score to 6 decimal places and the order of events.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `clock` | `gc_runtime.Clock` | `stored_at` and the TTL test |
| `log` | `gc_runtime.EventLog` | `log.append(kind, **fields)`; it adds `t` itself |
| `capacity` | max entries across **all** tenants | the LRU eviction trigger |
| `threshold` | minimum similarity for a hit | `score >= threshold` |
| `ttl_s` | entry lifetime from `stored_at` | expired when `now >= stored_at + ttl_s` |
| `embed(query, dim=64)` | deterministic unit vector | similarity is `v @ e["vec"]` |

Four details are easy to miss:

- **Every `get` and `put` starts with a purge** of all expired entries, from every partition, logged oldest first.
- **Capacity is global, lookups are per partition.** Memory is shared, so a busy tenant can evict another tenant's entries.
- **A hit refreshes recency but not `stored_at`.** A popular answer still expires on schedule.
- **Ties go to the most recently stored entry,** and an overwrite counts as a fresh store.

## 3. Trace the examples by hand

The tests use `threshold=0.8`.

**Example 1:**

| t | query | candidates (score) | result | events |
|---|---|---|---|---|
| 0 | `How do I reset my password?` | none | miss → model → `acme#1` | miss, store |
| 5 | `how do i reset my password` | RESET (0.92582) | **hit**, `acme#1` | hit |
| 9 | `What is your refund policy?` | RESET (low) | miss → `acme#2` | miss, store |
| 12 | `What's the refund policy?` | best is REFUND (0.617) | miss → `acme#3` | miss, store |

The lower-case version shares every word with the original, so its bag-of-words vector is close. `What's` tokenizes as `What`, `'`, `s`, which shares too little with `What is your` to clear 0.8.

**Example 2.** The same question four times, but each in a different partition: acme, globex, acme with `SYS_V2`, acme with `support-model-v2`. Four misses and four model calls. Serving acme's answer to globex would be the leak the problem warns about.

**Example 3** (`capacity=2`, `ttl_s=600`):

| t | op | entries after (last tick) | events |
|---|---|---|---|
| 0 | RESET miss, store | RESET (1) | miss, store |
| 10 | REFUND miss, store | RESET (1), REFUND (2) | miss, store |
| 20 | `How can I reset my password?` | hit RESET at 0.845154 → RESET (3), REFUND (2) | hit |
| 30 | SHIP miss; full, evict the smallest tick: REFUND | RESET (3), SHIP (4) | miss, evict REFUND (lru), store |
| 601 | purge: RESET stored at 0, 601 ≥ 600 | SHIP | evict RESET (ttl), miss, store |

At t=30 the oldest entry is RESET, but REFUND is the least recently **used**, so REFUND goes. At t=601 RESET is purged even though it was hit at t=20, because the TTL counts from `stored_at`.

## 4. Key idea: everything that changes the answer goes in the exact key

The tenant decides whose data the answer can contain. The model decides how it's written. The system prompt decides the rules it follows: a new disclaimer, a new refund policy. If any of these differ, a cached answer is wrong no matter how similar the question is. So they're compared exactly, and only the user's wording is fuzzy.

Hashing the system prompt keeps the key small and makes a prompt change automatically start a fresh partition. In "system prompt rollout", the V2 prompt misses on every question, while the V1 partition keeps working: at t=3, `how do i reset my password` under V1 still hits the t=0 entry.

## 5. Key idea: one counter for recency, a separate clock for expiry

Two different questions need two different numbers:

| question | number | changes on |
|---|---|---|
| has this entry expired? | `stored_at` | store and overwrite only |
| which entry is least recently used? | `used` (a global tick) | store, overwrite and hit |

"ttl counts from store, not from the last hit" makes the difference visible. RESET is stored at t=0 with `ttl_s=600`, then hit at 300, 550 and 599. At t=600 it's purged and the question misses. If a hit refreshed `stored_at`, the entry would live until 1199, and the most popular answers, the ones most likely to be out of date, would never expire.

## 6. Plan before you code

```
entries: list in store order (oldest first); tick = 0

purge(): drop entries with now >= stored_at + ttl, logging "evict"/"ttl" in list order
touch(e): tick += 1; e.used = tick

get(tenant, model, sys, q):
    purge; key = partition; v = embed(q)
    best = highest v @ e.vec among entries with this key (later entries win ties)
    best and score >= threshold -> touch, log hit, return answer
    log miss; return None

put(tenant, model, sys, q, answer):
    purge; key = partition
    same key and same query exists -> remove it, update answer and stored_at
    else: full -> evict min(used), log "evict"/"lru"; build a new entry
    append (now the most recently stored); touch; log store
```

Keeping `entries` in store order gives you three rules for free: the purge logs oldest first, a tie goes to the later entry in the list, and an overwrite moves to the end.

## 7. Build it one piece at a time

**Step 1: the partition key.** `hexdigest()` gives a stable string; Python's built-in `hash()` changes between processes.

```python
    def _partition(self, tenant, model, system_prompt):
        return (tenant, model, hashlib.sha256(system_prompt.encode()).hexdigest())
```

**Step 2: purge.** Rebuild the list, logging each expired entry as you pass it. Because the list is in store order, the log is oldest first. In "mass expiry logs oldest first", three entries from three tenants expire at t=130 and are logged globex, acme, initech.

```python
    def _purge(self):
        now = self.clock.now()
        keep = []
        for e in self.entries:
            if now >= e["stored_at"] + self.ttl_s:
                self.log.append("evict", tenant=e["key"][0], query=e["query"], reason="ttl")
            else:
                keep.append(e)
        self.entries = keep
```

**Step 3: lookup.** `>=` in the comparison lets a later entry with an equal score replace the current best, which is the "most recently stored wins" tie rule. In "warmed entries, overwrite and tie on equal scores", the queries `reset my password`, `my password reset` and `password reset my` have the same words, so they all score 1.0. The first `get` returns the later warm entry, `faq-v2`.

```python
        for e in self.entries:
            if e["key"] != key:
                continue
            s = float(v @ e["vec"])
            if best is None or s >= best_score:
                best, best_score = e, s
```

**Step 4: store or overwrite.** An exact-query overwrite removes the entry and re-appends it, so it becomes the most recently stored. In the same warm-entries case, re-warming `reset my password` with `faq-v3` at t=3 makes it win the next tie. Evict only when inserting a new entry into a full cache.

```python
        same = [e for e in self.entries if e["key"] == key and e["query"] == query]
        if same:
            e = same[0]
            self.entries.remove(e)
            e["answer"], e["stored_at"] = answer, self.clock.now()
        else:
            if len(self.entries) >= self.capacity:
                victim = min(self.entries, key=lambda x: x["used"])
                self.entries.remove(victim)
                self.log.append("evict", tenant=victim["key"][0], query=victim["query"], reason="lru")
            e = {"key": key, "query": query, "vec": embed(query, dim=64), "answer": answer, "stored_at": self.clock.now()}
        self.entries.append(e)
        self._touch(e)
```

## 8. Full solution

```python
import hashlib  # sha256 of the system prompt, stable across processes

from gc_runtime import embed  # the judge's deterministic unit-length embedding


class SemanticCache:  # exact partition, fuzzy match inside it, TTL plus global LRU
    def __init__(self, clock, log, capacity=100, threshold=0.9, ttl_s=3600.0):  # config and dependencies
        self.clock = clock  # virtual time for stored_at and expiry
        self.log = log  # the event log the judge grades
        self.capacity = capacity  # max entries across every tenant
        self.threshold = threshold  # minimum cosine similarity for a hit
        self.ttl_s = ttl_s  # lifetime from stored_at
        self.entries = []         # kept in store order, oldest first
        self.tick = 0  # recency counter: ticks on every store and every hit

    def _partition(self, tenant, model, system_prompt):  # everything that changes the answer, compared exactly
        return (tenant, model, hashlib.sha256(system_prompt.encode()).hexdigest())  # a prompt change is a new partition

    def _touch(self, e):  # mark an entry as just used
        self.tick += 1  # one global clock of uses
        e["used"] = self.tick  # the smallest value is the LRU victim

    def _purge(self):  # drop every expired entry, from every partition
        now = self.clock.now()  # one timestamp for the whole purge
        keep = []  # survivors, still in store order
        for e in self.entries:  # oldest first, so the log is oldest first
            if now >= e["stored_at"] + self.ttl_s:  # expired; TTL counts from the store, not the last hit
                self.log.append("evict", tenant=e["key"][0], query=e["query"], reason="ttl")  # record why it went
            else:  # still fresh
                keep.append(e)  # keep it
        self.entries = keep  # replace the list

    def get(self, tenant, model, system_prompt, query):  # a cached answer, or None
        self._purge()  # expired entries must never be served
        key = self._partition(tenant, model, system_prompt)  # only this partition is searched
        v = embed(query, dim=64)  # unit vector for the new question
        best, best_score = None, None  # the closest entry so far
        for e in self.entries:            # later entries win ties: they were stored more recently
            if e["key"] != key:  # another tenant, model or prompt
                continue  # never a candidate
            s = float(v @ e["vec"])  # cosine similarity, since both are unit length
            if best is None or s >= best_score:  # >= so a later entry wins an equal score
                best, best_score = e, s  # new best
        if best is not None and best_score >= self.threshold:  # close enough to reuse
            self._touch(best)  # a hit refreshes recency, but not stored_at
            self.log.append("hit", tenant=tenant, query=query, matched=best["query"], score=best_score)  # what matched
            return best["answer"]  # no model call needed
        self.log.append("miss", tenant=tenant, query=query)  # nothing close enough
        return None  # the caller will call the model and put

    def put(self, tenant, model, system_prompt, query, answer):  # store an answer
        self._purge()  # expire first, so we don't evict a live entry to make room an expired one holds
        key = self._partition(tenant, model, system_prompt)  # where it belongs
        same = [e for e in self.entries if e["key"] == key and e["query"] == query]  # exact same question already here?
        if same:  # overwrite in place
            e = same[0]  # the existing entry
            self.entries.remove(e)  # it will be re-appended as the most recently stored
            e["answer"], e["stored_at"] = answer, self.clock.now()  # new answer, new expiry clock
        else:  # a new entry
            if len(self.entries) >= self.capacity:  # full, across all tenants
                victim = min(self.entries, key=lambda x: x["used"])  # least recently used, not oldest
                self.entries.remove(victim)  # make room
                self.log.append("evict", tenant=victim["key"][0], query=victim["query"], reason="lru")  # record it
            # the vector is computed once, at store time
            e = {"key": key, "query": query, "vec": embed(query, dim=64), "answer": answer, "stored_at": self.clock.now()}
        self.entries.append(e)  # the end of the list is the most recently stored
        self._touch(e)  # storing counts as a use
        self.log.append("store", tenant=tenant, query=query)  # record the store
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | hit at 0.92582; refund paraphrase misses at 0.617 | the threshold |
| Example 2 | four misses, four model calls | tenant, system prompt and model are all in the key |
| Example 3 | evict REFUND (lru) at 30; evict RESET (ttl) at 601 | LRU, not FIFO; TTL despite a recent hit |
| ttl counts from store, not from the last hit | three hits, then expiry at exactly 600 | hits don't refresh `stored_at`; `>=` at the boundary |
| capacity is shared across tenants | globex's RESET evicted at 4, acme's at 6 | one global LRU across tenants |
| system prompt rollout | V2 misses everything; V1 still hits at t=3 | the hashed prompt in the key |
| warmed entries, overwrite and tie on equal scores | `faq-v2`, then `faq-v3`; globex misses | ties to the most recently stored; overwrite moves to the end |
| lru with many hits | five LRU evictions in a 3-entry cache | recency from hits as well as stores |
| mass expiry logs oldest first | three TTL evictions at 130 in store order; CANCEL expires at 200 after a hit at 190 | purge order; TTL from store |

## 10. Complexity

Each `get` is O(N · d) for N entries and embedding dimension d: a linear scan with one dot product per entry in the partition, plus the O(N) purge. `put` adds an O(N) `min` for the LRU victim. With N ≤ 1000 and d = 64, that's fine.

At scale, three things change. The vector search moves to an index (HNSW or IVF) with the partition as a metadata filter; that's how Redis `SemanticCache` and GPTCache work. The purge becomes a TTL in the store itself, and LRU becomes an `OrderedDict` or a doubly linked list for O(1) eviction. And the threshold becomes a tuned product decision: false hits (a confident wrong answer) cost far more than misses, so FAQ bots on real embedding models often run at 0.9 to 0.95 cosine.

## 11. If you got Wrong Answer

- **Example 2 has a hit for globex.** The tenant isn't in your key. That's a cross-tenant data leak.
- **Example 2's third question hits.** The system prompt isn't in your key.
- **Example 3 evicts RESET at t=30.** You're evicting the oldest entry (FIFO). Evict the smallest `used` tick.
- **"ttl counts from store, not from the last hit" hits at t=600.** A hit is refreshing `stored_at`.
- **"warmed entries, overwrite and tie on equal scores" returns `faq-v1` first.** Your tie-break keeps the first entry. Use `>=` so later entries win.
- **The same case returns `faq-v2` second.** Your overwrite updates in place without moving the entry to the end.
- **"lru with many hits" evicts the wrong entries.** A hit must tick the recency counter.

## 12. Follow-ups an interviewer might ask

- *How would you pick the threshold?* Label paraphrase pairs from your own logs (same intent or not), plot precision against recall as the threshold moves, and pick the point where false hits are rare enough for the use case.
- *What shouldn't be cached?* Anything that depends on the user's account state, tool results, or the time ("where is my order?"). Most teams cache only after a classifier or route tag says the question is generic.
- *How do you invalidate when the help article behind an answer changes?* Tag entries with their source documents and delete by tag on publish. TTL is the safety net, not the plan.
- *How does this relate to provider prompt caching?* A semantic cache skips the whole call. Prompt caching (problem 128, prompt-caching-cost) only discounts a repeated prefix, and the two stack.
- *How would you report the savings?* Count hits per tenant and multiply by the cost the model call would have had, alongside tenant cost attribution (problem 131, tenant-cost-attribution).
