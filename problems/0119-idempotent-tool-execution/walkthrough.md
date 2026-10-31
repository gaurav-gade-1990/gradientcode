## 1. What the problem is really asking

Retries are only safe when the thing you retry is **idempotent**: running it twice has the same effect as running it once. Charging a card isn't. If the first `charge_card` succeeded but the response was lost to a timeout, a blind retry charges the customer again.

The fix is the same one Stripe uses: the caller attaches an **idempotency key** to each logical operation, and a layer in front of the tool remembers what happened for that key. Under the story, this is **a dictionary with lazy expiry and a four-way decision**:

- no key → just run it;
- key seen, entry too old → forget it and treat the call as new;
- key seen, same request → hand back the stored result without running anything;
- key seen, different request → refuse with a conflict.

The judge grades two things: the list of dicts you return, and `tool_runs`, a record of every time `fn` really executed. A replay that secretly calls `fn` shows up as an extra side effect even if your return value looks right.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `clock` | a `gc_runtime.Clock` with virtual time | `clock.now()` once per `execute` |
| `ttl` | seconds an entry stays live | expired when `now - stored_at >= ttl` |
| `key` | idempotency key string, or `None` | the dictionary key; `None` means "don't dedupe" |
| `tool`, `args` | the request | together they form the **fingerprint** |
| `fn(args)` | performs the side effect | call it at most once per fresh run; it may raise `ToolError` |

Three details are easy to miss:

- **The fingerprint includes the tool name.** Keys are global. In Example 2, the same key with `refund_charge` instead of `charge_card` is a conflict.
- **The boundary is `>=`.** An entry stored at `t=0` with `ttl=30` is expired at exactly `t=30`.
- **Failures are never stored.** A `ToolError` means the side effect didn't happen, so a retry must be allowed to run it.

## 3. Trace the examples by hand

**Example 1** (`ttl=3600`):

| t | key | request | store before | decision | `fn` runs? |
|---|---|---|---|---|---|
| 0 | `run_77:step_3` | `charge_card` 12900 | empty | executed, `ch_001` | yes |
| 2.5 | `run_77:step_3` | same | live, same fingerprint | replayed `ch_001` | no |
| 4 | `run_77:step_4` | `send_email` | no entry for this key | executed, `send_email_002` | yes |

`tool_runs` has two entries, at t=0 and t=4. The retry at t=2.5 returned the original receipt and charged nobody.

**Example 3** (`ttl=60`), the failure and expiry case:

| t | outcome | why |
|---|---|---|
| 0 | `failed`, `card_declined: insufficient_funds` | `fn` raised; nothing stored |
| 5 | `executed`, `ch_002` | no entry, so it runs for real |
| 70 | `executed`, `ch_003` | `70 - 5 = 65 >= 60`, expired |

The charge id is `ch_002` at t=5 because the driver numbers ids by how many times `fn` has run, and the failed attempt at t=0 counted as a run.

**The trickiest hidden case, "replay does not extend ttl"** (`ttl=10`):

| t | age of entry | decision |
|---|---|---|
| 0 | none | executed, `ch_001` |
| 6 | 6 | replayed `ch_001` |
| 12 | 12 | expired → executed, `ch_002` |
| 15 | 3 (entry from t=12) | replayed `ch_002` |

If the replay at t=6 had refreshed `stored_at`, the entry's age at t=12 would be 6, and you'd replay instead of executing.

## 4. Key idea: the fingerprint is what makes the key safe

A key alone says "this is the same operation". A replay is only correct if it really is the same *request*. If a buggy agent reuses `run_77:step_3` for a $12.90 charge after a $129.00 one, returning the $129.00 receipt silently hides the bug and leaves the customer uncharged for the second purchase. So the store keeps a fingerprint, and a mismatch is a `conflict` that neither runs nor replays.

The fingerprint has to be canonical. Models don't promise key order, so `{"customer_id", "amount_cents", "currency"}` and `{"currency", "amount_cents", "customer_id"}` must match. `json.dumps(args, sort_keys=True)` sorts keys at every depth, which is why "key order does not matter" also replays `create_ticket` when only the nested `meta` dict's order changes.

## 5. Plan before you code

```
execute(key, tool, args, fn):
    now = clock.now()
    fp = (tool, json.dumps(args, sort_keys=True))
    entry = store[key] if key is not None
    if entry and now - entry.stored_at >= ttl: delete it, entry = None
    if entry: same fp -> replayed (stored result); else -> conflict
    try fn(args); ToolError e -> failed (store nothing)
    if key is not None: store (fp, result, now)
    return executed
```

| entry | fingerprint | result |
|---|---|---|
| none or expired | n/a | run `fn` |
| live | equal | `replayed` |
| live | different | `conflict` |

## 6. Build it one piece at a time

**Step 1: state.** One dict, with a tuple per key. `stored_at` is the time of the real execution.

```python
class IdempotentExecutor:
    def __init__(self, clock, ttl):
        self.clock = clock
        self.ttl = ttl
        self.store = {}  # key -> (fingerprint, result, stored_at)
```

**Step 2: look up, with lazy expiry.** There's no background sweeper; an entry is checked for age only when its key comes back. That's enough here, and it's how many caches work.

```python
        now = self.clock.now()
        fingerprint = (tool, json.dumps(args, sort_keys=True))
        entry = self.store.get(key) if key is not None else None
        if entry is not None and now - entry[2] >= self.ttl:
            del self.store[key]
            entry = None
```

**Step 3: replay or conflict.** Neither branch touches the store, so `stored_at` keeps counting from the original execution.

```python
        if entry is not None:
            if entry[0] == fingerprint:
                return {"status": "replayed", "result": entry[1]}
            return {"status": "conflict"}
```

**Step 4: a fresh run.** Store only after `fn` returns. If it raises, return `failed` and keep the store unchanged. With `key is None`, run but never store.

```python
        try:
            result = fn(args)
        except ToolError as e:
            return {"status": "failed", "error": str(e)}
        if key is not None:
            self.store[key] = (fingerprint, result, now)
        return {"status": "executed", "result": result}
```

## 7. Full solution

```python
import json  # canonical JSON for the request fingerprint

from gc_runtime import ToolError  # the only failure fn raises; it means "the side effect didn't happen"


class IdempotentExecutor:  # dedupes side-effecting tool calls by idempotency key
    def __init__(self, clock, ttl):  # virtual clock and entry lifetime in seconds
        self.clock = clock  # the only source of time
        self.ttl = ttl  # how long after the real execution we still dedupe
        self.store = {}  # key -> (fingerprint, result, stored_at)

    def execute(self, key, tool, args, fn):  # run fn at most once per key and request
        now = self.clock.now()  # one timestamp for the whole decision
        fingerprint = (tool, json.dumps(args, sort_keys=True))  # same request regardless of key order or tool reuse
        entry = self.store.get(key) if key is not None else None  # no key means no deduplication
        if entry is not None and now - entry[2] >= self.ttl:  # lazy expiry; >= so exactly ttl is expired
            del self.store[key]  # forget the stale entry
            entry = None  # and treat this call as brand new
        if entry is not None:  # a live entry for this key
            if entry[0] == fingerprint:  # the same request again: a retry
                return {"status": "replayed", "result": entry[1]}  # hand back the original result; fn not called
            return {"status": "conflict"}  # same key, different request: an upstream bug, don't run or replay
        try:  # a fresh run
            result = fn(args)  # the real side effect, exactly once
        except ToolError as e:  # it failed, so nothing happened downstream
            return {"status": "failed", "error": str(e)}  # store nothing, so a retry can run it again
        if key is not None:  # only keyed calls are remembered
            self.store[key] = (fingerprint, result, now)  # stored_at is the real execution time, never refreshed
        return {"status": "executed", "result": result}  # report the real run
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | executed, replayed, executed; 2 runs | the basic replay; different keys are independent |
| Example 2 | executed, conflict, conflict; 1 run | a different amount or a different tool is a conflict |
| Example 3 | failed, executed, executed; 3 runs | failures aren't stored; expiry at 65 s with `ttl=60` |
| key order does not matter | executed, replayed, conflict, executed, replayed | `sort_keys=True`, including nested dicts; an extra key is a different request |
| exact ttl boundary | executed, replayed (29.999), executed (30), replayed (45) | `>=`, not `>` |
| replay does not extend ttl | executed, replayed, executed (12), replayed | replays leave `stored_at` alone |
| never expires catches | executed, executed | an expired entry with a different request runs, not conflicts |
| no key always runs | executed ×3, then replayed | `key is None` never stores |
| repeated failures then success then conflict | failed, failed, executed, replayed, conflict; 3 runs | repeated failures still don't store; the scripted `should not run` failure never runs |
| conflict after expiry becomes fresh | executed, conflict, executed (61), replayed | a conflict doesn't touch the entry; expiry clears the way |
| many keys interleaved | 7 real runs in 25 calls | three keys expiring on their own schedules |

## 9. Complexity

Each call is O(size of `args`) for `json.dumps`, plus an O(1) dict lookup. Memory is O(live keys), but because expiry is lazy, a key that is never used again stays in the dict forever. In production the store is Redis with a native TTL (`SET key value NX PX ttl`) or a database table with a sweeper, so stale entries are reclaimed without waiting for their key to come back.

The bigger production issue is atomicity. "Run the side effect" and "store the result" are two steps. A crash between them brings the double charge back. Real systems write the idempotency row in the same transaction as the side effect (problem 172, transactional-outbox), or lock the key while the request is in flight so a concurrent duplicate waits instead of running (problem 171, request-coalescing).

## 10. If you got Wrong Answer

- **"key order does not matter" returns `conflict` at t=1.** Your fingerprint uses `json.dumps(args)` without `sort_keys=True`.
- **Example 2 returns `replayed` instead of `conflict`.** You're matching on the key alone. Compare the fingerprint.
- **Example 3's call at t=5 returns `failed` again and `tool_runs` has one entry.** You stored the failure. Don't store anything when `fn` raises.
- **"exact ttl boundary" replays at t=30.** You used `>` instead of `>=`.
- **"replay does not extend ttl" replays at t=12.** You refreshed `stored_at` on replay.
- **"never expires catches" returns `conflict` at t=100.** You never expire entries.
- **"no key always runs" replays at t=1.** You stored the result under the key `None`.

## 11. Follow-ups an interviewer might ask

- *Where should the key come from?* Something stable across retries of the same step: the agent run id plus the step index, or the model's `tool_use` id. A fresh UUID per attempt defeats the purpose.
- *What about two identical requests arriving at the same time?* Both see no entry and both run. Add an in-flight state: claim the key first (`SET NX`), run, then fill in the result; a second caller waits or gets `409` (problem 180, api-idempotent-create).
- *How does this combine with retries?* Retry with backoff (problem 124) is only safe once this layer exists. The retry loop reuses the same key on every attempt.
- *Should a conflict be an error the model sees?* Yes. Return it as a tool error ("this step was already executed with different arguments") so the agent notices instead of looping, and log it, because it usually means a bug in how keys are built.
- *What about durable workflows?* Engines like Temporal record each activity's result and replay it after a crash (problem 111, durable-workflow-replay). Downstream APIs still need idempotency keys, because activities are retried at least once.
