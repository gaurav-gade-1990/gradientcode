def run(ns, table, ops):
    """Replay a session against GET /v1/conversations: inserts land in the table between page requests,
    and each page request follows the cursor from the previous page (like a client scrolling)."""
    rows = [dict(r) for r in table]
    paginate = ns["paginate"]
    last = {"next_cursor": None, "prev_cursor": None}
    log = []
    for op in ops:
        if op["op"] == "insert":
            rows.append(dict(op["row"]))
            continue
        if op["op"] == "delete":
            rows = [r for r in rows if r["id"] != op["id"]]
            continue
        kwargs = {}
        follow = op.get("follow")
        if follow == "next":
            kwargs["after"] = last["next_cursor"]
        elif follow == "prev":
            kwargs["before"] = last["prev_cursor"]
        if "after" in op:
            kwargs["after"] = op["after"]
        if "before" in op:
            kwargs["before"] = op["before"]
        try:
            page = paginate([dict(r) for r in rows], op["limit"], **kwargs)
        except ValueError:
            log.append({"status": 400})
            continue
        page = {"items": list(page["items"]), "next_cursor": page["next_cursor"], "prev_cursor": page["prev_cursor"]}
        log.append({"status": 200, "items": page["items"], "next_cursor": page["next_cursor"], "prev_cursor": page["prev_cursor"]})
        last = page
    return log
