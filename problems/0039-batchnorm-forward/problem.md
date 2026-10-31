Implement the forward pass of **batch normalization** for a batch `x` of shape `(N, D)`, in both training and evaluation mode.

**Training mode** (`train=True`). Compute per-feature statistics over the batch axis, using the **biased** variance (divide by $N$):

$$
\mu_j = \frac{1}{N}\sum_i x_{ij}, \qquad \sigma^2_j = \frac{1}{N}\sum_i (x_{ij} - \mu_j)^2
$$

Normalize, then scale and shift:

$$
\hat x_{ij} = \frac{x_{ij} - \mu_j}{\sqrt{\sigma^2_j + \epsilon}}, \qquad \text{out}_{ij} = \gamma_j \hat x_{ij} + \beta_j
$$

Update the running statistics with an exponential moving average, where `momentum` weights the old value:

$$
\text{running\_mean} \leftarrow m \cdot \text{running\_mean} + (1 - m)\,\mu, \qquad
\text{running\_var} \leftarrow m \cdot \text{running\_var} + (1 - m)\,\sigma^2
$$

The running variance also uses the biased $\sigma^2$. (PyTorch writes `momentum` the other way round and uses the unbiased variance for its running estimate. Follow the formulas here.)

**Evaluation mode** (`train=False`). Normalize with `running_mean` and `running_var` in place of $\mu$ and $\sigma^2$, and return the running statistics unchanged.

Return a tuple `(out, new_running_mean, new_running_var)` with shapes `(N, D)`, `(D,)` and `(D,)`. Don't modify the inputs in place.

**Constraints**

- `x` is a float array of shape `(N, D)` with `1 <= N <= 256`, `1 <= D <= 64`
- `gamma`, `beta`, `running_mean`, `running_var` have shape `(D,)`, with `running_var >= 0`
- `0 <= momentum < 1`, `eps > 0`
