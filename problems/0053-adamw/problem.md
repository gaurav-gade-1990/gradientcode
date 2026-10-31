Implement one step of **AdamW** (Loshchilov & Hutter, 2019), exactly as PyTorch's `torch.optim.AdamW` does it (with `amsgrad=False`).

AdamW **decouples** weight decay from the gradient. The decay shrinks the parameters directly. It never enters the moment estimates, so Adam's per-parameter scaling never rescales it.

You get the parameters `param`, their gradient `grad`, the moment estimates `m` and `v`, and the step number `t`. `t` starts at `1` on the first update. Compute, in this order:

$$
\begin{aligned}
\theta' &= \theta_{t-1}\,(1 - \eta\lambda) \\
m_t &= \beta_1 m_{t-1} + (1-\beta_1)\, g \\
v_t &= \beta_2 v_{t-1} + (1-\beta_2)\, g^2 \\
\hat m_t &= \frac{m_t}{1-\beta_1^t}, \qquad \hat v_t = \frac{v_t}{1-\beta_2^t} \\
\theta_t &= \theta' - \eta\, \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}
\end{aligned}
$$

where $\eta$ is `lr`, $\lambda$ is `weight_decay` and $g$ is the raw `grad`. The decay is multiplied by the learning rate, as in PyTorch. $\epsilon$ is added outside the square root.

Return a tuple `(new_param, new_m, new_v)`. Don't modify the inputs in place.

**Constraints**

- `param`, `grad`, `m` and `v` are float arrays of the same shape
- `t >= 1`
- `0 < beta1, beta2 < 1`, `weight_decay >= 0`, `lr * weight_decay < 1`
