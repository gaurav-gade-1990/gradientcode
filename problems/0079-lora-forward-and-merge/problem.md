Implement the forward pass of a **LoRA** adapter (Hu et al., 2021) on a frozen linear layer, and the merge that folds the adapter back into the weight for inference.

The layer has a frozen weight $W \in \mathbb{R}^{d_{in} \times d_{out}}$ and two low-rank factors $A \in \mathbb{R}^{d_{in} \times r}$ and $B \in \mathbb{R}^{r \times d_{out}}$. The rank is $r$ = `A.shape[1]`.

$$
y = x W + \frac{\alpha}{r}\,(x A) B,
\qquad
W' = W + \frac{\alpha}{r}\, A B
$$

Return a tuple `(y, W_merged)`. `y` has shape `(N, d_out)` and `W_merged` has shape `(d_in, d_out)`. Don't modify `W` in place.

**Constraints**

- `x` has shape `(N, d_in)`, `1 <= N <= 64`
- `1 <= r <= min(d_in, d_out) <= 64`
- `alpha > 0` is a float
