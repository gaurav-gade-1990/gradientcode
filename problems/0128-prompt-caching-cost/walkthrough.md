## 1. What the problem is really asking

An agent resends the same long prefix on every turn: system prompt, tool catalog, maybe a few documents. Providers let you cache that prefix. The first call **writes** it at a premium, and later calls within the cache's lifetime **read** it at a deep discount. Finance wants to know what that would really have saved on last week's traffic.

Under the story, this is **a replay with one expiry timestamp per prefix**. Walk the calls in time order, classify each one as `uncacheable`, `read` or `write`, price it, and add up two totals: with the cache and without it. Three rules decide the status:

- A prefix shorter than `min_cacheable_tokens` is never cached and never touches the cache.
- A call hits only if it arrives **strictly before** the stored expiry.
- Both reads and writes reset the expiry to `t + ttl_s`. An active conversation keeps its cache warm.

The function is pure. The judge compares each call's status and cost, and the three totals, with a tight tolerance, so the order of the arithmetic matters only in that you follow the formula as written.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `t` | call time in seconds, never decreasing | compared with the prefix's expiry |
| `prefix_id` | which cacheable prefix this call uses | the cache key |
| `prefix_tokens` | size of the prefix | billed at the status's price |
| `input_tokens` | the new, uncached suffix | always billed at `input_per_mtok` |
| `output_tokens` | the model's answer | always billed at `output_per_mtok` |
| `pricing` | prices per million tokens, two multipliers, TTL, minimum size | sets the three prefix prices |

With the test pricing (`$3` in, `$15` out, write ×1.25, read ×0.1):

| status | prefix price per million |
|---|---|
| `uncacheable` | $3.00 |
| `write` | 1.25 × $3 = $3.75 |
| `read` | 0.1 × $3 = $0.30 |

Two details are easy to miss:

- **An uncacheable call changes nothing,** not even the expiry of a prefix with the same `prefix_id`.
- **`savings` can be negative.** A write that's never read costs 25% more on the prefix than not caching.

## 3. Trace the examples by hand

**Example 1.** Prefix `support-v7`, 6,000 tokens, TTL 300 s.

| call | t | expiry before | status | cost |
|---|---|---|---|---|
| t1 | 0 | none | write | (6000 × 3.75 + 200 × 3 + 300 × 15) / 1e6 = $0.0276 |
| t2 | 40 | 300 | read | (6000 × 0.30 + 180 × 3 + 250 × 15) / 1e6 = $0.00609 |
| t3 | 90 | 340 | read | (6000 × 0.30 + 220 × 3 + 400 × 15) / 1e6 = $0.00846 |

`total_with_cache` is $0.04215. Without caching, the prefix costs $3/M on all three calls, for $0.07005 in total. `savings` is $0.0279. Note that t2 moved the expiry from 300 to 340, and t3 moved it to 390.

**Example 2** shows why refreshing matters:

| call | t | expiry before | status | expiry after |
|---|---|---|---|---|
| a | 0 | none | write | 300 |
| b | 280 | 300 | read | 580 |
| c | 560 | 580 | read | 860 |
| d | 900 | 860 | write | 1200 |

c is 560 s after the write, well past one TTL, and still hits, because b refreshed the cache at 280.

**Example 3** is the negative case. The 800-token `classifier` prefix is below the 1,024 minimum, so both calls are `uncacheable` and cost exactly what they would without caching. The 4,000-token `batch-job-17` prefix is written once and never read: 4,000 × ($3.75 − $3.00) / 1e6 = $0.003 extra. `savings` is −$0.003.

## 4. Key idea: when caching pays

Measure in units of one full-price prefix. A write costs 1.25 and each read 0.1. Without caching, `n` uses cost `n`. With caching and one write followed by `n − 1` reads, they cost `1.25 + 0.1(n − 1)`.

| uses within the TTL | without | with | saving |
|---|---|---|---|
| 1 | 1.00 | 1.25 | −0.25 |
| 2 | 2.00 | 1.35 | 0.65 |
| 3 | 3.00 | 1.45 | 1.55 |

So caching pays as soon as the prefix is read **once** within the TTL. It only loses on prompts written and never reused: one-shot batch jobs, or prompts with a timestamp or user name near the top, which change the prefix on every call. "long agent session" shows the win at scale: 45 calls, 39 reads and 6 writes, $0.4257 with the cache against $1.0305 without.

## 5. Plan before you code

```
expires = {}
for each call, in order:
    if prefix_tokens < min_cacheable:  status uncacheable, prefix price = p_in   (cache untouched)
    else:
        if prefix_id in expires and t < expires[prefix_id]: status read,  price = read_mult * p_in
        else:                                               status write, price = write_mult * p_in
        expires[prefix_id] = t + ttl                    (reads AND writes)
    cost = (prefix * price + input * p_in + output * p_out) / 1e6
    base = ((prefix + input) * p_in + output * p_out) / 1e6
sum both; savings = without - with
```

## 6. Build it one piece at a time

**Step 1: the minimum-length gate.** Check it first, before touching `expires`. The comparison is `<`, so a prefix of exactly `min_cacheable_tokens` is cacheable. In "exactly at the minimum is cacheable", 1,024 tokens writes and then reads, and 1,023 is `uncacheable`.

```python
        if c["prefix_tokens"] < pricing["min_cacheable_tokens"]:
            status, p_prefix = "uncacheable", p_in
```

**Step 2: hit or miss.** Strict `<`: a call at exactly the expiry is a miss. In "expiry boundary is a miss", the write at 0 expires at 300, so the call at 300 is another write. That write sets the expiry to 600, so the call at 599.5 reads.

```python
            if c["prefix_id"] in expires and c["t"] < expires[c["prefix_id"]]:
                status, p_prefix = "read", pricing["cache_read_mult"] * p_in
            else:
                status, p_prefix = "write", pricing["cache_write_mult"] * p_in
```

**Step 3: refresh on both.** The assignment sits after the `if`/`else`, at the same indentation, so it runs for reads and writes alike. Indenting it under `else` is the "TTL not refreshed on read" bug.

```python
            expires[c["prefix_id"]] = c["t"] + pricing["ttl_s"]
```

**Step 4: both costs.** Price the call, then the same call with no cache, and keep running totals.

```python
        cost = (c["prefix_tokens"] * p_prefix + c["input_tokens"] * p_in + c["output_tokens"] * p_out) / 1e6
        base = ((c["prefix_tokens"] + c["input_tokens"]) * p_in + c["output_tokens"] * p_out) / 1e6
```

## 7. Full solution

```python
def prompt_cache_cost(calls, pricing):  # replay traffic and price it with and without prompt caching
    p_in, p_out = pricing["input_per_mtok"], pricing["output_per_mtok"]  # base prices per million tokens
    expires = {}  # prefix_id -> time the cached prefix expires
    rows, with_cache, without = [], 0.0, 0.0  # per-call rows and the two running totals
    for c in calls:  # in time order
        if c["prefix_tokens"] < pricing["min_cacheable_tokens"]:  # too short for the provider to cache
            status, p_prefix = "uncacheable", p_in  # plain input price, and the cache is left alone
        else:  # cacheable
            if c["prefix_id"] in expires and c["t"] < expires[c["prefix_id"]]:  # still cached; exactly at expiry is a miss
                status, p_prefix = "read", pricing["cache_read_mult"] * p_in  # the discounted read
            else:  # never cached, or expired
                status, p_prefix = "write", pricing["cache_write_mult"] * p_in  # pay the write premium
            expires[c["prefix_id"]] = c["t"] + pricing["ttl_s"]  # both reads and writes refresh the TTL
        # the suffix and output are never cached
        cost = (c["prefix_tokens"] * p_prefix + c["input_tokens"] * p_in + c["output_tokens"] * p_out) / 1e6
        base = ((c["prefix_tokens"] + c["input_tokens"]) * p_in + c["output_tokens"] * p_out) / 1e6  # same call, no caching
        rows.append({"id": c["id"], "status": status, "cost": cost})  # input order
        with_cache += cost  # what we'd pay with caching
        without += base  # what we'd pay without it
    # savings is negative when writes are never read back
    return {"calls": rows, "total_with_cache": with_cache, "total_without_cache": without, "savings": without - with_cache}
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | write, read, read; savings $0.0279 | basic pricing of the three statuses |
| Example 2 | write, read, read, write | reads refresh the TTL; a gap longer than the TTL expires it |
| Example 3 | uncacheable ×2, write; savings −$0.003 | the minimum length; an unread write loses money |
| expiry boundary is a miss | write at 0, write at 300, read at 599.5 | strict `t < expires_at` |
| uncacheable does not refresh | write, uncacheable, write | the short call at 200 doesn't touch the expiry |
| interleaved prefixes | `b2` at 320 writes while `a2` and `a3` read | one expiry per `prefix_id` |
| exactly at the minimum is cacheable | write, read, uncacheable | `<` at the minimum |
| empty | all totals 0.0 | no calls |
| long agent session | 39 reads, 6 writes; savings $0.6048 | a long session plus a second session with 400 s gaps |
| 1-hour ttl, 2x write | one write, five reads; savings $0.063 | different TTL and write multiplier |

In "long agent session", the second session (`agent-v13`) has 400 s between calls, longer than the 300 s TTL, so all five of its calls are writes. Together with the first session's single write, that's the six writes.

## 9. Complexity

One pass, O(1) per call: a dict lookup and some arithmetic. Memory is one float per distinct `prefix_id`. Ten thousand calls take a few milliseconds.

The model is only as good as its assumptions. Real caches are per organization, per model and often per region, and live on the provider side, so traffic spread across many API keys or regions hits less often than this replay predicts. The way to check is the usage block on each response: `cache_creation_input_tokens` and `cache_read_input_tokens` on Anthropic, `prompt_tokens_details.cached_tokens` on OpenAI. Reconcile the forecast against those numbers after you turn caching on.

## 10. If you got Wrong Answer

- **Example 2's c is a write.** You only set the expiry on writes. Reads refresh it too.
- **Example 3's short calls are `write` and `read`.** You ignored `min_cacheable_tokens`.
- **Example 1's first call costs $0.0231.** You billed the write at the plain input price. Apply `cache_write_mult`.
- **"expiry boundary is a miss" reads at t=300.** Your hit test is `<=`. Use `<`.
- **"uncacheable does not refresh" reads at 350.** Your uncacheable branch updates the expiry. It must leave the cache alone.

## 11. Follow-ups an interviewer might ask

- *How do you design prompts so they cache well?* Put stable content first (tools, system prompt, documents) and volatile content last. A timestamp or user name near the top changes the prefix on every call and silently disables caching.
- *When is the 1-hour TTL worth its higher write price?* When calls on the same prefix are spaced more than 5 minutes apart but less than an hour, as in "1-hour ttl, 2x write", where 1,000 s gaps would make every call a write under a 5-minute TTL.
- *How do providers differ?* Anthropic uses explicit `cache_control` breakpoints, a 5-minute TTL refreshed on use, writes at 1.25×, reads at 0.1×. OpenAI caches automatically from 1,024 tokens with no write premium. Gemini also offers explicit cache objects billed per hour of storage. Check current pricing pages; these change.
- *How does this compare with a semantic cache?* A semantic cache skips the whole call when a similar question was already answered (problem 127, semantic-cache). Prompt caching only discounts the prefix, but it applies to every call, and the two stack.
- *How do you bill tenants fairly with caching?* Attribute cached and uncached input tokens separately at their real prices, so the tenant whose call paid the write premium isn't the only one charged for a prefix everyone reads (problem 131, tenant-cost-attribution).
