## 1. What the problem is really asking

Max pooling shrinks a feature map by keeping only the largest value in each small window, typically 2×2 with stride 2, which halves the height and width. It has no parameters. Its backward pass is the interesting half: the gradient of a max is 1 for the input that won and 0 for the rest, so each window acts as a **router** that sends its entire upstream gradient to one pixel.

Under the story, it's a **windowed argmax, then a scatter-add**:

- Forward: for each window, find the position of the maximum (the first one, on ties) and output its value.
- Backward: add `dout[n, c, y, z]` to `dx` at that position. Every other pixel gets 0.

The judge compares `(out, dx)` with `rtol=1e-9`. The forward output is easy; the tests are about the backward pass: the **tie rule** (first in row-major order) and **overlapping windows** (add, don't overwrite).

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(N, C, H, W)` | input feature maps | windows over the last two axes |
| `dout` | `(N, C, out_h, out_w)` | upstream gradient, one per window | routed to each window's max |
| `pool_h`, `pool_w` | ints | window size | |
| `stride` | int | step between windows; no padding | |
| return | `(N, C, out_h, out_w)`, `(N, C, H, W)` | `out, dx` | |

The details that are easy to miss:

- **Ties go to the first position in row-major order** (smallest `i`, then smallest `j`). `np.argmax` on the flattened window does exactly that. A hand-written loop with `>=` picks the last.
- **Only one position per window gets the gradient**, even when several tie. Sending it to all of them duplicates gradient.
- **Windows overlap when `stride < pool size`.** A pixel can be the max of several windows and must collect the sum of their gradients.
- **Channels never mix.** Pooling runs independently on every `(n, c)` plane.

## 3. The math

For window $(y, z)$ of plane $(n, c)$, with $s$ the stride:

$$\text{out}[n, c, y, z] = \max_{0 \le i < p_h,\ 0 \le j < p_w} x[n, c,\, ys + i,\, zs + j], \qquad \text{out\_h} = \left\lfloor \frac{H - p_h}{s} \right\rfloor + 1.$$

**Derivative of a max.** Let $m = \max_k v_k$ over a window's values $v_1, \dots, v_K$. If $v_{k^*}$ is the **unique** maximum, then small changes to any other $v_k$ don't change $m$, and $m$ moves one-for-one with $v_{k^*}$:

$$\frac{\partial m}{\partial v_k} = [k = k^*].$$

**Ties.** If two values tie for the maximum, $m$ isn't differentiable there: raising either one raises $m$, lowering either doesn't lower it. Any convex combination of the tied indicator vectors is a valid subgradient. Frameworks pick **one** winner, which keeps the total gradient right: $\sum_k \partial m / \partial v_k = 1$, so $\sum dx$ over a window equals that window's `dout`. Giving each tied position the full gradient would make the sum $t$ times too large for $t$ ties. This problem fixes the winner as the first in row-major order, which is what `np.argmax` returns.

**Chain rule with overlap.** Pixel $x[n, c, p, q]$ can be in several windows. Its gradient sums over every window where it was the chosen winner:

$$dx[n, c, p, q] = \sum_{(y, z)\,:\ \text{winner}(n, c, y, z) = (p, q)} dout[n, c, y, z].$$

As a check, every window sends its gradient to exactly one pixel, so $\sum dx = \sum dout$ for every plane.

**From a flat index back to coordinates.** Flatten a $p_h \times p_w$ window in row-major order; position $(i, j)$ becomes $k = i\,p_w + j$. So $i = \lfloor k / p_w \rfloor$, $j = k \bmod p_w$, and the pixel is at $(ys + i,\ zs + j)$ in `x`.

## 4. Trace an example by hand

**Example 1:** a `(1, 1, 4, 4)` input, 2×2 windows, stride 2, so `out` is `(1, 1, 2, 2)` and no windows overlap.

```
x = [[1, 3, 2, 0],
     [4, 2, 1, 5],
     [0, 1, 3, 2],
     [2, 6, 1, 1]]        dout = [[1, 2], [3, 4]]
```

| window `(y, z)` | values (flattened) | `k = argmax` | pixel | `out` | `dx` gets |
|---|---|---|---|---|---|
| `(0, 0)` | `[1, 3, 4, 2]` | 2 | `(1, 0)` | 4 | 1 |
| `(0, 1)` | `[2, 0, 1, 5]` | 3 | `(1, 3)` | 5 | 2 |
| `(1, 0)` | `[0, 1, 2, 6]` | 3 | `(3, 1)` | 6 | 3 |
| `(1, 1)` | `[3, 2, 1, 1]` | 0 | `(2, 2)` | 3 | 4 |

`out = [[4, 5], [6, 3]]`; `dx` holds `1, 2, 3, 4` at those four pixels and 0 elsewhere.

**Example 2**, where both rules matter: `x = [[1, 1, 0], [0, 2, 2], [0, 0, 3]]`, 2×2 windows, **stride 1**, `dout = [[1, 10], [100, 1000]]`.

| window `(y, z)` | values | `k` | pixel | `dout` routed |
|---|---|---|---|---|
| `(0, 0)` | `[1, 1, 0, 2]` | 3 | `(1, 1)` | 1 |
| `(0, 1)` | `[1, 0, 2, 2]` | 2 (tie with 3; first wins) | `(1, 1)` | 10 |
| `(1, 0)` | `[0, 2, 0, 0]` | 1 | `(1, 1)` | 100 |
| `(1, 1)` | `[2, 2, 0, 3]` | 3 | `(2, 2)` | 1000 |

The 2 at `(1, 1)` wins three windows and collects `1 + 10 + 100 = 111`. The 3 at `(2, 2)` gets 1000. `out = [[2, 2], [2, 3]]`.

**"constant input"** is all zeros with 2×2 windows and stride 1, so every window is a four-way tie. Each window's first position, its top-left corner, wins. The top-left `3 × 3` block of `dx` receives `dout` exactly, and the last row and column get 0.

## 5. Key idea: one fancy-indexed `+=` per window position

Loop over the `out_h × out_w` window positions; vectorize over all `N × C` planes at once.

```python
n_idx, c_idx = np.meshgrid(np.arange(N), np.arange(C), indexing="ij")   # (N, C) each
...
k = win.argmax(axis=2)                                                  # (N, C)
dx[n_idx, c_idx, h0 + k // pool_w, w0 + k % pool_w] += dout[:, :, y, z]
```

All four index arrays are `(N, C)`, so the fancy index picks one element of `dx` per `(n, c)` plane, and `dout[:, :, y, z]` (also `(N, C)`) supplies the values. `indexing="ij"` makes `n_idx[n, c] = n` and `c_idx[n, c] = c`.

Why this is safe: NumPy's fancy-indexed `+=` does **not** accumulate when the same element appears twice in one statement (a scratch test of `a[[0, 0, 1]] += 1` on zeros gives `[1, 1, 0]`, not `[2, 1, 0]`). Within one window position, every `(n, c)` pair is different, so no element repeats. The overlap between windows is handled by the loop: each window position is its own `+=` statement. If you vectorized across window positions too, you'd need `np.add.at`, which does accumulate duplicates.

## 6. Plan before you code

```
out_h, out_w from the floor formula
out = empty (N, C, out_h, out_w);  dx = zeros like x
n_idx, c_idx = index grids of shape (N, C)
for each window position (y, z):
    win = x window, flattened to (N, C, pool_h*pool_w)
    k   = first argmax per plane                              # (N, C)
    out[:, :, y, z] = the value at k
    dx[n, c, top + k // pool_w, left + k % pool_w] += dout[:, :, y, z]
```

| rule | right | wrong |
|---|---|---|
| ties | `argmax` (first) | `>=` in a loop (last), or `win == max` (all) |
| overlap | `+=` | `=` |

## 7. Build it one piece at a time

**Step 1: sizes, buffers, index grids.**

```python
N, C, H, W = x.shape
out_h = (H - pool_h) // stride + 1
out_w = (W - pool_w) // stride + 1
out = np.empty((N, C, out_h, out_w))
dx = np.zeros_like(x, dtype=float)                       # (N, C, H, W), zero where nothing wins
n_idx, c_idx = np.meshgrid(np.arange(N), np.arange(C), indexing="ij")
```

**Step 2: each window's argmax and value.**

```python
h0, w0 = y * stride, z * stride
win = x[:, :, h0:h0 + pool_h, w0:w0 + pool_w].reshape(N, C, -1)     # (N, C, pool_h*pool_w)
k = win.argmax(axis=2)                                              # (N, C)
out[:, :, y, z] = np.take_along_axis(win, k[:, :, None], axis=2)[:, :, 0]
```

The slice is `(N, C, pool_h, pool_w)`; `reshape(N, C, -1)` flattens the window in row-major order, so `argmax` over axis 2 applies the tie rule. `take_along_axis` needs an index with the same number of dimensions, hence `k[:, :, None]` of shape `(N, C, 1)`; the trailing `[:, :, 0]` drops that axis. `win.max(axis=2)` gives the same values; `take_along_axis` just guarantees the output and the gradient use the same position.

**Step 3: route the gradient.** The `+=` line from section 5, with `k // pool_w` and `k % pool_w` turning the flat index back into a row and column offset inside the window.

## 8. Full solution

```python
# NumPy for windowed argmax and fancy-indexed scatter-add
import numpy as np


# x: (N, C, H, W), dout: (N, C, out_h, out_w); returns (out, dx)
def maxpool(x, dout, pool_h, pool_w, stride):
    # batch, channels and spatial size of the input
    N, C, H, W = x.shape
    # number of window rows; floor drops a partial window at the bottom
    out_h = (H - pool_h) // stride + 1
    # number of window columns
    out_w = (W - pool_w) // stride + 1
    # (N, C, out_h, out_w): every entry is written in the loop
    out = np.empty((N, C, out_h, out_w))
    # (N, C, H, W): pixels that never win a window keep gradient 0
    dx = np.zeros_like(x, dtype=float)
    # (N, C) grids with n_idx[n, c] = n and c_idx[n, c] = c, to address every plane at once
    n_idx, c_idx = np.meshgrid(np.arange(N), np.arange(C), indexing="ij")
    # one iteration per window row
    for y in range(out_h):
        # one iteration per window column
        for z in range(out_w):
            # top-left corner of this window
            h0, w0 = y * stride, z * stride
            # (N, C, pool_h*pool_w): the window flattened row-major, so argmax order = tie order
            win = x[:, :, h0:h0 + pool_h, w0:w0 + pool_w].reshape(N, C, -1)
            # (N, C) flat index of the FIRST maximum in each plane's window
            k = win.argmax(axis=2)
            # the winning value itself, read at k so output and gradient use the same position
            out[:, :, y, z] = np.take_along_axis(win, k[:, :, None], axis=2)[:, :, 0]
            # (n, c) pairs are distinct here, so += does not collide; overlap across windows accumulates.
            dx[n_idx, c_idx, h0 + k // pool_w, w0 + k % pool_w] += dout[:, :, y, z]
    # pooled values and the routed gradient
    return out, dx
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `out = [[4, 5], [6, 3]]` | the basic route: each `dout` lands on its window's max |
| Example 2 | `dx[1, 1] = 111`, `dx[2, 2] = 1000` | overlap adds; a tie goes to the first position |
| random 2x2 stride 2 | `(2, 3, 6, 6)` input | the standard non-overlapping layer over several planes |
| overlap 3x3 stride 1 | `(2, 2, 5, 5)` input | heavy overlap with distinct values |
| ties everywhere | integer inputs in `0..3`, 3×3 stride 2 | many ties, plus overlap on one row and column |
| ties with overlap | integer inputs, 2×3 window, stride 1 | ties and overlap together |
| constant input | `dx` top-left 3×3 block equals `dout` | every window ties; each picks its top-left |
| stride leftover | `H = 7`, `W = 8`, stride 3 | uncovered pixels get 0 |
| global pool | window equals the whole `4 × 5` plane | `out_h = out_w = 1` |
| 1x1 window | stride 2 | `out` subsamples `x`; only every other pixel gets gradient |

## 10. Complexity

Each window looks at $p_h p_w$ values for each of $NC$ planes, so time is $O(NC\, \text{out\_h}\, \text{out\_w}\, p_h p_w)$. With non-overlapping windows that's $O(NCHW)$: one look at every pixel. Memory is $O(NCHW)$ for `dx`. The Python loop runs `out_h · out_w` times, which is fine at these sizes; production code instead uses a strided view or a fused kernel.

Frameworks save the argmax indices in the forward pass (PyTorch's `return_indices=True`), so the backward pass is a pure scatter. That costs one integer per output, far less than keeping the input. Max pooling has largely been replaced by strided convolutions in modern architectures, but it survives in many CNNs and in the global max pool at the end of some.

## 11. If you got Wrong Answer

- **Example 2's `dx` has `101` at `(1, 1)` and `10` at `(1, 2)`.** On the tie, you kept the last maximum, typically with `if v >= best` (`wrong_last_max.py`). It also fails "constant input": every window picks its bottom-right pixel.
- **Example 2's `dx[1, 1]` is `100` instead of `111`.** You assigned with `=` instead of adding (`wrong_overwrite.py`). Each new window overwrote the last. "constant input" still passes, because there every pixel wins at most one window.
- **Example 2's `dx` has `111` at `(1, 1)` and an extra `10` at `(1, 2)`.** You sent the gradient to every tied maximum with `(win == max) * dout` (`wrong_ties_to_all.py`). Check: `dx.sum()` no longer equals `dout.sum()`.
- **An `IndexError: shape mismatch`, or `dx` filled only on the planes where `n == c`.** Your fancy index used `np.arange(N)` and `np.arange(C)` directly instead of the `(N, C)` meshgrid. With `N != C` the index arrays can't broadcast; with `N == C` they pair up as `(0, 0), (1, 1), ...` and skip every other plane.

## 12. Follow-ups an interviewer might ask

- *What's average pooling's backward pass?* Every pixel in a window gets `dout / (pool_h * pool_w)`, also added across overlapping windows. No tie rule needed.
- *How would you vectorize across window positions too?* Build all windows with `sliding_window_view` or im2col (problem 42), take one `argmax`, and scatter with `np.add.at`, which accumulates duplicate indices. A plain fancy `+=` would drop the overlaps.
- *Why does max pooling give some translation invariance?* A feature that shifts by a pixel within a window doesn't change the window's max.
- *How do you check the gradient numerically?* Finite differences work if no window has a tie, because the max isn't differentiable at ties (problem 46, numerical-gradient-check).
- *How does this compare with conv backward?* Both scatter gradients back through windows and add across overlaps. Convolution sends `dout · w` to every pixel of the window; max pooling sends all of `dout` to one (problem 44, conv2d-backward).
