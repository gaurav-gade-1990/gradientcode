Implement **scaled dot-product attention** (Vaswani et al., 2017):

$$
\operatorname{Attention}(Q, K, V) = \operatorname{softmax}\left(\frac{Q K^\top}{\sqrt{d_k}} + M\right) V
$$

- `q` has shape `(..., T_q, d_k)`, `k` has shape `(..., T_k, d_k)` and `v` has shape `(..., T_k, d_v)`. The leading axes `...` (zero or more batch or head axes) are the same for all three.
- `mask` is either `None` (attend everywhere) or a **boolean** array that broadcasts to `(..., T_q, T_k)`. `True` means *keep* this query–key pair and `False` means *drop* it. A dropped pair gets weight exactly `0`.
- The softmax is over the key axis (the last one) and must be numerically stable. Scores can be as large as `1e4`.

Return a tuple `(output, weights)`:

- `output` has shape `(..., T_q, d_v)`.
- `weights` has shape `(..., T_q, T_k)`, the attention probabilities after masking. Each row sums to `1`.

**Constraints**

- `0 <= len(...) <= 2`, `1 <= T_q, T_k <= 32`, `1 <= d_k, d_v <= 16`
- Every query row keeps at least one key
