## Approach

RMSProp keeps Adagrad's per-parameter scaling but forgets old gradients. The running **sum** of squares becomes an exponential moving **average**, so the step size can recover after a burst of large gradients. With $\alpha = 0.99$ the average covers roughly the last 100 steps.

$$
s_t = \alpha\, s_{t-1} + (1-\alpha)\, g_t^2, \qquad \theta_t = \theta_{t-1} - \eta\, \frac{g_t}{\sqrt{s_t} + \epsilon}
$$

```python
def rmsprop_step(param, grad, square_avg, lr=0.01, alpha=0.99, eps=1e-8, weight_decay=0.0):
    g = grad + weight_decay * param
    square_avg = alpha * square_avg + (1 - alpha) * g * g
    param = param - lr * g / (np.sqrt(square_avg) + eps)
    return param, square_avg
```

Adam is RMSProp plus a momentum term plus bias correction. RMSProp has no bias correction, so its first steps are large: from $s_0 = 0$ you get $\sqrt{s_1} = \sqrt{1-\alpha}\,|g|$, a step of $\eta / \sqrt{1-\alpha} = 10\eta$ for $\alpha = 0.99$.

## Common mistakes

- **Swapping $\alpha$.** $\alpha$ is the weight on the old average. Putting it on $g^2$ makes the average forget almost everything.
- **`eps` inside the root.** PyTorch adds it after the square root.
- **Adding bias correction.** That's Adam. `torch.optim.RMSprop` doesn't correct.

## Complexity

- **Time:** $O(n)$ per step for $n$ parameters.
- **Space:** $O(n)$ for the squared-gradient average.
