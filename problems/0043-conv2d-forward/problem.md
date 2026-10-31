Implement the forward pass of a **2-D convolution layer** in NCHW layout.

- `x` has shape `(N, C, H, W)`: a batch of `N` images with `C` channels.
- `w` has shape `(F, C, kh, kw)`: `F` filters, each spanning all `C` input channels.
- `b` has shape `(F,)`: one bias per filter.

Zero-pad `x` by `pad` on both sides of `H` and `W` to get `xp`. The output has shape `(N, F, out_h, out_w)` with

$$
\text{out\_h} = \left\lfloor \frac{H + 2\,\text{pad} - kh}{\text{stride}} \right\rfloor + 1, \qquad
\text{out\_w} = \left\lfloor \frac{W + 2\,\text{pad} - kw}{\text{stride}} \right\rfloor + 1
$$

and entries

$$
\text{out}[n, f, y, z] = b_f + \sum_{c=0}^{C-1} \sum_{i=0}^{kh-1} \sum_{j=0}^{kw-1} w[f, c, i, j]\; \text{xp}[n, c,\, y \cdot \text{stride} + i,\, z \cdot \text{stride} + j]
$$

This is cross-correlation, as in every deep-learning framework. Do **not** flip the kernel. Rows or columns of `xp` that no full window reaches are ignored.

**Constraints**

- `1 <= N, C, F <= 8`, `1 <= H, W <= 16`
- `1 <= kh <= H + 2*pad`, `1 <= kw <= W + 2*pad`, `1 <= stride <= 3`, `0 <= pad <= 2`
