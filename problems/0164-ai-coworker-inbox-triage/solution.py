import heapq


def triage(coworkers, requests):
    by_name = {c["name"]: c for c in coworkers}
    active = {c["name"]: 0 for c in coworkers}
    busy = {c["name"]: 0.0 for c in coworkers}
    finishing = []                       # heap of (finish time, seq, coworker)
    arrivals = sorted(requests, key=lambda r: (r["arrives"], r["id"]))
    pending, events, seq, i = [], [], 0, 0

    def duration(c, r):
        return r["minutes"] / c["speed"]

    while i < len(arrivals) or finishing:
        t = float(min(arrivals[i]["arrives"] if i < len(arrivals) else float("inf"),
                      finishing[0][0] if finishing else float("inf")))
        while finishing and finishing[0][0] == t:
            _, _, name = heapq.heappop(finishing)
            active[name] -= 1
        while i < len(arrivals) and arrivals[i]["arrives"] == t:
            pending.append(arrivals[i])
            i += 1
        pending.sort(key=lambda r: (r["deadline"], r["arrives"], r["id"]))
        still = []
        for r in pending:
            skilled = [c for c in coworkers if r["skill"] in c["skills"]]
            if not skilled:
                events.append({"t": t, "request": r["id"], "action": "escalate", "reason": "no_skill"})
                continue
            if t + min(duration(c, r) for c in skilled) > r["deadline"]:
                events.append({"t": t, "request": r["id"], "action": "escalate", "reason": "sla"})
                continue
            free = [c for c in skilled if active[c["name"]] < c["capacity"] and t + duration(c, r) <= r["deadline"]]
            if not free:
                still.append(r)
                continue
            c = min(free, key=lambda c: (t + duration(c, r), active[c["name"]], c["name"]))
            finish = t + duration(c, r)
            active[c["name"]] += 1
            busy[c["name"]] += duration(c, r)
            seq += 1
            heapq.heappush(finishing, (finish, seq, c["name"]))
            events.append({"t": t, "request": r["id"], "action": "assign", "coworker": c["name"], "finish": finish})
        pending = still
    assigned = sum(1 for e in events if e["action"] == "assign")
    return {"events": events, "assigned": assigned, "escalated": len(events) - assigned,
            "busy_minutes": {name: busy[name] for name in sorted(by_name)}}
