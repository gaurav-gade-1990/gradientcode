import json


class LoopGuard:
    # Bug: the history is checked before the new call is added, so the guard trips one call late
    # (the n-th identical call already ran).
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n, self.c, self.h = n_repeat, max_cycle, []

    def check(self, name, arguments):
        h = self.h
        verdict = None
        if len(h) >= self.n and len(set(h[-self.n:])) == 1:
            verdict = {"reason": "repeat", "block": [h[-1]]}
        else:
            for L in range(2, self.c + 1):
                if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:] and len(set(h[-L:])) >= 2:
                    verdict = {"reason": "cycle", "block": h[-L:]}
                    break
        h.append(name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":")))
        return verdict
