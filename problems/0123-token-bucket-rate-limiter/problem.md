Your LLM gateway sits in front of one shared provider key. Every tenant has a contract that caps both **requests per minute** (RPM) and **tokens per minute** (TPM), the same two limits the Anthropic and OpenAI APIs enforce. Write the limiter the gateway calls before it forwards a request.

Implement `class TenantRateLimiter`:

- `TenantRateLimiter(limits, clock, max_wait=0.0)`. `limits` maps a tenant id to `{"rpm": int, "tpm": int}`. `clock` is a `gc_runtime.Clock`. `max_wait` is how many seconds the gateway is willing to hold a request in its queue.
- `acquire(tenant, tokens) -> float` admits a request that will use `tokens` tokens (prompt plus `max_tokens`) and returns how many seconds the caller must wait before it sends. `0.0` means send now.
- `settle(tenant, reserved, actual)` runs when the response arrives. The request reserved `reserved` tokens but really used `actual`, so the difference goes back to (or comes out of) the token bucket.

**Buckets.** Each tenant has two token buckets, created full when the limiter is constructed (at `clock.now()`):

| bucket | capacity | refill rate |
|---|---|---|
| requests | `rpm` | `rpm / 60` per second |
| tokens | `tpm` | `tpm / 60` per second |

Refill lazily. Whenever you touch a bucket at time `now`, set `level = min(capacity, level + rate * (now - last))` and `last = now`. A level may be negative (see reservations below), and the refill pays that debt back at the same rate.

**`acquire(tenant, tokens)`**, in this order:

1. If `tenant` is not in `limits`, raise `BadRequestError`.
2. If `tokens > tpm`, raise `BadRequestError`. This request can never fit, and retrying will not help.
3. Refill both buckets to `now`. Compute `wait_req = max(0, (1 - level_req) / rate_req)` and `wait_tok = max(0, (tokens - level_tok) / rate_tok)`, then `wait = max(wait_req, wait_tok)`.
4. If `wait > max_wait`, raise `RateLimitError(retry_after=wait)` and **change nothing**.
5. Otherwise deduct `1` from the request bucket and `tokens` from the token bucket (levels may go negative; that is the reservation) and return `wait`.

Because an admitted request deducts immediately, the next request at the same moment sees the lower level and queues behind it. Admission is first come, first served.

**`settle(tenant, reserved, actual)`**: refill the tenant's token bucket to `now`, then set `level_tok = min(capacity, level_tok + reserved - actual)`. If `actual > reserved`, the level drops. The request bucket is not touched.

Tenants are fully isolated: one tenant's traffic never changes another tenant's buckets.

The judge advances `clock` to each operation's time, calls your method, and records `["admit", wait]`, `["429", retry_after]`, `["400", None]` or `["settled", None]`. Times are in seconds.

**Constraints**

- `1 <= rpm <= 10_000`, `1 <= tpm <= 10_000_000`
- `1 <= tokens`, `0 <= reserved, actual`
- Operation times never decrease
- Raise the error classes from `gc_runtime`; don't import `time`
