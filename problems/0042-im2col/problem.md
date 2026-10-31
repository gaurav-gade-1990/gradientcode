Implement **im2col**, the transform that turns a 2-D convolution into one matrix multiplication.

The input `x` is a batch of images in **NCHW** layout, shape `(N, C, H, W)`. First zero-pad `H` and `W` by `pad` on **both** sides, giving `xp`. A `kh × kw` window then slides over `xp` with step `stride`, so

$$
\text{out\_h} = \left\lfloor \frac{H + 2\,\text{pad} - kh}{\text{stride}} \right\rfloor + 1, \qquad
\text{out\_w} = \left\lfloor \frac{W + 2\,\text{pad} - kw}{\text{stride}} \right\rfloor + 1
$$

Return a matrix `cols` of shape `(C * kh * kw, N * out_h * out_w)`. Each **column** is one window position, and each **row** is one (channel, kernel offset) pair:

$$
\text{cols}\big[\,c \cdot kh \cdot kw + i \cdot kw + j,\;\; n \cdot \text{out\_h} \cdot \text{out\_w} + y \cdot \text{out\_w} + z\,\big]
= \text{xp}\big[n,\; c,\; y \cdot \text{stride} + i,\; z \cdot \text{stride} + j\big]
$$

for $0 \le c < C$, $0 \le i < kh$, $0 \le j < kw$, $0 \le n < N$, $0 \le y < \text{out\_h}$ and $0 \le z < \text{out\_w}$.

In other words, rows are ordered `(c, i, j)` and columns are ordered `(n, y, z)`, both row-major. With this layout, a weight tensor `w` of shape `(F, C, kh, kw)` gives the convolution as `w.reshape(F, -1) @ cols`.

When `H + 2*pad - kh` is not a multiple of `stride`, the last rows (or columns) of `xp` that no full window reaches are simply unused.

**Constraints**

- `1 <= N, C <= 4`, `1 <= H, W <= 12`
- `1 <= kh <= H + 2*pad`, `1 <= kw <= W + 2*pad`, `1 <= stride <= 3`, `0 <= pad <= 2`
