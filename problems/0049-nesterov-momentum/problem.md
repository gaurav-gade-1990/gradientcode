Implement one step of **SGD with Nesterov momentum**, exactly as PyTorch's `torch.optim.SGD(..., nesterov=True)` does it (with `dampening=0`).

You get the parameters `param`, their gradient `grad` at `param`, and the momentum buffer `buf`. On the first step `buf` is all zeros. Compute:

$$
\begin{aligned}
g &= \nabla_\theta + \lambda\, \theta_{t-1} \\
b_t &= \mu\, b_{t-1} + g \\
\theta_t &= \theta_{t-1} - \eta\, \bigl(g + \mu\, b_t\bigr)
\end{aligned}
$$

where $\eta$ is `lr`, $\mu$ is `momentum` and $\lambda$ is `weight_decay` (plain L2, added to the gradient).

The buffer update is the same as classical momentum. Only the step differs. Classical momentum steps along $b_t$, while Nesterov steps along $g + \mu b_t$, which uses the **updated** buffer. This is the reformulation from Sutskever et al. (2013) that evaluates the gradient at the current parameters instead of at a look-ahead point.

Return a tuple `(new_param, new_buf)`. Don't modify the inputs in place.

**Constraints**

- `param`, `grad` and `buf` are float arrays of the same shape
- `lr > 0`, `0 <= momentum < 1`, `weight_decay >= 0`
