## Approach

Keep a map from key to `(fingerprint, result, stored_at)`. Each call takes one of four paths:

```python
def execute(self, key, tool, args, fn):
    now = self.clock.now()
    fp = (tool, json.dumps(args, sort_keys=True))
    entry = self.store.get(key) if key is not None else None
    if entry and now - entry[2] >= self.ttl:      # lazy expiry
        del self.store[key]; entry = None
    if entry:
        return {"status": "replayed", "result": entry[1]} if entry[0] == fp else {"status": "conflict"}
    try:
        result = fn(args)
    except ToolError as e:
        return {"status": "failed", "error": str(e)}     # not stored: safe to retry
    if key is not None:
        self.store[key] = (fp, result, now)
    return {"status": "executed", "result": result}
```

The fingerprint is what makes a key safe. A replay is only correct if it is the *same* request. A different request reusing a key is a bug somewhere upstream, so surface it as a conflict and don't hand back somebody else's result.

## Common mistakes

- **Key without the arguments.** A replay hands a $129 charge receipt to a request for $12.90. Stripe returns an error in this case, for exactly this reason.
- **`json.dumps(args)` without `sort_keys`.** Models don't promise key order, so a retry with reordered keys looks like a conflict.
- **Caching failures.** A transient `gateway_timeout` gets replayed forever, and the charge never happens.
- **No expiry.** Keys are often derived (`run_id:step`), so a nightly job that reuses a key replays yesterday's export forever.
- **Sliding TTL.** Refreshing `stored_at` on replay keeps a hot key alive indefinitely. The TTL should bound how long after the real side effect you'll still dedupe.

## Production notes

- Derive the key from something stable across retries: the agent run id plus the step index, or the model's `tool_use` id. A fresh UUID per attempt defeats the purpose.
- Stripe keeps keys for 24 hours, compares request parameters, and returns `409`/`400` on a mismatch. It also locks a key while a request is in flight, so concurrent duplicates wait instead of both executing (problems 171 and 180).
- At scale the store is Redis (`SET key value NX PX ttl`) or a database row with a unique constraint written in the **same transaction** as the side effect. Otherwise a crash between "charged" and "stored" brings back the double charge (problem 172).
- Temporal and other durable-execution engines give you this per activity. Downstream APIs still need their own idempotency keys, because activities are retried at least once.
- Pairs with **retry-with-backoff** (124): retries are only safe once this layer exists.
