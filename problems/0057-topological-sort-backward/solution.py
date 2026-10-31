import math
from collections import deque

import numpy as np


def _topo_order(parents):
    n = len(parents)
    children = [[] for _ in range(n)]
    indeg = [0] * n
    for i, ps in enumerate(parents):
        for p in ps:
            children[p].append(i)
            indeg[i] += 1
    queue = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for c in children[u]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    return order


def _forward(op, xs, i, inputs):
    if op == "input":
        return float(inputs[i])
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
    if op == "relu":
        return max(xs[0], 0.0)
    raise ValueError("unknown op " + op)


def _local_grads(op, xs, y):
    """d y / d parent_k for each parent slot k."""
    if op == "add":
        return [1.0, 1.0]
    if op == "sub":
        return [1.0, -1.0]
    if op == "mul":
        return [xs[1], xs[0]]
    if op == "div":
        return [1.0 / xs[1], -xs[0] / (xs[1] * xs[1])]
    if op == "neg":
        return [-1.0]
    if op == "exp":
        return [y]
    if op == "log":
        return [1.0 / xs[0]]
    if op == "tanh":
        return [1.0 - y * y]
    if op == "sigmoid":
        return [y * (1.0 - y)]
    if op == "relu":
        return [1.0 if xs[0] > 0 else 0.0]
    return []


def graph_backward(ops, parents, inputs, output):
    n = len(ops)
    order = _topo_order(parents)
    values = np.zeros(n)
    for i in order:
        values[i] = _forward(ops[i], [values[p] for p in parents[i]], i, inputs)
    grads = np.zeros(n)
    grads[output] = 1.0
    for i in reversed(order):
        if grads[i] == 0.0:
            continue
        xs = [values[p] for p in parents[i]]
        for p, d in zip(parents[i], _local_grads(ops[i], xs, values[i])):
            grads[p] += grads[i] * d
    return values, grads
