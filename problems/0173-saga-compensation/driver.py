import copy

from gc_runtime import Clock, ServerError, ToolError


class ProcessCrash(BaseException):
    """The worker process died. Not an Exception, so `except Exception` does not swallow it."""


class Journal:
    """Durable append-only log: the only thing that survives a crash."""

    def __init__(self):
        self._recs = []

    def append(self, record):
        if not isinstance(record, dict) or "type" not in record:
            raise TypeError("journal records are dicts with a 'type'")
        self._recs.append(copy.deepcopy(record))

    def records(self):
        return copy.deepcopy(self._recs)


class World:
    """The external systems (hotel, payments, email). Side effects persist across crashes."""

    def __init__(self, steps, fail_step, flaky_undo, crash):
        self.steps = steps
        self.fail_step = fail_step
        self.flaky = dict(flaky_undo)
        self.crash = crash
        self.n = 0
        self.calls = []
        self.by_key = {}
        self.bookings = {}  # result -> {"step", "active"}
        self.booked = []    # steps in booking order (one entry per real side effect)
        self.cancelled = []
        self.bad = []
        self.run_undos = {}

    def _boundary(self, phase):
        if self.crash == (self.n, phase):
            self.crash = None
            raise ProcessCrash()

    def do(self, step, idempotency_key):
        self.n += 1
        self.calls.append("do %s" % step)
        self._boundary("before")
        if step not in self.steps:
            raise AssertionError("unknown step %r" % step)
        err, res = None, None
        if step == self.fail_step:
            err = ToolError("%s declined" % step)
        elif idempotency_key in self.by_key:
            res = self.by_key[idempotency_key]
        else:
            res = "%s#%d" % (step, len(self.bookings) + 1)
            self.by_key[idempotency_key] = res
            self.bookings[res] = {"step": step, "active": True}
            self.booked.append(step)
        self._boundary("after")
        if err is not None:
            raise err
        return res

    def undo(self, step, result):
        self.n += 1
        self.calls.append("undo %s" % step)
        self.run_undos[step] = self.run_undos.get(step, 0) + 1
        self._boundary("before")
        err = None
        b = self.bookings.get(result)
        if b is None or b["step"] != step:
            self.bad.append("undo of %s, which never ran" % step)
        elif self.flaky.get(step, 0) > 0:
            self.flaky[step] -= 1
            err = ServerError("%s: upstream 503" % step)
        elif b["active"]:
            b["active"] = False
            self.cancelled.append(step)
        self._boundary("after")
        if err is not None:
            raise err

    def new_run(self, max_comp_attempts):
        for s, k in self.run_undos.items():
            if k > max_comp_attempts:
                self.bad.append("undo %s called %d times in one run (max %d)" % (s, k, max_comp_attempts))
        self.run_undos = {}


def _violations(world, journal, status, max_comp_attempts):
    world.new_run(max_comp_attempts)
    v = list(world.bad)
    recs = journal.records()
    for s in world.steps:
        k = world.booked.count(s)
        if k > 1:
            v.append("%s performed %d times" % (s, k))
    rev = [s for s in reversed(world.booked) if s in world.cancelled]
    if world.cancelled != rev:
        v.append("compensations ran in order %s, expected reverse booking order" % world.cancelled)
    fins = [r for r in recs if r.get("type") == "saga_finished"]
    if len(fins) != 1 or recs[-1].get("type") != "saga_finished":
        v.append("journal must end with exactly one saga_finished, has %d" % len(fins))
    elif fins[0].get("status") != status:
        v.append("returned %r but journaled %r" % (status, fins[0].get("status")))
    active = sorted(b["step"] for b in world.bookings.values() if b["active"])
    failed_comps = sorted(r.get("step") for r in recs if r.get("type") == "comp_failed")
    if status == "completed" and active != sorted(world.steps):
        v.append("completed but active bookings are %s" % active)
    if status == "compensated" and active:
        v.append("compensated but %s still active" % active)
    if status == "stuck" and (not active or active != failed_comps):
        v.append("stuck: active %s should equal comp_failed steps %s" % (active, failed_comps))
    if status not in ("completed", "compensated", "stuck"):
        v.append("bad status %r" % (status,))
    return v


def _short(r):
    return " ".join(str(r.get(k)) for k in ("type", "step", "status") if r.get(k) is not None)


def run(ns, saga_id, steps, fail_step=None, flaky_undo=None, max_comp_attempts=3):
    flaky_undo = flaky_undo or {}

    def scenario(crash):
        world = World(steps, fail_step, flaky_undo, crash)
        journal, clock = Journal(), Clock()
        args = (saga_id, list(steps), world, journal, clock, max_comp_attempts)
        crashed = False
        try:
            status = ns["run_saga"](*args)
        except ProcessCrash:
            crashed = True
        mark = (len(world.calls), len(journal.records()), len(clock.sleeps))
        if crashed:
            world.new_run(max_comp_attempts)
            status = ns["resume_saga"](*args)
        return status, world, journal, clock, mark, crashed

    status, world, journal, clock, _, _ = scenario(None)
    out = {
        "status": status,
        "journal": journal.records(),
        "calls": list(world.calls),
        "sleeps": list(clock.sleeps),
        "violations": _violations(world, journal, status, max_comp_attempts),
    }
    base_calls = list(world.calls)
    crash_runs = []
    for i, name in enumerate(base_calls, 1):
        for phase in ("before", "after"):
            st, w, j, c, (nc, nj, ns_), crashed = scenario((i, phase))
            crash_runs.append({
                "crash": "%s call %d (%s)" % (phase, i, name),
                "status": st,
                "resume_calls": w.calls[nc:],
                "resume_journal": [_short(r) for r in j.records()[nj:]],
                "resume_sleeps": c.sleeps[ns_:],
                "violations": _violations(w, j, st, max_comp_attempts) + ([] if crashed else ["crash point never reached"]),
            })
    out["crash_runs"] = crash_runs
    return out
