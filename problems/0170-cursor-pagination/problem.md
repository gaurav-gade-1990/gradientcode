Your agent product lists a user's conversations in the sidebar, newest first, through `GET /v1/conversations?limit=&after=&before=`. The current endpoint uses `OFFSET`, so when a new conversation starts while the user scrolls, they see a row twice. Replace it with keyset pagination.

Implement `paginate(rows, limit, after=None, before=None)`.

- `rows` is the whole table, in no particular order. Each row is a dict with at least `"id"` (str, unique) and `"created_at"` (int, Unix seconds, **not** unique).
- The listing order is by the key `(created_at, id)`, **descending**: newest first, and among equal timestamps the larger `id` (string comparison) first.
- Return `{"items": [ids of the page, in listing order], "next_cursor": str or None, "prev_cursor": str or None}`.

**Which rows go on the page**

| request | page |
|---|---|
| no cursor | the first `limit` rows of the listing |
| `after=c` | the first `limit` rows whose key is strictly **less** than the key in `c` (older) |
| `before=c` | of the rows whose key is strictly **greater** than the key in `c` (newer), the `limit` rows **closest** to `c`, still returned newest first |

**Cursors.** A cursor encodes one row's key. Build it exactly like this, so cursors are stable across your API servers:

```python
base64.urlsafe_b64encode(json.dumps([created_at, id], separators=(",", ":")).encode()).decode()
```

- `next_cursor` is the cursor of the **last** item if any row in `rows` has a smaller key than it; otherwise `None`.
- `prev_cursor` is the cursor of the **first** item if any row in `rows` has a larger key than it; otherwise `None`.
- If the page is empty, both are `None`.

A cursor still works after its row is deleted or newer rows are inserted, because it compares keys and stores no position.

**Errors.** Raise `ValueError` (the API returns 400) if both `after` and `before` are given, or if a cursor does not decode to a JSON list `[int, str]`. That covers bad base64, bad JSON, the wrong shape and the wrong types (a boolean is not an int).

The judge replays a session: it inserts rows between requests, follows `next_cursor` and `prev_cursor` from the previous page the way a client would, and grades every page and every 400.

**Constraints**

- `0 <= len(rows) <= 200`, `1 <= limit <= 50`
- `id` values are ASCII strings like `"conv_0412"`
- Do not mutate `rows`
