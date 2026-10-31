Implement **global gradient-norm clipping**, exactly as PyTorch's `torch.nn.utils.clip_grad_norm_` does it with the L2 norm.

You get `grads`, a list of float arrays (one per parameter tensor, with any shapes), and a threshold `max_norm`. Treat all the arrays as one long vector:

$$
\|g\| = \sqrt{\sum_{k} \sum_{i} g_{k,i}^2}, \qquad
c = \min\!\left(1,\ \frac{\text{max\_norm}}{\|g\| + 10^{-6}}\right)
$$

Multiply **every** array by the same coefficient $c$. If the total norm is already at or below `max_norm`, $c$ is clamped to $1$ and the gradients come back unchanged. They are never scaled up. The $10^{-6}$ is PyTorch's guard against dividing by zero.

Return a tuple `(clipped, total_norm)`:

- `clipped`: a list of arrays, in the same order and with the same shapes as `grads`
- `total_norm`: the global norm $\|g\|$ **before** clipping, as a float

Don't modify the input arrays in place.

**Constraints**

- `1 <= len(grads) <= 10`; each array has `0 <= ndim <= 3`
- `max_norm > 0`
