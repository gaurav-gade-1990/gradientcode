## 1. What the problem is really asking

Many tenants share one provider API key. If any one of them goes over the provider's limits, the provider throttles the key, and **every** tenant suffers. So the gateway enforces each tenant's contract itself, before forwarding: requests per minute (RPM) and tokens per minute (TPM), the same two limits Anthropic and OpenAI enforce.

Under the story, this is **two token buckets per tenant**, refilled lazily from the clock, with three twists:

- A request needs room in **both** buckets, and its wait is set by whichever bucket is further behind.
- An admitted request with a wait is a **reservation**: you deduct right away, and the level may go negative. The next caller sees the debt and queues behind it.
- You admit on an estimate (prompt plus `max_tokens`), so `settle` corrects the token bucket when the real usage comes back.

The judge advances a virtual clock to each operation's time and records `["admit", wait]`, `["429", retry_after]`, `["400", None]` or `["settled", None]` for every operation, compared to 6 decimal places.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `limits` | tenant → `{"rpm", "tpm"}` | builds two buckets per tenant, both full |
| `clock` | a `gc_runtime.Clock` | `clock.now()` whenever you touch a bucket |
| `max_wait` | seconds the gateway will queue a request | admit if `wait <= max_wait`, else 429 |
| `acquire(tenant, tokens)` | one request about to be sent | returns the wait, or raises |
| `settle(tenant, reserved, actual)` | the response arrived | adjusts the token bucket by `reserved - actual` |

| bucket | capacity | refill per second |
|---|---|---|
| requests | `rpm` | `rpm / 60` |
| tokens | `tpm` | `tpm / 60` |

Three details are easy to miss:

- **Two different errors.** An unknown tenant or `tokens > tpm` is `BadRequestError` (400): retrying can never help. Over the limit for now is `RateLimitError` with `retry_after` (429).
- **A rejection changes nothing.** Compute the wait, decide, and only deduct if you admit.
- **Refill is capped at capacity.** An idle tenant banks at most one minute of quota.

## 3. Trace the examples by hand

**Example 1.** `acme` has `rpm=60`, `tpm=60000`, so the token bucket refills at 1,000 tokens/s. `max_wait` is 0.

| t | request | token level before | wait | result | token level after |
|---|---|---|---|---|---|
| 0 | 25,000 | 60,000 | 0 | admit | 35,000 |
| 0 | 25,000 | 35,000 | 0 | admit | 10,000 |
| 0 | 25,000 | 10,000 | (25,000 − 10,000) / 1,000 = 15 | **429**, `retry_after=15` | 10,000 (unchanged) |
| 15 | 25,000 | 10,000 + 15 × 1,000 = 25,000 | 0 | admit | 0 |

The client that honoured `retry_after=15` gets in on its first retry.

**Example 2** adds a queue (`max_wait=30`) and a settle:

| t | op | token level before | wait | result | level after |
|---|---|---|---|---|---|
| 0 | acquire 40,000 | 60,000 | 0 | admit 0 | 20,000 |
| 0 | acquire 35,000 | 20,000 | 15 | admit 15 | −15,000 |
| 0 | acquire 5,000 | −15,000 | (5,000 + 15,000) / 1,000 = 20 | admit 20 | −20,000 |
| 2 | settle 40,000 reserved, 1,200 used | −20,000 + 2,000 = −18,000 | | settled | −18,000 + 38,800 = 20,800 |
| 2 | acquire 10,000 | 20,800 | 0 | admit 0 | 10,800 |

The negative level is the queue. The third request computes its wait from the debt the second one left, so it's served after it.

**Example 3** is the request bucket. `globex` has `rpm=6`, so six requests at t=0 drain the request bucket to 0. The seventh needs one request token at 6/60 = 0.1 per second: `retry_after=10`. `acme` has its own buckets and is admitted. `initech` has no contract: 400.

## 4. Key idea: lazy refill

There are no timers. Each bucket stores `level` and `last`, the time you last looked. Whenever you touch it, you catch up:

```
level = min(capacity, level + rate * (now - last))
last = now
```

That one line covers three behaviours. It pays back debt from reservations, it refills after use, and the `min` stops an idle tenant from banking unlimited quota. In "idle tenant does not bank more than one minute", acme uses 1,000 tokens at t=0 and then sits idle for 600 seconds. Without the cap the level would be 59,000 + 600,000. With it, the level is 60,000, so the third and fourth 30,000-token requests at t=600 get 429s with `retry_after=30`.

## 5. Key idea: decide before you deduct

A 429 must leave both buckets exactly as they were. "rejected retries must not drain the bucket" shows why. `globex` uses all six request tokens at t=0, then a client retries every second from t=1 to t=9:

| t | request level | wait | result |
|---|---|---|---|
| 1 | 0.1 | 9 | 429 |
| 2 | 0.2 | 8 | 429 |
| ... | ... | ... | ... |
| 9 | 0.9 | 1 | 429 |
| 10.5 | 1.05 | 0 | admit |

Each retry sees the level a little higher, because nothing was taken. If each rejection deducted, every retry would push the level further negative, and a client in a tight retry loop would lock itself out for as long as it kept retrying.

## 6. Plan before you code

```
__init__: for each tenant, a full request bucket and a full token bucket, last = now

acquire(tenant, tokens):
    unknown tenant          -> BadRequestError
    tokens > tpm            -> BadRequestError
    refill both buckets to now
    wait = max(wait_for_requests(1), wait_for_tokens(tokens))
    wait > max_wait         -> RateLimitError(retry_after=wait), nothing deducted
    deduct 1 and tokens (levels may go negative)
    return wait

settle(tenant, reserved, actual):
    refill the token bucket to now
    level = min(capacity, level + reserved - actual)
```

The wait for one bucket is how long the refill takes to bring `level` up to `need`:

$$
\text{wait}_b = \max\left(0,\ \frac{\text{need} - L_b}{r_b}\right), \qquad \text{wait} = \max(\text{wait}_{req}, \text{wait}_{tok})
$$

where $L_b$ is the bucket's level after the refill, $r_b$ its refill rate per second, and need is 1 for the request bucket and `tokens` for the token bucket.

## 7. Build it one piece at a time

**Step 1: a bucket.** Both buckets behave the same, so write one small class. `rate` is per second.

```python
class _Bucket:
    def __init__(self, capacity, per_minute, now):
        self.capacity = float(capacity)
        self.rate = per_minute / 60.0
        self.level = float(capacity)
        self.last = now

    def refill(self, now):
        self.level = min(self.capacity, self.level + self.rate * (now - self.last))
        self.last = now

    def wait_for(self, need):
        return max(0.0, (need - self.level) / self.rate)
```

**Step 2: buckets per tenant.** Keyed by tenant, never shared. With one shared pair, `globex`'s six requests in Example 3 would eat into `acme`'s quota.

```python
        now = clock.now()
        self.req = {t: _Bucket(l["rpm"], l["rpm"], now) for t, l in limits.items()}
        self.tok = {t: _Bucket(l["tpm"], l["tpm"], now) for t, l in limits.items()}
```

**Step 3: the 400s, then the decision.** The size check uses `>`: a request of exactly `tpm` tokens fits a full bucket. In "oversize and unknown tenant", 12,001 tokens against `tpm=12000` is 400, and 12,000 is admitted.

```python
        rb, tb = self.req[tenant], self.tok[tenant]
        rb.refill(now)
        tb.refill(now)
        wait = max(rb.wait_for(1), tb.wait_for(tokens))
        if wait > self.max_wait:
            raise RateLimitError("tenant %s over limit" % tenant, retry_after=wait)
        rb.level -= 1
        tb.level -= tokens
        return wait
```

**Step 4: settle both ways.** `reserved - actual` is positive when the estimate was too high (a refund) and negative when it was too low (an overage). In "actual usage above the reservation", a 10,000-token reservation really used 40,000, so the level drops from 50,000 + 1,000 = 51,000 to 21,000, and the next 25,000-token request waits 4 seconds.

```python
    def settle(self, tenant, reserved, actual):
        tb = self.tok[tenant]
        tb.refill(self.clock.now())
        tb.level = min(tb.capacity, tb.level + reserved - actual)
```

The `min` matters for refunds. In "queue chain with settle refund capped at capacity", three refunds would push the level to 60,000 + 19,900 at t=4; the cap holds it at 60,000.

## 8. Full solution

```python
from gc_runtime import BadRequestError, RateLimitError  # 400 for "never fits", 429 for "not yet"


class _Bucket:  # one token bucket with lazy refill
    def __init__(self, capacity, per_minute, now):  # starts full
        self.capacity = float(capacity)  # the most it can ever hold: one minute's worth
        self.rate = per_minute / 60.0  # refill per second
        self.level = float(capacity)  # current level; may go negative while reservations are owed
        self.last = now  # when we last brought the level up to date

    def refill(self, now):  # catch up on the time since we last looked
        self.level = min(self.capacity, self.level + self.rate * (now - self.last))  # pay back debt, never overfill
        self.last = now  # the level is now current

    def wait_for(self, need):  # seconds until the level reaches need
        return max(0.0, (need - self.level) / self.rate)  # 0 when there's already room


class TenantRateLimiter:  # per-tenant RPM and TPM in front of one shared provider key
    def __init__(self, limits, clock, max_wait=0.0):  # contracts, virtual time, and the queue limit
        self.limits = limits  # tenant -> {"rpm", "tpm"}
        self.clock = clock  # the only source of time
        self.max_wait = max_wait  # how long the gateway will hold a request
        now = clock.now()  # buckets are created full at construction time
        self.req = {t: _Bucket(l["rpm"], l["rpm"], now) for t, l in limits.items()}  # request bucket per tenant
        self.tok = {t: _Bucket(l["tpm"], l["tpm"], now) for t, l in limits.items()}  # token bucket per tenant

    def acquire(self, tenant, tokens):  # admit a request, returning how long to wait before sending
        if tenant not in self.limits:  # no contract
            raise BadRequestError("unknown tenant %r" % tenant)  # retrying can't help
        if tokens > self.limits[tenant]["tpm"]:  # bigger than a full bucket
            raise BadRequestError("request needs %d tokens; tenant TPM is %d" % (tokens, self.limits[tenant]["tpm"]))  # never fits
        now = self.clock.now()  # one timestamp for the whole decision
        rb, tb = self.req[tenant], self.tok[tenant]  # this tenant's buckets only
        rb.refill(now)  # bring the request bucket up to date
        tb.refill(now)  # and the token bucket
        wait = max(rb.wait_for(1), tb.wait_for(tokens))  # the slower bucket decides
        if wait > self.max_wait:  # longer than the gateway will queue
            raise RateLimitError("tenant %s over limit" % tenant, retry_after=wait)  # reject and change nothing
        rb.level -= 1  # reserve the request slot, possibly going negative
        tb.level -= tokens  # reserve the tokens; the next caller queues behind this debt
        return wait  # 0.0 means send now

    def settle(self, tenant, reserved, actual):  # correct the estimate once the real usage is known
        tb = self.tok[tenant]  # only tokens are corrected; a request is a request
        tb.refill(self.clock.now())  # bring it up to date first
        tb.level = min(tb.capacity, tb.level + reserved - actual)  # refund or charge the difference, capped
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | admit, admit, 429 (15), admit at t=15 | the token bucket and `retry_after` |
| Example 2 | admit 0, 15, 20, settled, admit 0 | reservations queue behind debt; settle refunds |
| Example 3 | six admits, 429 (10), admit for acme, 400 | the request bucket; isolation; unknown tenant |
| rejected retries must not drain the bucket | 429s with retry_after 9 down to 1, admit at 10.5, then 429 (9.5) | rejections deduct nothing |
| idle tenant does not bank more than one minute | admit, admit, admit, 429 (30), 429 (30) | the `min(capacity, ...)` cap |
| interleaved tenants stay isolated | globex 429 (1) at t=5 while acme is admitted; acme 429 (12) at t=10 | separate buckets per tenant |
| oversize and unknown tenant | 400, 400, admit 0, admit 0.005 | `tokens > tpm` uses `>`; a tiny request still queues behind debt |
| queue chain with settle refund capped at capacity | admit 0, 30, 50, 51; settles; admit 0, admit 1 | a chain of reservations; refunds capped |
| actual usage above the reservation | settled, 429 (4), admit 0, 429 (17.5) | settle charges overage too |
| rpm binds before tpm | waits 8.571429 and 17.142857, then 429 (22.414286) | the request bucket can be the binding one |
| tpm binds before rpm | waits 12, 35.75, 26, 25.06 | the token bucket can be the binding one |

## 10. Complexity

Each `acquire` and `settle` is O(1): a dict lookup, two refills, and a few arithmetic operations. Memory is two small objects per tenant.

With more than one gateway replica, the buckets have to live in shared state, or each replica admits a full contract's worth and the tenant gets `replicas ×` its limit. The usual answer is Redis with a Lua script that does refill, check and deduct atomically, which is how Envoy's global rate limit service and Kong's rate-limiting plugin work. Splitting the limit as `limit / replicas` per replica is cheaper but unfair when load balancing is uneven.

## 11. If you got Wrong Answer

- **"rejected retries must not drain the bucket" keeps returning 429 with growing `retry_after`.** You deduct before deciding. Compute the wait first, and deduct only when you admit.
- **Example 3's seventh `globex` request is admitted.** You only enforce TPM. Add the request bucket.
- **Example 3's `acme` request gets a 429, or "interleaved tenants stay isolated" is off.** Your buckets are shared across tenants.
- **"idle tenant does not bank more than one minute" admits all four requests.** Your refill has no `min(capacity, ...)`.
- **"actual usage above the reservation" admits the 25,000-token request.** Your settle only refunds. Apply `reserved - actual` in both directions.
- **Example 2's third wait is 5, not 20.** You clamp the level at 0 after a deduction. The negative level is the queue.

## 12. Follow-ups an interviewer might ask

- *How should a client react to the 429?* Sleep for `retry_after` and retry, with jitter and a cap on attempts (problem 124, retry-with-backoff, which honours `retry_after`).
- *Why not a sliding-window counter instead?* A sliding log is exact but stores every request. A token bucket is O(1) memory, allows controlled bursts up to capacity, and gives you an exact `retry_after`. GCRA is the same idea with a single timestamp per key.
- *How do providers actually limit?* Separately for RPM, input TPM and output TPM, per model, with `retry-after` and `x-ratelimit-remaining-*` headers. A good gateway enforces tenant limits below the key's limits, so its own 429s arrive before the provider's.
- *How would you give a big tenant priority?* Separate buckets per priority class, or weighted fair queuing on top of the buckets, so a batch job can't fill the queue ahead of interactive traffic.
- *Rate limits stop bursts. What stops a big bill?* A budget. Pair this with tenant cost attribution (problem 131, tenant-cost-attribution), which alerts as a tenant approaches its monthly spend even while it stays inside its TPM.
