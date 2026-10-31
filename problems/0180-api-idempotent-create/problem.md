Your agent platform exposes `POST /runs` to start an agent run. Mobile clients and SDKs retry on timeouts, so the same request often arrives twice, sometimes at the same moment. Make the handler idempotent with an `Idempotency-Key` header.

`handle_create_run(db, user_id, headers, body)` is a **generator** that the server runs on a `gc_runtime.EventLoop`. It returns (with `return`) a response dict:

```python
{"status": 201, "run_id": "run_001", "replayed": False}
```

**The database** (`db`, built by the judge) offers:

| call | what it does |
|---|---|
| `db.claim(key, fingerprint)` | Atomic. If `key` is free, stores `{"fingerprint": fingerprint, "status": "pending", "response": None}` and returns `None`. Otherwise returns a copy of the existing record. |
| `db.get(key)` / `db.put(key, record)` | Plain, non-atomic read and write of a record (`None` when absent). |
| `db.complete(key, response)` | Sets the record's status to `"done"` and stores `response`. |
| `db.release(key)` | Deletes the record. |
| `run_id = yield from db.create_run(user_id, body)` | Inserts the run. Takes 0.2 virtual seconds and may raise `gc_runtime.ServerError`. |

`key` may be any hashable value.

**Rules**

| situation | response |
|---|---|
| no `Idempotency-Key` header (header names are case-insensitive), or an empty value | `{"status": 400, "run_id": None, "replayed": False}`, with no db calls |
| the key is free for this user | claim it, create the run, `complete` the record, and return `{"status": 201, "run_id": id, "replayed": False}` |
| the key exists for this user with a different body fingerprint (pending or done) | `{"status": 422, "run_id": None, "replayed": False}` |
| the key exists with the same fingerprint and is `"done"` | the stored response with `"replayed": True` |
| the key exists with the same fingerprint and is `"pending"` | `yield 0.05`, then try `db.claim` again. Repeat until one of the other rows applies. |
| `create_run` raises `ServerError` | `release` the key and return `{"status": 500, "run_id": None, "replayed": False}` |

- Keys are scoped per user: store the record under `(user_id, idempotency_key)`. The same key from two users means two runs.
- The fingerprint is `json.dumps(body, sort_keys=True, separators=(",", ":"))`. Bodies that differ only in key order are the same request.
- A released key is free again, so a waiting duplicate that re-claims it creates the run itself.

The judge sends each request at its arrival time and records every response with the time it finished, the runs that were created, and the number of `create_run` attempts. A request that has not finished after 30 virtual seconds is reported as `"timeout"`.

**Constraints**

- At most 10 requests per case.
- Bodies are small JSON objects, for example `{"agent": "support-triage", "input": {"ticket": "T-1182"}}`.
- Don't import `time`, threads or asyncio. Wait only with `yield <seconds>`.
