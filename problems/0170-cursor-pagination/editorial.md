## Approach

Offset pagination says "skip the first 20 rows". That stops meaning the same rows as soon as one is inserted above them. Keyset pagination says "the rows after this one", and that stays true however the table changes. The key has to be **unique and totally ordered**, so it's the pair `(created_at, id)`, not the timestamp alone.

```python
key = lambda r: (r["created_at"], r["id"])
ordered = sorted(rows, key=key, reverse=True)
if after:
    page = [r for r in ordered if key(r) < c][:limit]
elif before:
    page = [r for r in ordered if key(r) > c][-limit:]     # the rows nearest the cursor
else:
    page = ordered[:limit]
has_next = any(key(r) < key(page[-1]) for r in rows)
has_prev = any(key(r) > key(page[0]) for r in rows)
```

In SQL this is `WHERE (created_at, id) < (:c, :i) ORDER BY created_at DESC, id DESC LIMIT :n`, backed by an index on `(user_id, created_at DESC, id DESC)`. The before-page flips the comparison and the sort, takes `LIMIT :n`, and reverses the result in the application. Fetching `limit + 1` rows tells you whether a next page exists without a second query.

## Common mistakes

- **An offset in a base64 costume.** Encoding `{"offset": 20}` makes the cursor opaque but keeps every offset bug. One insert at the top and the next page repeats a row.
- **Keying on `created_at` alone.** `WHERE created_at < :c` skips every other row that shares the boundary timestamp. Bulk imports and batch jobs create many rows in the same second.
- **The wrong rows for a before-page.** Taking the first `limit` newer rows jumps to the top of the list instead of the page just above. Returning them oldest first flips the order on screen.
- **"Full page means more."** Setting `next_cursor` whenever `len(page) == limit` sends the client to an empty last page. On infinite scroll that's an extra request for every user who reaches the end.

## Production notes

- Stripe (`starting_after`/`ending_before`), the OpenAI list endpoints (`after`, `has_more`), Slack and GitHub GraphQL all use cursor pagination. Some of them return `has_more` in place of a null cursor.
- Opaque doesn't mean secret. Base64 is readable, so sign the cursor with an HMAC, or encrypt it, if it includes a tenant id or a filter. Otherwise a client can edit it and page through rows it shouldn't see. Re-apply the authorization filter on every request either way.
- Put the filters and the sort order in the cursor, or reject a cursor used with different query parameters. Following a cursor under a different filter returns nonsense.
- Use a tie-breaker that's monotonic and unique, such as a ULID, a UUIDv7 or a Snowflake id. Then the key is just `id`, and the index is smaller.
- Pairs with **api-idempotent-create** (180), which creates the rows this endpoint lists.
