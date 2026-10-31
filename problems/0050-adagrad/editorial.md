## Approach

Adagrad gives every parameter its own learning rate. It divides the step by the root of the **total** squared gradient that parameter has seen. Parameters with large or frequent gradients slow down, and rarely updated ones (think sparse embedding rows) keep a large step.

$$
s_t = s_{t-1} + g_t^2, \qquad \theta_t = \theta_{t-1} - \eta\, \frac{g_t}{\sqrt{s_t} + \epsilon}
$$

```python
def adagrad_step(param, grad, state_sum, lr=0.01, eps=1e-10, weight_decay=0.0):
    g = grad + weight_decay * param
    state_sum = state_sum + g * g
    param = param - lr * g / (np.sqrt(state_sum) + eps)
    return param, state_sum
```

On the first step $\sqrt{s_1} = |g|$, so every parameter moves by $\eta$ against its gradient's sign, whatever the gradient's size.

The weakness is that $s_t$ only grows. The effective learning rate decays like $1/\sqrt{t}$ and training can stall. RMSProp fixes that by replacing the sum with an exponential moving average.

## Common mistakes

- **Stale accumulator.** Add $g^2$ before dividing. If you divide by the old sum, the first step is $g / \epsilon$, which is enormous.
- **`eps` inside the root.** PyTorch uses $\sqrt{s} + \epsilon$. With small gradients and a larger `eps`, $\sqrt{s + \epsilon}$ gives a very different step.
- **Weight decay only in the step.** The decayed gradient is what gets squared and accumulated.

## Complexity

- **Time:** $O(n)$ per step for $n$ parameters.
- **Space:** $O(n)$ for the accumulator.
