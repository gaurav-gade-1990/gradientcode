from collections import defaultdict


def _union_length(intervals):
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(intervals):
        if e <= s:
            continue
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total


def analyze_trace(spans):
    # Bug: child durations are summed instead of unioned. Parallel tool calls give the parent negative self time.
    by_id = {s["id"]: s for s in spans}
    root = next(s for s in spans if s["parent"] is None)
    children = defaultdict(list)
    for s in spans:
        if s["parent"] is not None:
            children[s["parent"]].append(s)
    reachable, stack = [], [root]
    while stack:
        s = stack.pop()
        reachable.append(s)
        stack.extend(children[s["id"]])
    seen = {s["id"] for s in reachable}
    orphans = sorted(s["id"] for s in spans if s["id"] not in seen)

    self_time = {}
    for s in reachable:
        clipped = [(max(c["start"], s["start"]), min(c["end"], s["end"])) for c in children[s["id"]]]
        self_time[s["id"]] = round((s["end"] - s["start"]) - sum(e - b for b, e in clipped), 9)

    path, cur = [root["id"]], root
    while children[cur["id"]]:
        cur = min(children[cur["id"]], key=lambda c: (-c["end"], -c["start"], c["id"]))
        path.append(cur["id"])

    kinds = defaultdict(list)
    for s in reachable:
        kinds[s["kind"]].append((s["start"], s["end"]))
    time_by_kind = {k: round(_union_length(v), 9) for k, v in sorted(kinds.items())}
    return {
        "duration": round(root["end"] - root["start"], 9),
        "critical_path": path,
        "self_time": dict(sorted(self_time.items())),
        "time_by_kind": time_by_kind,
        "orphans": orphans,
    }
