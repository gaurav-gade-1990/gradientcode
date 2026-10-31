import heapq


def parse(v):
    return tuple(int(x) for x in v.split("."))


def term_ok(term, v):
    if term == "*":
        return True
    if term[0] == "^":
        lo = parse(term[1:])
        hi = (lo[0] + 1, 0, 0)
        return lo <= v < hi
    if term[0] == "~":
        lo = parse(term[1:])
        return lo <= v < (lo[0], lo[1] + 1, 0)
    for op in (">=", "<=", ">", "<", "="):
        if term.startswith(op):
            w = parse(term[len(op):])
            return {">=": v >= w, "<=": v <= w, ">": v > w, "<": v < w, "=": v == w}[op]
    return v == parse(term)


def satisfies(rng, version):
    v = parse(version)
    return all(term_ok(t, v) for t in rng.split())


def resolve(registry, requirements):
    first_dead_end = []

    def dead_end(pkg, reqs):
        if not first_dead_end:
            first_dead_end.append({"package": pkg, "requirements": [{"by": b, "range": r} for b, r in sorted(reqs)]})

    def solve(chosen, reqs):
        undecided = sorted(p for p in reqs if p not in chosen)
        if not undecided:
            return chosen
        p = undecided[0]
        versions = sorted(registry.get(p, {}), key=parse, reverse=True)
        candidates = [v for v in versions if all(satisfies(r, v) for _, r in reqs[p])]
        if not candidates:
            dead_end(p, reqs[p])
            return None
        for v in candidates:
            new = {k: list(x) for k, x in reqs.items()}
            conflict = None
            for dep, rng in sorted(registry[p][v].items()):
                new.setdefault(dep, []).append((p + "@" + v, rng))
                if conflict is None and dep in chosen and not satisfies(rng, chosen[dep]):
                    conflict = dep
            if conflict is not None:
                dead_end(conflict, new[conflict])
                continue
            out = solve(dict(chosen, **{p: v}), new)
            if out is not None:
                return out
        return None

    root = {p: [("root", r)] for p, r in requirements.items()}
    chosen = solve({}, root)
    if chosen is None:
        return {"ok": False, "conflict": first_dead_end[0]}

    deps = {p: sorted(registry[p][v]) for p, v in chosen.items()}
    waiting = {p: len(d) for p, d in deps.items()}
    users = {p: [] for p in chosen}
    for p, d in deps.items():
        for q in d:
            users[q].append(p)
    heap = [p for p, n in waiting.items() if n == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        p = heapq.heappop(heap)
        order.append(p)
        for u in users[p]:
            waiting[u] -= 1
            if waiting[u] == 0:
                heapq.heappush(heap, u)
    return {"ok": True, "versions": {p: chosen[p] for p in sorted(chosen)}, "install_order": order}
