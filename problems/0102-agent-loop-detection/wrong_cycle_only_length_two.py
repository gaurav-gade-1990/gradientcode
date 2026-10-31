import json


class LoopGuard:
    # Bug: hard-codes the A-B-A-B ping-pong; a three-tool cycle runs until the step limit.
    def __init__(self, n_repeat=3, max_cycle=3):
        self.n, self.h = n_repeat, []

    def check(self, name, arguments):
        h = self.h
        h.append(name + " " + json.dumps(arguments, sort_keys=True, separators=(",", ":")))
        if len(h) >= self.n and len(set(h[-self.n:])) == 1:
            return {"reason": "repeat", "block": [h[-1]]}
        if len(h) >= 4 and h[-4:-2] == h[-2:] and h[-1] != h[-2]:
            return {"reason": "cycle", "block": h[-2:]}
        return None
