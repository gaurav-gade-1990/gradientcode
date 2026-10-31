def run(ns, chunks):
    """Feed the chunks one at a time, as they come off the socket, and record what each feed() emitted."""
    parser = ns["SSEParser"]()
    per_chunk = []
    for chunk in chunks:
        events = parser.feed(chunk)
        if events is None:
            raise TypeError("feed() must return a list of events (possibly empty)")
        per_chunk.append([{"event": e["event"], "data": e["data"], "id": e["id"]} for e in events])
    return {"events_per_chunk": per_chunk, "last_event_id": parser.last_event_id,
            "retry": parser.retry, "done": bool(parser.done)}
