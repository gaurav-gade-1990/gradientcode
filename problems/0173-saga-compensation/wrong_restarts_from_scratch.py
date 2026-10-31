from gc_runtime import ServerError, ToolError


def run_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3):
    return resume_saga(saga_id, steps, services, journal, clock, max_comp_attempts)


# Resume ignores the journal and replays every step from the top.
def resume_saga(saga_id, steps, services, journal, clock, max_comp_attempts=3):
    done, started, comp_started, comp_closed = {}, set(), set(), set()
    failed, stuck = False, False
    for r in []:
        t, s = r["type"], r.get("step")
        if t == "saga_finished":
            return r["status"]
        if t == "step_started":
            started.add(s)
        elif t == "step_done":
            done[s] = r["result"]
        elif t == "step_failed":
            failed = True
        elif t == "comp_started":
            comp_started.add(s)
        elif t == "comp_done":
            comp_closed.add(s)
        elif t == "comp_failed":
            comp_closed.add(s)
            stuck = True

    if not failed:
        for s in steps:
            if s in done:
                continue
            if s not in started:
                journal.append({"type": "step_started", "step": s})
            try:
                result = services.do(s, "%s:%s" % (saga_id, s))
            except ToolError as e:
                journal.append({"type": "step_failed", "step": s, "error": str(e)})
                failed = True
                break
            journal.append({"type": "step_done", "step": s, "result": result})
            done[s] = result
        if not failed:
            journal.append({"type": "saga_finished", "status": "completed"})
            return "completed"

    for s in reversed([s for s in steps if s in done]):
        if s in comp_closed:
            continue
        if s not in comp_started:
            journal.append({"type": "comp_started", "step": s})
        for k in range(max_comp_attempts):
            try:
                services.undo(s, done[s])
            except ServerError:
                if k == max_comp_attempts - 1:
                    journal.append({"type": "comp_failed", "step": s, "attempts": max_comp_attempts})
                    stuck = True
                else:
                    clock.sleep(2 ** k)
                continue
            journal.append({"type": "comp_done", "step": s})
            break

    status = "stuck" if stuck else "compensated"
    journal.append({"type": "saga_finished", "status": status})
    return status
