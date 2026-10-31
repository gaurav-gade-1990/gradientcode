## Approach: two residual sublayers, each normalized on the way in

Build the pieces, then wire them. In a pre-LN block the residual stream $x$ is never normalized itself. Each sublayer reads a normalized copy and writes its output back into the stream.

$$
a = x + \operatorname{MHA}(\operatorname{LN}_1(x)), \qquad y = a + \operatorname{MLP}(\operatorname{LN}_2(a))
$$

```python
def layer_norm(z, g, b, eps=1e-5):
    mu = z.mean(axis=-1, keepdims=True)
    var = ((z - mu) ** 2).mean(axis=-1, keepdims=True)
    return g * (z - mu) / np.sqrt(var + eps) + b

def gelu(z):
    return 0.5 * z * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (z + 0.044715 * z ** 3)))

def transformer_block(x, params, num_heads):
    p = params
    a = x + causal_mha(layer_norm(x, p["ln1_g"], p["ln1_b"]),
                       p["W_q"], p["W_k"], p["W_v"], p["W_o"], num_heads)
    m = gelu(layer_norm(a, p["ln2_g"], p["ln2_b"]) @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]
    return a + m
```

`causal_mha` is the multi-head attention from the previous problem with a lower-triangular boolean mask: split with `reshape(B, T, h, d_head).transpose(0, 2, 1, 3)`, scale by $1/\sqrt{d_{head}}$, set future scores to `-inf`, take a stable softmax, merge and project with $W_o$.

### Why pre-LN?

In the original post-LN layout, $\operatorname{LN}(x + f(x))$, every gradient passes through a LayerNorm on its way down the stack. Pre-LN leaves an identity path from the output to the input of every block, so deep stacks train without learning-rate warmup tricks. GPT-2 and later models then put one extra LayerNorm after the last block.

## Common mistakes

- **Post-LN wiring.** Normalizing after the residual add is the 2017 layout, not the one specified.
- **Adding the residual to the normalized input.** `u = ln1(x); a = u + attn(u)` throws away the scale of the residual stream.
- **No causal mask.** Every token can then see the future.
- **Exact GELU.** $\tfrac{1}{2}z(1 + \operatorname{erf}(z/\sqrt 2))$ differs from the tanh form by up to about $10^{-3}$. Use the form you're given.
- **Unbiased variance.** LayerNorm divides by $d$, not $d - 1$.

## Complexity

- **Time:** $O(B T (4d^2 + 2 d\,d_{ff}))$ for the projections and the MLP, plus $O(B T^2 d)$ for attention.
- **Space:** $O(B h T^2)$ for the attention scores, $O(B T d_{ff})$ for the MLP hidden layer.
