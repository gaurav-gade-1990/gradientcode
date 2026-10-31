## Approach

**Signing** binds the timestamp to the body: `HMAC(secret, f"{t}.{body}")`. An attacker who captures a request can't change the timestamp without breaking the signature, so the tolerance window bounds replays to a few minutes.

**Verifying** follows Stripe's library: parse every `key=value` pair, compute the expected signature over the raw body, accept if any `v1` matches with a constant-time compare, then check the window in both directions.

```python
expected = hmac.new(secret.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()
if not any(hmac.compare_digest(expected.encode(), s.encode()) for s in sigs):
    return "bad_signature"
if abs(now - t) > tolerance:
    return "stale"
```

**Delivering** is a retry loop with one twist: sign *inside* the loop. The schedule here (60 s, 5 min, 30 min, 2 h) is far longer than the 5-minute tolerance, so a signature made once at the start is stale by the third retry.

**Receiving** is idempotent by event id. At-least-once delivery means duplicates are normal: the receiver processed the event but the 200 never made it back, so the sender retries. Answer 200 and do nothing.

## Common mistakes

- **Signing once, before the retries.** Every retry after the first few minutes is rejected as stale, so a short customer outage turns into permanent loss.
- **Verifying a re-serialized body.** Frameworks like Express parse JSON before your handler runs. `JSON.stringify(req.body)` reorders keys and changes whitespace, and every signature fails. Verify the raw bytes.
- **`==` on signatures.** String comparison returns at the first differing byte, which leaks timing an attacker can use to forge a signature byte by byte.
- **Checking only the first `v1`.** Webhooks break for every customer in the middle of a secret rotation.
- **`now - t > tolerance` only.** A timestamp in the future passes forever, so a captured request can be replayed indefinitely.
- **No dedupe at the receiver.** A lost response means the customer's agent runs the `invoice.paid` workflow twice.
- **Retrying a 410.** The customer deleted the endpoint; continuing to send is noise and sometimes a contract violation.

## Production notes

- This is Stripe's scheme (`Stripe-Signature: t=…,v1=…`, 300 s default tolerance, multiple `v1` during rotation). The Standard Webhooks spec used by Svix, Clerk and others is the same idea with `webhook-id`, `webhook-timestamp` and `webhook-signature` headers, and the id is signed too.
- Send from an outbox (`transactional-outbox`) so an event is never lost between the database commit and the first attempt, and persist the attempt log so customers can see and replay deliveries.
- Real schedules add jitter (`retry-with-backoff`), cap total retry time at a few days, and auto-disable endpoints that fail for days, with an email to the customer.
- Receivers should do the minimum synchronously (verify, dedupe, enqueue) and return 2xx fast; slow handlers cause timeouts, and timeouts cause duplicates.
- Pairs with `idempotent-tool-execution`: an agent tool that calls a customer's API should send its own idempotency key for the same reason.
