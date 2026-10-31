## Approach: an index matrix

First count the windows. A window starting at $s$ is full when $s + w \le n$. The starts are multiples of the stride, so the last valid one is $\lfloor (n - w)/\text{stride} \rfloor \cdot \text{stride}$, and

$$
\text{num} = \left\lfloor \frac{n - w}{\text{stride}} \right\rfloor + 1 \quad (n \ge w)
$$

Then build every index at once. Row $k$ of the index matrix is `k * stride + [0, 1, ..., w-1]`. That is a column of starts plus a row of offsets, which broadcasts to `(num, w)`. Indexing `x` with it gathers all windows in one shot and returns a copy.

```python
def sliding_windows(x, window, stride):
    n = x.shape[0]
    if n < window:
        return np.zeros((0, window), dtype=x.dtype)
    num = (n - window) // stride + 1
    idx = np.arange(num)[:, None] * stride + np.arange(window)[None, :]
    return x[idx]
```

### The zero-copy alternative

`np.lib.stride_tricks.sliding_window_view(x, window)[::stride]` gives the same windows as a read-only view that shares memory with `x`, with no copy at all. Append `.copy()` if the caller needs to own the result. `as_strided` can do the same, but a wrong shape or stride reads arbitrary memory.

## Common mistakes

- **`range(0, n - window, stride)`.** The stop is exclusive, so a window that ends exactly at `n` is dropped.
- **Wrong count formula.** `(n - window + 1) // stride` matches when `stride = 1` and is off otherwise.
- **Reshaping into chunks.** `x[:num * window].reshape(num, window)` only works when `stride == window`. Overlapping windows share samples, so they can't come from a reshape of contiguous memory.
- **Forgetting `n < window`.** Return an empty `(0, window)` array, not a crash or a `(0,)` array.

## Complexity

- **Time:** $O(\text{num} \cdot w)$ to copy the windows.
- **Space:** $O(\text{num} \cdot w)$ for the output and the index matrix. The stride-trick view is $O(1)$ extra.
