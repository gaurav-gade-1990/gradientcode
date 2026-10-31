## 1. What the problem is really asking

Every time you write `x @ W + b` with `b` of shape `(d,)`, NumPy quietly copies `b` onto each of the `N` rows. The forward pass doesn't care. The backward pass does: the gradient arriving at the `+` has shape `(N, d)`, but `b` has shape `(d,)`, and the optimizer needs a gradient shaped like `b`. Each copy of `b` sent back its own gradient, and they must be **summed**.

That operation is called **unbroadcasting**, or "sum to size". Every tensor autograd engine has it: PyTorch's `sum_to_size`, JAX's `_unbroadcast`, micrograd-for-tensors. It is the piece problem 59 calls after every elementwise op.

Strip the story and this is: **find the axes that broadcasting stretched, and sum over them.** There are exactly two kinds, and the subtle part is lining up axis numbers between two arrays of different rank. The judge checks the values and the exact output **shape**, including `()` and `(1,)`.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `grad` | float array, 0 to 5 dims; $\partial L / \partial y$ | the upstream gradient, shaped like the broadcast result |
| `shape` | tuple of ints, broadcastable to `grad.shape` | the original shape of `x`; the output must have exactly this shape |
| return | float array with `.shape == shape` | $\partial L / \partial x$ |

Easy to miss:

- **Shapes align from the right.** `(3,)` against `(2, 3)` matches the `3` with the *last* axis. The missing axis is in front.
- **A size-1 axis isn't always stretched.** In "size-1 that was not stretched", `grad` is `(5, 1, 3)` and `shape` is `(1, 3)`: the target's 1 lines up with `grad`'s 1, so nothing to sum there.
- **`shape = ()` means a scalar.** The answer is the total sum as a 0-d array, not a Python float and not shape `(1,)`.

## 3. The math

**Forward.** Broadcasting builds $y = \text{broadcast\_to}(x, S)$, where $S$ is `grad.shape`. Every output position $j$ reads some input position $\pi(j)$:

$$
y_j = x_{\pi(j)} .
$$

For `x` of shape `(3,)` broadcast to `(2, 3)`, $\pi(r, c) = c$: both rows read the same three elements.

**Backward.** Apply the chain rule to each element of $x$. Since $\partial y_j / \partial x_i = 1$ if $\pi(j) = i$ and $0$ otherwise,

$$
\frac{\partial L}{\partial x_i} = \sum_j \frac{\partial L}{\partial y_j}\,\frac{\partial y_j}{\partial x_i} = \sum_{j\,:\,\pi(j) = i} \text{grad}_j .
$$

So each input element's gradient is the **sum** of `grad` over every position it was copied to. Not the mean: each copy contributes with weight 1.

**Which positions?** NumPy's rule, aligning shapes from the right: let $r = $ `grad.ndim` and $q = $ `len(shape)`, with $r \ge q$.

1. The first $r - q$ axes of `grad` don't exist in `x`. Every index along them maps to the same `x` element, so **sum them away**.
2. After that the ranks match. On each remaining axis $i$, if `shape[i] == 1` and `grad.shape[i] > 1`, every index along it maps to index 0 of `x`. **Sum with `keepdims=True`** so the axis stays as size 1.

Axes where the sizes are equal map one-to-one and are left alone.

## 4. Trace the examples by hand

**Example 1**: `grad = [[1, 2, 3], [4, 5, 6]]` of shape `(2, 3)`, `shape = (3,)`.

| step | operation | result | shape |
|---|---|---|---|
| align | `(2, 3)` vs `(·, 3)` | 1 extra leading axis | |
| 1 | `grad.sum(axis=0)` | `[5, 7, 9]` | `(3,)` |
| 2 | no size-1 axes in `(3,)` | `[5, 7, 9]` | `(3,)` |

This is exactly the bias gradient for `x @ W + b`: column sums.

**Example 2**: same `grad`, `shape = (2, 1)`. No extra axes. Axis 1 has target size 1 and `grad` size 3, so it was stretched: `grad.sum(axis=1, keepdims=True) = [[6], [15]]`, shape `(2, 1)`. Without `keepdims` you'd get `(2,)`, which is the right numbers in the wrong shape.

**Example 3**: `shape = ()`. Both axes of the `(2, 2)` grad are extra, so step 1 sums everything to `10`, a 0-d array.

**The case that combines both, "leading and inner size-1"**: `grad` is `(2, 3, 4, 5)`, `shape = (3, 1, 5)`.

| step | shapes aligned | action | result shape |
|---|---|---|---|
| align | `(2, 3, 4, 5)` vs `(·, 3, 1, 5)` | one extra leading axis | |
| 1 | | sum axis 0 | `(3, 4, 5)` |
| 2 | `(3, 4, 5)` vs `(3, 1, 5)` | axis 1: target 1, grad 4: stretched | |
| 2 | | sum axis 1 with `keepdims` | `(3, 1, 5)` |

The first element of the result is `-1.3768`.

**"five dims"**: `grad` is `(2, 1, 3, 2, 4)`, `shape = (1, 3, 1, 4)`. Step 1 sums axis 0 to `(1, 3, 2, 4)`. In step 2, axis 0 has target 1 and grad 1, so it's **not** stretched; axis 2 has target 1 and grad 2, so it is. Sum axis 2 with `keepdims`: `(1, 3, 1, 4)`.

## 5. Key idea: drop leading axes first, then compare

The order of the two steps is what keeps the axis numbers honest. Before step 1, `shape`'s axis `i` corresponds to `grad`'s axis `i + extra`. After step 1 the ranks match and axis `i` means the same thing in both. If you look for size-1 axes first, using the target's numbering on the un-trimmed `grad`, you sum the wrong axes. In "leading and inner size-1" that sums `grad`'s axis 1 (size 3) instead of axis 2 (size 4), and the final `reshape` fails with `cannot reshape array of size 20 into shape (3,1,5)`. Every case with both leading axes and stretched inner axes breaks this way. Cases with no leading axes pass, which is why it can survive the examples.

## 6. Plan before you code

```
extra = grad.ndim - len(shape)
if extra > 0: grad = grad.sum(axis = 0 .. extra-1)                  # now same rank as shape
axes = [i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1]
if axes: grad = grad.sum(axis=axes, keepdims=True)                  # stretched size-1 axes
return grad.reshape(shape)                                          # exact shape, incl. ()
```

## 7. Build it one piece at a time

**Step 1: normalize the input.** `np.asarray(..., dtype=float)` handles a 0-d `grad` like `np.array(2.5)` and guarantees float output.

```python
grad = np.asarray(grad, dtype=float)
```

**Step 2: sum away the leading axes.** `sum` accepts a tuple of axes, so one call removes all of them.

```python
extra = grad.ndim - len(shape)                  # e.g. 4 - 3 = 1
if extra > 0:
    grad = grad.sum(axis=tuple(range(extra)))   # (2, 3, 4, 5) -> (3, 4, 5)
```

**Step 3: sum the stretched size-1 axes.** The condition needs both halves. `s == 1` alone would also pick axes where `grad` is already 1; summing those with `keepdims` is harmless, but the explicit check makes the intent clear.

```python
axes = tuple(i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1)
if axes:
    grad = grad.sum(axis=axes, keepdims=True)   # (3, 4, 5) -> (3, 1, 5)
```

**Step 4: the exact shape.** After steps 2 and 3 the shape already matches in every case except `shape = ()`, where summing all axes of a non-scalar `grad` yields a NumPy scalar. `reshape(())` turns it into a 0-d array.

```python
return grad.reshape(shape)
```

## 8. Full solution

```python
# NumPy for sums over chosen axes
import numpy as np


# sum an upstream gradient back down to the shape of the input that was broadcast
def unbroadcast(grad: np.ndarray, shape: tuple) -> np.ndarray:
    grad = np.asarray(grad, dtype=float)        # accept 0-d input and guarantee a float result
    extra = grad.ndim - len(shape)              # leading axes that broadcasting added (shapes align from the right)
    if extra > 0:                               # x had fewer dimensions than grad
        grad = grad.sum(axis=tuple(range(extra)))  # every copy along those axes adds its gradient; now same rank
    # size-1 axes of x that were stretched to a larger size in grad
    axes = tuple(i for i, s in enumerate(shape) if s == 1 and grad.shape[i] != 1)
    if axes:                                    # only sum when something was actually stretched
        grad = grad.sum(axis=axes, keepdims=True)  # sum the copies, keeping each axis as size 1
    return grad.reshape(shape)                  # exact target shape; turns a full sum into a 0-d array for ()
```

## 9. How the test cases map to the code

| test case | expected shape | what it checks |
|---|---|---|
| Example 1 | `(3,)`, `[5, 7, 9]` | leading axis summed away (bias gradient) |
| Example 2 | `(2, 1)`, `[[6], [15]]` | stretched size-1 axis kept with `keepdims` |
| Example 3 | `()`, `10` | scalar target: total sum, 0-d |
| no broadcasting | `(3, 4)` | nothing to sum: returns `grad` unchanged |
| leading and inner size-1 | `(3, 1, 5)` | both kinds at once; axis numbers after trimming |
| leading axes plus trailing 1 | `(3, 1)` | two leading axes plus a trailing stretched axis |
| all ones target | `(1, 1, 1)`, `-13.3945` | every axis stretched: total sum, rank kept |
| size-1 that was not stretched | `(1, 3)` | a 1 aligned with a 1 is left alone |
| target of shape (1,) | `(1,)`, `-3.053` | one leading axis summed, then the last one stretched |
| scalar grad, scalar target | `()`, `2.5` | a 0-d grad passes straight through |
| five dims | `(1, 3, 1, 4)` | five-dimensional alignment; one size-1 stretched, one not |
| size-1 in front of target | `(1, 2, 1)` | same rank, two stretched axes |

## 10. Complexity

$O(N)$ time for $N$ elements of `grad`: each sum reads its input once, and the second sum reads an array no bigger than the first. Memory is $O(N)$ in the worst case for the intermediate after step 2, and the output has $\prod(\text{shape})$ elements.

In an autograd engine this runs on the backward pass of **every** broadcasting op: `+`, `-`, `*`, `/` between tensors of different shapes. The bias in every linear layer, LayerNorm's `gamma` and `beta` (problem 41), and attention's scale factors all rely on it. The sums are cheap compared with the matrix multiplies, but getting the shape wrong is one of the most common bugs when you hand-write a tensor engine.

## 11. If you got Wrong Answer

- **Example 2 returns shape `(2, 3)`, and "all ones target" returns `(2, 3, 4)`.** You only summed the leading axes and forgot the stretched size-1 axes.
- **`cannot reshape array of size 20 into shape (3,1,5)` on "leading and inner size-1".** You summed the size-1 axes before dropping the leading ones, using the target's axis numbers on the full `grad`. Section 5 explains the fix.
- **Example 1 gives `[2.5, 3.5, 4.5]` instead of `[5, 7, 9]`.** You used `mean` instead of `sum`. Every copy contributes its full gradient.
- **Example 2 returns `[6, 15]` with shape `(2,)`.** You summed axis 1 without `keepdims=True`.
- **Example 3 fails with "expected a number" or a shape `(1,)`.** You returned `np.array([total])` or reshaped to `(1,)`. For `shape = ()`, return a 0-d array: `grad.reshape(())`.

## 12. Follow-ups an interviewer might ask

- *Where does an autograd engine call this?* In the backward closure of every binary elementwise op: `a.grad += unbroadcast(out.grad * local_a, a.shape)`, and the same for `b` (problem 59).
- *What does PyTorch call it?* `Tensor.sum_to_size(shape)`, and internally `at::sum_to`. It does the same two steps.
- *What about `np.repeat` or `np.tile`, which also copy elements?* Their backward is also a sum over the copies, but the copies are laid out differently, so you reshape to separate the repeat axis before summing. Broadcasting is the special case where the copy is along a size-1 or missing axis.
- *Why not just use `np.sum` and then `reshape`?* A single `reshape` can't tell which axes to sum. You need the axis bookkeeping first; `reshape` is only safe at the end, once the element count already matches.
