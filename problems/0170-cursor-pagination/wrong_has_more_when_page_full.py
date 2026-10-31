import base64
import json


def encode_cursor(row):
    raw = json.dumps([row["created_at"], row["id"]], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor):
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        raise ValueError("invalid cursor")
    if (not isinstance(value, list) or len(value) != 2 or isinstance(value[0], bool)
            or not isinstance(value[0], int) or not isinstance(value[1], str)):
        raise ValueError("invalid cursor")
    return (value[0], value[1])


def paginate(rows, limit, after=None, before=None):
    if after is not None and before is not None:
        raise ValueError("pass after or before, not both")
    key = lambda r: (r["created_at"], r["id"])
    ordered = sorted(rows, key=key, reverse=True)          # newest first
    if after is not None:
        c = decode_cursor(after)
        page = [r for r in ordered if key(r) < c][:limit]
    elif before is not None:
        c = decode_cursor(before)
        newer = [r for r in ordered if key(r) > c]
        page = newer[-limit:]                              # the `limit` rows closest to the cursor
    else:
        page = ordered[:limit]
    if not page:
        return {"items": [], "next_cursor": None, "prev_cursor": None}
    first, last = key(page[0]), key(page[-1])
    has_next = len(page) == limit
    has_prev = any(key(r) > first for r in rows)
    return {
        "items": [r["id"] for r in page],
        "next_cursor": encode_cursor(page[-1]) if has_next else None,
        "prev_cursor": encode_cursor(page[0]) if has_prev else None,
    }
