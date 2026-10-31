## 1. What the problem is really asking

Most training steps produce a gradient of a reasonable size. Occasionally one batch, an outlier example, or a recurrent network unrolled over a long sequence produces a gradient hundreds of times larger, and a single update of that size can throw the weights somewhere the loss never recovers from. Gradient clipping is the seatbelt: **if the whole gradient is longer than `max_norm`, shrink it to length `max_norm`; otherwise leave it alone.**

The key word is *global*. A model's gradient arrives as a list of arrays, one per parameter tensor (a weight matrix, a bias vector, a scalar). Clipping treats them as **one long vector**: one norm over everything, one scale factor applied to every array. That keeps the update pointing in exactly the same direction and only changes its length.

Strip the story and this is a sum of squares across a ragged list of arrays, a clamped ratio, and a scale. The judge compares the list of clipped arrays (shapes and order preserved) and the **pre-clip** norm, at `rtol = 1e-7`, which is tight enough that PyTorch's `1e-6` guard is part of the answer.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `grads` | list of 1 to 10 float arrays, each with `ndim` 0 to 3 | square and sum every element of every array |
| `max_norm` | positive float | the length you clip to |
| return | `(clipped, total_norm)` | a list of arrays in the same order and shapes, and a float |

Easy to miss:

- **The arrays have different shapes**, so you can't stack them into one array. "scalar and 3d arrays" mixes a 0-d array (`np.array(7.0)`), a `(2, 3, 2)` array and a `(1,)` array.
- **`total_norm` is the norm before clipping.** That's what PyTorch's `clip_grad_norm_` returns, and it's what you log to spot loss spikes.
- **The `+ 1e-6` is graded.** With `rtol = 1e-7`, dropping it changes the coefficient by about $2 \times 10^{-7}$ relative, and four cases fail.

## 3. The math

Number the arrays $k = 1, \dots, K$ and their elements $i$. Treat everything as one vector $g$:

$$
\lVert g \rVert = \sqrt{\sum_{k=1}^{K} \sum_{i} g_{k,i}^2} = \sqrt{\sum_{k=1}^{K} \lVert g_k \rVert^2}.
$$

The second form says the global norm is the root of the sum of **squared** per-array norms. It is not the sum of the per-array norms, and not their maximum.

The coefficient:

$$
c = \min\!\left(1,\ \frac{\tau}{\lVert g \rVert + 10^{-6}}\right), \qquad g_k \leftarrow c\, g_k \quad \text{for every } k,
$$

with $\tau$ the `max_norm`.

**Direction is preserved.** Multiplying every component of a vector by the same positive $c$ gives a vector pointing the same way: the cosine between $g$ and $cg$ is $\frac{c\,\lVert g\rVert^2}{c\,\lVert g\rVert^2} = 1$. So clipping never changes *which way* you step, only how far. That is the whole argument for global clipping over per-array clipping (section 5).

**The new length.** When clipping is active, $\lVert c g \rVert = \tau \cdot \frac{\lVert g \rVert}{\lVert g \rVert + 10^{-6}}$, which is a hair under $\tau$. In "single array just above" the norm is `1.00008`, and after clipping it's `0.999999`, not exactly `1`.

**The guard.** If every gradient is zero, $\lVert g \rVert = 0$ and $\tau / 0$ would be `inf`. With the guard, $c = \min(1, \tau / 10^{-6}) = 1$, and zeros stay zeros.

**Why clamp at 1.** Without the `min`, a gradient of norm `0.5` with `max_norm = 1` is multiplied by about `2`. Every update would then have length exactly `max_norm`, which is a different algorithm (normalized gradient descent) and scales healthy small gradients *up*.

## 4. Trace the examples by hand

**Example 1**: `grads = [array([3, 0]), array([[0, 4]])]` with shapes `(2,)` and `(1, 2)`, `max_norm = 1`.

| quantity | value |
|---|---|
| `sum(g0 * g0)` | `9` |
| `sum(g1 * g1)` | `16` |
| `total_norm = sqrt(9 + 16)` | `5` |
| `coef = min(1, 1 / (5 + 1e-6))` | `0.19999996` |
| `g0 * coef` | `[0.59999988, 0]`, shape `(2,)` |
| `g1 * coef` | `[[0, 0.79999984]]`, shape `(1, 2)` |

The second array keeps its `(1, 2)` shape. The combined vector `[0.6, 0, 0, 0.8]` points the same way as `[3, 0, 0, 4]`, with length just under 1.

**Example 2**: `grads = [array([0.3, -0.4]), array([0.0])]`, `max_norm = 1`. The norm is `sqrt(0.09 + 0.16 + 0) = 0.5`. `1 / 0.500001` is about `2`, so `min` clamps the coefficient to `1` and the arrays come back unchanged, with `total_norm = 0.5`.

**"one dominant layer"** shows why the norm is global. A `(3, 3)` array has entries around `100` and a `(5,)` array entries around `0.01`. The total norm is `338.513`, almost all from the first array. With `max_norm = 2`, `c ≈ 0.0059`, and the small array's entries go from about `0.0128` to `0.0001`. Clipping each array on its own would have left the small one untouched, which changes the direction of the update.

## 5. Key idea: one coefficient for every array

Per-tensor clipping (clip each array by its own norm) sounds safer but gives a different update. In Example 1 each array alone has norm `3` and `4`, both above `1`, so per-tensor clipping gives `[1, 0]` and `[[0, 1]]`. The combined vector is now `[1, 0, 0, 1]`, and the angle between it and the original `[3, 0, 0, 4]` is about 8.1 degrees. Per-tensor clipping rotated the gradient. Global clipping is a pure rescale, so it's equivalent to temporarily lowering the learning rate for this one step, which is exactly what you want from a safety mechanism.

## 6. Plan before you code

```
total = 0
for each array g in grads:  total += sum(g * g)      # sum of squares, any shape
total_norm = sqrt(total)
coef = min(1, max_norm / (total_norm + 1e-6))
clipped = [g * coef for g in grads]                   # new arrays, same shapes
return clipped, total_norm
```

## 7. Build it one piece at a time

**Step 1: the global norm.** `np.sum(g * g)` collapses an array of any shape, including 0-d, to one number. A Python `sum` over the generator adds those numbers across the list.

```python
total_norm = float(np.sqrt(sum(np.sum(g * g) for g in grads)))   # scalar
```

You could also write `np.sqrt(sum(np.linalg.norm(g) ** 2 for g in grads))`. Don't take `np.linalg.norm(grads)`: it tries to build one array from a ragged list and fails.

**Step 2: the coefficient.** Python's `min` on two floats is the clamp.

```python
coef = min(1.0, max_norm / (total_norm + 1e-6))                  # scalar in (0, 1]
```

**Step 3: scale every array.** `g * coef` broadcasts a scalar over each array and returns a new array with `g`'s shape, so the input list is untouched.

```python
clipped = [g * coef for g in grads]                               # same order, same shapes
```

`g *= coef` would modify the caller's gradients. PyTorch's `clip_grad_norm_` (trailing underscore) does modify in place, but this problem asks you not to.

## 8. Full solution

```python
# NumPy for the elementwise squares and the square root
import numpy as np


# global L2-norm clipping over a list of differently shaped gradient arrays, as torch's clip_grad_norm_
def clip_grad_norm(grads, max_norm):
    total_norm = float(np.sqrt(sum(np.sum(g * g) for g in grads)))  # one norm over ALL elements of ALL arrays
    coef = min(1.0, max_norm / (total_norm + 1e-6))  # shrink only when too long; 1e-6 guards an all-zero gradient
    return [g * coef for g in grads], total_norm     # same factor everywhere keeps the direction; report the PRE-clip norm
```

## 9. How the test cases map to the code

| test case | expected `total_norm` | what it checks |
|---|---|---|
| Example 1 | `5` | global norm across two arrays of different shapes; scale by about `1/5` |
| Example 2 | `0.5` | below `max_norm`: coefficient clamped at 1, arrays unchanged |
| many layers clipped | `5.62822` | four arrays, one coefficient |
| one dominant layer | `338.513` | the small array is scaled too: no per-tensor clipping |
| small grads, large max_norm | `0.0395498` | never scale up |
| all zeros | `0` | the `1e-6` guard: no division by zero, zeros stay zeros |
| scalar and 3d arrays | `7.89112` | a 0-d array and a `(2, 3, 2)` array; the scalar `7` becomes `2.66122` |
| single array just above | `1.00008` | barely above the threshold; clipped norm is `0.999999`, but the pre-clip norm is returned |

## 10. Complexity

$O(n)$ time for $n$ total gradient elements: one pass to square and sum, one pass to scale. Memory is $O(n)$ for the clipped copies (zero extra if done in place, as PyTorch does).

At scale the cost that matters is communication. With the model sharded across GPUs (tensor or pipeline parallelism, or ZeRO), each device holds only part of the gradient, so each computes its local sum of squares, then one all-reduce adds the partial sums before the square root. That single scalar all-reduce is why global clipping is cheap even on thousands of GPUs. Large-language-model training commonly uses `max_norm = 1.0`, and the logged pre-clip norm is one of the first things you look at when the loss spikes.

## 11. If you got Wrong Answer

- **Example 2 comes back as `[0.6, -0.8]`.** You forgot the `min(1, ...)` clamp, so small gradients are scaled up to `max_norm`. "small grads, large max_norm" fails the same way.
- **Example 1 gives `[1, 0]` and `[[0, 1]]`.** You clipped each array by its own norm (section 5).
- **`total_norm` is `1` in Example 1, `0.5` in "many layers clipped".** You returned the norm after clipping. Return the one you computed first.
- **Example 1 is off in the 7th significant digit (`0.6` against `0.59999988`).** You left out the `+ 1e-6`. With `rtol = 1e-7`, Example 1, "many layers clipped", "scalar and 3d arrays" and "single array just above" all fail.
- **A shape error, or `ValueError: setting an array element with a sequence`.** You tried to turn the ragged list into one array (`np.array(grads)` or `np.linalg.norm(grads)`). Sum per array instead.
- **"scalar and 3d arrays" fails with "expected a number, got ndarray".** You turned the 0-d array into shape `(1,)`, for example with `np.atleast_1d` or `reshape(-1)`. `g * coef` keeps a 0-d array 0-d.

## 12. Follow-ups an interviewer might ask

- *Clip by norm or clip by value?* Value clipping (`np.clip(g, -v, v)` elementwise) changes the direction, because it caps large components and leaves small ones. Norm clipping is a pure rescale. Norm clipping is the standard choice for transformers and RNNs.
- *Should you clip before or after the optimizer?* Before. You clip the raw gradient, then feed it to Adam (problem 52), so a spike doesn't inflate the second moment $v$ for the next thousand steps.
- *How do you pick `max_norm`?* Log the pre-clip norm for a while and set the threshold a bit above its typical value, so clipping only triggers on outliers. If it triggers on most steps, it is acting as a learning-rate cut and your `lr` is probably too high.
- *How does this interact with mixed precision?* With loss scaling, the gradients are scaled by a large factor, so you must unscale them before computing the norm, otherwise the threshold is meaningless.
