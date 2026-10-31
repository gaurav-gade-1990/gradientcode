import math

import numpy as np

UNARY = ["neg", "exp", "log", "tanh", "sigmoid", "relu"]
BINARY = ["add", "sub", "mul", "div"]


def _value(op, xs):
    if op == "add":
        return xs[0] + xs[1]
    if op == "sub":
        return xs[0] - xs[1]
    if op == "mul":
        return xs[0] * xs[1]
    if op == "div":
        return xs[0] / xs[1]
    if op == "neg":
        return -xs[0]
    if op == "exp":
        return math.exp(xs[0])
    if op == "log":
        return math.log(xs[0])
    if op == "tanh":
        return math.tanh(xs[0])
    if op == "sigmoid":
        return 1.0 / (1.0 + math.exp(-xs[0]))
    return max(xs[0], 0.0)


def _random_graph(rng, n_inputs, n_ops, window=None):
    """Build a random DAG in topological order, then shuffle the node indices."""
    ops, parents, vals = [], [], []
    for _ in range(n_inputs):
        ops.append("input")
        parents.append([])
        vals.append(round(float(rng.uniform(-2, 2)), 3))
    while len(ops) < n_inputs + n_ops:
        lo = 0 if window is None else max(0, len(ops) - window)
        pick = lambda: int(rng.integers(lo, len(ops)))
        if rng.random() < 0.55:
            op, ps = str(rng.choice(BINARY)), [pick(), pick()]
        else:
            op, ps = str(rng.choice(UNARY)), [pick()]
        xs = [vals[p] for p in ps]
        if op == "log" and xs[0] <= 0.1:
            continue
        if op == "div" and abs(xs[1]) < 0.3:
            continue
        if op == "exp" and xs[0] > 3:
            continue
        v = _value(op, xs)
        if abs(v) > 20 or (op == "relu" and xs[0] == 0.0):
            continue
        ops.append(op)
        parents.append(ps)
        vals.append(v)
    n = len(ops)
    perm = rng.permutation(n)  # old index -> new index
    new_ops, new_parents = [None] * n, [None] * n
    inputs = {}
    for old in range(n):
        new = int(perm[old])
        new_ops[new] = ops[old]
        new_parents[new] = [int(perm[p]) for p in parents[old]]
        if ops[old] == "input":
            inputs[new] = vals[old]
    return new_ops, new_parents, inputs, int(perm[n - 1])


def cases():
    rng = np.random.default_rng(57)
    out = [
        {"name": "Example 1", "hidden": False,
         "args": {"ops": ["input", "input", "mul", "add"], "parents": [[], [], [0, 1], [2, 0]],
                  "inputs": {0: 2.0, 1: 3.0}, "output": 3},
         "explanation": "Node 3 = x*y + x = 8. x reaches the output along two paths, so d/dx = y + 1 = 4, and d/dy = x = 2."},
        {"name": "Example 2", "hidden": False,
         "args": {"ops": ["tanh", "mul", "input", "exp"], "parents": [[1], [2, 2], [], [2]],
                  "inputs": {2: 0.5}, "output": 0},
         "explanation": "The nodes are out of order: node 0 = tanh(node 1) and node 1 = x * x. Node 3 = exp(x) is not used by the output, so its gradient is 0."},
        {"name": "Example 3", "hidden": False,
         "args": {"ops": ["sub", "input", "relu", "input", "div"], "parents": [[4, 2], [], [3], [], [1, 3]],
                  "inputs": {1: 6.0, 3: -2.0}, "output": 0},
         "explanation": "out = a / b - relu(b) with a = 6, b = -2. relu(-2) = 0 passes no gradient, so d/db = -a / b^2 = -1.5 and d/da = 1 / b = -0.5."},
        {"name": "single input is the output", "args": {"ops": ["input"], "parents": [[]], "inputs": {0: 4.2}, "output": 0}},
        {"name": "output is an intermediate node",
         "args": {"ops": ["mul", "input", "exp", "add", "input"], "parents": [[1, 4], [], [0], [2, 1], []],
                  "inputs": {1: 0.7, 4: -1.3}, "output": 0}},
        {"name": "diamond with unequal path lengths",
         "args": {"ops": ["input", "tanh", "sigmoid", "exp", "neg", "add", "mul"],
                  "parents": [[], [0], [1], [2], [0], [3, 4], [5, 1]],
                  "inputs": {0: 0.4}, "output": 6}},
        {"name": "every op once",
         "args": {"ops": ["log", "input", "input", "div", "sub", "sigmoid", "relu", "neg", "tanh", "exp", "add", "mul"],
                  "parents": [[9], [], [], [1, 2], [3, 0], [4], [1], [6], [7], [2], [5, 8], [10, 10]],
                  "inputs": {1: 1.5, 2: 0.8}, "output": 11}},
        {"name": "relu exactly at zero",
         "args": {"ops": ["input", "sub", "relu", "mul", "input"], "parents": [[], [0, 0], [1], [2, 4], []],
                  "inputs": {0: 3.0, 4: 2.0}, "output": 3}},
    ]
    for name, ni, no, win in [("random shuffled small", 3, 12, None), ("random shuffled medium", 5, 40, None),
                              ("random deep chain", 2, 120, 4), ("random wide", 20, 150, None)]:
        ops, parents, inputs, output = _random_graph(rng, ni, no, win)
        out.append({"name": name, "args": {"ops": ops, "parents": parents, "inputs": inputs, "output": output}})
    return out
