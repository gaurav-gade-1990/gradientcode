## Approach

Adam combines **momentum**, an exponential moving average of the gradient $m$, with **RMSProp-style scaling**, an exponential moving average of the squared gradient $v$. Each parameter effectively gets its own step size.

```python
m = beta1 * m + (1 - beta1) * grad
v = beta2 * v + (1 - beta2) * grad * grad
m_hat = m / (1 - beta1 ** t)
v_hat = v / (1 - beta2 ** t)
param = param - lr * m_hat / (np.sqrt(v_hat) + eps)
```

### Why bias correction?

$m_0 = v_0 = 0$, so the early averages are pulled toward zero. With $\beta_2 = 0.999$, the first step gives $v_1 = 0.001\,g^2$. Dividing by $1 - \beta_2^1 = 0.001$ recovers $g^2$. Without the correction, the first steps are far too large or too small. The two moments are biased by different amounts.

### Where does `eps` go?

The paper puts it **outside** the square root: $\sqrt{\hat v} + \epsilon$. PyTorch and the original paper agree on this. When gradients are tiny, putting it inside changes the answer.

## Complexity

- **Time:** $O(n)$ per step for $n$ parameters.
- **Space:** $O(n)$ for the two moment buffers, which is 2× the parameter memory. That's why optimizer state dominates memory in LLM training.
