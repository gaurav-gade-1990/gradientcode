## Approach

A classic transformer MLP is `act(x W1) W2`. A **gated linear unit** adds a second up-projection and lets one branch gate the other elementwise. SwiGLU uses SiLU as the gate's activation:

$$
h = \operatorname{SiLU}(x W_1) \odot (x W_3), \qquad y = h W_2
$$

```python
def silu(z):
    return z / (1.0 + np.exp(-z))

def swiglu_ffn(x, W1, W3, W2):
    return (silu(x @ W1) * (x @ W3)) @ W2
```

`@` broadcasts over leading axes, so the same code handles `(d,)`, `(T, d)` and `(B, T, d)`.

Because there are three weight matrices instead of two, LLaMA shrinks the hidden size to about $\tfrac{2}{3} \cdot 4d$ to keep the parameter count of a standard $4d$ MLP.

## Common mistakes

- **Activating the wrong branch.** SiLU goes on `x @ W1`, not `x @ W3`. The two are not interchangeable.
- **Plain sigmoid instead of SiLU.** `sigmoid(z)` is the original GLU gate. SiLU is `z * sigmoid(z)`.
- **Activating after the product.** `SiLU(a * b)` is not `SiLU(a) * b`.

## Complexity

- **Time:** $O(N d h)$ for $N$ tokens: three matrix products.
- **Space:** $O(N h)$ for the two hidden activations.
