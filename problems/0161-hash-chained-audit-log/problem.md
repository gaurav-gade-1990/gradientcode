Every action an AI coworker takes on your platform (issuing a refund, reading a customer record, changing a role) goes into an audit log that compliance reviews later. An admin with database access must not be able to quietly edit or delete a row. Make the log tamper-evident with a hash chain.

Implement two functions. The constant `GENESIS = "0" * 64` is the `prev_hash` of the first entry.

**`append_event(chain, event)`** appends one entry to the list `chain` (in place) and returns it. An entry is

```
{"seq": i, "prev_hash": p, "event": e, "hash": h}
```

- `seq` is the entry's index in `chain`.
- `prev_hash` is `GENESIS` for the first entry, else the previous entry's `hash`.
- `event` is a **deep copy** of the event, so a caller who later mutates its own dict can't change the log.
- `hash = sha256((prev_hash + canonical_json(event)).encode("utf-8")).hexdigest()`, where

```python
canonical_json(e) = json.dumps(e, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

**`verify_chain(chain, head=None)`** returns the index of the **first** entry that fails, or `-1` if the chain is intact. For each index `i` in order, the entry fails if any of these is false:

| # | check |
|---|---|
| 1 | `entry["seq"] == i` |
| 2 | `entry["prev_hash"]` equals `GENESIS` when `i == 0`, else `chain[i-1]["hash"]` as stored |
| 3 | `entry["hash"]` equals the hash recomputed from this entry's own `prev_hash` and `event` |

If every entry passes and `head` is given, `head` is the hash the platform published externally when the log was last sealed. Compare it with the current head (the last entry's `hash`, or `GENESIS` for an empty chain). If they differ, return `len(chain)`, because the tail was truncated or rewritten.

The judge builds the chain with your `append_event`, records every hash, may mutate the original event dicts, then tampers with a copy of the chain the way an attacker would (edit a field, recompute one hash, delete and renumber rows, rewrite the whole tail, truncate) and calls your `verify_chain`.

**Constraints**

- `0 <= len(events) <= 200`
- Events are JSON objects: strings (possibly non-ASCII), ints, floats, bools, nulls, lists and nested objects.
- `verify_chain` must not modify `chain`.
