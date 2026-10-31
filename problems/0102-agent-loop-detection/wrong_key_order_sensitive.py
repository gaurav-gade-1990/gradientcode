import json


class LoopGuard:
    # Bug: json.dumps without sort_keys. The model reorders keys between turns, so the loop is never seen.
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n, self.c, self.h = n_repeat, max_cycle, []

    def check(self, name, arguments):
        h = self.h
        h.append(name + " " + json.dumps(arguments, separators=(",", ":")))
        if len(h) >= self.n and len(set(h[-self.n:])) == 1:
            return {"reason": "repeat", "block": [h[-1]]}
        for L in range(2, self.c + 1):
            if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:] and len(set(h[-L:])) >= 2:
                return {"reason": "cycle", "block": h[-L:]}
        return None
