import json


class LoopGuard:
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n_repeat = n_repeat
        self.max_cycle = max_cycle
        self.history = []

    @staticmethod
    def signature(name, arguments):
        return name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":"))

    def check(self, name, arguments):
        h = self.history
        h.append(self.signature(name, arguments))
        n = self.n_repeat
        if len(h) >= n and len(set(h[-n:])) == 1:
            return {"reason": "repeat", "block": [h[-1]]}
        for L in range(2, self.max_cycle + 1):
            if len(h) >= 2 * L and h[-2 * L:-L] == h[-L:] and len(set(h[-L:])) >= 2:
                return {"reason": "cycle", "block": h[-L:]}
        return None
