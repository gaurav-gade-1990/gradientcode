## Approach

An idempotency key turns "create" into "create once". The record under the key is a small state machine: absent, `pending` while the first request works, then `done` with the response to replay.

The two things that make it correct under concurrency are an **atomic claim** and a **scoped key**:

```python
def handle_create_run(db, user_id, headers, body):
    key = next((v for k, v in headers.items() if k.lower() == "idempotency-key"), None)
    if not key:
        return {"status": 400, "run_id": None, "replayed": False}
    fp = json.dumps(body, sort_keys=True, separators=(",", ":"))
    scoped = (user_id, key)
    while True:
        rec = db.claim(scoped, fp)          # INSERT ... ON CONFLICT DO NOTHING
        if rec is None:
            break                           # we own the key
        if rec["fingerprint"] != fp:
            return {"status": 422, ...}
        if rec["status"] == "done":
            return dict(rec["response"], replayed=True)
        yield 0.05                          # someone else is creating it
    try:
        run_id = yield from db.create_run(user_id, body)
    except ServerError:
        db.release(scoped)                  # let the retry through
        return {"status": 500, ...}
    resp = {"status": 201, "run_id": run_id, "replayed": False}
    db.complete(scoped, resp)
    return resp
```

The claim happens before any side effect, so a second request that arrives during the 0.2 s insert sees `pending` instead of an empty slot. Looping back to `claim` after each poll also handles the release case: if the first request failed and freed the key, the waiter claims it and does the work itself.

## Common mistakes

- **Check then insert.** `get()` returns nothing for both concurrent requests, both create a run, and the user is billed twice. The reservation has to be one atomic write.
- **Key not scoped to the user.** Two customers who both send `retry-1` collide. One gets the other's run id back, which is a data leak, not just a bug.
- **Fingerprint without sorted keys.** A client that rebuilds the body in a different key order on retry gets a spurious 422.
- **Case-sensitive header lookup.** HTTP/2 and most proxies lowercase header names, so `headers["Idempotency-Key"]` misses and the retry creates a duplicate.
- **Not releasing on failure.** The key stays `pending` forever: the waiting duplicate spins until the gateway times out, and every retry hangs.

## Production notes

- Stripe's design is the reference: keys are scoped per account, stored for 24 hours, the request parameters are compared on reuse, and a concurrent in-flight duplicate gets `409 Conflict` instead of waiting. Waiting (as here) gives a nicer client experience but holds a connection, so cap the wait and return 409 after it.
- In Postgres, the claim is `INSERT INTO idempotency_keys (user_id, key, fingerprint, status) VALUES (...) ON CONFLICT DO NOTHING RETURNING ...`, with a unique index on `(user_id, key)`. In Redis it is `SET key value NX PX ttl`.
- Give pending records a lock timeout too. If the process dies between claim and complete, a sweeper (or a `locked_until` column) frees the key so it does not stay stuck.
- Store the full response, status code included, and replay it byte for byte. The IETF `Idempotency-Key` draft and Stripe both say a replay must look like the original.
- Pairs with **idempotent-tool-execution** (the same idea for agent tool calls), **request-coalescing** (deduping reads instead of writes) and **transactional-outbox** (making the run's side effects survive crashes).
