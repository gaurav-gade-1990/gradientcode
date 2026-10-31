Implement **per-row (per-channel) absmax int8 quantization** of a weight matrix, the scheme behind LLM.int8() and most int8 weight-only inference.

For each row $i$ of `W`:

$$
s_i = \frac{\max_j |W_{ij}|}{127}, \qquad
q_{ij} = \operatorname{clip}\!\left(\operatorname{round}\!\left(\frac{W_{ij}}{s_i}\right), -127, 127\right), \qquad
\hat W_{ij} = q_{ij}\, s_i
$$

Specifics:

- **Rounding is half away from zero**: `2.5 -> 3`, `-2.5 -> -3`, `0.5 -> 1`, `2.4 -> 2`. Compute $x = W_{ij} / s_i$ by dividing (not by multiplying with a reciprocal), then round.
- An **all-zero row** gets scale $s_i = 1$, so its codes are all `0`.
- The int8 range is symmetric: codes stay within `[-127, 127]`.

Return a tuple `(q, scales, W_hat)`:

- `q`: shape `(n, m)`, dtype `int8`
- `scales`: shape `(n,)`, float64
- `W_hat`: shape `(n, m)`, float64, the dequantized matrix

**Constraints**

- `W` is a 2-D float64 array with `1 <= n, m <= 256`
- `|W_ij| <= 1e3`
