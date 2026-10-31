## Approach

Classical momentum computes the gradient at $\theta$, then moves along the accumulated velocity. Nesterov's idea is to look ahead: since you are going to move by roughly $\mu b$ anyway, evaluate the gradient at the point you are about to reach. That correction damps oscillation.

Evaluating the gradient at a shifted point is awkward in a training loop, so PyTorch uses the Sutskever et al. reformulation. Track the look-ahead point as the parameter, and the step becomes

$$
b_t = \mu\, b_{t-1} + g_t, \qquad \theta_t = \theta_{t-1} - \eta\,(g_t + \mu\, b_t)
$$

```python
def nesterov_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    g = grad + weight_decay * param
    buf = momentum * buf + g
    param = param - lr * (g + momentum * buf)
    return param, buf
```

Expanding gives $g + \mu b_t = (1 + \mu) g + \mu^2 b_{t-1}$. The current gradient gets a little more weight and the history a little less than in classical momentum ($g + \mu b_{t-1}$).

## Common mistakes

- **Stepping along the buffer.** That is classical momentum. The extra $\mu b_t$ on top of $g$ is the whole point.
- **Using the old buffer.** The look-ahead term uses $b_t$, the buffer after this step's update.
- **Dropping weight decay from the step.** In PyTorch the decayed gradient $g$ is used both in the buffer and in the step.

## Complexity

- **Time:** $O(n)$ per step for $n$ parameters.
- **Space:** $O(n)$ for one buffer, the same as classical momentum.
