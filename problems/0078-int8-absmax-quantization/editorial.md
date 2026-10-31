## Approach

Int8 has 255 usable codes in `[-127, 127]`. Absmax quantization maps the largest magnitude in each row to `±127` and scales everything else linearly. Per-row scales matter: one outlier channel would otherwise crush the resolution of every other row.

$$
s_i = \tfrac{\max_j |W_{ij}|}{127}, \quad q_{ij} = \operatorname{clip}(\operatorname{round}(W_{ij}/s_i), \pm 127), \quad \hat W_{ij} = q_{ij} s_i
$$

```python
absmax = np.max(np.abs(W), axis=1)
scales = np.where(absmax > 0, absmax / 127.0, 1.0)
x = W / scales[:, None]
q = np.clip(np.sign(x) * np.floor(np.abs(x) + 0.5), -127, 127).astype(np.int8)
W_hat = q.astype(np.float64) * scales[:, None]
```

The reconstruction error per element is at most $s_i / 2$. The clip is a safety net: by construction $|x| \le 127$.

## Common mistakes

- **`np.round`.** NumPy rounds halves to even (`2.5 -> 2`, `-0.5 -> -0`). The spec asks for halves away from zero.
- **`floor(x + 0.5)`.** That rounds halves up, so `-2.5 -> -2` instead of `-3`.
- **One scale for the whole tensor.** Rows with small values lose almost all their precision.
- **Zero rows.** `0 / 0` gives `nan`, and the scale itself is wrong. Give such rows scale `1`.
- **Casting before rounding.** `astype(np.int8)` truncates toward zero.

## Complexity

- **Time:** $O(nm)$: one pass for the absmax, one to quantize, one to dequantize.
- **Space:** $O(nm)$ bytes for `q`, a quarter of float32 storage, plus $O(n)$ scales.
