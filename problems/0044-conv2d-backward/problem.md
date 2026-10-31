Implement the backward pass of the **2-D convolution layer** from the forward problem.

The forward pass (NCHW layout, cross-correlation, no kernel flip) was

$$
\text{out}[n, f, y, z] = b_f + \sum_{c,\,i,\,j} w[f, c, i, j]\; \text{xp}[n, c,\, y \cdot \text{stride} + i,\, z \cdot \text{stride} + j]
$$

where `xp` is `x` zero-padded by `pad` on both sides of `H` and `W`, and

$$
\text{out\_h} = \left\lfloor \frac{H + 2\,\text{pad} - kh}{\text{stride}} \right\rfloor + 1, \qquad
\text{out\_w} = \left\lfloor \frac{W + 2\,\text{pad} - kw}{\text{stride}} \right\rfloor + 1
$$

You get the upstream gradient `dout` of shape `(N, F, out_h, out_w)`, the input `x` of shape `(N, C, H, W)`, the weights `w` of shape `(F, C, kh, kw)`, and the same `stride` and `pad`. Compute

$$
dx = \frac{\partial L}{\partial x}, \qquad dw = \frac{\partial L}{\partial w}, \qquad db = \frac{\partial L}{\partial b}
$$

Return a tuple `(dx, dw, db)` with shapes `(N, C, H, W)`, `(F, C, kh, kw)` and `(F,)`.

`dx` is the gradient with respect to the **unpadded** input. Pixels that no window covers, because the stride doesn't divide evenly, get gradient `0`.

**Constraints**

- `1 <= N, C, F <= 6`, `1 <= H, W <= 12`
- `1 <= kh <= H + 2*pad`, `1 <= kw <= W + 2*pad`, `1 <= stride <= 3`, `0 <= pad <= 2`
