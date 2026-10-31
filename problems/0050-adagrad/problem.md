Implement one step of the **Adagrad** optimizer, exactly as PyTorch's `torch.optim.Adagrad` does it (with `lr_decay=0`).

You get the parameters `param`, their gradient `grad`, and `state_sum`, the running sum of squared gradients. On the first step `state_sum` is all zeros. Compute:

$$
\begin{aligned}
g &= \nabla_\theta + \lambda\, \theta_{t-1} \\
s_t &= s_{t-1} + g^2 \\
\theta_t &= \theta_{t-1} - \eta\, \frac{g}{\sqrt{s_t} + \epsilon}
\end{aligned}
$$

where $\eta$ is `lr`, $\epsilon$ is `eps` and $\lambda$ is `weight_decay`. All operations are elementwise. $\epsilon$ is added **outside** the square root, and the accumulator includes the current gradient.

Return a tuple `(new_param, new_state_sum)`. Don't modify the inputs in place.

**Constraints**

- `param`, `grad` and `state_sum` are float arrays of the same shape
- `state_sum >= 0`
- `lr > 0`, `eps > 0`, `weight_decay >= 0`
