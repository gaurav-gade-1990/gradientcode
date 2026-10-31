Implement one step of **SGD with momentum**, exactly as PyTorch's `torch.optim.SGD` does it (with `dampening=0` and `nesterov=False`).

You get the parameters `param`, their gradient `grad`, and the momentum buffer `buf`. On the first step `buf` is all zeros. Compute:

$$
\begin{aligned}
g &= \nabla_\theta + \lambda\, \theta_{t-1} \\
b_t &= \mu\, b_{t-1} + g \\
\theta_t &= \theta_{t-1} - \eta\, b_t
\end{aligned}
$$

where $\eta$ is `lr`, $\mu$ is `momentum` and $\lambda$ is `weight_decay`. Weight decay is plain L2: it is added to the gradient before the buffer update, so it also feeds the buffer.

This is PyTorch's convention. The buffer holds a running sum of gradients and the learning rate is applied outside it. The CS231n form $v = \mu v - \eta g,\ \theta \mathrel{+}= v$ moves the parameters the same way when `lr` is constant, but it stores a different buffer. Return the PyTorch buffer.

Return a tuple `(new_param, new_buf)`. Don't modify the inputs in place.

**Constraints**

- `param`, `grad` and `buf` are float arrays of the same shape
- `lr > 0`, `0 <= momentum < 1`, `weight_decay >= 0`
