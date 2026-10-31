## Approach

Two token buckets per tenant, one for requests and one for tokens. A request is admitted only when **both** have room, and the wait is set by whichever bucket is further behind.

$$
\text{wait} = \max\left(0,\ \frac{1 - L_{req}}{r_{req}},\ \frac{n - L_{tok}}{r_{tok}}\right)
$$

```python
def acquire(self, tenant, tokens):
    # 400s first: unknown tenant, or tokens > tpm (can never fit)
    rb, tb = self.req[tenant], self.tok[tenant]
    rb.refill(now); tb.refill(now)              # level = min(cap, level + rate*dt)
    wait = max(rb.wait_for(1), tb.wait_for(tokens))
    if wait > self.max_wait:
        raise RateLimitError(retry_after=wait)  # nothing deducted
    rb.level -= 1; tb.level -= tokens           # may go negative: a reservation
    return wait
```

**Lazy refill.** You never need a timer. Store the level and the time you last looked, and catch up whenever someone asks. Capping at capacity is what makes it a bucket: an idle tenant can burst at most one minute's worth.

**Reservations.** When a request is admitted with a wait, deduct right away and let the level go negative. The next request at the same instant then computes its wait from the debt and queues behind it, which gives you FIFO fairness for free. This is the `Reserve()` model from Go's `golang.org/x/time/rate` and the idea behind GCRA.

**Settle.** You admit on an estimate (prompt plus `max_tokens`) because you don't know the real output length yet. When the response comes back, refund the difference. Without this, a tenant that sets `max_tokens=4096` and gets 200-token answers is throttled at 5% of its contract.

## Common mistakes

- **Deducting before deciding.** A rejected call that still consumes quota turns every 429 retry loop into a permanent lockout.
- **One bucket for everyone.** Keying by the upstream API key instead of the tenant lets one tenant's batch job starve the others.
- **No cap on refill.** An overnight-idle tenant banks hours of quota and fires it at once.
- **Refund-only settle.** If the estimate undercounts (a different tokenizer, tool schemas you forgot), the overage has to come out of the bucket too.
- **Only enforcing TPM.** Lots of tiny calls stay under TPM and still break the provider's RPM.

## Production notes

- Providers enforce RPM, input TPM and output TPM separately per model, and return `retry-after` plus `x-ratelimit-remaining-*` headers. A good gateway mirrors those limits per tenant so that its own 429s come before the provider's, which would hit everyone sharing the key.
- At more than one gateway replica the buckets must live in shared state. The usual choice is Redis with a Lua script that does refill, check and deduct atomically. Envoy's global rate limit service and Kong's rate-limiting plugin both work this way. Local buckets per replica with `limit / replicas` are cheaper but unfair under skewed load balancing.
- Return `retry_after` to callers so they can back off precisely. That pairs with the client side in problem 124 (retry with backoff), which honours it.
- Rate limits protect capacity, and budgets protect money. Pair this with tenant cost attribution (problem 131) so that a tenant within its TPM still gets an alert as it approaches its monthly spend.
