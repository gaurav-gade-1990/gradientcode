import json


class LoopGuard:
    # Bug: no "at least 2 distinct" check, so four identical calls count as a cycle [A, A]
    # and the configured n_repeat is silently overridden.
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n, self.c, self.h = n_repeat, max_cycle, []

    def check(self, name, arguments):
        h = self.h
        h.append(name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":")))
        if len(h) >= self.n and len(set(h[-self.n:])) == 1:
            return {"reason": "repeat", "block": [h[-1]]}
        for L in range(2, self.c + 1):
            if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:]:
                return {"reason": "cycle", "block": h[-L:]}
        return None
