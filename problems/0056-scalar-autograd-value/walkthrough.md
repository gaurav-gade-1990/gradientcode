## 1. What the problem is really asking

Every time you call `loss.backward()` in PyTorch, an engine walks a graph of the operations you ran and applies the chain rule, one edge at a time, from the output back to the inputs. This problem has you build that engine for scalars, in the style of Karpathy's micrograd.

Underneath it are two ideas, and each test that fails points at one of them:

1. **Record the graph during the forward pass.** Each operation returns a new `Value` that remembers its inputs and carries a small closure, `_backward`, which knows the local derivative of that one operation.
2. **Replay the closures in reverse topological order.** A node may push its gradient to its inputs only after *every* node that uses it has finished pushing to it. Contributions from different paths **add up**.

The driver builds an expression such as `a * a + a` from your `Value`s with `eval`, calls `out.backward()`, and records `out.data` and each input's `.grad`. Only the leaves' gradients are graded, but they are only right if every interior node is handled correctly.

## 2. Understand the inputs

| piece | what it is | how you use it |
|---|---|---|
| `Value(data)` | wraps a float; `.grad` starts at `0.0` | the starter's `__init__` also stores `_prev` (children) and `_backward` |
| `+`, `*`, `** k` | the core operations you write | each builds an output node and its closure |
| `-`, `/`, `__r*__` | derived operators, already in the starter | they reduce to `+`, `*`, `**`, so they're correct once those are |
| `.tanh()`, `.relu()`, `.exp()` | unary operations you write | one child each |
| `.backward()` | called once on the output | seeds `out.grad = 1`, then runs closures in order |
| `expr`, `inputs` | the driver's case data | e.g. `"a * b + c"`, `{"a": 2, "b": -3, "c": 10}` |

Details that are easy to miss:

- **Plain numbers on either side.** `a * -2` and `3 * a` both appear. `__add__` and `__mul__` must wrap a non-`Value` in `Value(...)`. `2 * a` calls `int.__mul__` first, which fails, so Python falls back to your `__rmul__`.
- **The walrus operator creates shared interior nodes.** `(c := a * b) * c.tanh() + (c + 1) ** 2 + c` uses the *same* node `c` four times. By contrast, writing `(a + b)` twice creates two separate nodes.
- **`relu` at exactly 0 has gradient 0**, as the statement fixes. "relu at zero" checks it.

## 3. The math

**The chain rule, one edge at a time.** Let $L$ be the output. For any node $v$, write $\bar v = \partial L / \partial v$, its "adjoint", which is what `.grad` stores. If $v$ feeds a node $u = f(v, w)$, then the part of $\bar v$ that flows through $u$ is

$$
\bar u \cdot \frac{\partial u}{\partial v}.
$$

**Sum over paths.** If $v$ feeds several nodes $u_1, \dots, u_m$, the multivariate chain rule says

$$
\bar v = \sum_{j=1}^{m} \bar u_j \,\frac{\partial u_j}{\partial v}.
$$

That's why each closure does `child.grad += ...` and never `=`. In code, every consumer adds its term.

**The local derivatives**, derived once:

| operation | output $u$ | $\partial u / \partial$ input |
|---|---|---|
| add | $u = a + b$ | $1$ for $a$, $1$ for $b$ |
| multiply | $u = ab$ | $b$ for $a$, $a$ for $b$ |
| power, constant $k$ | $u = a^k$ | $k a^{k-1}$ |
| tanh | $u = \tanh a$ | $1 - \tanh^2 a = 1 - u^2$ |
| relu | $u = \max(0, a)$ | $1$ if $a > 0$, else $0$ |
| exp | $u = e^a$ | $e^a = u$ |

For tanh: $\tanh a = \frac{e^a - e^{-a}}{e^a + e^{-a}}$, and the quotient rule gives $\frac{(e^a+e^{-a})^2 - (e^a-e^{-a})^2}{(e^a+e^{-a})^2} = 1 - \tanh^2 a$. Both tanh and exp reuse the forward output, so the closure doesn't recompute anything.

**Derived operators need no new math.** $a - b = a + (-1)\cdot b$ and $a / b = a \cdot b^{-1}$, so their gradients come from add, multiply and power: $\frac{\partial}{\partial b}(a b^{-1}) = a \cdot (-1) b^{-2} = -a/b^2$.

**Why the order matters.** Node $v$'s closure multiplies by $\bar v$. If it runs before some consumer $u_j$ has added its term, it pushes an incomplete $\bar v$ to $v$'s own inputs, and the missing part never arrives. A **topological order** lists every node after all of its inputs. Reversing it puts every node after all of its consumers, which is exactly the condition we need.

## 4. Trace Example 2 by hand

`a * a + a` with `a = 3`. The graph has three nodes: `a`, `m = a * a`, and `out = m + a`. Note that `a` appears as **both** children of `m`.

**Forward.** `m.data = 9`, `out.data = 12`.

**Topological order.** DFS from `out`: visit `m`, which visits `a` (append `a`), then `a` again (already seen), append `m`; then `out`'s second child `a` (seen); append `out`. Order: `[a, m, out]`. Reversed: `[out, m, a]`.

| step | closure run | what it adds | `out.grad` | `m.grad` | `a.grad` |
|---|---|---|---|---|---|
| seed | – | `out.grad = 1` | 1 | 0 | 0 |
| 1 | `out` (add) | `m += 1`, `a += 1` | 1 | 1 | 1 |
| 2 | `m` (mul, both children `a`) | `a += a.data * 1` twice | 1 | 1 | 7 |
| 3 | `a` (leaf) | nothing | 1 | 1 | 7 |

`a.grad = 7 = 2a + 1`. With `=` instead of `+=`, step 2 would overwrite `a.grad` with `3` twice and you'd get `3`, which is what the ready-made `wrong_no_accumulate.py` returns.

**The hardest case, "shared intermediate".** `(c := a * b) * c.tanh() + (c + 1) ** 2 + c` with `a = 0.8`, `b = -1.1`. Here `c = -0.88` is an interior node with four consumers. The graph has 10 nodes. In reverse topological order, every consumer of `c` runs before `c` itself:

| node (reverse order) | data | grad when its closure runs |
|---|---|---|
| final `+` | `-0.243951` | `1` |
| `+` | `0.636049` | `1` |
| `** 2` | `0.0144` | `1` |
| `c + 1` | `0.12` | `0.24` |
| `c * tanh(c)` | `0.621649` | `1` |
| `tanh(c)` | `-0.706419` | `-0.88` |
| **`c = a * b`** | `-0.88` | `0.0927255` |
| `b`, `a` | | `0.0741804`, `-0.101998` |

`c`'s gradient is the sum of four paths: $\tanh c$ (from the product, `-0.7064`), $c\,(1 - \tanh^2 c)$ (through tanh, `-0.4409`), $2(c+1) = 0.24$, and $1$. Total `0.0927255`. Only then does `c` push to `a` and `b`: $\bar a = b\,\bar c = -1.1 \times 0.0927 = -0.102$.

## 5. Key idea: why a plain stack walk fails only some tests

The tempting `backward` pops a node, runs its closure, and pushes its children. That walks the graph once per *path*, not once per node. When the only shared nodes are leaves, that's harmless: a leaf's closure does nothing, and each path adds its own correct term. That's why `wrong_dfs_order.py` passes "diamond reuse": in that expression `(a + b)` is written twice, which creates two separate nodes, so only `a`, `b`, `c` are shared.

With a shared **interior** node, the stack walk runs that node's closure several times, each time with whatever partial gradient it has collected so far. In "shared intermediate" it gives `a.grad = -2.668` instead of `-0.101998`, and in "shared at two depths" `12.0122` instead of `4.07521`. A topological order runs each closure exactly once, when its gradient is complete.

## 6. Plan before you code

```
each op:
    other = wrap(other)                    # numbers become Values
    out = Value(result, children)
    def _backward(): child.grad += local_derivative * out.grad   (for each child)
    out._backward = _backward
    return out

backward():
    order = DFS post-order from self, each node once
    self.grad = 1
    for v in reversed(order): v._backward()
```

## 7. Build it one piece at a time

**Step 1: a binary operation.** The closure captures `self`, `other` and `out`. When it runs later, `out.grad` holds the final adjoint of `out`.

```python
def __mul__(self, other):
    other = other if isinstance(other, Value) else Value(other)
    out = Value(self.data * other.data, (self, other), "*")
    def _backward():
        self.grad += other.data * out.grad     # d(ab)/da = b
        other.grad += self.data * out.grad     # d(ab)/db = a
    out._backward = _backward
    return out
```

For `a * a`, `self` and `other` are the same object, so both lines add to `a.grad`. That's the $2a$ term, for free.

**Step 2: power with a constant exponent.** `k` is a plain number, never a `Value`, so there's only one child.

```python
def __pow__(self, k):
    out = Value(self.data ** k, (self,), "**")
    def _backward():
        self.grad += k * self.data ** (k - 1) * out.grad
    ...
```

**Step 3: unary ops reuse the forward value.** For tanh, store `t` and use `1 - t * t`. For relu, compare `self.data > 0`, which gives `0` at exactly `0`, as the statement asks.

**Step 4: the topological sort.** A recursive DFS appends a node only after all its children, so leaves come first and the output comes last. `seen` makes sure each node appears once, however many paths reach it.

```python
order, seen = [], set()
def build(v):
    if v not in seen:
        seen.add(v)
        for c in v._prev:
            build(c)
        order.append(v)
```

`Value` doesn't define `__eq__`, so `set` uses identity. That is what you want: two different nodes that happen to hold the same number are still different nodes. With at most 200 operations, recursion depth stays far below Python's default limit of 1,000.

## 8. Full solution

```python
# math for tanh and exp on plain floats
import math


# a scalar that records how it was computed, so gradients can flow back through it
class Value:
    # data is the number; _children and _op describe the operation that made it
    def __init__(self, data, _children=(), _op=""):
        self.data = float(data)                # the forward value
        self.grad = 0.0                        # dL/dself, filled in by backward()
        self._backward = lambda: None          # leaves have nothing to push
        self._prev = tuple(_children)          # inputs of the op that produced this node
        self._op = _op                         # op name, for debugging only

    # a + b, where b may be a plain number
    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)  # wrap constants so they fit the graph
        out = Value(self.data + other.data, (self, other), "+")      # record both inputs

        # chain rule for addition: both local derivatives are 1
        def _backward():
            self.grad += out.grad              # += so every path into self adds up
            other.grad += out.grad             # same for the other input
        out._backward = _backward              # attach the closure to the output node
        return out                             # the new node joins the graph

    # a * b, where b may be a plain number
    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)  # wrap constants
        out = Value(self.data * other.data, (self, other), "*")      # record both inputs

        # chain rule for multiplication: d(ab)/da = b, d(ab)/db = a
        def _backward():
            self.grad += other.data * out.grad  # for a * a both lines hit a, giving 2a
            other.grad += self.data * out.grad  # contribution to the second input
        out._backward = _backward              # attach the closure
        return out                             # the product node

    # a ** k with k a plain int or float constant
    def __pow__(self, k):
        out = Value(self.data ** k, (self,), "**")  # k is not a node, so one child

        # power rule: d(a^k)/da = k a^(k-1)
        def _backward():
            self.grad += k * self.data ** (k - 1) * out.grad  # also gives division via k = -1
        out._backward = _backward              # attach the closure
        return out                             # the power node

    # hyperbolic tangent
    def tanh(self):
        t = math.tanh(self.data)               # forward value, reused by the derivative
        out = Value(t, (self,), "tanh")        # one child

        # d tanh(a)/da = 1 - tanh(a)^2
        def _backward():
            self.grad += (1 - t * t) * out.grad  # no need to recompute tanh
        out._backward = _backward              # attach the closure
        return out                             # the tanh node

    # rectified linear unit, with relu(0) = 0
    def relu(self):
        out = Value(self.data if self.data > 0 else 0.0, (self,), "relu")  # max(0, a)

        # derivative is 1 where a > 0 and 0 elsewhere, including at exactly 0
        def _backward():
            self.grad += (1.0 if self.data > 0 else 0.0) * out.grad  # dead units pass nothing back
        out._backward = _backward              # attach the closure
        return out                             # the relu node

    # natural exponential
    def exp(self):
        e = math.exp(self.data)                # forward value, also its own derivative
        out = Value(e, (self,), "exp")         # one child

        # d e^a / da = e^a
        def _backward():
            self.grad += e * out.grad          # reuse the forward value
        out._backward = _backward              # attach the closure
        return out                             # the exp node

    # fill .grad on every node this output depends on
    def backward(self):
        order, seen = [], set()                # topological order and the visited set (by identity)

        # DFS post-order: a node is appended only after all of its inputs
        def build(v):
            if v not in seen:                  # each node once, however many paths reach it
                seen.add(v)                    # mark before recursing
                for c in v._prev:              # visit every input first
                    build(c)                   # recurse into the input
                order.append(v)                # now all of v's inputs are already in order
        build(self)                            # start from the output
        self.grad = 1.0                        # dL/dL = 1 seeds the chain rule
        for v in reversed(order):              # output first: every consumer runs before its inputs
            v._backward()                      # push this node's now-complete grad to its inputs

    # -a, as a times -1
    def __neg__(self):
        return self * -1                       # reuses multiplication's gradient

    # number + a
    def __radd__(self, other):
        return self + other                    # addition commutes

    # a - b
    def __sub__(self, other):
        return self + (-other)                 # reuses add and neg

    # number - a
    def __rsub__(self, other):
        return other + (-self)                 # -self is a Value, so this calls its __radd__

    # number * a
    def __rmul__(self, other):
        return self * other                    # multiplication commutes

    # a / b
    def __truediv__(self, other):
        return self * other ** -1              # b ** -1 via __pow__ (or plain float math if b is a number)

    # number / a
    def __rtruediv__(self, other):
        return other * self ** -1              # a ** -1 is a Value, so this calls its __rmul__

    # readable printout while debugging
    def __repr__(self):
        return "Value(data=%g, grad=%g)" % (self.data, self.grad)  # shows both fields
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | data `4`, grads `a=-3, b=2, c=1` | add and multiply closures |
| Example 2 | data `12`, `a=7` | the same leaf used three times: `+=` |
| Example 3 | data `-0.635149`, `a=-0.894879` | tanh's `1 - t²` |
| division and power | data `16.2978`, `a=22.2881, b=90.3125` | `/` and `** 2` through `** -1`; `3 / a` uses `__rtruediv__` |
| relu dead and alive | `a=0, b=3` | relu gradient is 0 for negative input |
| relu at zero | `a=0, b=0` | the forward value `relu(0) = 0`, so `b` gets `0`; `a`'s two paths cancel |
| exp chain | `a=0.149146, b=-0.149146` | exp's derivative is itself; this is a softmax entry |
| neuron | data `0.707107`, `w1=1, bias=0.5` | the classic micrograd neuron |
| diamond reuse | `b=0.928364` | leaves shared across a large expression |
| deep chain | `a=301.205, b=-22.9964` | 29 tanh terms, many paths into `a` and `b` |
| shared intermediate | `a=-0.101998, b=0.0741804` | an interior node with four consumers: topological order |
| shared at two depths | `a=4.07521, b=4.07521` | a shared node used at different depths |
| rsub rtruediv | data `2.64737`, `a=3.55402` | `1 - ...` and `2 / ...` with numbers on the left |

## 10. Complexity

With $V$ nodes and $E$ edges (at most 2 per node here), the forward pass and the backward pass are each $O(V + E)$: the topological sort visits every node and edge once, and each closure does $O(1)$ work per child. So computing every gradient costs about the same as computing the output, which is the whole point of reverse mode. Forward-mode differentiation, or the numerical check of problem 46, would cost one pass **per input**.

Memory is $O(V)$ for the graph, which stays alive until `backward` finishes. That's the scalar version of why training uses far more memory than inference: every intermediate activation is kept for the backward pass. A scalar engine is also hopelessly slow for real networks, with one Python object per number. PyTorch applies the same algorithm to tensor nodes (problem 59), so a single node covers a whole matrix multiply.

## 11. If you got Wrong Answer

- **Example 2 gives `a = 3` instead of `7`.** Your closures assign (`=`) instead of accumulating (`+=`). Every case with a reused value fails: "division and power", "diamond reuse", "deep chain" and others.
- **Only "shared intermediate" and "shared at two depths" fail (`-2.668` and `12.0122` for `a`).** Your `backward` walks with a stack or queue and runs a node's closure once per path. Use a DFS topological order with a `seen` set (section 5).
- **`TypeError: unsupported operand type(s) for *: 'int' and 'Value'`.** You're missing `__rmul__` or haven't wrapped plain numbers in `__mul__`. The starter provides the reflected operators, so check you didn't delete them.
- **"relu dead and alive" gives `a = -2` instead of `0`.** Your relu passes the gradient through unconditionally. It must multiply by `1` only where `data > 0`. Note that writing `>= 0` instead of `> 0` is also wrong by the statement, but no test catches it: "relu at zero" builds its zero as `a - a`, so whatever relu passes back reaches `a` once with each sign and cancels.

## 12. Follow-ups an interviewer might ask

- *Why reverse mode and not forward mode?* A loss has one output and millions of inputs. Reverse mode gets every $\partial L / \partial x_i$ in one backward pass; forward mode needs one pass per input.
- *How would you write the topological sort without recursion?* Use Kahn's algorithm: count each node's consumers, start from the output, and release a node once all its consumers are done. Problem 57 (topological-sort-backward) builds exactly that.
- *How do you extend this to tensors?* Each node holds an array, and each closure applies the tensor version of its local derivative, for matrix multiply $\bar A = \bar C B^\top$ and $\bar B = A^\top \bar C$, plus un-broadcasting for shapes that were broadcast in the forward pass (problems 58 and 59).
- *How would you check your engine?* Compare each leaf's `.grad` with a central-difference estimate on the same expression (problem 46).
- *Why does PyTorch need `zero_grad()`?* Because of the same `+=`: gradients from a second `backward()` add to the first. Accumulating on purpose is how gradient accumulation over micro-batches works.
