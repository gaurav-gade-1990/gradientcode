## Approach

A convolution computes a dot product between the kernel and every window of the input. If you copy each window into a column, all of those dot products become one matrix product. im2col does the copying.

Loop over the $kh \cdot kw$ **kernel offsets**, not over the output positions. For a fixed offset $(i, j)$, the input value under that kernel cell, across every window, is one strided slice:

```python
xp[:, :, i : i + stride*out_h : stride, j : j + stride*out_w : stride]   # (N, C, out_h, out_w)
```

Write these into `patches[:, :, i, j]`, where `patches` has shape `(N, C, kh, kw, out_h, out_w)`. The spec wants rows ordered `(c, i, j)` and columns `(n, y, z)`, so move the axes into that order and flatten:

```python
cols = patches.transpose(1, 2, 3, 0, 4, 5).reshape(C*kh*kw, N*out_h*out_w)
```

The loop runs only $kh \cdot kw$ times, usually 9, and each iteration is a vectorized copy.

The row order matches `w.reshape(F, -1)`, so the convolution is `w.reshape(F, -1) @ cols`. That gives `(F, N*out_h*out_w)`, which reshapes to `(F, N, out_h, out_w)` and transposes to NCHW.

## Common mistakes

- **Columns ordered `(y, z, n)`.** Some well-known implementations (the CS231n `im2col_indices`) put the batch index fastest. That's a valid layout, but it isn't the one specified. Reshaping the result back to `(N, F, out_h, out_w)` then scrambles images.
- **Rows ordered `(i, j, c)`.** That's the channels-last layout. It no longer lines up with `w.reshape(F, -1)` for an `(F, C, kh, kw)` kernel.
- **Padding one side only.** `np.pad` takes `(before, after)`. `(0, 2*pad)` shifts every window by `pad` pixels.

## Complexity

- **Time:** $O(C\,kh\,kw \cdot N\,\text{out\_h}\,\text{out\_w})$, the size of the output.
- **Space:** the same. im2col duplicates each input pixel up to $kh \cdot kw$ times, which is its main cost.
