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
    # Bug: spans with a missing parent are re-parented under the root. Spans from a different request
    # (or a sampled-away subtree) now count toward this request's numbers.
    ids = {s["id"] for s in spans}
    root = next(s for s in spans if s["parent"] is None)
    children = defaultdict(list)
    for s in spans:
        if s["parent"] is not None:
            children[s["parent"] if s["parent"] in ids else root["id"]].append(s)
    self_time = {}
    for s in spans:
        clipped = [(max(c["start"], s["start"]), min(c["end"], s["end"])) for c in children[s["id"]]]
        self_time[s["id"]] = round((s["end"] - s["start"]) - _union_length(clipped), 9)
    path, cur = [root["id"]], root
    while children[cur["id"]]:
        cur = min(children[cur["id"]], key=lambda c: (-c["end"], -c["start"], c["id"]))
        path.append(cur["id"])
    kinds = defaultdict(list)
    for s in spans:
        kinds[s["kind"]].append((s["start"], s["end"]))
    return {
        "duration": round(root["end"] - root["start"], 9),
        "critical_path": path,
        "self_time": dict(sorted(self_time.items())),
        "time_by_kind": {k: round(_union_length(v), 9) for k, v in sorted(kinds.items())},
        "orphans": [],
    }
