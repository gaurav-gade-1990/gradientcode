from gc_runtime import BadRequestError, ToolError


def fanout(loop, subscribers, channels, send):
    delivered, failed = {}, {}
    queues = {}
    for i, s in enumerate(subscribers):
        queues.setdefault(s["channel"], []).append((0.0, i, s["id"], 1))
    next_seq = [len(subscribers)]

    def worker(name):
        cfg = channels[name]
        q = queues[name]
        last_start = None
        while q:
            q.sort()
            ready, _, sid, attempt = q.pop(0)
            start = max(loop.now(), ready)
            if last_start is not None:
                start = max(start, last_start + cfg["interval"])
            if start > loop.now():
                yield start - loop.now()
            last_start = loop.now()
            try:
                yield from send(sid, name)
                delivered[sid] = loop.now()
            except (BadRequestError, ToolError):
                if attempt >= cfg["max_attempts"]:
                    failed[sid] = "exhausted"
                else:
                    q.append((loop.now() + cfg["retry_delay"] * 2 ** (attempt - 1), next_seq[0], sid, attempt + 1))
                    next_seq[0] += 1

    for name in sorted(queues):
        loop.spawn(worker(name), "channel:" + name)
    loop.run()
    return {"delivered": delivered, "failed": failed}
