import copy
import itertools
import json


def _canon(state):
    return json.dumps(state, sort_keys=True)


def run(ns, devices, ops):
    """Run local edits and syncs, then test commutativity, idempotence and convergence with your Replica."""
    Replica = ns["Replica"]
    reps = {d: Replica(d) for d in devices}
    views = []
    for op in ops:
        r = reps[op["device"]]
        if "put" in op:
            r.put(op["put"][0], op["put"][1])
            what = "put %s" % op["put"][0]
        elif "delete" in op:
            r.delete(op["delete"])
            what = "delete %s" % op["delete"]
        else:
            sent = copy.deepcopy(reps[op["sync_from"]].state())
            before = copy.deepcopy(sent)
            r.merge(sent)
            if sent != before:
                raise AssertionError("merge() mutated the state it was given")
            what = "sync from %s" % op["sync_from"]
        if op.get("show"):
            views.append({"device": op["device"], "after": what, "clock": r.clock, "view": r.view()})

    snaps = [copy.deepcopy(reps[d].state()) for d in devices]
    merged = set()
    first = None
    for order in itertools.permutations(range(len(snaps))):
        judge = Replica("~judge")
        for i in order:
            judge.merge(copy.deepcopy(snaps[i]))
        merged.add(_canon(judge.state()))
        if first is None:
            first = judge
    once = _canon(first.state())
    first.merge(copy.deepcopy(snaps[-1]))
    idempotent = _canon(first.state()) == once

    for _ in range(2):
        for d in devices:
            for e in devices:
                if d != e:
                    reps[d].merge(copy.deepcopy(reps[e].state()))
    finals = {d: reps[d].view() for d in devices}
    return {
        "views": views,
        "merged_state": json.loads(once),
        "commutative": len(merged) == 1,
        "idempotent": idempotent,
        "converged": all(v == finals[devices[0]] for v in finals.values()),
        "final_view": finals[devices[0]],
        "clocks": {d: reps[d].clock for d in devices},
    }
