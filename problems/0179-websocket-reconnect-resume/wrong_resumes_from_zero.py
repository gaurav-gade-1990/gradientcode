from gc_runtime import ServerError


def stream_chat(connect, backfill, on_event, clock, rand, max_failures=5, base=0.5, cap=8.0):
    last_id = 0
    failures = 0
    while True:
        try:
            sock = connect(0)
            while True:
                ev = sock.recv()
                if ev["id"] <= last_id:
                    continue
                batch = backfill(last_id, ev["id"]) if ev["id"] > last_id + 1 else []
                for e in list(batch) + [ev]:
                    if e["type"] == "done":
                        return "done"
                    on_event(e)
                    last_id = e["id"]
                    failures = 0
        except ServerError:
            failures += 1
            if failures >= max_failures:
                return "gave_up"
            clock.sleep(rand() * min(cap, base * 2 ** (failures - 1)))
