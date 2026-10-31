## Approach

Each entry commits to everything before it: its hash covers the previous hash, so changing any old row changes every later hash.

```python
def append_event(chain, event):
    prev = chain[-1]["hash"] if chain else GENESIS
    event = copy.deepcopy(event)
    entry = {"seq": len(chain), "prev_hash": prev, "event": event,
             "hash": sha256((prev + canonical_json(event)).encode()).hexdigest()}
    chain.append(entry)
    return entry
```

Verification walks the rows and reports the first one where `seq`, the link to the previous row, or the row's own hash is wrong. What each check catches:

| tamper | caught by |
|---|---|
| edit a field | check 3 on that row |
| edit and recompute that row's hash | check 2 on the next row |
| delete a row | check 1 (seq gap) on the next row |
| delete and renumber | check 2 on the next row |
| rewrite the whole tail | only the published head |
| truncate | only the published head |

The last two rows are why the head is published somewhere the attacker can't write: a transparency log, a daily email to the auditors, a ticket, or a signed checkpoint.

## Common mistakes

- **Non-canonical JSON.** `json.dumps(event)` depends on key insertion order and adds spaces. The same event serialized by another service, or after a round trip through a database, hashes differently and the log looks tampered.
- **`ensure_ascii` left on.** A verifier written in Go or JavaScript writes `ë` as UTF-8, not `ë`, and every row with a non-ASCII name fails verification.
- **Checking each row's hash but not the link.** An attacker deletes a row, renumbers `seq`, and the chain still "verifies".
- **No external anchor.** A chain checked only against itself can't detect a rewritten or truncated tail.
- **Storing the caller's dict.** The application reuses the dict for the next request, and the stored event silently changes after it was hashed.

## Production notes

- This is the structure behind Certificate Transparency, AWS CloudTrail log file integrity (hourly digest files, each signed and chained to the previous one), and append-only ledgers like Amazon QLDB. Real systems sign the periodic head with a KMS key, so the anchor itself can't be forged.
- Hash a canonical form. RFC 8785 (JSON Canonicalization Scheme) pins down number formatting as well, which `json.dumps` does not: Python writes `1.0` where JavaScript writes `1`.
- At scale, use a Merkle tree over each batch instead of one linear chain. You get O(log n) inclusion proofs for a single event and can verify a range without rereading the whole log.
- Keep PII out of the hashed event, or hash a redacted form (see `pii-redaction-vault`). Otherwise a GDPR erasure request forces you to break the chain.
