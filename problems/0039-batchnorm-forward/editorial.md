## Approach

Batch norm standardizes each feature with statistics from the current mini-batch, then lets the network undo it with a learned scale $\gamma$ and shift $\beta$. At test time there may be a single example, so the layer keeps running averages of the batch statistics and uses those instead.

$$
\hat x = \frac{x - \mu_B}{\sqrt{\sigma_B^2 + \epsilon}}, \qquad \text{out} = \gamma \hat x + \beta
$$

```python
if train:
    mu, var = x.mean(axis=0), x.var(axis=0)
    new_mean = momentum * running_mean + (1 - momentum) * mu
    new_var = momentum * running_var + (1 - momentum) * var
else:
    mu, var = running_mean, running_var
    new_mean, new_var = running_mean.copy(), running_var.copy()
out = gamma * (x - mu) / np.sqrt(var + eps) + beta
```

`np.var` divides by $N$ by default, which is the biased estimate.

### Two momentum conventions

This problem (like CS231n) uses `new = momentum * old + (1 - momentum) * batch`, with `momentum = 0.9`. PyTorch uses `new = (1 - momentum) * old + momentum * batch` with `momentum = 0.1`. The two are the same average with the parameter flipped. Read which one an API uses before porting weights.

## Common mistakes

- **Swapping the momentum weights.** The running stats then track the latest batch almost exactly.
- **Unbiased variance (`ddof=1`).** It changes the normalization. On a batch of 2 the difference is a factor of 2.
- **Batch statistics at eval time.** Predictions then depend on what else is in the batch, and a batch of one gives a zero variance.
- **`eps` outside the square root.** When a feature's variance is tiny, $\sqrt{\sigma^2} + \epsilon$ and $\sqrt{\sigma^2 + \epsilon}$ differ a lot.

## Complexity

- **Time:** $O(ND)$.
- **Space:** $O(ND)$ for the output, $O(D)$ for the statistics.
