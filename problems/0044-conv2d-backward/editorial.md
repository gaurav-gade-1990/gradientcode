## Approach

Write the forward pass as a sum over kernel offsets. With $s$ the stride, let

$$
\text{win}_{ij} = \text{xp}[:, :,\; i : i + s\cdot\text{out\_h} : s,\; j : j + s\cdot\text{out\_w} : s] \quad (N, C, \text{out\_h}, \text{out\_w})
$$

Then

$$
\text{out} = b + \sum_{i,j} \text{einsum}(\texttt{nchw,fc->nfhw},\; \text{win}_{ij},\; w[:, :, i, j])
$$

Each term is a plain bilinear contraction, so backprop through it is mechanical:

- $dw[:, :, i, j] = \text{einsum}(\texttt{nfhw,nchw->fc},\; dout,\; \text{win}_{ij})$
- $d\,\text{win}_{ij} = \text{einsum}(\texttt{nfhw,fc->nchw},\; dout,\; w[:, :, i, j])$, which gets **added** into the same strided slice of a padded buffer `dxp`
- $db = \sum_{n,y,z} dout$

The slices for different offsets overlap whenever the stride is smaller than the kernel, because one input pixel sits in several windows. Its gradient is the sum over all of them, so the update must be `+=`. Finally, crop the padding off: `dx = dxp[:, :, pad:pad+H, pad:pad+W]`.

```python
dxp = np.zeros_like(xp)
for i in range(kh):
    for j in range(kw):
        hs = slice(i, i + stride*out_h, stride)
        ws = slice(j, j + stride*out_w, stride)
        dw[:, :, i, j] = np.einsum("nfhw,nchw->fc", dout, xp[:, :, hs, ws])
        dxp[:, :, hs, ws] += np.einsum("nfhw,fc->nchw", dout, w[:, :, i, j])
dx = dxp[:, :, pad:pad + H, pad:pad + W]
db = dout.sum(axis=(0, 2, 3))
```

For stride 1 this is the familiar result: `dx` is a *full* convolution of `dout` with the flipped kernel, and `dw` is a cross-correlation of `x` with `dout`. The offset loop gets the same answer for any stride and padding, without reasoning about flips or dilated gradients.

The im2col view gives the same thing: `dw = dout_mat @ cols.T`, and `dcols = w_mat.T @ dout_mat` is scattered back with col2im, which also has to add.

## Common mistakes

- **`=` instead of `+=`.** Overlapping windows each contribute to the same pixel. Assigning keeps only the last kernel offset.
- **Cropping with `pad:-pad`.** When `pad = 0`, that slice is `0:0` and returns an empty array. Use `pad:pad + H`.
- **Flipping the kernel inside the offset loop.** The "flipped kernel" rule describes `dx` as a convolution over output positions. In the offset form, offset $(i, j)$ pairs with `w[:, :, i, j]` itself.
- **Averaging `db` over the batch.** The bias is shared by every output position in every image, so its gradient is a plain sum.

## Complexity

- **Time:** $O(N F C \cdot kh\, kw \cdot \text{out\_h}\, \text{out\_w})$ for each of `dx` and `dw`, the same as the forward pass.
- **Space:** $O(N C (H + 2\,\text{pad})(W + 2\,\text{pad}))$ for the padded gradient buffer.
