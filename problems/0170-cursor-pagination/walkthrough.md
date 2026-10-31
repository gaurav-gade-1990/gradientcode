## 1. What the problem is really asking

Strip the sidebar story and this is **filtering a sorted list by a tuple comparison**. Every row has a key `(created_at, id)`. The listing is that key, descending. A cursor is just one key, base64-wrapped. "Next page" means "the first `limit` rows whose key is smaller than the cursor's", and "previous page" means "the `limit` rows just above it".

The reason this beats `OFFSET` is that a key describes *where you are in the order*, not *how many rows came before you*. When a new conversation is inserted at the top, every offset shifts by one, so the next page repeats a row. A key doesn't shift: "older than `(1730000900, conv_0004)`" means the same rows before and after the insert.

The judge replays a whole session. Between requests it inserts and deletes rows. It follows your `next_cursor` or `prev_cursor` from the previous page, as a client would. It grades every page's `items` and both cursor strings exactly, and every `ValueError` as a `{"status": 400}` entry. Because it compares the cursor **strings**, your encoding has to be byte-for-byte the one in the statement.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `rows` | the whole table, unordered, as dicts with `id` and `created_at` (plus `title`) | sort by key, descending |
| `limit` | page size, 1 to 50 | slice length |
| `after` | a cursor from `next_cursor`, or `None` | keep keys strictly **less** than it |
| `before` | a cursor from `prev_cursor`, or `None` | keep keys strictly **greater** than it, then the `limit` closest |
| return | `{"items": [ids], "next_cursor": str or None, "prev_cursor": str or None}` | ids only, newest first |

The driver's loop, with the parts that matter:

```python
if follow == "next":
    kwargs["after"] = last["next_cursor"]
elif follow == "prev":
    kwargs["before"] = last["prev_cursor"]
try:
    page = paginate([dict(r) for r in rows], op["limit"], **kwargs)
except ValueError:
    log.append({"status": 400})
    continue
```

Three details are easy to miss:

- **`created_at` is not unique.** Three imports in the same second share a timestamp. Only the pair `(created_at, id)` is unique, and Python compares tuples element by element, so `key(r) < c` does the right thing in one expression.
- **`next_cursor` is not "the page was full".** It is set only if some row is actually older than the last item. A last page that happens to hold exactly `limit` rows has `next_cursor = None`.
- **`True` is an `int` in Python.** `isinstance(True, int)` is `True`, so a cursor `[true, "conv_0003"]` passes a naive type check. The statement says a boolean is not an int.

## 3. Trace Example 2 by hand

The table is `SIDEBAR`: `conv_0001` through `conv_0005`, 300 seconds apart, so the listing is `5, 4, 3, 2, 1`. Limit 2.

**Request 1, no cursor.** The page is `ordered[:2]` = `conv_0005, conv_0004`.

- Is any row older than `conv_0004`? Yes, so `next_cursor` is the cursor of `conv_0004`: `WzE3MzAwMDA5MDAsImNvbnZfMDAwNCJd`, which decodes to `[1730000900,"conv_0004"]`.
- Is any row newer than `conv_0005`? No, so `prev_cursor` is `None`.

**Insert** `conv_0006` at `1730001500`, newer than everything.

**Request 2, follow next.** `after` = the cursor above, so `c = (1730000900, "conv_0004")`. Rows with a smaller key, newest first: `conv_0003, conv_0002, conv_0001`. Take 2: `conv_0003, conv_0002`. Something is older (`conv_0001`), so `next_cursor` is `conv_0002`'s. Something is newer, so `prev_cursor` is `conv_0003`'s.

Compare the offset version (`wrong_offset_cursor.py`). Its cursor says "offset 2". After the insert the listing is `6, 5, 4, 3, 2, 1`, and offset 2 is `conv_0004` again. Its second page is `conv_0004, conv_0003`, a repeat. That's the bug the problem was written to remove.

**Request 3, follow prev.** `before` = `conv_0003`'s cursor, `c = (1730000600, "conv_0003")`. Newer rows, newest first: `conv_0006, conv_0005, conv_0004`. The two **closest** to the cursor are the last two of that list: `conv_0005, conv_0004`. That's the page the user just scrolled up to, not the top of the list. Its `prev_cursor` is set because `conv_0006` is newer.

**The tie case, Example 3.** The table `TIES` has `conv_0010`, `conv_0011`, `conv_0012` at `1730005000` and `conv_0009` at `1730004000`. Page 1 is `conv_0012, conv_0011` (ties order by id descending). Page 2, after `(1730005000, "conv_0011")`, is `conv_0010, conv_0009`, with `next_cursor = None`. If you compare only `created_at < 1730005000` (`wrong_timestamp_only_keyset.py`), page 2 is just `conv_0009`. `conv_0010` is silently skipped.

## 4. Key idea: a before-page is the tail of the newer rows

For `before=c` you want the rows the user would see by scrolling *up* one page from `c`. In listing order (newest first) the newer rows are:

```
newest ... [ the limit rows just above c ] c
```

So the page is the **last** `limit` entries of `newer`, i.e. `newer[-limit:]`, and because `newer` is already newest first the page is too. Two common mistakes:

| code | result for Example 2's request 3 |
|---|---|
| `newer[-limit:]` | `conv_0005, conv_0004` (correct) |
| `newer[:limit]` | `conv_0006, conv_0005`: jumps to the top (`wrong_before_page_from_top.py`) |
| `newer[-limit:][::-1]` | `conv_0004, conv_0005`: right rows, upside down |

In SQL you get the same thing by flipping the comparison and the sort (`WHERE key > :c ORDER BY key ASC LIMIT :n`) and reversing the result in the app.

## 5. Key idea: cursors are computed from the whole table, not the page

`next_cursor` asks "is anything older than my last item?" and `prev_cursor` asks "is anything newer than my first item?". Both questions are about `rows`, not about what this request filtered. That's why the before-page in request 3 above still gets a `prev_cursor`, and why the hidden case "exact multiple: last full page has no next" ends with `next_cursor = None` even though page 2 (`conv_0002, conv_0001`) is full.

## 6. Plan before you code

```
if after and before: 400
key(r) = (created_at, id)
ordered = rows sorted by key, descending        # a new list; don't mutate rows
after  -> page = [r with key < c][:limit]
before -> page = [r with key > c][-limit:]
none   -> page = ordered[:limit]
empty page -> items [], both cursors None
next_cursor = cursor(last item)  if any row's key < last's key
prev_cursor = cursor(first item) if any row's key > first's key
```

Cursor validation, all of which must raise `ValueError`:

| input | why it fails |
|---|---|
| `"not base64!!"` | base64 decode fails |
| `{"offset": 2}` | not a list |
| `[true, "conv_0003"]` | `bool` is excluded explicitly |
| `["1730000600", "conv_0003"]` | timestamp is a string |
| `[1730000600]` | wrong length |
| `[1730000600, conv_0003]` (unquoted) | not valid JSON |
| both `after` and `before` | ambiguous request |

## 7. Build it one piece at a time

**Step 1: the cursor codec.** Encoding has to match the statement exactly, since the judge compares cursor strings.

```python
def encode_cursor(row):
    raw = json.dumps([row["created_at"], row["id"]], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()
```

Leave out `separators` and `json.dumps` writes `[1730000900, "conv_0004"]` with a space, which base64-encodes to a different string. That one change fails 11 of the 14 cases.

**Step 2: decoding, with every failure mapped to `ValueError`.**

```python
def decode_cursor(cursor):
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        raise ValueError("invalid cursor")
    if (not isinstance(value, list) or len(value) != 2 or isinstance(value[0], bool)
            or not isinstance(value[0], int) or not isinstance(value[1], str)):
        raise ValueError("invalid cursor")
    return (value[0], value[1])
```

The broad `except` turns base64 errors, Unicode errors and JSON errors all into one 400. Returning a tuple, not the list, matters: `(1730000900, "conv_0004") < [1730000900, "conv_0004"]` raises `TypeError` in Python, because tuples and lists don't compare.

**Step 3: choosing the page.**

```python
key = lambda r: (r["created_at"], r["id"])
ordered = sorted(rows, key=key, reverse=True)
if after is not None:
    c = decode_cursor(after)
    page = [r for r in ordered if key(r) < c][:limit]
elif before is not None:
    c = decode_cursor(before)
    newer = [r for r in ordered if key(r) > c]
    page = newer[-limit:]
else:
    page = ordered[:limit]
```

`sorted` returns a new list, so `rows` is left alone. `reverse=True` reverses the whole tuple order, which gives "larger id first" among equal timestamps for free.

**Step 4: the cursors.**

```python
if not page:
    return {"items": [], "next_cursor": None, "prev_cursor": None}
first, last = key(page[0]), key(page[-1])
has_next = any(key(r) < last for r in rows)
has_prev = any(key(r) > first for r in rows)
```

The empty-page check comes first because `page[0]` would raise on an empty list. "before the newest row is empty" hits it: nothing is newer than `conv_0005`.

## 8. Full solution

```python
import base64  # cursors are URL-safe base64 so they travel in a query string
import json  # the cursor body is a JSON [created_at, id] pair


def encode_cursor(row):  # turn one row's sort key into an opaque cursor string
    # compact separators, so every server produces the identical string for the same row
    raw = json.dumps([row["created_at"], row["id"]], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()  # bytes -> base64 -> str for the API


def decode_cursor(cursor):  # parse a client-supplied cursor back into a comparable key
    try:  # anything malformed must become a 400, not a 500
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())  # base64 -> bytes -> JSON
    except Exception:  # bad base64, bad UTF-8 or bad JSON
        raise ValueError("invalid cursor")  # the API maps ValueError to 400
    # must be exactly [int, str]; bool is excluded because True is an int in Python
    if (not isinstance(value, list) or len(value) != 2 or isinstance(value[0], bool)
            or not isinstance(value[0], int) or not isinstance(value[1], str)):
        raise ValueError("invalid cursor")  # right JSON, wrong shape or types: still a 400
    return (value[0], value[1])  # a tuple, so it compares with the row keys (a list would raise)


def paginate(rows, limit, after=None, before=None):  # one GET /v1/conversations request
    if after is not None and before is not None:  # two directions at once is ambiguous
        raise ValueError("pass after or before, not both")  # reject it as a 400
    key = lambda r: (r["created_at"], r["id"])  # the unique sort key: timestamp, then id as tie-breaker
    ordered = sorted(rows, key=key, reverse=True)  # newest first, as a new list so rows isn't mutated
    if after is not None:  # scrolling down: older rows
        c = decode_cursor(after)  # the key of the last row the client saw
        page = [r for r in ordered if key(r) < c][:limit]  # first `limit` rows strictly older than it
    elif before is not None:  # scrolling up: newer rows
        c = decode_cursor(before)  # the key of the first row the client saw
        newer = [r for r in ordered if key(r) > c]  # every strictly newer row, still newest first
        page = newer[-limit:]  # the tail: the `limit` rows just above the cursor, not the top
    else:  # no cursor
        page = ordered[:limit]  # the first page of the listing
    if not page:  # nothing in that direction
        return {"items": [], "next_cursor": None, "prev_cursor": None}  # an empty page has no cursors
    first, last = key(page[0]), key(page[-1])  # the page's two boundary keys
    has_next = any(key(r) < last for r in rows)  # more only if a row is truly older, not "page was full"
    has_prev = any(key(r) > first for r in rows)  # a newer row exists above this page
    return {  # the response body
        "items": [r["id"] for r in page],  # ids only, in listing order
        "next_cursor": encode_cursor(page[-1]) if has_next else None,  # resume after the last item
        "prev_cursor": encode_cursor(page[0]) if has_prev else None,  # resume before the first item
    }
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `5,4` / `3,2` / `1`; the last `next_cursor` is `None` | the basic forward walk and both cursors |
| Example 2 | `5,4` / `3,2` / back to `5,4` with a `prev_cursor` | an insert doesn't shift a keyset cursor; before-page takes the closest rows |
| Example 3 | `12,11` / `10,9` | ties on `created_at` broken by `id` |
| exact multiple: last full page has no next | `4,3` / `2,1` with `next_cursor` `None` | `has_next` looks for an older row, not a full page |
| limit larger than table, empty table | all 5 with no cursors; `[]` with no cursors | edges of the slice and the empty-page return |
| before-page takes rows closest to cursor | before `conv_0001`: `3,2`, then `5,4`, then `5,4` again | `newer[-limit:]`; following a `None` `prev_cursor` gives the first page |
| before the newest row is empty | `[]`, both `None` | the empty-page guard |
| cursor of a deleted row still works | after deleting `conv_0004` and `conv_0003`: `2,1`, then `5` | a cursor compares keys and stores no position |
| ties straddling every boundary | `13, 12, 11, 10, 9, 8` one by one, then back `9` to `13` | every page boundary falls inside a tie group, in both directions |
| insert with a tied timestamp mid-scroll | `12,11` / `10,7` / `9` / prev of 3 gives `11,10,7` | a new tied row with a larger id (`conv_0015`) stays above the cursor; a smaller one (`conv_0007`) shows up |
| invalid cursors are 400 | seven 400s, then `2,1` | every branch of `decode_cursor` and the both-cursors check |
| big table walk forward then back | 120 rows drawn from 40 possible timestamps: 18 pages forward, 17 back | the whole thing at scale, with many ties |
| big table with inserts while scrolling | 12 rows inserted after page 4; the walk reaches the end on page 15 with 129 distinct rows and no repeats | the 9 inserts older than the cursor show up later; the 3 newer ones (`conv_0905`, `conv_0910`, `conv_0911`) never shift a page |

One note on the driver: following a cursor that is `None` passes `after=None` or `before=None`, which is a plain first page. That's why "before-page takes rows closest to cursor" ends with `5,4` twice, and why the requests after the end of "big table with inserts while scrolling" all return the first page.

## 10. Complexity

Each request sorts the table, O(n log n), then scans it a few times, O(n). With n ≤ 200 that's nothing.

In a real database it's very different, and that's the whole point of keyset pagination. With an index on `(user_id, created_at DESC, id DESC)`, the query `WHERE (created_at, id) < (:c, :i) ORDER BY created_at DESC, id DESC LIMIT :n` seeks straight to the cursor and reads `n` rows: O(log N + n) however deep the user has scrolled. `OFFSET 10000` makes the database read and throw away 10,000 rows first, so deep pages get slower. Fetch `limit + 1` rows to learn whether a next page exists without a second query.

## 11. If you got Wrong Answer

Compare the page lists one by one and find the first page that differs.

- **Every cursor string differs, but the items are right.** Your JSON has spaces. Use `separators=(",", ":")`.
- **A row appears twice after an insert, or every cursor looks like `eyJvZmZzZXQi...`.** You wrapped an offset in base64 (`wrong_offset_cursor.py`). It fails 12 of the 14 cases.
- **Example 3's second page is just `conv_0009`.** You compare `created_at` alone (`wrong_timestamp_only_keyset.py`), so rows tied with the cursor's timestamp are skipped.
- **The prev page in Example 2 is `conv_0006, conv_0005`.** You took the first `limit` newer rows, not the last (`wrong_before_page_from_top.py`).
- **The prev page has the right ids in the wrong order.** You built it ascending and forgot it must still be newest first.
- **The last page has a `next_cursor`, and following it gives `[]`.** You set it from `len(page) == limit` (`wrong_has_more_when_page_full.py`).
- **"invalid cursors are 400" has a 200 with empty items in the third slot.** You accepted `[true, ...]`. Check `isinstance(value[0], bool)` before the `int` check.
- **"invalid cursors are 400" has a 200 in the seventh slot.** You didn't reject `after` and `before` together.
- **Runtime Error `TypeError: '<' not supported between instances of 'tuple' and 'list'`.** Convert the decoded list to a tuple.

## 12. Follow-ups an interviewer might ask

- *Base64 is readable. Can a client forge a cursor?* Yes. If the cursor carries anything sensitive (a tenant id, a filter), sign it with an HMAC or encrypt it, and always re-apply the authorization filter on the server. Opaque means "don't depend on the format", not "secret".
- *What if the client changes the filter or sort and reuses an old cursor?* Put the query parameters in the cursor and reject a mismatch with a 400, or the client pages through nonsense.
- *Can you drop `created_at` from the key?* Yes, with a unique, time-ordered id such as a ULID, UUIDv7 or Snowflake id. Then the key is just `id`, the index is smaller, and ties can't happen.
- *How do Stripe and OpenAI expose this?* Stripe uses `starting_after` / `ending_before` with an object id, and OpenAI's list endpoints use `after` plus `has_more`. Same idea, with the cursor replaced by a row id.
- *Where do these rows come from?* A create endpoint that must not make duplicates on retry. Problem 180 (api-idempotent-create) builds it.
