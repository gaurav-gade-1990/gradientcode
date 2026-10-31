from gc_runtime import ToolError


def supervise(subtasks, workers, execute):
    # Bug: ties go to whoever is listed first in the config, not by name, so routing changes when someone edits the YAML.
    skills = {w["name"]: set(w["skills"]) for w in workers}
    names = [w["name"] for w in workers]
    queue = {n: [] for n in names}
    results = {t["id"]: {"id": t["id"], "status": None, "worker": None, "output": None, "attempts": 0} for t in subtasks}
    needs = {t["id"]: set(t["needs"]) for t in subtasks}
    failed_on = {t["id"]: set() for t in subtasks}

    def pick(tid):
        options = [n for n in names if needs[tid] <= skills[n] and n not in failed_on[tid]]
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
                failed_on[tid].add(n)
                nxt = pick(tid) if r["attempts"] < 2 else None
                if nxt is None:
                    r["status"] = "failed"
                else:
                    queue[nxt].append(tid)
    return [results[t["id"]] for t in subtasks]
