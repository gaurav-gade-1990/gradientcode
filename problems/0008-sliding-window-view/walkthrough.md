## 1. What the problem is really asking

You have a 1-D signal (audio samples, a sensor reading, a token sequence) and you want every chunk of `window` consecutive samples, starting every `stride` samples. Each chunk becomes a row, so the result is a 2-D matrix you can feed to a model, average, or multiply by a filter.

Under the story this is two small problems:

1. **Count the windows** with an exact floor formula, including the edge cases where the last window ends exactly at the end, or none fit.
2. **Gather all of them without a loop** by building a matrix of indices with broadcasting and indexing `x` with it once.

It's the 1-D version of `im2col` (problem 42), the trick that turns a convolution into a single matrix product. The judge compares your array **exactly** (`rtol=0`, `atol=0`) and checks the shape, so an off-by-one in the count is a shape mismatch.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `x` | 1-D int or float array, length `0 <= n <= 10^5` | the signal |
| `window` | int, `1 <= w <= 1000` | the length of each row |
| `stride` | int, `1 <= s <= 1000` | the step between window starts |
| return | shape `(num_windows, window)`, same dtype as `x` | row `k` is `x[k*s : k*s + w]` |

Details that are easy to miss:

- **Full windows only.** A window must satisfy `start + window <= n`. A window ending exactly at `n` is valid ("window equals length", "exact fit").
- **Windows can overlap** (`stride < window`), tile (`stride == window`) or skip samples (`stride > window`).
- **No windows means shape `(0, window)`**, not `(0,)`. That happens when `n < window` (Example 3) or `n = 0` ("empty signal").
- **The result must be a fresh array**, not a writable view into `x`. Fancy indexing always copies, so the index-matrix approach satisfies this automatically.

## 3. The math

Window $k$ (for $k = 0, 1, \dots$) starts at $k s$ and holds

$$
W_{k,t} = x[\,k s + t\,], \qquad 0 \le t < w .
$$

**Counting the windows.** Window $k$ is full when its last index is inside the signal: $k s + w - 1 \le n - 1$, that is, $k s \le n - w$. If $n < w$ the right side is negative and no $k \ge 0$ works. Otherwise the largest valid $k$ is $\lfloor (n - w)/s \rfloor$, and counting from $k = 0$ gives

$$
\text{num} = \left\lfloor \frac{n - w}{s} \right\rfloor + 1 \qquad (n \ge w).
$$

Check it on Example 2 ($n = 10$, $w = 4$, $s = 3$): $\lfloor 6/3 \rfloor + 1 = 3$ windows, starting at 0, 3, 6. A fourth at 9 would need indices 9 to 12.

**The index matrix.** Define $I \in \mathbb{Z}^{\text{num} \times w}$ with $I_{k,t} = k s + t$. That's an outer **sum** of a column and a row:

$$
I = \underbrace{\begin{bmatrix} 0 \\ s \\ 2s \\ \vdots \end{bmatrix}}_{(\text{num},\,1)} + \underbrace{\begin{bmatrix} 0 & 1 & \cdots & w-1 \end{bmatrix}}_{(1,\,w)},
\qquad W = x[I].
$$

Indexing a 1-D array with an integer matrix returns an array of the **index matrix's shape**, each entry replaced by `x` at that index.

**The gradient: gather forward, scatter-add backward.** If a loss $L$ depends on $W$, how does it depend on $x$? Each $x_j$ appears in every window position $(k, t)$ with $ks + t = j$. By the chain rule, the contributions add:

$$
\frac{\partial L}{\partial x_j} = \sum_{(k,t)\,:\,ks + t = j} \frac{\partial L}{\partial W_{k,t}} .
$$

With overlapping windows (`stride < window`) one sample feeds several rows, so its gradient is a sum. In NumPy that's `np.add.at(dx, I, dW)`. A plain `dx[I] += dW` is wrong, because repeated indices in a fancy assignment are written once, not accumulated. This is exactly the backward pass of `im2col` in problem 44 (conv2d-backward).

## 4. Trace an example by hand

**Example 2:** `x = arange(10)`, `window = 4`, `stride = 3`.

```python
n = 10
num = (10 - 4) // 3 + 1                          # 3
starts = np.arange(3)[:, None] * 3               # [[0], [3], [6]]             (3, 1)
offsets = np.arange(4)[None, :]                  # [[0, 1, 2, 3]]              (1, 4)
idx = starts + offsets                           # (3, 1) + (1, 4) -> (3, 4)
# [[0, 1, 2, 3],
#  [3, 4, 5, 6],
#  [6, 7, 8, 9]]
x[idx]                                           # same values here, since x[i] == i   (3, 4)
```

Samples 3 and 6 each appear in two windows: that's the overlap.

**"one leftover sample":** `n = 12`, `w = 3`, `s = 4`. `num = 9 // 4 + 1 = 3`, starts 0, 4, 8. The last full window is `[8, 9, 10]`. A fourth window would start at 12, past the end, so sample 11 is the one leftover and is dropped with no padding. Samples 3 and 7 are skipped too, because `stride > window`.

**Example 3:** `n = 3`, `w = 5`. `n < w`, so the answer is an empty `(0, 5)` array. Note that the formula alone would give `(3 - 5) // 1 + 1 = -1`. Python's `//` floors toward minus infinity, so for any `n < w` the count is 0 or negative, and `np.arange` of a negative number is empty. The reference guards explicitly anyway, which is clearer than relying on that.

## 5. Key idea: why a reshape can't do this

A tempting shortcut is `x[:num * w].reshape(num, w)`. A reshape only re-reads contiguous memory in order, so row `k` is always `x[k*w : (k+1)*w]`. That matches the definition only when `stride == window` ("exact fit"). With overlap, sample 3 must appear in two rows, and a reshape never duplicates anything. With `stride > window`, samples must be skipped, and a reshape never skips. The index matrix handles all three because each entry says exactly which sample to read.

The zero-copy alternative is `np.lib.stride_tricks.sliding_window_view(x, w)[::s]`. It changes the array's **strides** rather than copying: on an int64 `x`, its strides are `(24, 8)` bytes for `s = 3`, meaning "next row is 3 samples later, next column is 1 sample later". It's read-only by default and shares memory with `x`. That's ideal for large signals; `.copy()` it if you need to own the result.

## 6. Plan before you code

```
n = len(x)
if n < window: return empty array of shape (0, window), dtype of x
num = (n - window) // stride + 1
idx = (starts as a column) + (offsets as a row)     # (num, window)
return x[idx]                                        # fancy indexing copies
```

| approach | correct for | fails on |
|---|---|---|
| index matrix | every case | nothing |
| `range(0, n - w, s)` starts | cases where the last start isn't exactly `n - w` | "window equals length", "exact fit", Example 1 |
| count `(n - w + 1) // s` | `stride = 1` and a few lucky cases | Example 2, "exact fit" |
| reshape into chunks | `stride == window` | any overlap or skip |

## 7. Build it one piece at a time

**Step 1: handle "no windows".**

```python
n = x.shape[0]
if n < window:
    return np.zeros((0, window), dtype=x.dtype)    # (0, w), keeps the dtype
```

Passing `dtype=x.dtype` keeps integer inputs integer, as the problem asks.

**Step 2: count.**

```python
num = (n - window) // stride + 1                   # n >= window here, so num >= 1
```

**Step 3: build the index matrix and gather.**

```python
idx = np.arange(num)[:, None] * stride + np.arange(window)[None, :]   # (num, 1) + (1, w) -> (num, w)
return x[idx]                                                         # (num, w), a new array
```

`[:, None]` makes the starts a column and `[None, :]` makes the offsets a row; broadcasting fills the grid. The largest index is `(num - 1) * stride + window - 1`, which the count formula guarantees is at most `n - 1`, so there's no out-of-bounds read.

## 8. Full solution

```python
# NumPy gives arange, broadcasting and fancy (integer-array) indexing
import numpy as np


# x: (n,) signal; returns (num_windows, window) with row k = x[k*stride : k*stride + window]
def sliding_windows(x: np.ndarray, window: int, stride: int) -> np.ndarray:
    # signal length, used for the count and the "no windows" check
    n = x.shape[0]
    # a signal shorter than the window has no full window
    if n < window:
        # empty but still 2-D, (0, window), and the same dtype as the input
        return np.zeros((0, window), dtype=x.dtype)
    # window k fits when k*stride + window <= n, so k runs 0 .. (n - window) // stride
    num = (n - window) // stride + 1
    # column of starts (num, 1) plus row of offsets (1, window) -> every index, (num, window)
    idx = np.arange(num)[:, None] * stride + np.arange(window)[None, :]
    # gather all windows at once; fancy indexing copies, so the caller can't write into x
    return x[idx]
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | 4 rows, `[1, 2, 3]` to `[4, 5, 6]` | overlap with `stride = 1` |
| Example 2 | `[[0..3], [3..6], [6..9]]` | the floor in the count; the window at 9 is dropped |
| Example 3 | shape `(0, 5)` | `n < window` |
| empty signal | shape `(0, 2)` | `n = 0` |
| window equals length | `[[3, 1, 4, 1, 5]]` | exactly one window, ending at `n` |
| exact fit | `[[0, 10, 20, 30], [40, ...], [80, 90, 100, 110]]` | `stride == window`; the last window ends at `n` |
| stride larger than window | `[[0, 1], [5, 6], [10, 11], [15, 16]]` | gaps between windows |
| one leftover sample | `[[0, 1, 2], [4, 5, 6], [8, 9, 10]]` | `stride > window`, and the trailing sample 11 is dropped rather than padded |
| window 1 | `[[7], [9]]` | `w = 1`: picks every other sample |
| float signal, long signal | shapes `(8, 8)` and `(92, 64)` | floats, and a larger count |

## 10. Complexity

- **Time:** $O(\text{num} \cdot w)$ to build the index matrix and copy the windows.
- **Memory:** $O(\text{num} \cdot w)$ for the output and the same again for the index matrix.

The output is about $w / s$ times bigger than the input. With 50% overlap that doubles memory; with `stride = 1` and `w = 1000`, a 100k-sample signal becomes 100M entries. That's why audio pipelines (spectrograms) and convolution libraries use stride tricks or compute windows on the fly instead of materializing them. `sliding_window_view` costs $O(1)$ extra memory.

## 11. If you got Wrong Answer

- **One row too few on Example 1, "window equals length" and "exact fit".** Your starts came from `range(0, n - window, stride)` (`wrong_off_by_one.py`). The stop is exclusive, so a start of exactly `n - window` is dropped. Use `n - window + 1`. It passes "stride larger than window" and "long signal", where the last start isn't `n - window`.
- **Shape `(2, 4)` instead of `(3, 4)` on Example 2.** Your count was `(n - window + 1) // stride` (`wrong_count.py`). It equals the right formula only when `stride = 1` or by luck ("window 1").
- **"cannot reshape array of size 6 into shape (4,3)", or wrong values like `expected 5, got 2`.** You reshaped contiguous chunks (`wrong_chunks.py`). It only works for `stride == window`.
- **"shape mismatch, expected (0, 5), got (0,)" on Example 3.** Your empty case returned a 1-D array. Return `np.zeros((0, window), dtype=x.dtype)`.
- **IndexError "index 10 is out of bounds".** Your count is one too high, so the last window runs past the end.

## 12. Follow-ups an interviewer might ask

- *How do you do this with zero copies?* `np.lib.stride_tricks.sliding_window_view(x, window)[::stride]`, a read-only view whose strides are `(stride * itemsize, itemsize)`. `as_strided` can build it by hand, but a wrong stride reads arbitrary memory.
- *How does this become a convolution?* Multiply the window matrix `(num, w)` by a filter `(w,)`: `W @ f` is a 1-D "valid" cross-correlation with that stride. In 2-D, the windows are image patches and this is im2col (problems 42 and 43).
- *What's the gradient with respect to `x`?* A scatter-add of the window gradients back to their positions, `np.add.at(dx, idx, dW)` (section 3; problem 44, conv2d-backward).
- *What if you want partial windows or "same" output length?* Pad `x` first, for example with `np.pad(x, (left, right))`, then use the same code. Convolution's "same" padding is exactly that.
- *Where else does this appear?* Spectrograms (windows with overlap, then an FFT per row), chunking long documents for retrieval with overlap (problem 153, recursive-chunker), and n-gram extraction.
