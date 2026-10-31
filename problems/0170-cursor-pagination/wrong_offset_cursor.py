import base64
import json


def _enc(offset):
    return base64.urlsafe_b64encode(json.dumps({"offset": offset}).encode()).decode()


def _dec(cursor):
    try:
        return int(json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())["offset"])
    except Exception:
        raise ValueError("invalid cursor")


def paginate(rows, limit, after=None, before=None):
    # "Opaque" cursors that wrap OFFSET: a row inserted at the top shifts every page by one.
    if after is not None and before is not None:
        raise ValueError("pass after or before, not both")
    ordered = sorted(rows, key=lambda r: (r["created_at"], r["id"]), reverse=True)
    if after is not None:
        start = _dec(after)
    elif before is not None:
        start = max(0, _dec(before) - limit)
    else:
        start = 0
    page = ordered[start:start + limit]
    if not page:
        return {"items": [], "next_cursor": None, "prev_cursor": None}
    return {
        "items": [r["id"] for r in page],
        "next_cursor": _enc(start + len(page)) if start + len(page) < len(ordered) else None,
        "prev_cursor": _enc(start) if start > 0 else None,
    }
