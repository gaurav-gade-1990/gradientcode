## 1. What the problem is really asking

An audit log is only worth something if the people it audits can't rewrite it. Here the threat is an admin with write access to the table: they can edit a row, delete a row, renumber rows, and even recompute hashes, because the hash formula isn't secret.

The defence is a **hash chain**. Every entry's hash covers the previous entry's hash plus its own event:

```
hash_i = sha256(hash_{i-1} + canonical_json(event_i))
```

So each row commits to every row before it. Change anything old and every later hash is wrong. To hide an edit, the attacker has to recompute the whole tail, and that's what the **published head** catches: the platform wrote the last hash somewhere the attacker can't reach.

Under the story there are two small jobs: a deterministic serializer feeding SHA-256, and a linear scan that reports the first index where one of three checks fails. The judge records the first 12 characters of every `prev_hash` and `hash` your `append_event` produced, the full head, and two verdicts: `intact` (your `verify_chain` on the untouched chain) and `first_bad` (on a tampered copy). Because the hashes themselves are graded, your serialization has to match the spec byte for byte.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `chain` | a list of entry dicts, appended to in place | `chain[-1]["hash"]` is the previous hash; `len(chain)` is the next `seq` |
| `event` | a JSON object, possibly nested, possibly non-ASCII | deep-copied, then hashed via `canonical_json` |
| `GENESIS` | `"0" * 64` | the `prev_hash` of entry 0, and the head of an empty chain |
| `head` | the hash published when the log was sealed, or `None` | compared with the current last hash after the scan |
| return of `verify_chain` | `-1`, an index `i`, or `len(chain)` | the first failing row, or "the tail is wrong" |

The driver is short and worth reading, because it tells you exactly what's graded:

```python
chain = []
for e in events:
    got = append(chain, e)          # must be chain[-1]
hashes = [e["hash"] for e in chain]
head = chain[-1]["hash"] if chain else GENESIS
for m in mutate_input:              # the caller reuses its dicts
    events[m["index"]][m["field"]] = m["value"]
intact = verify(chain, head)
tampered = copy.deepcopy(chain)
for op in tamper: _tamper(tampered, op)
first_bad = verify(tampered, head if anchor else None)
```

Three details are easy to miss:

- **`seq` is not part of the hash.** The hash covers `prev_hash` and `event` only. That means check 1 (`seq == i`) is the *only* thing that catches a forged `seq` on an otherwise untouched row.
- **Check 2 compares with the previous entry's *stored* hash**, not a recomputed one. A row's link is about what's actually written in the row before it.
- **The head check happens only if every row passes**, and it returns `len(chain)`, an index one past the end. It means "something after the last row I can see is wrong."

## 3. Trace the examples by hand

**Example 1** logs three events: a refund, a customer read, and a role grant. The refund serializes to:

```
{"action":"refund.issue","actor":"agent:billing-bot","amount":42.5,"target":"order_1182","tenant":"acme"}
```

Keys are sorted and there are no spaces. The caller wrote the dict as `actor, action, tenant, target, amount`, and `json.dumps` without options would keep that order and add a space after every `:` and `,`.

| seq | prev_hash (first 12) | hash (first 12) |
|---|---|---|
| 0 | `000000000000` | `6f160832523d` |
| 1 | `6f160832523d` | `aa75e371242b` |
| 2 | `aa75e371242b` | `efc9e0a8235c` |

Each `prev_hash` is the `hash` in the row above. The head is `efc9e0a8235c8d4c...`. Nothing is tampered, so `intact` and `first_bad` are both `-1`.

**Example 2** changes row 0's `amount` from `42.5` to `4250.0`. Row 0's `seq` is 0 and its `prev_hash` is `GENESIS`, so checks 1 and 2 pass. Recomputing its hash now gives `ca18e8b5e74c...`, which isn't the stored `6f160832523d...`. Check 3 fails, so `first_bad = 0`.

**Example 3** is the attacker getting smarter: edit row 0, then **rehash** row 0 so its stored hash is `ca18e8b5e74c...` and check 3 passes. Now look at row 1. Its `prev_hash` is still `6f160832523d...`, but `chain[0]["hash"]` is `ca18e8b5e74c...`. Check 2 fails at index 1, so `first_bad = 1`. This is the whole point of chaining: fixing one row breaks the next.

**The tricky hidden one, "rewrite whole tail, anchored":** ten events, edit row 6, then recompute `prev_hash` and `hash` for rows 6 through 9. Every row now passes all three checks, because the attacker rebuilt the chain correctly from row 6 on. The only evidence left is that the new last hash isn't the published head `1b876add35fa...`. So the scan finishes, the head comparison fails, and you return `len(chain) = 10`. The same tamper with `anchor: False` returns `-1`. Without an external anchor, a full rewrite is undetectable.

## 4. Key idea: one byte string per event

A hash is over bytes, so "the same event" has to mean "the same bytes", every time and on every machine. `canonical_json` fixes the three things `json.dumps` leaves open:

| option | what goes wrong without it |
|---|---|
| `sort_keys=True` | key order follows insertion order, so the same event built in a different order hashes differently (and at every depth: nested dicts are sorted too) |
| `separators=(",", ":")` | the default adds spaces after `,` and `:`, so the bytes differ from the spec |
| `ensure_ascii=False` | `zoë` becomes `zoë`, so a verifier in another language that writes UTF-8 gets a different hash |

Then encode with `.encode("utf-8")`. With `ensure_ascii=False` the string can contain `ë` or `東京`, and UTF-8 is the encoding the spec names.

## 5. Key idea: store a copy, not the caller's dict

`append_event` hashes the event *now*. If you store the caller's dict and the caller later reuses it, the stored event changes but the stored hash doesn't. Your own verification then reports tampering that never happened. That's what "caller reuses its dict" does: after appending, the driver sets `events[1]["fields"] = ["ssn"]`. With a copy, `intact` is `-1`. Storing the caller's dict makes `intact` and `first_bad` both `1`, because row 1's event no longer matches its hash.

Use `copy.deepcopy`. A shallow `dict(event)` would protect against top-level reassignment but not against the caller appending to a nested list it still holds.

## 6. Plan before you code

```
append_event(chain, event):
    prev = last entry's hash, or GENESIS if chain is empty
    e = deep copy of event
    entry = {seq: len(chain), prev_hash: prev, event: e, hash: sha256(prev + canonical(e))}
    append entry; return it

verify_chain(chain, head):
    for i, entry in enumerate(chain):
        if entry.seq != i: return i                               # check 1
        if entry.prev_hash != (GENESIS if i == 0 else chain[i-1].hash): return i   # check 2
        if entry.hash != recompute(entry.prev_hash, entry.event): return i         # check 3
    if head is given and current head != head: return len(chain)
    return -1
```

What each attacker move trips:

| tamper | first check that fails |
|---|---|
| edit a field | check 3 on that row |
| edit and rehash that row | check 2 on the next row |
| delete a row | check 1 on the next row (a `seq` gap) |
| delete and renumber | check 2 on the next row |
| swap two rows | check 1 at the first swapped position |
| forge a `seq` | check 1 on that row (nothing else covers `seq`) |
| rewrite the whole tail, or truncate | only the head |

## 7. Build it one piece at a time

**Step 1: the canonical form and the hash.** Two helpers, so `append_event` and `verify_chain` can't drift apart. If they serialized differently, every row would fail check 3.

```python
def canonical_json(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_hash(prev_hash, event):
    return hashlib.sha256((prev_hash + canonical_json(event)).encode("utf-8")).hexdigest()
```

**Step 2: append.** Read `prev` before appending, and use `len(chain)` before appending as `seq`. Hash the *copy*, so what's stored and what's hashed are the same object.

```python
def append_event(chain, event):
    prev = chain[-1]["hash"] if chain else GENESIS
    event = copy.deepcopy(event)
    entry = {"seq": len(chain), "prev_hash": prev, "event": event, "hash": entry_hash(prev, event)}
    chain.append(entry)
    return entry
```

The driver checks `got is chain[-1]`, so return the same dict you appended, not a copy of it.

**Step 3: the per-row checks.** Return on the first failure. All three checks return the same `i`, so their order inside one row doesn't change the answer, but doing them in the table's order keeps the code readable.

```python
def verify_chain(chain, head=None):
    for i, entry in enumerate(chain):
        expected_prev = GENESIS if i == 0 else chain[i - 1]["hash"]
        if entry["seq"] != i:
            return i
        if entry["prev_hash"] != expected_prev:
            return i
        if entry["hash"] != entry_hash(entry["prev_hash"], entry["event"]):
            return i
```

Check 3 recomputes from the entry's *own* `prev_hash`, not from `expected_prev`. Check 2 has already compared those two, so they agree whenever check 3 runs.

**Step 4: the anchor.** Only after the loop. An empty chain's head is `GENESIS`, so an empty log verified against a `GENESIS` head is intact.

```python
    current = chain[-1]["hash"] if chain else GENESIS
    if head is not None and current != head:
        return len(chain)
    return -1
```

Nothing here writes to `chain`. The driver compares the chain with a snapshot after `verify_chain` and raises if you changed it.

## 8. Full solution

```python
import copy  # deep-copy events so the caller can't change them after they're logged
import hashlib  # SHA-256 for the chain
import json  # canonical serialization of each event

GENESIS = "0" * 64  # the prev_hash of entry 0, and the head of an empty chain


def canonical_json(event):  # one exact byte string per event, on any machine
    # sorted keys at every depth, no spaces, raw UTF-8 instead of \u escapes
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_hash(prev_hash, event):  # shared by append and verify so they can't disagree
    # the hash commits to the previous hash, which commits to everything before it
    return hashlib.sha256((prev_hash + canonical_json(event)).encode("utf-8")).hexdigest()


def append_event(chain, event):  # add one tamper-evident entry to the end of the log
    prev = chain[-1]["hash"] if chain else GENESIS  # link to the last row, or to GENESIS
    event = copy.deepcopy(event)  # store and hash our own copy, not the caller's dict
    # seq is the index this entry will have; hash covers prev_hash and the copied event
    entry = {"seq": len(chain), "prev_hash": prev, "event": event, "hash": entry_hash(prev, event)}
    chain.append(entry)  # the log grows in place
    return entry  # the driver checks this is the same object as chain[-1]


def verify_chain(chain, head=None):  # first failing index, len(chain) for a bad tail, or -1
    for i, entry in enumerate(chain):  # scan in order so we report the first bad row
        # what this row's link must be: GENESIS for row 0, else the stored hash above it
        expected_prev = GENESIS if i == 0 else chain[i - 1]["hash"]
        if entry["seq"] != i:  # check 1: catches deletes, swaps and forged seq (seq isn't hashed)
            return i  # this row is the first one that fails
        if entry["prev_hash"] != expected_prev:  # check 2: the link to the row above is broken
            return i  # e.g. the row above was edited and rehashed
        if entry["hash"] != entry_hash(entry["prev_hash"], entry["event"]):  # check 3: content changed
            return i  # the event no longer matches its stored hash
    current = chain[-1]["hash"] if chain else GENESIS  # the head of the chain as it stands now
    if head is not None and current != head:  # every row is consistent, but is it the chain we sealed?
        return len(chain)  # the tail was rewritten or truncated: point one past the end
    return -1  # every row passed and the head matches (or none was published)
```

## 9. How the test cases map to the code

| test case | expected `first_bad` | what it checks |
|---|---|---|
| Example 1 | -1 (hashes `6f16...`, `aa75...`, `efc9...`) | the exact canonical serialization and chaining |
| Example 2 | 0 | an edited event fails check 3 on its own row |
| Example 3 | 1 | a rehashed row breaks the next row's link (check 2) |
| empty log, empty log truncation of nothing | -1 | an empty chain's head is `GENESIS` |
| key order does not matter | -1 | `sort_keys=True`, including nested dicts |
| non-ascii names | -1 (hashes `ce6e...`, `316a...`) | `ensure_ascii=False` and UTF-8 encoding |
| delete and renumber | 3 | the renumbered row's `prev_hash` points at the deleted row |
| delete without renumber | 5 | the `seq` gap (check 1) |
| rewrite whole tail, anchored | 10 | only the published head catches a full rewrite |
| rewrite whole tail, no anchor | -1 | with no head, a full rewrite passes |
| truncate tail | 9 | a shorter chain whose last hash isn't the head |
| swap two rows | 2 | position 2 holds `seq` 4 |
| forged seq | 4 | check 1 is the only guard on `seq` |
| caller reuses its dict | -1, and `intact` -1 | the stored event is a copy |
| long log, edit late | 141 | the scan reaches a late row and stops there |

## 10. Complexity

`append_event` is O(size of the event) for the copy, the serialization and the hash. `verify_chain` is O(total size of all events), because it reserializes and rehashes every row. At 200 events that's instant. On a real audit log with billions of rows, a full scan is a batch job, so production systems seal the log periodically (hourly in AWS CloudTrail's digest files) and verify one sealed segment at a time against its signed head. A Merkle tree over each segment lets you prove one event is included with O(log n) hashes instead of rereading everything.

## 11. If you got Wrong Answer

Compare the `entries` hashes first, then `intact`, then `first_bad`.

- **Every hash prefix differs from the expected one, even in Example 1.** Your serialization isn't canonical. Most often `sort_keys=True` is missing, or you used the default separators.
- **Only "non-ascii names" has different hashes.** You left `ensure_ascii` at its default, so `zoë` was hashed as `zoë`.
- **"caller reuses its dict" gives `intact: 1`.** You stored the caller's dict instead of a deep copy, so the driver's later mutation changed your log.
- **Example 3 and "delete and renumber" return `-1`.** You check each row's own hash but never compare `prev_hash` with the previous row's stored hash (check 2).
- **"rewrite whole tail, anchored" and "truncate tail" return `-1`.** You ignore `head`, or compare it before the loop. Compare it after every row passes and return `len(chain)`.
- **"forged seq" returns `-1`.** You skipped check 1. `seq` isn't hashed, so nothing else catches it.

## 12. Follow-ups an interviewer might ask

- *How do you stop the attacker from forging the head too?* Sign it. Periodically sign the current head with a KMS key and store the signature somewhere append-only (a transparency log, a write-once bucket, an email to auditors). The verifier checks the signature before trusting the head.
- *A customer files a GDPR erasure request for data that's in a hashed event. What now?* You can't delete it without breaking the chain. Keep PII out of the event: store a vault token instead (problem 162, pii-redaction-vault), or hash a commitment to the PII and store the raw value separately so it can be erased.
- *Can you verify one event without rereading the whole log?* Build a Merkle tree over each batch and publish the root. An inclusion proof is the O(log n) sibling hashes on the path to the root.
- *Python writes `1.0` where JavaScript writes `1`. Does that matter?* Yes, a verifier in another language would hash different bytes. RFC 8785 (JSON Canonicalization Scheme) fixes number formatting too. Use it when more than one language has to verify the log.
- *Why does `rewrite_from` without an anchor pass?* A chain checked only against itself proves internal consistency, not that it's the chain you wrote. The same reasoning underlies signed webhook deliveries (problem 167, signed-webhook-delivery): integrity needs a secret or an external reference the attacker doesn't control.
