## 1. What the problem is really asking

Problem 56 built a graph implicitly: each `Value` held pointers to its inputs, and a recursive DFS found the order. Here the graph is handed to you as **data**: a list of ops and a list of parent indices, like the serialized graph an ML compiler or ONNX file stores. Your job is the two sweeps every autodiff engine does:

1. **Forward**: compute every node's value from its parents' values.
2. **Backward**: starting from `grads[output] = 1`, push each node's gradient into its parents with the chain rule.

The catch is in the first sentence of the statement: the nodes are **shuffled**. Node 0 might be `tanh` of node 1, which is computed from node 2. So before either sweep you need a **topological order**, and the backward sweep must run that order in reverse. Underneath, this is Kahn's algorithm on a DAG, followed by two linear passes.

The judge compares **both** arrays, `values` and `grads`, for every node, including nodes the output doesn't use (gradient `0`) and the output's own descendants (also `0`).

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `ops` | list of `n` op names (`"input"`, `"add"`, `"mul"`, ...) | picks the forward formula and the local derivative |
| `parents` | list of `n` lists of indices | `parents[i]` are the inputs of node `i`, in slot order |
| `inputs` | dict `{index: float}` for every `"input"` node | the leaf values |
| `output` | an index | the node you differentiate; `grads[output] = 1` |
| return | `(values, grads)`, two float arrays of length `n` | |

Details that are easy to miss:

- **A parent may appear twice.** `mul` with parents `[2, 2]` is $x_2^2$. If you dedupe parents, or loop over a set, you lose one of the two contributions.
- **`sub` and `div` are not symmetric.** Slot 0 is the numerator or the minuend. Keep the parent list in order.
- **The output need not be the last node.** In "output is an intermediate node", nodes downstream of the output exist and must get gradient `0`, though you still compute their values.
- **Every value must be computed**, even for nodes the output doesn't depend on, like node 3 (`exp`) in Example 2.

## 3. The math

Write $x_i$ for the value of node $i$ and $\bar x_i = \partial x_{\text{out}} / \partial x_i$ for its gradient. A node's gradient collects one term per edge leaving it:

$$
\bar x_p = \sum_{(i,\,k)\,:\ \text{parents}[i][k] = p} \bar x_i \,\frac{\partial x_i}{\partial (\text{slot } k)} .
$$

The sum runs over **slots**, not over distinct children, which is why `mul(a, a)` gives $a$ twice. All the local derivatives, with $a$ the slot-0 value, $b$ the slot-1 value and $y$ the node's own value:

| op | value $y$ | slot 0 | slot 1 |
|---|---|---|---|
| add | $a + b$ | $1$ | $1$ |
| sub | $a - b$ | $1$ | $-1$ |
| mul | $ab$ | $b$ | $a$ |
| div | $a/b$ | $1/b$ | $-a/b^2$ |
| neg | $-a$ | $-1$ | |
| exp | $e^a$ | $y$ | |
| log | $\ln a$ | $1/a$ | |
| tanh | $\tanh a$ | $1 - y^2$ | |
| sigmoid | $\sigma(a)$ | $y(1-y)$ | |
| relu | $\max(a, 0)$ | $1$ if $a > 0$ else $0$ | |

Two of these are worth deriving. For div, $\frac{\partial}{\partial b}(a b^{-1}) = -a b^{-2}$. For sigmoid, $\sigma(a) = (1 + e^{-a})^{-1}$, so

$$
\sigma'(a) = \frac{e^{-a}}{(1+e^{-a})^2} = \frac{1}{1+e^{-a}} \cdot \frac{e^{-a}}{1+e^{-a}} = \sigma(a)\,\big(1 - \sigma(a)\big).
$$

Exp, tanh and sigmoid are all written in terms of the output $y$, so the backward pass never recomputes a transcendental function.

**Why reverse topological order is exactly right.** $\bar x_p$ is complete once every node that lists $p$ as a parent has added its term. In a topological order every such child comes **after** $p$. In the reversed order every child comes **before** $p$. So when you reach $p$, its gradient is final, and you can safely push it further up.

## 4. Trace by hand

**Example 1** (in order already): `ops = [input, input, mul, add]`, `parents = [[], [], [0, 1], [2, 0]]`, `x = 2`, `y = 3`, `output = 3`.

Values: `[2, 3, 6, 8]`. Reverse order `3, 2, 1, 0`:

| process | pushes | `grads` after |
|---|---|---|
| seed | `grads[3] = 1` | `[0, 0, 0, 1]` |
| node 3 (add of 2, 0) | `+1` to node 2, `+1` to node 0 | `[1, 0, 1, 1]` |
| node 2 (mul of 0, 1) | `+1 * 3` to node 0, `+1 * 2` to node 1 | `[4, 2, 1, 1]` |
| nodes 1, 0 (inputs) | nothing | `[4, 2, 1, 1]` |

$x$ reaches the output twice, so $\bar x = y + 1 = 4$.

**Example 2** (shuffled): `ops = [tanh, mul, input, exp]`, `parents = [[1], [2, 2], [], [2]]`, input node 2 = `0.5`, `output = 0`. Kahn's algorithm starts from node 2 (the only node with no parents) and produces the order `[2, 1, 3, 0]`. Forward along it: node 2 = `0.5`, node 1 = `0.25`, node 3 = `1.6487`, node 0 = `tanh(0.25) = 0.2449`. Backward from node 0: node 1 gets `1 - 0.2449² = 0.94`, then node 2 gets `0.94 * 0.5` twice (both slots of the `mul`), total `0.94`. Node 3 is never reached, so `grads = [1, 0.94, 0.94, 0]`. A plain `range(n)` loop would compute node 0 first, from node 1's not-yet-computed value of `0`.

**The tricky one, "diamond with unequal path lengths"**: `x = 0.4`, node 1 = `tanh(x)`, node 2 = `sigmoid(n1)`, node 3 = `exp(n2)`, node 4 = `neg(x)`, node 5 = `n3 + n4`, node 6 = `n5 * n1`, output 6. Node 1 has two consumers: node 6 directly, and node 2 at the end of a longer path. Kahn's order is `[0, 1, 4, 2, 3, 5, 6]`. In reverse:

| process | `grads[1]` | `grads[0]` |
|---|---|---|
| node 6 (mul) | `1.411` (from node 6) | `0` |
| nodes 5, 3 | `1.411` | `0` |
| node 2 (sigmoid) | `1.5769` (adds node 2's share) | `0` |
| node 4 (neg) | `1.5769` | `-0.3799` |
| node 1 (tanh) | final `1.5769` | `0.9693` |

Node 1 is processed only after node 2 has delivered its share. A breadth-first walk from the output processes node 1 right after node 5, while its gradient is still `1.411`, and ends with `grads[0] = 0.8273` instead of `0.9693`.

## 5. Key idea: Kahn's algorithm

Kahn's algorithm builds a topological order without recursion:

1. Count each node's **in-degree**, the number of parent slots it has. `mul(a, a)` gives in-degree 2 and also makes `a` appear twice in its parent's child list, so the counts stay consistent.
2. Put every node with in-degree 0 (the inputs) into a queue.
3. Pop a node, append it to the order, and decrement the in-degree of each child. When a child reaches 0, all its parents are done; push it.

Each node and each edge is touched once, and since the graph is a DAG every node is eventually released. A DFS post-order, like problem 56's, works equally well. Kahn's has the advantage of no recursion depth limit for the "random deep chain" case, which is 120 operations long.

## 6. Plan before you code

```
children, indeg from parents          # one entry per parent SLOT
order = Kahn(children, indeg)
values = zeros(n)
for i in order: values[i] = forward(ops[i], values of parents[i])
grads = zeros(n); grads[output] = 1
for i in reversed(order):
    for (p, d) in zip(parents[i], local_grads(ops[i], ...)):
        grads[p] += grads[i] * d
return values, grads
```

## 7. Build it one piece at a time

**Step 1: the topological order.** Build child lists and in-degrees in one pass.

```python
children = [[] for _ in range(n)]
indeg = [0] * n
for i, ps in enumerate(parents):
    for p in ps:                     # duplicates kept on purpose
        children[p].append(i)
        indeg[i] += 1
queue = deque(i for i in range(n) if indeg[i] == 0)
```

**Step 2: the forward sweep.** `values` is a `(n,)` float array. Along `order`, every parent's value is already there when you need it.

```python
for i in order:
    values[i] = _forward(ops[i], [values[p] for p in parents[i]], i, inputs)
```

**Step 3: local derivatives, one per slot.** `_local_grads` returns a list as long as `parents[i]`, so `zip` pairs each parent slot with its derivative. Input nodes return `[]` and push nothing.

**Step 4: the backward sweep.**

```python
grads[output] = 1.0
for i in reversed(order):
    if grads[i] == 0.0:
        continue                     # nothing to push; also skips the output's descendants
    xs = [values[p] for p in parents[i]]
    for p, d in zip(parents[i], _local_grads(ops[i], xs, values[i])):
        grads[p] += grads[i] * d
```

Nodes after `output` in the order, and nodes it doesn't depend on, keep their initial `0`, which is what the statement asks. The `continue` is only a speed-up: pushing `0 * d` would add nothing. It also means `_local_grads` never runs for a node that doesn't matter.

## 8. Full solution

```python
import math                                  # exp, log and tanh on plain floats
from collections import deque                # O(1) pops from the front for Kahn's queue

import numpy as np                           # the two result arrays


# Kahn's algorithm: an order in which every node comes after all of its parents
def _topo_order(parents):
    n = len(parents)                         # number of nodes
    children = [[] for _ in range(n)]        # children[p] lists every node that reads p (once per slot)
    indeg = [0] * n                          # number of parent slots still unprocessed, per node
    for i, ps in enumerate(parents):         # walk every edge once
        for p in ps:                         # duplicates like mul(a, a) count twice, consistently
            children[p].append(i)            # edge p -> i
            indeg[i] += 1                    # i waits for one more parent slot
    queue = deque(i for i in range(n) if indeg[i] == 0)  # inputs have no parents and can go first
    order = []                               # the topological order being built
    while queue:                             # until every node has been released
        u = queue.popleft()                  # a node whose parents are all done
        order.append(u)                      # it is safe to compute u now
        for c in children[u]:                # tell each consumer one parent slot is done
            indeg[c] -= 1                    # one fewer slot to wait for
            if indeg[c] == 0:                # all of c's parents are now in the order
                queue.append(c)              # so c can be released
    return order                             # length n, since the graph is a DAG


# forward value of node i from its parents' values xs
def _forward(op, xs, i, inputs):
    if op == "input":                        # a leaf: read its value from the dict
        return float(inputs[i])              # inputs is keyed by node index
    if op == "add":                          # a + b
        return xs[0] + xs[1]                 # slot order doesn't matter here
    if op == "sub":                          # a - b
        return xs[0] - xs[1]                 # slot 0 minus slot 1
    if op == "mul":                          # a * b
        return xs[0] * xs[1]                 # may be the same node twice
    if op == "div":                          # a / b
        return xs[0] / xs[1]                 # constraints promise b != 0
    if op == "neg":                          # -a
        return -xs[0]                        # single parent
    if op == "exp":                          # e^a
        return math.exp(xs[0])               # inputs are kept small enough not to overflow
    if op == "log":                          # ln a
        return math.log(xs[0])               # constraints promise a > 0
    if op == "tanh":                         # tanh a
        return math.tanh(xs[0])              # bounded in (-1, 1)
    if op == "sigmoid":                      # logistic function
        return 1.0 / (1.0 + math.exp(-xs[0]))  # 1 / (1 + e^-a)
    if op == "relu":                         # max(a, 0)
        return max(xs[0], 0.0)               # relu(0) = 0
    raise ValueError("unknown op " + op)     # fail loudly on a typo rather than return garbage


# d y / d parent for each parent slot, given parent values xs and this node's value y
def _local_grads(op, xs, y):
    """d y / d parent_k for each parent slot k."""  # one derivative per entry of parents[i], same order
    if op == "add":                          # d(a+b)/da, d(a+b)/db
        return [1.0, 1.0]                    # both 1
    if op == "sub":                          # d(a-b)/da, d(a-b)/db
        return [1.0, -1.0]                   # minuend +1, subtrahend -1
    if op == "mul":                          # d(ab)/da = b, d(ab)/db = a
        return [xs[1], xs[0]]                # each slot gets the OTHER value
    if op == "div":                          # d(a/b)/da = 1/b, d(a/b)/db = -a/b^2
        return [1.0 / xs[1], -xs[0] / (xs[1] * xs[1])]  # quotient rule
    if op == "neg":                          # d(-a)/da
        return [-1.0]                        # constant
    if op == "exp":                          # d e^a / da = e^a
        return [y]                           # reuse the forward value
    if op == "log":                          # d ln a / da
        return [1.0 / xs[0]]                 # 1 / a
    if op == "tanh":                         # d tanh a / da = 1 - tanh^2 a
        return [1.0 - y * y]                 # in terms of the output
    if op == "sigmoid":                      # d sigma / da = sigma (1 - sigma)
        return [y * (1.0 - y)]               # in terms of the output
    if op == "relu":                         # 1 where a > 0, 0 elsewhere, including at 0
        return [1.0 if xs[0] > 0 else 0.0]   # strict > as the statement requires
    return []                                # inputs have no parents, so nothing to push


# values of every node, and d values[output] / d values[i] for every node
def graph_backward(ops, parents, inputs, output):
    n = len(ops)                             # number of nodes
    order = _topo_order(parents)             # the list is shuffled, so sort it first
    values = np.zeros(n)                     # (n,) forward values
    for i in order:                          # parents are always computed before children
        values[i] = _forward(ops[i], [values[p] for p in parents[i]], i, inputs)  # every node, used or not
    grads = np.zeros(n)                      # (n,) gradients; unreachable nodes stay 0
    grads[output] = 1.0                      # d out / d out = 1 seeds the chain rule
    for i in reversed(order):                # every consumer of a node runs before that node
        if grads[i] == 0.0:                  # nothing to push (unused node or the output's descendant)
            continue                         # skip it; pushing 0 would change nothing
        xs = [values[p] for p in parents[i]] # parent values in slot order
        for p, d in zip(parents[i], _local_grads(ops[i], xs, values[i])):  # one term per parent SLOT
            grads[p] += grads[i] * d         # chain rule; += sums over all paths into p
    return values, grads                     # both (n,) arrays, as the judge expects
```

## 9. How the test cases map to the code

| test case | expected `grads` | what it checks |
|---|---|---|
| Example 1 | `[4, 2, 1, 1]` | two paths into `x` add up |
| Example 2 | `[1, 0.94, 0.94, 0]` | shuffled nodes; `mul(x, x)`; an unused node gets `0` |
| Example 3 | `[1, -0.5, -1, -1.5, 1]` | `div` and `sub` slot order; relu of a negative passes nothing |
| single input is the output | `[1]` | the smallest graph |
| output is an intermediate node | `[1, -1.3, 0, 0, 0.7]` | descendants of the output get `0`, but their values are computed |
| diamond with unequal path lengths | `grads[0] = 0.9693` | a shared node on paths of different lengths: reverse topological order |
| every op once | `grads[0] = 0.0606` | all eleven ops' derivatives |
| relu exactly at zero | `[0, 0, 2, 1, 0]` | relu's gradient at exactly `0` is `0` (strict `>`) |
| random shuffled small, random shuffled medium | per-node values | random shuffled DAGs |
| random deep chain | per-node values | a 120-op chain: no recursion limit issues, long dependency chains |
| random wide | per-node values | 20 inputs, 150 ops, many shared nodes |

## 10. Complexity

Building child lists and Kahn's sort are $O(V + E)$ for $V$ nodes and $E$ parent slots. The forward and backward sweeps each touch every node and edge once, so they're also $O(V + E)$. Here $E \le 2V$, so everything is linear in the graph size. Memory is $O(V + E)$ for the child lists, the order and the two arrays.

This is how real frameworks run a static graph. TensorFlow 1, JAX after tracing, and ONNX runtimes all store the graph as a node list, sort it once, and then replay the order on every step. The sort is amortized away, and the backward pass costs about the same as the forward pass.

## 11. If you got Wrong Answer

- **Example 2's `values` start with `0` instead of `0.2449`.** You ran the forward pass over `range(n)`, assuming the list is sorted. Node 0 read node 1 before it was computed. On "every op once" this goes further and raises `math domain error`, because a `log` reads a not-yet-computed `0`.
- **Example 1 gives `grads[0] = 3` instead of `4`.** You assign with `=` instead of `+=`, so only the last path into `x` survives. Example 2 gives `0.47` instead of `0.94` for the same reason (the two `mul` slots).
- **Only "diamond with unequal path lengths" and "random deep chain" fail (`0.8273` instead of `0.9693`).** You walked breadth-first from the output, processing each node the first time you reach it. Section 4 shows node 1 being processed before node 2 has pushed to it.
- **"relu exactly at zero" gives `grads[1] = 2`.** Your relu derivative uses `>= 0`. At exactly `0` it must be `0`.

## 12. Follow-ups an interviewer might ask

- *How would you detect a cycle?* If Kahn's algorithm ends with fewer than `n` nodes in `order`, the leftover nodes are on a cycle or downstream of one, because their in-degree never reached 0.
- *Can you skip the forward values of nodes the output doesn't need?* Yes: do a reverse reachability search from `output` and only compute the ancestors. This problem asks for every value, but compilers prune dead nodes this way.
- *How would you handle tensors instead of scalars?* Each node holds an array, the local derivatives become vector-Jacobian products (for matmul, $\bar A = \bar C B^\top$), and broadcast inputs need their gradient summed back to the input shape (problems 58 and 59).
- *How does this relate to problem 56?* Same algorithm. Problem 56 discovers the graph from object pointers and sorts it with a DFS; here the graph is explicit data and you sort it with Kahn's algorithm.
