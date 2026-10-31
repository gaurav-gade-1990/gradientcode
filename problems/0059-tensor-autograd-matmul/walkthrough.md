## 1. What the problem is really asking

Problem 56 built autograd for single numbers. Real networks are made of matrices, so this problem lifts the same engine to NumPy arrays. The structure doesn't change at all: every op returns a new node with its parents and a `_backward` closure, and `backward()` runs the closures in reverse topological order with `+=`. Two genuinely new things appear once values have shapes:

1. **Matrix multiply has a matrix-shaped chain rule.** For $C = AB$, the gradient for $A$ is $G B^\top$, not "$B$".
2. **Broadcasting has to be undone.** A bias of shape `(m,)` added to an `(n, m)` matrix was copied onto every row, so its gradient is the **sum** over rows: problem 58's `unbroadcast`.

The driver wraps each named input in your `Tensor`, evaluates an expression such as `((x @ W1 + b1).relu() @ W2 + b2 - y)`, reduces it to one number, calls `backward()`, and compares the loss and **each input's `.grad`**. Every gradient must have exactly its tensor's shape, so a shape bug is a Wrong Answer even when the numbers inside are right.

## 2. Understand the inputs

| piece | what it is | how you use it |
|---|---|---|
| `Tensor(data)` | `.data` is a float64 array; `.grad` starts as zeros of the same shape | from the starter |
| `a + b`, `a * b` | elementwise, with broadcasting; either side may be a Python number | gradients pass through `unbroadcast` |
| `a @ b` | `(n, k) @ (k, m) -> (n, m)`, 2-D only | $G B^\top$ and $A^\top G$ |
| `.relu()` | elementwise $\max(x, 0)$ | mask `x > 0` |
| `.sum()`, `.mean()` | reduce **all** elements to shape `()` | spread the scalar gradient back |
| `-a`, `a - b`, `1 - a` | already in the starter | built from `+` and `*` |
| `.backward()` | on a one-element Tensor | seed with ones, run closures in reverse order |

Shapes that appear in the tests: `(4, 3)` inputs, `(5,)` and `(1, 4)` and `(6, 1)` biases, 0-d scalars like `g = np.array(0.7)`.

Details that are easy to miss:

- **0-d tensors broadcast against everything.** In Example 3, `s` has shape `()`, and `ds` must come back with shape `()`, the sum of all its contributions.
- **The walrus operator shares nodes.** `(h := (x @ A).relu()) @ B ... + (h * h).mean()` uses the same `h` three times, so `+=` and topological order both matter, exactly as in problem 56.
- **`self.grad` keeps its shape.** Write `self.grad += ...` with an array of the right shape. If the right-hand side has a bigger shape, NumPy raises an error on the in-place add, which is actually a useful alarm.

## 3. The math

**Matrix multiply.** Let $C = AB$ with $A$ of shape $(n, k)$, $B$ of shape $(k, m)$, and $G = \partial L / \partial C$ of shape $(n, m)$. In index form, $C_{ij} = \sum_r A_{ir} B_{rj}$, so $\partial C_{ij} / \partial A_{ir} = B_{rj}$. By the chain rule,

$$
\frac{\partial L}{\partial A_{ir}} = \sum_{j} G_{ij}\, B_{rj} = \sum_j G_{ij}\,(B^\top)_{jr} = (G B^\top)_{ir}.
$$

Likewise $\partial C_{ij} / \partial B_{rj} = A_{ir}$, so

$$
\frac{\partial L}{\partial B_{rj}} = \sum_i A_{ir}\, G_{ij} = (A^\top G)_{rj}.
$$

Shapes check out: $G B^\top$ is $(n, m)(m, k) = (n, k)$, the shape of $A$; $A^\top G$ is $(k, n)(n, m) = (k, m)$, the shape of $B$. If you're ever unsure which side the transpose goes on, this shape check settles it.

**Elementwise add and multiply with broadcasting.** For $y = a + b$, the local derivative is 1 for each input, so each receives $G$. For $y = a \odot b$, $a$ receives $G \odot b$ and $b$ receives $G \odot a$. Those arrays have the **output's** shape. If $a$ was broadcast, then by problem 58 its gradient is the sum over the copies:

$$
\bar a = \text{unbroadcast}(G \odot b,\ \text{shape}(a)).
$$

**ReLU.** $\partial \max(x, 0) / \partial x = [x > 0]$, so $\bar x = G \odot [x > 0]$, with gradient 0 at exactly 0.

**Reductions.** For $s = \sum_i x_i$, every $\partial s / \partial x_i = 1$, so $\bar x = \bar s \cdot \mathbf{1}$. For $\mu = \frac1N \sum_i x_i$, $\bar x = \frac{\bar\mu}{N}\mathbf{1}$, with $N$ the element count. $\bar s$ is a 0-d array, and multiplying `np.ones_like(x)` by it broadcasts it over $x$'s shape.

## 4. Trace the examples by hand

**Example 1**: `(x @ w).sum()` with `x = [[1, 2], [3, 4]]` `(2, 2)` and `w = [[1], [-1]]` `(2, 1)`.

| node | data | shape | grad after backward |
|---|---|---|---|
| `C = x @ w` | `[[-1], [-1]]` | `(2, 1)` | `[[1], [1]]` (from `sum`) |
| `L = C.sum()` | `-2` | `()` | `1` (seed) |
| `x` | | `(2, 2)` | `G @ w.T = [[1, -1], [1, -1]]` |
| `w` | | `(2, 1)` | `x.T @ G = [[1+3], [2+4]] = [[4], [6]]` |

**Example 2**: `(x + b).relu().mean()` with `x` of shape `(2, 3)` and `b = [0.5, 1, -1]` of shape `(3,)`.

| node | data | grad |
|---|---|---|
| `s = x + b` (b broadcast over 2 rows) | `[[1.5, -1, 2], [-0.5, 1.5, -4]]` | `[[1/6, 0, 1/6], [0, 1/6, 0]]` |
| `r = s.relu()` | `[[1.5, 0, 2], [0, 1.5, 0]]` | `1/6` everywhere (from `mean`, `N = 6`) |
| `L = r.mean()` | `0.833333` | `1` |
| `x` | | same as `s.grad`, shape `(2, 3)` |
| `b` | | column sums of `s.grad`: `[1/6, 1/6, 1/6]`, shape `(3,)` |

Each column of `s.grad` has exactly one live element, so `b` gets `1/6` per column. Without unbroadcasting, `b.grad` would come out as the `(2, 3)` matrix.

**Example 3**: `(x * x * s).sum() + 1` with `x = [1, -2, 3]` `(3,)` and `s = 0.5` `()`. The node `x * x` receives `G * s = 0.5` per element, then sends `x * 0.5` to `x` **twice** (both operands are `x`), for `dx = 2 * 0.5 * x = [1, -2, 3]`. For `s`, the product node sends `(x * x) * G`, shape `(3,)`, which unbroadcasts to shape `()` as `1 + 4 + 9 = 14`.

## 5. Key idea: every broadcasting op unbroadcasts both sides

You can't tell inside `__add__` which operand was broadcast, and in "scalar tensor gate", `((x @ W) * g + g)`, the 0-d `g` is broadcast in both the `*` and the `+`. So always unbroadcast **both** gradients to their own operand's shape. When no broadcasting happened, `unbroadcast` returns its input unchanged, so it costs nothing to be safe. Matmul is the exception: its operands are never broadcast here, and its gradient formulas already produce exactly the right shapes.

## 6. Plan before you code

```
_unbroadcast(grad, shape)               # problem 58
each op:
    wrap plain numbers as Tensors
    out = Tensor(result, (self, other))
    _backward: self.grad += unbroadcast(local_grad * out.grad, self.shape), same for other
backward():
    DFS post-order from self
    self.grad = ones_like(self.data)
    for t in reversed(order): t._backward()
```

## 7. Build it one piece at a time

**Step 1: `_unbroadcast`**, exactly as in problem 58: sum the leading axes, then the stretched size-1 axes with `keepdims`, then `reshape` to the exact shape.

**Step 2: add and multiply.** Wrap numbers first, so `2 * x` and `x + 1` work through the starter's `__rmul__` and `__radd__`.

```python
def __mul__(self, other):
    other = other if isinstance(other, Tensor) else Tensor(other)
    out = Tensor(self.data * other.data, (self, other), "*")      # broadcast shape
    def _backward():
        self.grad += _unbroadcast(other.data * out.grad, self.data.shape)
        other.grad += _unbroadcast(self.data * out.grad, other.data.shape)
    ...
```

`other.data * out.grad` has the broadcast output's shape, for example `(4, 2)` in "scalar tensor gate". `_unbroadcast` takes it down to `()` for `g`.

**Step 3: matmul.**

```python
def __matmul__(self, other):
    out = Tensor(self.data @ other.data, (self, other), "@")      # (n, k) @ (k, m) -> (n, m)
    def _backward():
        self.grad += out.grad @ other.data.T                       # (n, m) @ (m, k) -> (n, k)
        other.grad += self.data.T @ out.grad                       # (k, n) @ (n, m) -> (k, m)
    ...
```

In "x @ x.T style reuse", `(a @ b @ a).sum()` uses `a` as both the left and right operand of different matmuls, and both contributions must add into `a.grad`.

**Step 4: relu, sum and mean.** The relu mask is a boolean array, and `(self.data > 0) * out.grad` promotes it to float. For `mean`, divide by `self.data.size`, the total element count.

**Step 5: `backward`.** The same DFS as problem 56, with the seed `np.ones_like(self.data)` so it works whether the output has shape `()` or `(1, 1)`.

## 8. Full solution

```python
# NumPy arrays hold every value and every gradient
import numpy as np


# sum grad down to `shape`, undoing NumPy broadcasting (problem 58)
def _unbroadcast(grad, shape):
    """Sum grad over the axes that broadcasting stretched, so it has shape `shape`."""  # the backward of broadcast_to
    extra = grad.ndim - len(shape)               # leading axes the operand didn't have
    if extra > 0:                                # the operand had lower rank than the result
        grad = grad.sum(axis=tuple(range(extra)))  # every copy along those axes adds its share
    axes = tuple(i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1)  # stretched size-1 axes
    if axes:                                     # something was actually stretched
        grad = grad.sum(axis=axes, keepdims=True)  # sum the copies and keep the size-1 axis
    return grad.reshape(shape)                   # exact shape, including 0-d for ()


# an array that records how it was computed, so gradients can flow back through it
class Tensor:
    # data is any array-like; _children and _op describe the operation that produced it
    def __init__(self, data, _children=(), _op=""):
        self.data = np.array(data, dtype=float)  # float64 copy of the value
        self.grad = np.zeros_like(self.data)     # dL/dself, same shape as data
        self._backward = lambda: None            # leaves have nothing to push
        self._prev = tuple(_children)            # the op's inputs
        self._op = _op                           # op name, for debugging only

    # elementwise a + b with broadcasting
    def __add__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)  # numbers become 0-d Tensors
        out = Tensor(self.data + other.data, (self, other), "+")       # result has the broadcast shape

        # local derivative 1 for both, then sum each back to its own shape
        def _backward():
            self.grad += _unbroadcast(out.grad, self.data.shape)    # e.g. (n, m) -> (n, m)
            other.grad += _unbroadcast(out.grad, other.data.shape)  # e.g. (n, m) -> (m,) for a bias
        out._backward = _backward                # attach the closure
        return out                               # the new node

    # elementwise a * b with broadcasting
    def __mul__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)  # numbers become 0-d Tensors
        out = Tensor(self.data * other.data, (self, other), "*")       # broadcast shape

        # d(ab)/da = b and d(ab)/db = a, elementwise, then unbroadcast
        def _backward():
            self.grad += _unbroadcast(other.data * out.grad, self.data.shape)   # for x * x both hit x
            other.grad += _unbroadcast(self.data * out.grad, other.data.shape)  # a 0-d gate sums everything
        out._backward = _backward                # attach the closure
        return out                               # the new node

    # matrix product of two 2-D Tensors: (n, k) @ (k, m) -> (n, m)
    def __matmul__(self, other):
        out = Tensor(self.data @ other.data, (self, other), "@")  # no broadcasting for 2-D matmul

        # dL/dA = G B^T and dL/dB = A^T G; shapes come out exactly right
        def _backward():
            self.grad += out.grad @ other.data.T     # (n, m) @ (m, k) -> (n, k), A's shape
            other.grad += self.data.T @ out.grad     # (k, n) @ (n, m) -> (k, m), B's shape
        out._backward = _backward                # attach the closure
        return out                               # the new node

    # elementwise max(x, 0)
    def relu(self):
        out = Tensor(np.maximum(self.data, 0.0), (self,), "relu")  # same shape as self

        # gradient passes only where the input was strictly positive
        def _backward():
            self.grad += (self.data > 0) * out.grad  # boolean mask -> 0/1; exactly 0 passes nothing
        out._backward = _backward                # attach the closure
        return out                               # the new node

    # sum of all elements, as a 0-d Tensor
    def sum(self):
        out = Tensor(self.data.sum(), (self,), "sum")  # shape ()

        # every element contributed with weight 1
        def _backward():
            self.grad += np.ones_like(self.data) * out.grad  # broadcast the scalar grad back to self's shape
        out._backward = _backward                # attach the closure
        return out                               # the new node

    # mean of all elements, as a 0-d Tensor
    def mean(self):
        out = Tensor(self.data.mean(), (self,), "mean")  # shape ()

        # every element contributed with weight 1/N
        def _backward():
            self.grad += np.ones_like(self.data) * out.grad / self.data.size  # N = total element count
        out._backward = _backward                # attach the closure
        return out                               # the new node

    # fill .grad on every Tensor this one-element output depends on
    def backward(self):
        order, seen = [], set()                  # topological order and the visited set (by identity)

        # DFS post-order: a node is appended only after all of its inputs
        def build(t):
            if t not in seen:                    # each node once, however many paths reach it
                seen.add(t)                      # mark before recursing
                for c in t._prev:                # visit every input first
                    build(c)                     # recurse into the input
                order.append(t)                  # all of t's inputs are already in order
        build(self)                              # start from the output
        self.grad = np.ones_like(self.data)      # dL/dL = 1, shaped like the output (() or (1, 1))
        for t in reversed(order):                # every consumer runs before its inputs
            t._backward()                        # push this node's complete grad to its inputs

    # -a, as a times -1
    def __neg__(self):
        return self * -1                         # reuses multiplication's backward

    # number + a
    def __radd__(self, other):
        return self + other                      # addition commutes

    # a - b
    def __sub__(self, other):
        return self + (-other)                   # reuses add and neg

    # number - a
    def __rsub__(self, other):
        return other + (-self)                   # -self is a Tensor, so this calls its __radd__

    # number * a
    def __rmul__(self, other):
        return self * other                      # multiplication commutes

    # readable printout while debugging
    def __repr__(self):
        return "Tensor(shape=%s)" % (self.data.shape,)  # the shape is what you usually need to see
```

## 9. How the test cases map to the code

| test case | expected loss | what it checks |
|---|---|---|
| Example 1 | `-2` | matmul backward: `G @ w.T` and `x.T @ G` |
| Example 2 | `0.833333` | a `(3,)` bias broadcast over rows; relu mask; mean's `1/N` |
| Example 3 | `8` | `x * x` reuse; a 0-d tensor's gradient sums to `14` |
| two-layer MLP, MSE loss | `8.53149` | the full forward and backward of a real network |
| MLP with column-vector bias | `-2.00984` | a `(6, 1)` bias stretched across columns |
| three layers, shared weight | `10.5103` | the same `W` and `b` used in two layers: `+=` |
| branch reuse | `-1.91631` | a hidden layer `h` feeding two branches |
| relu exactly at zero | `3` | the mask is `x > 0`, not `>=` |
| scalar constants on both sides | `2.90089` | `1 - 2 * x + x * 3`: reflected operators |
| sum vs mean scale | `-0.0678014` | `sum` and `mean` scale gradients differently |
| x @ x.T style reuse | `-6.25211` | one tensor as both left and right matmul operand |
| scalar tensor gate | `3.5278` | a 0-d tensor broadcast in both `*` and `+` |

## 10. Complexity

The backward pass costs about the same as the forward pass, up to a constant. Each matmul of $(n, k) \times (k, m)$ costs $O(nkm)$ forward and two matmuls of the same size backward, so roughly $2\times$ the forward FLOPs. That is the usual rule of thumb: training costs about 3 times inference (one forward plus two for backward). Elementwise ops and `unbroadcast` are linear in the number of elements.

Memory is the bigger issue at scale. Every intermediate `.data` stays alive until `backward()` reaches it, because the closures need them (`self.data.T @ out.grad` reads the forward input). For a deep network this activation memory grows with depth and batch size, and **gradient checkpointing** trades it for recomputation: keep only some activations and recompute the rest during the backward pass.

## 11. If you got Wrong Answer

- **"shape mismatch, expected (3,), got (2, 3)" on Example 2's `b`.** You didn't unbroadcast in `+` or `*`. The same bug shows up as `(4, 5)` for `b1` in the MLP and `(4, 2)` for `g` in "scalar tensor gate". If you accumulate with `+=`, the same bug raises `ValueError: non-broadcastable output operand` instead, because NumPy can't add a `(2, 3)` array into a `(3,)` one in place.
- **Example 3 gives `dx = [0.5, -1, 1.5]`, half the expected value.** You assign gradients with `=` instead of `+=`, so the second operand of `x * x` overwrites the first. "three layers, shared weight" and "x @ x.T style reuse" fail for the same reason.
- **Example 2's `x` gradient is `1` instead of `0.1667`.** Your `mean` backward forgot to divide by `self.data.size`. Example 1 and Example 3 still pass because they use `sum`.
- **Only "relu exactly at zero" fails (`2` instead of `0` at `[0, 0]`).** Your relu mask is `>= 0`.
- **A shape `ValueError` inside a matmul backward.** The transposes are on the wrong side. Use the shape check from section 3: $\bar A = G B^\top$, $\bar B = A^\top G$.
- **`TypeError: unsupported operand type(s)` for `2 * x` or `1 - x`.** You removed the starter's `__rmul__` or `__rsub__`, or `__mul__` doesn't wrap plain numbers.

## 12. Follow-ups an interviewer might ask

- *How would you support batched matmul, `(b, n, k) @ (k, m)`?* The forward broadcasts the batch axis. In the backward, $\bar B = \sum_b A_b^\top G_b$, which is `unbroadcast` again, applied to `np.swapaxes(A, -1, -2) @ G`.
- *How would you add softmax cross-entropy as one fused op?* Its gradient with respect to the logits is $(p - y)/N$ (problem 36), which is cheaper and more stable than chaining exp, sum, log and divide through the graph.
- *Why does PyTorch keep `.grad` only for leaf tensors by default?* To save memory. Interior gradients are needed only while the backward pass runs, so they're freed unless you call `retain_grad()`.
- *How would you test this engine?* Compare every input's `.grad` with a central-difference estimate on the same expression (problem 46). Keep inputs away from relu's kink at 0.
