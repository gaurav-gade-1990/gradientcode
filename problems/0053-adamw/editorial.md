## Approach

With plain Adam, L2 regularization means adding $\lambda\theta$ to the gradient. That term then passes through $m$ and $v$ and gets divided by $\sqrt{\hat v}$. Parameters with large gradients barely get decayed, and those with small gradients get decayed hard. That isn't weight decay any more.

AdamW takes the decay out of the gradient and applies it to the weights directly:

$$
\theta' = \theta\,(1 - \eta\lambda), \qquad \theta_t = \theta' - \eta\, \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}
$$

```python
def adamw_step(param, grad, m, v, t, lr=1e-3, beta1=0.9, beta2=0.999, eps=1e-8, weight_decay=1e-2):
    param = param * (1 - lr * weight_decay)
    m = beta1 * m + (1 - beta1) * grad
    v = beta2 * v + (1 - beta2) * grad * grad
    m_hat = m / (1 - beta1 ** t)
    v_hat = v / (1 - beta2 ** t)
    param = param - lr * m_hat / (np.sqrt(v_hat) + eps)
    return param, m, v
```

Every parameter now shrinks by the same fraction $\eta\lambda$ per step, whatever its gradient history. PyTorch multiplies the decay by `lr`, so a learning-rate schedule also anneals the decay.

## Common mistakes

- **L2 in the gradient.** That's `torch.optim.Adam(weight_decay=...)`, not AdamW. The moments come out wrong too.
- **Forgetting `lr`.** `param * (1 - weight_decay)` matches the paper's notation, which uses a separate schedule multiplier. It doesn't match PyTorch, and with `weight_decay=0.01` it removes 1% of every weight per step.
- **Decaying after the step.** The decay should act on $\theta_{t-1}$. Applying it to the updated weights also shrinks the Adam step.

## Complexity

- **Time:** $O(n)$ per step for $n$ parameters.
- **Space:** $O(n)$ for the two moment buffers, the same as Adam. The decay needs no extra state.
