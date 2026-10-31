Implement **max pooling** over an NCHW batch, together with its backward pass.

`x` has shape `(N, C, H, W)`. A `pool_h × pool_w` window slides over each channel with step `stride`. There is no padding. The output has shape `(N, C, out_h, out_w)` with

$$
\text{out\_h} = \left\lfloor \frac{H - \text{pool\_h}}{\text{stride}} \right\rfloor + 1, \qquad
\text{out\_w} = \left\lfloor \frac{W - \text{pool\_w}}{\text{stride}} \right\rfloor + 1
$$

$$
\text{out}[n, c, y, z] = \max_{0 \le i < \text{pool\_h},\; 0 \le j < \text{pool\_w}} x[n, c,\, y \cdot \text{stride} + i,\, z \cdot \text{stride} + j]
$$

You also get the upstream gradient `dout`, shape `(N, C, out_h, out_w)`. In the backward pass, each window sends its **entire** `dout[n, c, y, z]` to one position: the window's maximum.

- **Ties:** if several positions share the maximum, use the first one in row-major order inside the window (smallest `i`, then smallest `j`).
- **Overlap:** when `stride` is smaller than the window, one pixel can be the chosen maximum of several windows. Its gradient is the sum of theirs.
- Every other pixel gets gradient `0`.

Return a tuple `(out, dx)` with shapes `(N, C, out_h, out_w)` and `(N, C, H, W)`.

**Constraints**

- `1 <= N, C <= 4`, `1 <= H, W <= 12`
- `1 <= pool_h <= H`, `1 <= pool_w <= W`, `1 <= stride <= 3`
