## Approach

Momentum keeps a running sum of past gradients, decayed by $\mu$ each step. Directions where the gradient points the same way every step build up speed. Directions where it flips sign cancel out.

$$
b_t = \mu\, b_{t-1} + g_t, \qquad \theta_t = \theta_{t-1} - \eta\, b_t
$$

```python
def sgd_momentum_step(param, grad, buf, lr=0.01, momentum=0.9, weight_decay=0.0):
    g = grad + weight_decay * param
    buf = momentum * buf + g
    param = param - lr * buf
    return param, buf
```

With a constant gradient the buffer settles at $g / (1 - \mu)$, so $\mu = 0.9$ gives up to a 10x larger effective step.

### PyTorch vs CS231n

The CS231n form folds the learning rate into the buffer: $v = \mu v - \eta g$, $\theta \mathrel{+}= v$. With a constant `lr` it produces the same parameters, since $v = -\eta b$. They differ once `lr` changes during training. PyTorch's buffer reacts to a new `lr` right away, while the CS231n buffer still carries the old one.

## Common mistakes

- **An EMA buffer.** Writing $\mu b + (1-\mu) g$ copies Adam's first moment. It shrinks every step by $1 - \mu$.
- **Weight decay outside the buffer.** In `torch.optim.SGD` the decay term is added to the gradient, so momentum accumulates it too.
- **Returning the CS231n buffer.** The parameters match, but the state you carry to the next step does not.

## Complexity

- **Time:** $O(n)$ per step for $n$ parameters.
- **Space:** $O(n)$ for one buffer.
