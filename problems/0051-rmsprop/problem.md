Implement one step of the **RMSProp** optimizer, exactly as PyTorch's `torch.optim.RMSprop` does it (with `momentum=0` and `centered=False`).

You get the parameters `param`, their gradient `grad`, and `square_avg`, a running average of squared gradients. On the first step `square_avg` is all zeros. Compute:

$$
\begin{aligned}
g &= \nabla_\theta + \lambda\, \theta_{t-1} \\
s_t &= \alpha\, s_{t-1} + (1 - \alpha)\, g^2 \\
\theta_t &= \theta_{t-1} - \eta\, \frac{g}{\sqrt{s_t} + \epsilon}
\end{aligned}
$$

where $\eta$ is `lr`, $\alpha$ is the smoothing constant `alpha`, $\epsilon$ is `eps` and $\lambda$ is `weight_decay`. All operations are elementwise. $\alpha$ multiplies the **old** average. $\epsilon$ is added **outside** the square root. There is no bias correction.

Return a tuple `(new_param, new_square_avg)`. Don't modify the inputs in place.

**Constraints**

- `param`, `grad` and `square_avg` are float arrays of the same shape
- `square_avg >= 0`
- `lr > 0`, `0 < alpha < 1`, `eps > 0`, `weight_decay >= 0`
