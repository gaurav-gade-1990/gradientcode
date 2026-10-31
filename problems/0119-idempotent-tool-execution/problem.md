Your agent retries tool calls when the network times out, and last week a customer was charged twice because the first `charge_card` had actually succeeded. Put an idempotency layer in front of every side-effecting tool.

Implement `class IdempotentExecutor`:

- `IdempotentExecutor(clock, ttl)`, where `clock` is a `gc_runtime.Clock` and `ttl` is in seconds.
- `execute(key, tool, args, fn)`, where `key` is the idempotency key (a string, or `None`), `tool` is the tool name, `args` is a JSON-like dict, and `fn(args)` performs the side effect and returns a result, or raises `gc_runtime.ToolError`.

**Fingerprint.** A request's fingerprint is `(tool, json.dumps(args, sort_keys=True))`, so dict key order doesn't matter.

**Rules for `execute`.** Let `now = clock.now()`.

| situation | do | return |
|---|---|---|
| `key is None` | call `fn(args)`, store nothing | as for a fresh run |
| a stored entry for `key` has `now - stored_at >= ttl` | delete it, then continue as if there were none | |
| live entry, same fingerprint | don't call `fn` | `{"status": "replayed", "result": stored_result}` |
| live entry, different fingerprint | don't call `fn` | `{"status": "conflict"}` |
| no live entry | call `fn(args)` once | see the next table |

A fresh run of `fn(args)`:

| outcome | store | return |
|---|---|---|
| returns `r` | `key -> (fingerprint, r, stored_at=now)` | `{"status": "executed", "result": r}` |
| raises `ToolError` `e` | nothing, so a retry runs the tool again | `{"status": "failed", "error": str(e)}` |

Replays and conflicts don't change `stored_at`, so the TTL always counts from the original execution. Keys are global: the same key with a different tool is a conflict.

The judge advances the virtual clock between calls and grades every return value and every real invocation of `fn`.

**Constraints**

- At most 40 calls, with `0 < ttl <= 86400`.
- `fn` takes no virtual time. Use only `clock.now()` for time.
