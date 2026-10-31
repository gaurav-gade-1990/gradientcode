## Approach

**Forward.** Loop over the `out_h × out_w` window positions and vectorize over `N` and `C`. Flatten each window to length `pool_h * pool_w` and take `argmax`. NumPy's `argmax` returns the first maximum in row-major order, which is the tie rule here.

**Backward.** $\max$ has gradient $1$ for the winning input and $0$ for the others, so each window passes its whole `dout` to one pixel. Convert the flat index `k` back to window coordinates `(k // pool_w, k % pool_w)` and scatter:

```python
for y in range(out_h):
    for z in range(out_w):
        h0, w0 = y * stride, z * stride
        win = x[:, :, h0:h0 + pool_h, w0:w0 + pool_w].reshape(N, C, -1)
        k = win.argmax(axis=2)
        out[:, :, y, z] = np.take_along_axis(win, k[..., None], axis=2)[..., 0]
        dx[n_idx, c_idx, h0 + k // pool_w, w0 + k % pool_w] += dout[:, :, y, z]
```

`n_idx` and `c_idx` come from `np.meshgrid(np.arange(N), np.arange(C), indexing="ij")`. Within a single window position, every `(n, c)` pair is distinct, so fancy-indexed `+=` never hits the same element twice in one statement. Across window positions it does, and that's what the `+=` is for.

Frameworks usually save the argmax indices in the forward pass so the backward pass doesn't recompute them. Here both happen in one loop.

## Common mistakes

- **Sending the gradient to every tied maximum.** `(win == max) * dout` duplicates the gradient on ties. The sum of `dx` then no longer equals the sum of `dout`.
- **Assigning instead of adding.** With overlapping windows, a pixel that wins two windows must collect both gradients.
- **Keeping the last maximum.** A loop with `if v >= best` picks the last tied position, not the first.

## Complexity

- **Time:** $O(N C \cdot \text{out\_h}\, \text{out\_w} \cdot \text{pool\_h}\, \text{pool\_w})$.
- **Space:** $O(N C H W)$ for `dx`.
