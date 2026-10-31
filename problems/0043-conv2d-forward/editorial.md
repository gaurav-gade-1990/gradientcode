## Approach

The definition is a 7-deep loop: batch, filter, two output coordinates, channel, two kernel coordinates. Vectorize everything except the $kh \cdot kw$ kernel offsets.

For a fixed offset $(i, j)$, the input pixel under kernel cell $(i, j)$ for every window in every image is one strided slice:

$$
\text{win}_{ij} = \text{xp}[:, :,\; i : i + s\cdot\text{out\_h} : s,\; j : j + s\cdot\text{out\_w} : s] \quad (N, C, \text{out\_h}, \text{out\_w})
$$

Its contribution to the output is a contraction over channels with `w[:, :, i, j]`, which has shape `(F, C)`. Summing over all offsets and adding the bias gives the layer:

```python
xp = np.pad(x, ((0, 0), (0, 0), (pad, pad), (pad, pad)))
out = np.zeros((N, F, out_h, out_w))
for i in range(kh):
    for j in range(kw):
        win = xp[:, :, i:i + stride*out_h:stride, j:j + stride*out_w:stride]
        out += np.einsum("nchw,fc->nfhw", win, w[:, :, i, j])
out += b[None, :, None, None]
```

The im2col route is equivalent. Build `cols` of shape `(C*kh*kw, N*out_h*out_w)` and compute `w.reshape(F, -1) @ cols`. That is one big GEMM, which is how cuDNN-era libraries did it, but it costs $kh \cdot kw$ times the input memory.

## Common mistakes

- **Flipping the kernel.** Signal-processing convolution flips it. Deep-learning layers don't, and a learned kernel doesn't care, but the output for a given `w` changes.
- **Rounding the output size up.** With stride 2, a 6-pixel input and a 3-pixel kernel gives $\lfloor 3/2 \rfloor + 1 = 2$ outputs. The partial window at the edge is dropped, not padded.
- **Collapsing the channel weights.** Every filter has its own weight for every input channel, `w[f, c, i, j]`. Reusing one channel's weights for all of them loses the channel mixing.

## Complexity

- **Time:** $O(N F C \cdot kh\, kw \cdot \text{out\_h}\, \text{out\_w})$.
- **Space:** $O(N F\, \text{out\_h}\, \text{out\_w})$ for the output plus the padded input. The im2col version adds $O(C\, kh\, kw \cdot N\, \text{out\_h}\, \text{out\_w})$.
