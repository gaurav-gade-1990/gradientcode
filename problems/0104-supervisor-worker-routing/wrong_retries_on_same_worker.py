from gc_runtime import ToolError


def supervise(subtasks, workers, execute):
    # Bug: the retry goes to the least-loaded eligible worker, which is very often the one that just failed
    # (its queue is now shorter). A crashed worker gets the same task again.
    skills = {w["name"]: set(w["skills"]) for w in workers}
    names = sorted(skills)
    queue = {n: [] for n in names}
    results = {t["id"]: {"id": t["id"], "status": None, "worker": None, "output": None, "attempts": 0} for t in subtasks}
    needs = {t["id"]: set(t["needs"]) for t in subtasks}

    def pick(tid):
        options = [n for n in names if needs[tid] <= skills[n]]
        return min(options, key=lambda n: (len(queue[n]), n)) if options else None

    for t in subtasks:
        w = pick(t["id"])
        if w is None:
            results[t["id"]]["status"] = "unroutable"
        else:
            queue[w].append(t["id"])
    while any(queue.values()):
        for n in names:
            if not queue[n]:
                continue
            tid = queue[n].pop(0)
            r = results[tid]
            r["attempts"] += 1
            r["worker"] = n
            try:
                r["output"] = execute(n, tid)
                r["status"] = "done"
            except ToolError:
                if r["attempts"] < 2:
                    queue[pick(tid)].append(tid)
                else:
                    r["status"] = "failed"
    return [results[t["id"]] for t in subtasks]
