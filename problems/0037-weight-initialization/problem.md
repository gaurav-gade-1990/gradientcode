Initialize the weights of a dense layer with **Xavier (Glorot) uniform** and **He (Kaiming) normal** initialization.

The weight matrix has shape `(fan_in, fan_out)`, so the layer computes `x @ W`. The randomness is passed in so the answer is deterministic:

- `u` has shape `(fan_in, fan_out)` with entries drawn from $U[0, 1)$.
- `z` has shape `(fan_in, fan_out)` with entries drawn from $\mathcal{N}(0, 1)$.

**Xavier uniform** draws from $U[-a, a]$ with

$$
a = \sqrt{\frac{6}{\text{fan\_in} + \text{fan\_out}}}
$$

Turn `u` into such a draw with $W = (2u - 1)\,a$.

**He normal** (for ReLU layers, fan-in mode) draws from $\mathcal{N}(0, \sigma^2)$ with

$$
\sigma = \sqrt{\frac{2}{\text{fan\_in}}}
$$

Turn `z` into such a draw with $W = \sigma z$.

Return a dict with four keys:

- `"xavier_limit"`: the float $a$
- `"xavier"`: the Xavier weight matrix
- `"he_std"`: the float $\sigma$
- `"he"`: the He weight matrix

**Constraints**

- `1 <= fan_in, fan_out <= 512`
- `u` and `z` are float arrays of shape `(fan_in, fan_out)`, with `0 <= u < 1`
