from gc_runtime import BadRequestError, ToolError


def fanout(loop, subscribers, channels, send):
    delivered, failed = {}, {}
    queues = {}
    for s in subscribers:
        queues.setdefault(s["channel"], []).append(s["id"])

    def worker(name):
        cfg = channels[name]
        last_start = None
        for sid in queues[name]:
            attempt = 1
            while True:
                if last_start is not None and last_start + cfg["interval"] > loop.now():
                    yield last_start + cfg["interval"] - loop.now()
                last_start = loop.now()
                try:
                    yield from send(sid, name)
                    delivered[sid] = loop.now()
                    break
                except BadRequestError:
                    failed[sid] = "rejected"
                    break
                except ToolError:
                    if attempt >= cfg["max_attempts"]:
                        failed[sid] = "exhausted"
                        break
                    # Blocks everyone behind this subscriber while it backs off.
                    yield cfg["retry_delay"] * 2 ** (attempt - 1)
                    attempt += 1

    for name in sorted(queues):
        loop.spawn(worker(name), "channel:" + name)
    loop.run()
    return {"delivered": delivered, "failed": failed}
