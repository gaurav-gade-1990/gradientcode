## 1. What the problem is really asking

Clients retry. A phone on a flaky connection sends `POST /runs`, times out waiting for the answer, and sends it again, sometimes while the first request is still running. Without protection, each retry starts another agent run, which costs tokens and may take real actions twice.

An **`Idempotency-Key` header** turns "create" into "create once". The server keeps one small record per key, and that record is a **three-state machine**:

- **absent:** nobody has used the key, so claim it and do the work.
- **`pending`:** someone else is doing the work right now, so wait and look again.
- **`done`:** the work is finished, so replay the stored response.

Two things make it correct under concurrency. The claim must be **atomic**: a read followed by a later write lets two requests both see an empty slot. And the key must be **scoped to the caller**, because two users can pick the same key string.

The judge sends each request at its arrival time on a virtual clock. It records every response with the time it finished (`t`), the list of `runs` actually created and the number of `create_run` attempts. So it grades *how many runs exist*, not just the status codes, and *when* each duplicate got its answer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `db` | the judge's fake database | `claim`, `complete`, `release`, and `yield from db.create_run(...)` |
| `user_id` | the caller, like `"u_ana"` | half of the scoped key `(user_id, key)` |
| `headers` | a dict of HTTP headers | find `Idempotency-Key`, matching the name case-insensitively |
| `body` | the request JSON as a dict | create the run from it; fingerprint it to detect key reuse |
| `db.claim(key, fp)` | atomic insert-if-absent | `None` means you own the key; otherwise a copy of the existing record |
| `db.create_run(user_id, body)` | a generator taking 0.2 s | `run_id = yield from ...`; may raise `ServerError` |
| return value | `{"status", "run_id", "replayed"}` | returned with `return`, because the handler is a generator |

Three details are easy to miss:

- **The handler must be a generator, even on paths that never wait.** The driver runs it with `yield from`. A `yield` anywhere in the function body is enough. The 400 path returns immediately without ever yielding, which is fine.
- **Header names are case-insensitive.** HTTP/2 proxies lowercase every header name, so `idempotency-key` and `IDEMPOTENCY-KEY` are the same header as `Idempotency-Key`.
- **An empty value counts as missing.** `if not key:` catches both `None` and `""`. `if key is None:` lets an empty key through, and every client that sends `Idempotency-Key:` with no value would then share one record.

## 3. Trace Example 1 by hand

Two identical requests from `u_ana` with key `k-7f3a`, at t=0 and t=0.1. A run takes 0.2 s to create.

These are the database calls, logged as they happen:

| t | request | call | result | what the handler does next |
|---|---|---|---|---|
| 0.00 | #0 | `claim(("u_ana", "k-7f3a"), fp)` | `None` | owns the key; starts `create_run` (finishes at 0.2) |
| 0.10 | #1 | `claim(...)` | pending, same fingerprint | `yield 0.05` |
| 0.15 | #1 | `claim(...)` | pending | `yield 0.05` |
| 0.20 | #0 | `complete(..., run_001)` | record is now done | returns `201, run_001` |
| 0.20 | #1 | `claim(...)` | done | returns the stored response with `replayed: True` |

The judge's output: `[{status: 201, run_id: run_001, replayed: False, t: 0.2}, {status: 201, run_id: run_001, replayed: True, t: 0.2}]`, one run and `create_attempts = 1`.

Both events at t=0.2 happen in a fixed order. Request #0's 0.2-second sleep was scheduled at t=0, before request #1's last poll was scheduled at t=0.15, so the event loop resumes #0 first. When #1 claims again, the record is already done.

**Example 3, a failure.** The first `create_run` raises `ServerError`. The handler releases the key and returns `500` at t=0.2. The client's retry at t=0.5 finds the key free, claims it and creates `run_001` at t=0.7. `create_attempts = 2`, one run.

**The tricky hidden case, "failure while a duplicate waits".** Request #0 claims at t=0 and will fail. Request #1 arrives at 0.1 and polls at 0.1 and 0.15 (pending both times). At t=0.2, #0's insert fails and it calls `release`. Then #1's poll at t=0.2 calls `claim` on a now-free key, gets `None`, and **becomes the owner**. It creates `run_001` itself and finishes at t=0.4 with `replayed: False`. Request #2 at t=1.0 replays it. That's why the waiting loop calls `claim`, not `get`: the same call that checks the record also takes it over when it has gone.

## 4. Key idea: claim, don't check-then-insert

The tempting version reads first, and writes only after the run is created:

```python
rec = db.get(scoped)            # nothing there yet...
if rec is None:
    run_id = yield from db.create_run(...)   # ...0.2 s pass...
    db.put(scoped, {...})       # ...but another request also saw nothing
```

During those 0.2 seconds there is no record at all, so a duplicate arriving at t=0.1 also sees nothing and creates a second run. In Example 1, `wrong_check_then_insert.py` gives the second request `run_002` instead of `run_001`. This is the classic time-of-check to time-of-use race.

`db.claim` closes the gap: checking and reserving the key happen in one atomic step. In SQL it is `INSERT ... ON CONFLICT DO NOTHING` on a unique index over `(user_id, key)`. In Redis it is `SET key value NX`.

## 5. Key idea: the fingerprint catches key reuse

The key says "this is the same request". The fingerprint checks that the client means it. If a client reuses `k-7f3a` with a different body, that is a client bug. Replaying the first response would silently drop the second request, and running it would break the promise of the key. So answer `422`, whether the stored record is pending or done. In "conflict while pending", request #1 with a different body gets `422` at t=0.1, immediately, while request #0 is still creating.

The fingerprint must ignore key order, because JSON objects are unordered and SDKs serialize them differently. `json.dumps(body, sort_keys=True, separators=(",", ":"))` sorts keys at every depth. Without `sort_keys` (`wrong_fingerprint_key_order.py`), "reordered body is the same request" returns `422` for a request that is identical.

## 6. Plan before you code

```
key = the value of the header whose lowercase name is "idempotency-key"
if key is missing or empty: return 400            # no db calls
fp = canonical JSON of body
scoped = (user_id, key)
loop:
    rec = claim(scoped, fp)
    None                  -> we own it; leave the loop
    different fingerprint -> return 422
    done                  -> return stored response, replayed = True
    pending               -> yield 0.05 and loop
try create_run:
    ServerError -> release(scoped); return 500
complete(scoped, 201 response); return it
```

| record from `claim` | same fingerprint | different fingerprint |
|---|---|---|
| `None` (key was free) | create the run | (n/a: we just stored ours) |
| pending | wait 0.05 s, claim again | 422 |
| done | replay, `replayed: True` | 422 |

## 7. Build it one piece at a time

**Step 1: find the key.** Compare header names in lowercase.

```python
key = None
for name, value in headers.items():
    if name.lower() == "idempotency-key":
        key = value
if not key:
    return _resp(400)
```

**Step 2: fingerprint and scope.** A tuple is hashable, so it works directly as the record's key and can't collide the way string joining can.

```python
fingerprint = json.dumps(body, sort_keys=True, separators=(",", ":"))
scoped = (user_id, key)
```

Leave out `user_id` (`wrong_key_not_scoped_per_user.py`) and in Example 2 `u_ben` gets `u_ana`'s `run_001` replayed instead of a run of his own. That's a data leak, not just a wrong answer.

**Step 3: the claim loop.**

```python
while True:
    rec = db.claim(scoped, fingerprint)
    if rec is None:
        break
    if rec["fingerprint"] != fingerprint:
        return _resp(422)
    if rec["status"] == "done":
        return dict(rec["response"], replayed=True)
    yield POLL
```

`dict(rec["response"], replayed=True)` copies the stored response and overrides one field. The stored record keeps `replayed: False`, and every replay says `True`.

**Step 4: create, then complete or release.**

```python
try:
    run_id = yield from db.create_run(user_id, body)
except ServerError:
    db.release(scoped)
    return _resp(500)
resp = _resp(201, run_id)
db.complete(scoped, resp)
return resp
```

The `release` matters twice over. Without it (`wrong_no_release_on_failure.py`), the record stays `pending` forever. The client's retry in Example 3 then polls until the judge reports `"timeout"`. In "many keys mixed", a later request with a different body gets `422` against a record that never produced anything.

## 8. Full solution

```python
# canonical JSON for the body fingerprint
import json

# the transient failure create_run can raise
from gc_runtime import ServerError

# seconds between checks while another request holds the key
POLL = 0.05


# build a response dict in the shape the judge expects
def _resp(status, run_id=None, replayed=False):
    return {"status": status, "run_id": run_id, "replayed": replayed}  # one shape for every outcome


# POST /runs, made safe to retry with an Idempotency-Key header
def handle_create_run(db, user_id, headers, body):
    key = None  # no key until we find the header
    for name, value in headers.items():  # header names are case-insensitive, so scan them all
        if name.lower() == "idempotency-key":  # matches any capitalization, e.g. from HTTP/2 proxies
            key = value  # remember the client's key
    if not key:  # missing or empty: we can't deduplicate safely
        return _resp(400)  # reject before touching the database
    fingerprint = json.dumps(body, sort_keys=True, separators=(",", ":"))  # same body, any key order, same string
    scoped = (user_id, key)  # keys belong to a user; two users may pick the same one
    while True:  # until we own the key or can answer from its record
        rec = db.claim(scoped, fingerprint)  # atomic: reserve the key if it is free
        if rec is None:  # it was free, and now it is ours
            break  # go and create the run
        if rec["fingerprint"] != fingerprint:  # same key, different request: a client bug
            return _resp(422)  # refuse rather than replay or run the wrong thing
        if rec["status"] == "done":  # the original request already finished
            return dict(rec["response"], replayed=True)  # replay it, marked as a replay
        yield POLL  # still pending: wait a little, then claim again
    try:  # the only step that can fail
        run_id = yield from db.create_run(user_id, body)  # the real side effect, done once
    except ServerError:  # the insert failed
        db.release(scoped)  # free the key so the retry and any waiting duplicates can proceed
        return _resp(500)  # tell this caller it failed
    resp = _resp(201, run_id)  # the response every duplicate will replay
    db.complete(scoped, resp)  # store it and mark the key done
    return resp  # the original caller gets it too
```

## 9. How the test cases map to the code

| test case | expected (from the judge) | what it checks |
|---|---|---|
| Example 1 | both `run_001`, the second `replayed: True` at t=0.2; one run | a duplicate waits on `pending` and replays |
| Example 2 | `422` for the reused key with another body; `u_ben` gets `run_002` | fingerprint conflict, and per-user scoping |
| Example 3 | `500` at 0.2, then the retry creates `run_001` at 0.7 | release on failure frees the key |
| three concurrent duplicates | one run; two replays at t=0.2 | the atomic claim under a real race |
| same moment, two users | `run_001` for u_ana, `run_002` for u_ben, then u_ben's replay | scoping when both arrive at t=0 |
| reordered body is the same request | replay at 0.3 | `sort_keys=True` against a done record |
| reordered body while pending | replay at 0.2 | `sort_keys=True` against a pending record |
| lowercase header from HTTP/2 proxy | `201`, then a replay at 0.5 | case-insensitive header lookup |
| missing and empty key | two `400`s at t=0; zero attempts | `if not key` covers both, with no db calls |
| failure while a duplicate waits | the waiter creates `run_001` itself at 0.4 | the poll re-claims a released key |
| conflict while pending | `422` at t=0.1 while #0 is still creating | the fingerprint check runs before the status check |
| many keys mixed | 3 runs, 4 attempts; u_ana's `k-b` retry creates `run_003` at 0.5 | everything together, including a release followed by a different body |

## 10. Complexity

Each request makes one `claim`, plus one per 0.05-second poll while another request holds the key. With a 0.2-second create, a duplicate polls at most a handful of times. Storage is one record per `(user, key)`, holding the fingerprint and the response.

In production those records need a lifetime. Stripe keeps idempotency keys for 24 hours, and that window is the promise you make to clients. Pending records need a lock timeout too. If the process dies between `claim` and `complete`, nothing releases the key, and every duplicate polls forever. A `locked_until` column, or a sweeper that frees stale pending rows, fixes that. Polling also isn't free at scale: a long-running create with many waiting duplicates turns into a burst of reads. Long polls or a notification channel are the usual fix.

## 11. If you got Wrong Answer

- **A duplicate gets `run_002` instead of a replay of `run_001`** (Example 1). You read with `get` and write after creating, so nothing is reserved during the insert: `wrong_check_then_insert.py`.
- **A response is `"timeout"`** (Example 3's retry). The record stayed `pending` after a failure because you never call `release`: `wrong_no_release_on_failure.py`. The same symptom on almost every case means you forgot `db.complete`.
- **`u_ben` gets `run_001`** (Example 2). The key isn't scoped per user: `wrong_key_not_scoped_per_user.py`.
- **A reordered body gets `422`.** The fingerprint is missing `sort_keys=True`: `wrong_fingerprint_key_order.py`.
- **The first request in "lowercase header from HTTP/2 proxy" gets `400`.** You match the header name exactly: `wrong_case_sensitive_header.py`.
- **The empty key gets `201`** ("missing and empty key"). You test `key is None` instead of `not key`.
- **Duplicates get `409` instead of waiting.** Returning a conflict on `pending` is a valid API design (Stripe does it), but this problem says to poll and replay.
- **A replay has `replayed: False`.** You returned the stored response without overriding the flag.

## 12. Follow-ups an interviewer might ask

- *Why not just make `create_run` itself idempotent?* You can, by passing the key down as a unique column on the runs table. The key table is still useful, because it stores the *response* to replay and catches body mismatches before any work starts.
- *How long do you keep keys, and what about the pending ones?* Keep done records for a fixed window (Stripe uses 24 hours). Give pending records a lock timeout so a crashed worker can't block the key forever.
- *The run starts an agent that calls tools. Are those safe to retry?* Not automatically. Each tool call needs its own idempotency key, derived from the run and the step (problem 119, idempotent-tool-execution).
- *How do you get the "run created" event to other services exactly once?* Write the run and an outbox row in the same transaction, and have a relay publish from the outbox (problem 172, transactional-outbox).
- *What's the read-side equivalent?* For identical concurrent reads you don't need a durable record. Coalesce them in memory onto one upstream call (problem 171, request-coalescing).
